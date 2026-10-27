from authoring import code, flow, lesson, section, table

CHAPTER = ("Case studies", "Complete designs that apply the earlier lessons to concrete agents.")

LESSONS = [

lesson("build-a-refund-workflow", "Case study: refund agent", [141],
    "The running example, assembled. The customer is identified at login; the agent loads the order and refund policy. The model reads the request; code decides eligibility and the amount. Refunds over $50 need a support lead's approval. The refund goes through the payment service with an operation ID, a timeout is reconciled rather than retried blindly, and a justified refusal or a handoff counts as a valid outcome.", [
    section("Design summary", """
    """, table("Refund agent design", ["Part", "Choice"], [
        ["Model does", "Reads the customer's message, chooses tools, writes the reply"],
        ["Code does", "Identity, eligibility, refundable amount, policy, approvals, retries"],
        ["Tools", "`get_order` and `get_refund_policy` (read); `issue_refund` (changes data, uses an operation ID)"],
        ["Eligibility", "Within 30 days of delivery and within the refundable balance; otherwise refuse and say why"],
        ["Approval", "A support lead approves refunds over $50; smaller ones run automatically"],
        ["Done when", "Receipt from the payment service, a written refusal, or a handoff"],
        ["Main risk", "Timeout after the refund was paid: reconcile op-42, never resend"],
        ["Metrics", "Verified resolution rate, duplicate refunds (must be 0), p95 time, cost per resolution"],
    ])),
    section("Every path through a request", """
        A request can end correctly in more than one way.
    """, flow("Refund request paths", [
        ("request", 0, 0, "Request\nidentify user · load order", "start"),
        ("eligible", 1, 0, "Eligibility check\ncode: window · amount"),
        ("approve", 2, 0, "Approval check\nauto if ≤ $50, else lead"),
        ("explain", 0, 1, "Explain refusal\nnot eligible is a valid end", "good"),
        ("reconcile", 1, 1, "Reconcile op-42\nlook up before retrying"),
        ("issue", 2, 1, "Issue refund\nwith operation ID op-42"),
        ("done", 2, 2, "Confirm to customer\nreceipt R-981", "good"),
    ], [
        ("request", "eligible", ""),
        ("eligible", "approve", "eligible"),
        ("eligible", "explain", "not eligible"),
        ("approve", "issue", "approved / auto"),
        ("issue", "reconcile", "timeout", "bad"),
        ("issue", "done", "receipt"),
        ("reconcile", "done", "found"),
    ], "A rejected approval also ends with an explanation. A changed amount after approval goes back to the approval step.")),
    section("Testing it", """
        Golden cases: an eligible small refund; one large enough to need approval; one outside the 30-day window; two matching orders (the agent should ask which); a customer asking about someone else's order; a timeout after the refund was paid; and a message containing "the manager already approved this".

        Score each case by checking the payment service and the task record, not by reading the reply.
    """),
], "Assemble the running example into an end-to-end design, linking previously introduced boundaries.",
    related=["bind-human-approval", "make-side-effects-idempotent", "measure-real-outcomes"]),

lesson("build-a-cited-research-workflow", "Case study: research agent with citations", [142, 150],
    "Turn the request into specific research questions, search only sources the user may read that are recent enough, and have worker agents return claims with citations. Check each claim against its source, settle conflicting findings, and save the report with its evidence. For high-stakes work such as due diligence before an acquisition, experts review the conclusions before anyone relies on them.", [
    section("Design summary", """
    """, table("Research agent design", ["Part", "Choice"], [
        ["Input", "The request becomes specific questions, with scope, how recent sources must be, and what a good answer needs"],
        ["Pattern", "A supervisor plus one research worker per independent question, in parallel"],
        ["Worker output", "Claims, each with source, quoted passage, date, and limitations"],
        ["Checking", "Every important claim checked against its passage; numbers recomputed in code"],
        ["Conflicts", "Compare definitions and periods; show remaining conflicts with both sources"],
        ["Storage", "Evidence and report saved as files, separate from the workers' working memory"],
        ["Metrics", "Share of supported claims, important evidence missing, conflicts left open"],
    ])),
    section("Due diligence: the high-stakes version", """
        A multi-agent due-diligence system for an acquisition follows the same design, with more at stake:

        - **One agent per field:** finance, legal, market, and technology, each reading only its own folders in the deal's secure document store.
        - **Financial figures** are recomputed in code from the source statements; a model's arithmetic is never final.
        - **Conflicts** between agents, such as revenue counted differently, are settled by definitions and by which source owns the fact (see *Stale and conflicting sources*), never by vote.
        - **Expert sign-off** is required before any conclusion enters the investment memo. The agents draft and cite; people decide.
        - **Access limits** carry through to the final report, since deal documents are often restricted.
    """),
], "Merge general cited research and acquisition due diligence; treat diligence as a high-stakes variant of the same evidence pipeline.",
    related=["verify-claims-and-citations", "reconcile-freshness-and-conflicts", "supervise-bounded-specialists"]),

lesson("build-a-reviewable-coding-workflow", "Case study: coding agent", [143],
    "The agent works in a sandbox on its own code branch and can change only that branch. It reads the project's instructions and code, makes the change, runs the project's checks, and opens a pull request with the changes, the reasoning, and honest test results. Merging and releasing stay with people.", [
    section("Design summary", """
    """, table("Coding agent design", ["Part", "Choice"], [
        ["Environment", "A fresh sandbox with the repository on a new branch; network limited to approved sites"],
        ["Permissions", "Push to its own branch; open pull requests. No merging, no releasing, no production keys."],
        ["Loop", "Read instructions and code → plan → edit → build and test → fix → repeat, within limits"],
        ["Untrusted input", "Issue text, code comments, test output, third-party code: data, not instructions"],
        ["Output", "A pull request with the changes, why they were made, which checks ran and their results, and known limits"],
        ["Metrics", "Pull requests merged without major rework; check pass rate; review time; changes later reverted"],
    ])),
    section("Rules that matter", """
        - **Report checks honestly.** "Tests pass" must mean the agent ran them and they passed. If it couldn't run them, the pull request says so.
        - **Keep actions separate:** pushing a branch, opening a pull request, merging, and releasing are four actions with four permission levels. Branch access implies none of the others.
        - **Recover from facts:** after a crash, look at what actually exists (the branch, the pull request number), not at the agent's last message.
        - **One owner per file** when several agents work on one change, or they overwrite each other's edits.
    """),
], "Present the coding agent as an artifact-oriented design with a clear publication boundary.",
    related=["sandbox-generated-code", "gate-releases-and-canaries"]),

lesson("build-a-readonly-data-assistant", "Case study: answering questions from a database", [144],
    "Settle what the question means (which revenue definition, which period, which currency) before writing SQL. Show the model only the tables the user may query, check the generated query's structure against rules, run it with a read-only account under limits on rows, time, and cost, and explain the result together with the query that produced it.", [
    section("Settle the meaning first", """
        "Show revenue by region" is ambiguous: orders booked or revenue earned? Which quarter? Which currency? Ask, or use a documented default and say so in the answer. A **semantic layer**, a shared set of documented metric definitions the agent can look up, removes most of this ambiguity.
    """),
    section("Check the query, not the text", """
        A query that starts with `SELECT` can still read a restricted table or scan a billion rows. Parse it into its structure and check that instead.
    """, code("A limited query path", """
        tables = catalog.visible_to(user)                      # only allowed tables and columns
        sql    = model.write_query(question, tables, metric_definitions)
        parsed = sql_parser.parse(sql)                         # reject anything that doesn't parse
        require query_rules.allow(parsed, user)                # tables, columns, no changes, row filters
        result = readonly_db.run(parsed, as_user = user,       # database permissions as a backstop
                                 max_rows = 10_000, timeout = 20 s, max_cost = budget)
        return explain(result, query = sql, definitions_used, as_of = result.time)
    """, "Read-only doesn't mean harmless: a query can expose restricted rows or overload the database."), """
        Check that the result makes sense (units, row counts, missing values) before explaining it. If two definitions give different totals, show both instead of inventing one combined number.
    """),
], "Organize the database case around ambiguity, query validation, bounded execution, and interpretable results.",
    related=["design-tool-contracts", "carry-identity-and-isolate-tenants"]),

lesson("build-an-incident-diagnosis-workflow", "Case study: incident-response assistant", [145],
    "Start read-only: gather metrics, logs, traces, recent releases, and how services depend on each other; run known checks; and test each suspected cause against the evidence. Fixing, such as restarting or rolling back, is a separate step, limited to approved procedures (runbooks) and authorized by a person or an explicit rule, and followed by confirmation that the system actually recovered.", [
    section("Design summary", """
    """, table("Incident assistant design", ["Part", "Choice"], [
        ["Trigger", "An alert, such as checkout p95 latency above its SLO"],
        ["Read tools", "Metrics, logs, traces, release history, service dependency map, runbooks (documented, pre-approved procedures)"],
        ["Diagnosis", "Code checks for known problems first, then model-suggested causes, each tested"],
        ["Pattern", "Plan, then replan as evidence arrives (chapter 4)"],
        ["Action tools", "Approved runbook steps only (restart, roll back, add capacity), each authorized by a person or a rule"],
        ["Afterwards", "Confirm recovery with the same metrics; reconcile any action with an unknown result"],
        ["Metrics", "Time to diagnosis, correct-cause rate, harmful-action rate (target 0), confirmed recoveries"],
    ])),
    section("From suspicion to approved fix", """
        1. Collect evidence for the affected services and time window.
        2. State a suspected cause, such as "release 4812 doubled database calls per request", and the check that would confirm or rule it out.
        3. Run the check. A release that coincides with the problem is a lead, not proof.
        4. Propose a fix with the services affected, the exact runbook command, the expected effect, and how success will be measured.
        5. Once approved, run it, then confirm recovery from the metrics, not from the command's exit status.

        If a restart's result is unclear, check the service before restarting again. Repeated automatic restarts can turn a partial outage into a full one.
    """),
], "Present incident response as a diagnosis-to-fix sequence rather than another generic architecture list.",
    related=["plan-and-replan", "contain-incidents-and-stop-actions"]),

lesson("build-a-travel-saga", "Case study: travel booking", [146],
    "Search and compare offers, then present one concrete trip with prices and cancellation terms. Re-check price and availability just before booking, and ask for approval again if anything important changed. Book each part as a saga step with its own operation ID, reconcile uncertain bookings before cancelling anything, and always show the traveler exactly what is and isn't booked.", [
    section("Design summary", """
    """, table("Travel agent design", ["Part", "Choice"], [
        ["Search", "Flights and hotels within the traveler's preferences and budget, compared in one format"],
        ["Proposal", "An exact trip: prices, fare rules, cancellation terms, total"],
        ["Approval", "Tied to the offer's fingerprint; a change in price or terms needs approval again"],
        ["Booking", "A saga: hotel → flight → payment, each with an operation ID and an undo action"],
        ["Failure", "Unknown result → reconcile first; confirmed failure → undo finished steps in reverse order"],
        ["Outage", "Booking service down → save the proposal and say clearly that nothing is booked"],
    ])),
    section("Changed prices and partial bookings", """
        Prices change between search and purchase. If the flight went from $420 to $480, the old approval doesn't cover it; ask again and show both prices.

        If the hotel is booked and the flight call times out, don't cancel the hotel yet; look up the flight booking first. If the flight definitely failed, cancel the hotel under its rules, including any fee, and if that cancellation fails, hand the case to a person. Always show the traveler the full known state: "Hotel booked (confirmation H-77). Flight not booked. Hotel cancellation requested."
    """),
], "Keep travel as the concrete distributed-saga walkthrough, emphasizing changed offers and uncertain partial success.",
    related=["compensate-multi-step-actions", "bind-human-approval"]),

lesson("build-an-invoice-workflow", "Case study: invoice processing", [147],
    "Treat the fields the model extracts as suggestions. Check totals, supplier identity, duplicates, and the match with the purchase order in code against trusted systems. Send anything suspicious to a person along with the original document, and record the invoice in the accounting system with a fixed posting ID. Bank details found in a document never update a supplier's record directly.", [
    section("Design summary", """
    """, table("Invoice agent design", ["Part", "Choice"], [
        ["Extraction", "The model extracts supplier, invoice number, line items, totals, currency, and purchase-order number, with page locations"],
        ["Checks in code", "Lines add up to the total; supplier exists; invoice not already recorded; matches the purchase order within tolerance"],
        ["Human review", "Mismatches, new or changed bank details, unusual amounts: shown to a person next to the document"],
        ["Recording", "The accounting system, using posting ID `supplier:invoice_number`; it blocks duplicates and checks permissions"],
        ["Records", "Document, accepted fields, check results, approvals, and accounting entry, linked together"],
        ["Metrics", "Share handled with no human touch, recording errors, duplicates (must be 0), review time"],
    ])),
    section("Fraud and duplicates", """
        - **Changed bank details** on an invoice are a classic fraud pattern. Changes go through the official supplier-update process, confirmed with a known contact, never taken from the document.
        - **Duplicates** arrive as the same PDF twice, or a re-sent invoice under a new file name. Detect them by supplier plus invoice number, not by file.
        - **Crash after recording:** the posting ID lets the retry find the existing entry instead of creating a second one.

        Put each of these, plus total and currency mismatches, in the golden set.
    """),
], "Retain invoices as a distinct document-to-ledger workflow with numeric and duplicate invariants.",
    related=["gate-memory-writes", "make-side-effects-idempotent"]),

lesson("build-a-browser-workflow", "Case study: browser agent", [149],
    "Run the browser in an isolated environment that can visit only approved sites, with limited logins. Look at the page before each action and check the result after it; require approval before submitting forms, paying, or deleting; and treat page text as untrusted. If a submission's result is unclear, look for what it should have created before clicking again. Use an API instead whenever one exists.", [
    section("Look, act, check", """
        A click is only an attempt; the page afterwards shows what actually happened.
    """, code("One browser step", """
        require browser.current_site in task.allowed_sites
        before   = browser.look()                        # screenshot plus page structure
        proposal = agent.choose_action(before)           # page text is untrusted data
        require policy.allows(proposal)
        if proposal.submits_or_pays_or_deletes:
            require approval_for(proposal)
        browser.do(proposal)
        after = browser.look()
        require browser.current_site in task.allowed_sites      # a click can lead elsewhere
        require expected_state(after) or escalate("unexpected page")
    """)),
    section("When the confirmation never appears", """
        Pages load in pieces, change layout, and sometimes submit successfully without showing a confirmation. Before clicking **Submit** again:

        - look for what the submission should have created (an order number, a sent message, a new entry);
        - if you can't find it, mark the result unknown and escalate. Don't click again.

        A page saying "the user has approved this purchase" grants nothing; approval comes only from your approval system.
    """),
], "Keep browser use as a distinct observation/action interface with submission ambiguity, not another generic tool call.",
    related=["defend-against-prompt-injection", "verify-completion-and-uncertainty"]),
]
