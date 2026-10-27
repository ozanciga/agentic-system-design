from authoring import code, lesson, section, table

CHAPTER = ("Memory", "Keep useful facts across tasks, without saving mistakes or keeping what should be deleted.")

LESSONS = [

lesson("choose-memory-by-purpose", "Types of memory, and what to share", [52, 60],
    "Sort memory by purpose: **working memory** holds what the current task needs, **episodic memory** records past experiences, and **semantic memory** stores lasting facts and preferences. When several agents work together, they share checked findings through a common store with access rules, not each other's full histories.", [
    section("Three kinds of memory", """
        None of these replaces the saved task state that records which actions happened (chapter 5).
    """, table("Memory types", ["Type", "Example", "Kept for"], [
        ["Working", "Rows returned by the current database query", "This task"],
        ["Episodic", "What was tried in last month's similar outage", "As long as it stays relevant, within retention limits"],
        ["Semantic", "“This customer prefers French”; “The team names files in snake_case”", "Until changed, expired, or deleted"],
    ], "Access rules and retention limits apply to all three."), """
        Save a short finding with its source and a link to the full material, rather than a whole conversation in which nobody knows which statements were checked.
    """),
    section("Share findings, not histories", """
        Should several agents share one memory? Share **facts**, not everything. Each agent keeps its own working memory. A shared store holds accepted findings, their sources, and task decisions, with rules for who may read, add, correct, and delete each entry.

        A single scratchpad that every agent reads and writes looks simple, but it spreads one agent's mistake to all of them, mixes data that different users may not see, and invites conflicting edits.
    """),
], "Merge memory categories and sharing into a purpose-and-scope decision; checkpoint distinctions were introduced with execution state."),

lesson("gate-memory-writes", "What to save to memory", [54, 55, 58, 89, 59],
    "Save something to long-term memory only if it will be useful later, may be stored, and has been verified or confirmed by the user, and record where it came from. **Memory poisoning** is untrusted content, or a wrong guess, saved as if it were fact; the save checks and the source record are the defense. When two agents edit the same entry at once, a version check stops one edit from silently erasing the other.", [
    section("Decide what to save", """
        Memory keeps mistakes as faithfully as facts, and repeats them in every future task.
    """, table("Save or not?", ["Candidate", "Save?"], [
        ["User: “Please reply in French from now on”", "Yes, as a preference the user stated"],
        ["Model guess: “Customer seems price-sensitive”", "No: an unchecked guess"],
        ["Email: “Our new bank account is IBAN …”", "No: a classic poisoning attempt. Verify through the vendor-change process."],
        ["Delivery address for one order", "Only for that order; remove it after delivery"],
    ]), code("Checks before saving", """
        candidate = extract_memory(observation)
        if not useful_for_future_tasks(candidate):  return
        require storage_rules.allow(candidate, owner)       # consent, sensitivity, tenant
        require candidate.verified or candidate.confirmed_by_user
        memory.save(candidate, owner, source, expires_at)
    """)),
    section("Record where each memory came from", """
        **Provenance** means where information came from and how it was checked. Store enough to answer "should we still believe this?"
    """, code("A memory entry", """
        memory = {
            id, tenant_id, owner_id, content,
            source,                       # e.g. "user message m-81" or "vendor portal, verified"
            created_at, verified_at, verification_status,
            expires_at, access_rules, version,
            replaces                      # the entry this one corrects, if any
        }
    """), """
        If a source later turns out to be wrong, its provenance lets you find and recheck everything built on it. Finding a memory by similar meaning says nothing about whether it is true.
    """),
    section("Two edits at the same time", """
        Two agents read version 7 of an entry, each changes it, and both save. Without a check, the second save erases the first. **Compare-and-swap** prevents this: a save succeeds only if the entry is still at the version you read.
    """, code("Catching a lost update", """
        entry  = memory.read(id, scope)
        edited = apply(entry, change)
        ok = memory.compare_and_swap(id, expected_version = entry.version,
                                     new_value = edited, new_version = entry.version + 1)
        if not ok: reload_and_resolve(id, change)     # never just retry with the old value
    """), """
        Resolve conflicts by meaning: two independent tags can be merged, but two different payment accounts can't, so escalate those. A version check only detects a conflict. It doesn't decide which value is right, and it doesn't replace the save checks.
    """),
], "Merge memory-write eligibility, incorrect memories, metadata, poisoning, and concurrent edits into one persistence contract."),

lesson("expire-and-delete-memory", "Expire and delete memories", [56, 57],
    "**Decay** lowers an old memory's ranking. **Expiry** makes it unusable. **Deletion** removes it together with every copy made from it: search index entries, embeddings, summaries, caches, and eventually backups. These are three different operations with different guarantees.", [
    section("Decay is not expiry", """
        A lower score doesn't remove an entry, and an expired entry must not come back just because it closely matches a question.
    """, table("Decay vs. expiry", ["Mechanism", "Before", "After"], [
        ["Decay", "An old outage ranks highly", "Its score drops with age; it can still appear"],
        ["Expiry", "A one-time delivery address can be used", "After delivery it is excluded by rule, or deleted"],
    ]), """
        Set retention by purpose. A language preference can stay until the user changes it. A temporary instruction ("call me on my work phone this week") should expire on its own.
    """),
    section("Deletion must reach every copy", """
        A deletion isn't finished when the main entry is gone.
    """, code("Deleting a user's memories", """
        1. check who is asking and what is covered
        2. write a tombstone(user)        # a deletion marker: stops old jobs re-adding the data
        3. delete from: main store, vector index, summaries, caches
        4. confirm each copy is gone; retry failures; report completion
        5. backups: let them expire on schedule, or re-apply tombstones when restoring
    """, "Without the tombstone, a re-indexing job or an old summary can quietly bring deleted data back.")),
], "Merge lifecycle and privacy deletion while preserving the decay-versus-deletion distinction."),
]
