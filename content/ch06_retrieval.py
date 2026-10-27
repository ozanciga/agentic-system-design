from authoring import code, lesson, section, table

CHAPTER = ("Retrieval (RAG)", "Find the right documents, respect permissions, and make sure answers match their sources.")

LESSONS = [

lesson("build-an-evidence-pipeline", "How RAG works", [42],
    "**RAG** (retrieval-augmented generation) means fetching relevant documents the user is allowed to see at request time and giving them to the model, so its answer is **grounded**: based on those sources rather than on what the model remembers from training. For an agent, retrieval is one tool among several. Facts that change by the minute, such as an order's status, should come from live systems, not from a document search.", [
    section("The steps", """
        Each step can fail on its own, and each has a lesson in this chapter:

        1. **Index:** split documents into pieces and store them in a search index with their source and permissions.
        2. **Search:** find candidate pieces, filtered to what this user may see.
        3. **Rank:** order the candidates and keep the few that fit in the model's input.
        4. **Answer:** generate a reply from those pieces, citing them.
        5. **Check:** confirm each cited piece supports its claim.

        Log the query, the sources used (with versions), and the claims made. When an answer is wrong, this tells you which step failed (see *Evaluate retrieval on its own*).
    """),
    section("Document search or live system?", """
        Choose by how fast the fact changes and how exact it must be.
    """, table("Where each fact should come from", ["Information", "Source", "Why"], [
        ["Refund policy", "Document search", "Long text that rarely changes"],
        ["Product manuals", "Document search", "Large and mostly static"],
        ["Status of order 42", "Orders system", "Changes by the minute; the system is the source of truth"],
        ["Account balance", "Live system", "Must be exact and current"],
    ])),
], "Retain a short retrieval foundation that maps the pipeline stages to the lessons that follow."),

lesson("ingest-and-chunk-documents", "Split and index documents", [43, 148],
    "Split documents into **chunks** (sections, paragraphs, clauses, or functions) that still make sense on their own, and store each chunk with its source, version, location, and who may read it. With millions of documents, the hard part is keeping the index correct as documents change, gain or lose permissions, or are deleted.", [
    section("Keep a rule with its exception", """
        A chunk that matches the question but lost its condition produces a confident wrong answer.
    """, code("A bad split and a good one", """
        ✗ chunk 1: "Refunds are available within 30 days of delivery."
          chunk 2: "Exceptions: final-sale items and opened software."

        ✓ chunk:   "Refund policy > Eligibility
                    Refunds are available within 30 days of delivery.
                    Exceptions: final-sale items and opened software."
          labels:  {doc: "refund-policy", version: "2026-09", section: "4.2",
                    readers: ["customers"], updated: "2026-09-03"}
    """, "Retrieving only chunk 1 tells a customer that opened software is refundable."), """
        Starting points, to tune by testing retrieval (chapter 7):

        - Split at headings, paragraphs, clauses, or functions, not every N characters.
        - Aim for a few hundred words per chunk, with a little overlap between neighbors.
        - Start each chunk with its document title and section, so it reads correctly alone.
    """),
    section("Design: a knowledge assistant over millions of documents", """
        This brings the whole chapter together.
    """, table("Knowledge assistant design", ["Part", "Choice"], [
        ["Indexing", "Connectors report document changes; split, embed, and index only what changed"],
        ["Index", "Keyword and vector indexes, sharded by tenant or region; approximate nearest-neighbor search for vectors"],
        ["Search", "Rewrite the question → hybrid search filtered by permissions → rerank the top 50–100 → keep 5–10"],
        ["Answer", "Generate with citations, then check each claim against its source"],
        ["Live facts", "Order status, balances, and similar values come from live systems"],
        ["Speed and cost", "Cache embeddings and stable results per permission level; cap reranking and generation per query"],
        ["Metrics", "Recall@k on labeled questions, share of supported claims, permission-update delay, p95 latency"],
    ])), section("Keeping a large index correct", """
        - **Update incrementally:** process change events, re-embed only changed chunks, and keep version numbers.
        - **Propagate permission changes and deletions** to the index, caches, and summaries. Measure how long it takes: until it finishes, people may see what they shouldn't.
        - **Shard** (split) indexes by tenant or region where isolation or data-location rules require it.
        - **Re-check permissions when answering** anyway, since the index may lag behind the source.
    """),
], "Merge chunking with the large knowledge-assistant case because ingestion and update propagation are the same pipeline."),

lesson("combine-search-and-reranking", "Hybrid search and reranking", [44],
    "Keyword search finds exact terms such as error codes, IDs, and names. **Vector search** finds passages with similar meaning, even in different words. **Hybrid search** runs both and merges the results; a **reranker** then puts the best few on top.", [
    section("Each search finds what the other misses", """
        Keyword search usually uses **BM25**, which scores documents by how often the query's words appear in them. Vector search compares **embeddings**: lists of numbers representing meaning, where similar texts get similar numbers.

        Query: "ORA-00060 deadlock when saving orders"
    """, table("One query, two searches", ["Search", "Finds", "Misses"], [
        ["Keyword (BM25)", "The article titled “ORA-00060”", "The guide “Handling lock contention”, which never mentions the code"],
        ["Vector", "“Handling lock contention”, “Deadlocks in the order service”", "May rank the exact-code article low"],
        ["Both, merged and reranked", "All three, best first", "—"],
    ]), """
        The two searches score on different scales, so don't just add the scores. **Reciprocal rank fusion** merges by position instead: each document scores `1 / (60 + rank)` for each list it appears in, summed.
    """),
    section("Rerank the shortlist", """
        A reranker (usually a "cross-encoder" model) reads the query and each candidate together, and judges relevance more accurately than either search. It is too slow for every document, so run it on the top 50–100 merged results and keep the best 5–10.

        Keep each passage's source and permissions attached. A relevant passage can still be outdated or wrong; relevance and correctness are measured separately (chapter 7).
    """),
], "Keep search fusion separate from claim grounding; add the score-comparability caution and a concrete fusion method."),

lesson("enforce-access-before-context", "Filter by permission before the model sees text", [45],
    "Apply the user's permissions during the search, before any text reaches the model. Filtering the final answer is too late: the model, the logs, and any other agents have already seen the data.", [
    section("Filter in the search, then check again", """
        Store each chunk's **ACL** (access control list: who may read it), and pass the user's permissions into the search itself.
    """, code("Permission check before the model", """
        scope      = session.user.document_scope            # from the login, not the model
        candidates = index.search(query, filter = scope)    # never fetch first and hide later
        allowed    = [c for c in candidates if acl.can_read(session.user, c.doc_id)]  # current check
        context    = label_as_outside_data(load_text(allowed))
        answer     = model(question, context)
    """, "The second check catches access removed since the document was indexed.")),
    section("When access is removed", """
        When someone loses access to a document, everything derived from it must stop reaching them too: cached search results, summaries, saved citations, and memories. Store the source document and its permission version with each derived item, and check again before showing it. Test with users of the same tenant who have different access, as well as with different tenants.
    """),
], "Keep retrieval access as an explicit boundary and extend it to permission revocation and derived context."),

lesson("reconcile-freshness-and-conflicts", "Stale and conflicting sources", [46, 49, 68],
    "Decide how up to date each fact must be, and fetch it accordingly: live systems for current values, document search for stable text, keeping timestamps either way. When sources disagree, first check whether they measure the same thing (period, currency, definition). Then trust the source that owns that fact, and show any remaining conflict instead of averaging it away.", [
    section("Match freshness to the need", """
        A recently indexed copy can still hold an old document. Track when the **source** was last updated, not just when you fetched it.
    """, code("Choosing a source by freshness", """
        if question.needs_live_value:                     # balance, stock, order status
            evidence = live_system.read(question.item)
        else:
            evidence = index.search(question)
        if evidence.source_updated_at < now - task.max_age:
            evidence = refresh_from_source(evidence)
        return evidence.with(timestamp, version)
    """)),
    section("Compare definitions before picking a winner", """
        Many contradictions are two sources measuring different things.
    """, table("Two “Q3 revenue” figures", ["Figure", "Source", "What it measures"], [
        ["$4.1M", "Sales dashboard", "Orders booked, updated hourly, including pending ones"],
        ["$3.8M", "Finance ledger", "Revenue earned, minus refunds, final for the quarter"],
    ], "Not a contradiction: two definitions. Answer “revenue” from the ledger and mention the difference."), """
        If the definitions match and the numbers still differ, trust the source that owns that fact: the ledger for revenue, the HR system for headcount. If the conflict matters and remains, show both figures with their sources and ask someone to confirm. Never average two incompatible numbers.
    """),
    section("When agents disagree", """
        Two agents reporting different totals are two conflicting sources; handle them the same way. Compare their assumptions (period, currency, how refunds count), then recompute once from the source data with a fixed query. Asking a third model to vote proves nothing. Keep the replaced findings and where they came from, and escalate an important conflict that remains to a responsible person.
    """),
], "Merge stale knowledge, conflicting sources, and specialist disagreements; the same authority/scope/provenance procedure resolves all three."),

lesson("verify-claims-and-citations", "Check that citations support claims", [47],
    "A citation helps only if the cited passage actually supports the sentence, conditions included. Split the answer into individual claims, check each against its passage, and fix or remove the ones that aren't supported.", [
    section("Support, not just a link", """
        Smooth summaries tend to drop exactly the condition that made a statement true.
    """, table("Claims checked against one passage", ["Claim", "Passage: “Unopened products may be returned within 30 days.”"], [
        ["“All products are refundable.”", "Unsupported: the conditions were dropped"],
        ["“Unopened products can be returned within 30 days.”", "Supported"],
        ["“The return window is 60 days.”", "Contradicted"],
    ])),
    section("A claim-checking pass", """
        Run it after the answer is written and before the user sees it.
    """, code("Check each claim", """
        for claim in split_into_claims(answer):
            passage = sources[claim.citation]
            verdict = check_support(claim, passage)  # SUPPORTED | PARTIAL | UNSUPPORTED | CONTRADICTED
            if verdict != SUPPORTED: revise_or_remove(claim)
        require every citation opens a document the user may read
    """), """
        Use code where it can decide: the document exists, the version matches, a quoted number appears in the passage. Use a model to judge whether the meaning is supported, after testing it against human ratings (see *LLM-as-a-judge*).
    """),
], "Keep claim grounding distinct from relevance so a good retrieval score is not mistaken for a supported answer.",
    related=["evaluate-retrieval-separately", "calibrate-model-judges"]),

lesson("retrieve-in-dependent-hops", "Multi-hop retrieval", [48],
    "**Multi-hop retrieval** answers questions where one search reveals what to search for next. Each round (a “hop”) passes a specific, sourced finding, such as an ID, a name, or a date, to the next search, with limits on the number of hops and the cost.", [
    section("Each hop narrows the next", """
        "Why did revenue drop last quarter?" can't be answered by one search:
    """, table("A three-hop investigation", ["Hop", "Search", "Found"], [
        ["1", "Which products' revenue fell in Q3?", "SKU-17 and SKU-22 (sales report, section 2)"],
        ["2", "What changed for SKU-17 and SKU-22 in Q3?", "A price increase on July 4 (pricing log)"],
        ["3", "Did sales drop after July 4 for every customer group?", "Only for small businesses (orders database)"],
    ], "Conclusion: the price change coincides with the small-business drop. That is a supported guess, not a proven cause.")),
    section("Limit the search", """
        - Cap the hops, searches, and time.
        - Stop when the question is answered, when a hop finds nothing new, or when the next step needs data you can't access.
        - Pass facts forward, not guesses, and keep the chain of sources so the answer can show its reasoning.
        - Say what kind of conclusion it is: confirmed, a likely explanation, or still open.
    """),
], "Retain multi-hop retrieval as a distinct dependency pattern, with explicit evidence transfer and stopping rules."),

lesson("budget-and-compress-context", "Fit the context window", [50, 122],
    "The **context window** is the most text a model can read in one call, measured in tokens (a token is roughly three-quarters of a word). Always keep the goal, permissions, pending commitments, and the information for the next step; summarize or link everything else. Then confirm on your test set that cutting tokens didn't cut quality.", [
    section("Keep what must survive", """
        Shortening must never drop a limit, an approval, or an action with an unknown result.
    """, code("Building context within a budget", """
        keep     = [goal, permissions, pending_approvals, unfinished_actions, limits]
        evidence = select_for(next_step, max_tokens = EVIDENCE_BUDGET)
        history  = summarize(completed_steps, keep = source_links)
        require tokens(keep) <= BUDGET                   # if not, split the task
        context  = keep + fit(evidence + history, BUDGET - tokens(keep))
    """, "A summary must not turn an outside claim into a fact, or drop a condition that limits an action.")),
    section("Use fewer tokens without losing quality", """
        Roughly in order of impact:

        - Fetch fewer, better passages: rerank and keep the top few.
        - Link to large files and fetch sections only when needed.
        - Summarize finished steps; keep IDs and sources, drop the narration.
        - Offer only the tools this task needs; every tool description is re-sent on every call.
        - Ask for compact output.
        - Use **prompt caching**, a provider feature that reuses the processed form of a repeated prompt start (system prompt, tool list). It cuts cost and delay, though not the amount of text.

        Test every change on the golden set (success, grounding, policy, speed, cost) before and after.
    """),
], "Merge context-window management and token reduction; both are tested information-preservation choices."),
]
