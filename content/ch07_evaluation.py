from authoring import code, lesson, section, table

CHAPTER = ("Evaluation", "Test what the agent did, what actually changed, and the rules that must never break, before adding more parts.")

LESSONS = [

lesson("evaluate-the-whole-trajectory", "Evaluate the whole run, not just the answer", [101, 103, 105],
    "Test at several levels: the final outcome, each tool choice and its inputs, the whole **trajectory** (the full sequence of decisions and tool calls in one task), and the reply. A right answer reached by reading another customer's data, or after twenty wasted calls, is still a failure.", [
    section("Check every level", """
        Each level catches failures the others miss.
    """, table("What to measure", ["Level", "Question", "Example metric"], [
        ["Outcome", "Did the requested change actually happen?", "Verified success rate"],
        ["Tool choice", "Was it the right tool for the step?", "Share of correct tool choices"],
        ["Tool inputs", "Right target, valid inputs?", "Share of invalid or denied calls"],
        ["Trajectory", "Did it stay within the task? Was it efficient?", "Out-of-scope calls; steps per task"],
        ["Reply", "Backed by sources, and clear?", "Share of supported claims; rubric score"],
        ["Operations", "Fast and cheap enough?", "p95 latency; cost per success; escalation rate"],
    ])),
    section("Why the path matters", """
        Two runs can end with the same correct summary. One read only the requested account; the other read five unrelated customers' accounts along the way. Only the trajectory shows the difference, and the second run is a privacy incident.

        Long chains also multiply failure. If each of 10 steps independently succeeded 95% of the time, the whole task would succeed only about 60% of the time (0.95^10 ≈ 0.60). Real errors aren't independent, since one early misunderstanding derails every later step, so measure complete runs instead of multiplying step scores.

        Break results down by task type and by cause (bad search, misread request, invalid action, outside service failed, false success claim). One average hides what to fix.
    """),
], "Merge evaluation levels, metric lists, and trajectory evaluation; add a worked example of error accumulation."),

lesson("evaluate-retrieval-separately", "Evaluate retrieval on its own", [],
    "A model can't use a passage it never received. Test search, ranking, and answer writing as separate steps, so a search failure isn't mistaken for a model failure.", [
    section("Precision and recall", """
        For each test question, mark which passages are relevant. Then look at the top **k** results, where k is how many passages you actually give the model:

        - **precision@k:** of those k passages, the share that are relevant;
        - **recall@k:** of all relevant passages, the share that made it into the top k.

        Example: a question has 4 relevant passages, and the top 5 results include 3 of them. Precision@5 = 3/5 = 0.6; recall@5 = 3/4 = 0.75. Both are only as good as the relevance labels.
    """, table("Find the step that failed", ["What you see", "Where to look"], [
        ["The relevant passage was never found", "Indexing, the query, filters, or the search"],
        ["Found, but dropped before reaching the model", "Ranking and selection"],
        ["Given to the model, but the claim is still wrong", "Answer writing and claim checking"],
        ["A forbidden passage reached the model", "Permissions: a security failure, not a relevance problem"],
    ])),
    section("Link step scores to results", """
        Measure ranking with the number of passages you really use, then check answers built from exactly those passages. Study cases where recall improved but task success didn't; they usually point to answer writing or checking.

        Include questions your documents **can't** answer. The right reply is "I couldn't find this". Recall makes no sense when nothing is relevant, so score these cases separately.
    """),
], "Add a retrieval-specific evaluation layer so answer scores cannot hide upstream search failures.",
    questions=["How do you test the retrieval part of a RAG system?"],
    references=[("Stanford IR book: precision and recall", "https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-unranked-retrieval-sets-1.html", "Precision and recall, defined.")]),

lesson("calibrate-model-judges", "LLM-as-a-judge", [106],
    "**LLM-as-a-judge** means using a language model to score outputs against criteria. It is useful for qualities code can't check, such as clarity, relevance, or completeness. But it is only as reliable as its measured agreement with human ratings on your data: measure that agreement, correct for its known biases, and never use a judge where an exact check exists.", [
    section("Exact checks first", """
        If code can check something, let code check it: the output's shape, the database state, a calculation, whether a citation exists, whether a call was allowed. Use a judge only for what needs interpretation.

        Give the judge specific criteria ("Does the reply state the refund amount and when it will arrive?") rather than "Rate quality from 1 to 10", and ask it to quote the text behind its verdict.
    """),
    section("Known biases, and fixes", """
        - **Position bias:** when comparing two answers, judges favor one slot. Run each pair in both orders.
        - **Length bias:** longer answers score higher. Reward brevity in the criteria, and check whether scores track length.
        - **Self-preference:** a judge may favor answers from its own model family. Use a different model where possible.
        - **Wording sensitivity:** small prompt changes move scores. Fix the judge's model and prompt.

        Have people rate 100–200 typical cases, and measure how well the judge agrees with them. Use **Cohen's kappa**, an agreement score that corrects for lucky agreement (1 is perfect, 0 is chance), rather than plain percent agreement. Measure again whenever the judge changes, and report judge scores together with that agreement.
    """),
], "Keep model-judge calibration separate from evaluator-optimizer mechanics because scoring reliability is its own concern."),

lesson("test-adversarial-boundaries", "Test prompt-injection resistance", [107],
    "Plant malicious instructions wherever untrusted content enters, then check what the agent actually revealed, called, or saved. What the reply says doesn't count. A good result blocks the attack **and** still completes the real task.", [
    section("Score what happened, not what was said", """
        Hide attacks in fetched pages, emails, tool results, attachments, and messages from other agents, under realistic task permissions. Try data theft, gaining extra permissions, misusing tools, and memory poisoning.
    """, code("An injection test loop", """
        for attack in attack_set:                       # include new and held-out attacks
            run = agent.run(real_task, documents = inject(attack))
            check(run.leaked_restricted_data == 0)
            check(run.forbidden_calls_executed == 0)    # the controls must hold
            record(run.forbidden_calls_attempted)       # the model was fooled; track how often
            check(run.unapproved_memory_saves == 0)
            record(run.real_task_completed)
    """, "Report three numbers: attacks that caused harm (must be 0), attacks that fooled the model but were blocked, and real-task success while under attack.")),
    section("Keep the product working", """
        A system that refuses every document containing an instruction is safe but useless, so track real-task success alongside attack results.

        Vary attacks: different encodings, languages, and hiding places, plus every attack seen in production. Keep some attacks out of tuning, so you don't just fit the known ones. New wording will sometimes fool the model, which is why the controls in chapter 3 must not depend on the model.
    """),
], "Retain attack testing as a separate evaluation lesson, distinguishing observed effects, attempted misuse, and useful task completion."),

lesson("inject-failures-and-check-invariants", "Failure injection and chaos testing", [108, 120],
    "Cause failures on purpose (crashes, timeouts, duplicate messages, provider outages) at the worst moments, then check that the rules that must always hold still do: no double charge, no expired approval used, no data sent to an unapproved provider. **Chaos testing** does this in a realistic environment, with the possible damage kept small.", [
    section("Aim at the crash window", """
        The most valuable test kills the worker after an action goes through but before its result is saved (see the timeline in *Durable execution: survive crashes*).
    """, code("A crash-window test", """
        test "crash after the refund is paid, before the result is saved":
            inject crash at: after payments.pay(op-42), before history.save(step 4)
            resume the task to completion
            assert payments.refunds(order = 42).count == 1
            assert task.status == COMPLETED and task.receipt == "R-981"
    """)),
    section("Pair each failure with an invariant", """
        A test passes only if the invariant holds; a process that merely restarts isn't enough.
    """, table("Failures and what must stay true", ["Failure caused", "What must stay true"], [
        ["Worker killed right after an action", "The action isn't repeated after recovery"],
        ["The same message delivered twice", "One action, one receipt"],
        ["Approval arrives after it expired", "Nothing runs on the expired approval"],
        ["A tool slower than the deadline", "No endless wait; no blind retry of the change"],
        ["Main model provider down", "No fallback to a provider that breaks privacy rules"],
        ["A worker frozen past its lease", "The stale worker's write is rejected"],
    ]), """
        Start in test environments. Record the exact failure timing and versions, so every failure you find becomes a repeatable test.
    """),
], "Merge reliability failure injection and chaos testing; teach fault timing and invariants together."),

lesson("gate-releases-and-canaries", "Release gates and canary releases", [110, 135],
    "A new version ships only if it passes hard blockers (zero security failures, zero duplicate actions) and meets quality, speed, and cost limits on the golden set. Then it reaches users gradually: first in **shadow mode** (running on copies of real requests without taking real actions), then as a **canary** (a small share of real traffic), expanding or rolling back by rules set in advance.", [
    section("What blocks a release", """
        Write the blockers down before seeing results, so nobody argues them away afterwards.
    """, code("Release gate", """
        require security_failures == 0
        require duplicate_actions == 0
        require golden_set.success_rate >= QUALITY_BAR     # per category, not just overall
        require p95_latency <= LATENCY_LIMIT
        require cost_per_success <= COST_LIMIT
        require tested_versions == shipping_versions       # prompt, model, tools, policy
    """, "A high average can't make up for one unauthorized payment.")),
    section("Widen exposure step by step", """
        Each stage has a written condition for moving on and a trigger for rolling back.
    """, table("Rollout stages", ["Stage", "Traffic", "Real actions?", "Move on when"], [
        ["Offline", "Golden set", "Test data only", "All gates pass"],
        ["Shadow", "Copies of live requests", "No: proposals are logged and compared", "Proposals match or beat the current version"],
        ["Canary", "1–5% of suitable requests", "Yes, low-risk only", "Results at least as good as the current version for the agreed period"],
        ["Ramp-up", "25% → 50% → 100%", "Yes", "Same checks at each step"],
    ], "Any serious violation rolls back automatically. Test the rollback before the canary starts."), """
        Make sure shadow mode truly can't act: a shadow agent with access to the live payment tool is not a shadow.
    """),
], "Merge release blockers with canary rollout so testing and increasing authority form one gated progression."),

lesson("compare-designs-with-controlled-experiments", "Compare designs fairly", [109, 157],
    "Compare designs on the same versioned test set with the same scoring, looking at quality, safety, speed, cost, and upkeep. To compare on live traffic, run an **A/B test**: randomly assign each user (or account) to one design and compare outcomes, using shadow mode first when actions are risky.", [
    section("Offline: same tasks, same scoring", """
        Run every design on the same golden set with the same scoring, and look at the full picture rather than one number:
    """, table("Example comparison", ["", "One agent with tools", "Team of four agents"], [
        ["Verified success", "82%", "84%"],
        ["p95 latency", "12 s", "31 s"],
        ["Cost per success", "$0.04", "$0.13"],
        ["Parts to run", "1 loop, 6 tools", "4 agents, routing, shared memory"],
    ], "Two points of quality rarely justify three times the cost and time. Prefer the simpler design unless the gain matters."), """
        Check whether the gap is real before acting on it. With a few hundred test cases, two points is often noise. Because both designs ran the same cases, use a test built for paired results, such as **McNemar's test**, which asks whether the cases where only one design passed lean one way by more than chance. Record the decision and its assumptions, so you can revisit it when the workload changes.
    """),
    section("Online: an A/B test", """
        - **Assign by user or account,** so no one switches designs mid-conversation, and analyze results per user, not per request; one user's requests aren't independent.
        - **Keep the two groups apart:** no shared memory or caches that leak one design's behavior into the other.
        - **Choose the main metric and the safety limits before starting,** and run long enough to detect the difference you care about.
        - **Never run two real actions for one customer request** just to compare designs. For risky actions, compare in shadow mode.
    """),
], "Merge architecture comparison and online experimentation while distinguishing offline paired workloads from live random assignment."),
]
