from authoring import code, lesson, section, table

CHAPTER = ("Orchestration patterns", "Arrange model calls and tools to fit the shape of the work.")

LESSONS = [

lesson("route-or-chain", "Choose an orchestration pattern", [21, 22, 29, 30],
    "Choose the pattern from the shape of the work. **Routing** sends each request to the one handler that suits it. **Prompt chaining** runs dependent steps in order, checking each output before the next step uses it. Let the model decide only where judgment is needed; steps with clear rules belong in code.", [
    section("Patterns, simplest first", """
        Start at the top and move down only when the simpler pattern fails your tests.
    """, table("Orchestration patterns", ["Pattern", "Use when", "Example"], [
        ["Single call", "One transformation", "Summarize a ticket"],
        ["Routing", "Requests fall into distinct types", "Billing vs. technical vs. unclear"],
        ["Prompt chaining", "Fixed steps, each needing the previous output", "Extract → check → assess → draft"],
        ["Parallel", "Independent pieces of work", "Research three competitors at once"],
        ["Orchestrator–worker", "The pieces aren't known in advance", "An open-ended research report"],
        ["Evaluator–optimizer", "Feedback against criteria improves the output", "Draft a report, then revise it"],
        ["Agent loop", "The next step depends on what you find", "Investigate an outage"],
    ], "Patterns combine: a routed request can go to a chain, and one step of a chain can be a small agent loop.")),
    section("Routing", """
        A classifier (simple rules, or a small model you have tested) picks one handler per request, such as billing, technical support, or account changes. Two rules keep routing safe:

        - **Give "unsure" its own route.** When the classifier isn't confident, or the request isn't supported, ask a question or pass it to a person instead of forcing it into the nearest handler.
        - **Handlers still check their inputs.** Being picked by the router grants no extra permission.

        Count wrong routes as failures when testing; they cost real time and money.
    """),
    section("Prompt chaining", """
        Each step uses only output that passed the check before it. A failed check stops the chain, so bad data doesn't flow onward.
    """, code("Contract review as a chain", """
        clauses = model.extract_clauses(contract)
        require every clause has a type and a page number      # code check
        risks   = model.assess_risks(clauses)
        require every risk points to a clause that exists      # code check
        report  = model.draft_report(risks)
    """), """
        Should the model decide every step? No. If a software build fails, code blocks the release; the model can explain the failure. Use the model for judgment calls and code wherever the rule can be written down.
    """),
], "Merge the pattern overview with routing, chaining, and deterministic transitions; use one lesson instead of four thin pages.",
    references=[("Anthropic: Building effective agents", "https://www.anthropic.com/engineering/building-effective-agents", "Source of the pattern names used in this chapter.")]),

lesson("plan-and-replan", "Plan, then replan on new evidence", [26, 27],
    "In **plan-and-execute**, the model first writes a list of steps, then the steps run one at a time with the usual checks. Change the plan only when a result contradicts something the plan assumed or a step is blocked, and keep a record of what actually ran.", [
    section("A plan that meets the evidence", """
        A written plan shows intent, can be reviewed, and lets cheaper models or plain code carry out routine steps. Its weakness: it goes out of date as soon as the evidence disagrees.
    """, code("An outage plan that changes", """
        goal: checkout is 4x slower than normal

        plan v1
          1. check database speed           # assumes the database is the cause
          2. if slow: find the slow queries
          3. compare with recent releases

        ran
          1. database speed is normal        → assumption wrong → replan

        plan v2 (step 1 kept in the record)
          2. check the payment provider's speed
          3. compare with recent releases
    """)),
    section("When to replan", """
        Replan when a result contradicts the plan's assumptions, when a step is blocked (permission denied, tool down), or when the user changes the request. A new idea from the model, with no new evidence, is not enough.
    """, code("Replanning trigger", """
        result = execute(plan.next_step())
        task.save(result)
        if result.contradicts(plan.assumptions) or result.blocked:
            plan = replan(goal, history = task.history, evidence = result)   # counts toward the step limit
    """), """
        Replanning never erases what already happened; completed steps and their effects stay on record. Planning counts against the task's step, time, and cost limits. If no workable path remains, ask the user or escalate.
    """),
], "Combine planning and dynamic replanning, keeping actual execution history separate from intended work."),

lesson("parallelize-by-dependency", "Run work in parallel safely", [23, 115],
    "Run steps at the same time only when none needs another's result and none changes the same thing. Reading in parallel is usually safe. Changing shared data in parallel (a balance, stock count, or file) needs a fixed order, a lock, or a service that applies the rule atomically.", [
    section("Fan out independent work", """
        Starting several independent pieces of work at once and collecting their results is called **fan-out**. Researching competitors A, B, and C can fan out, because each has its own input and its own result. Set limits:
    """, code("Bounded fan-out", """
        results = parallel([research("A"), research("B"), research("C")],
                           max_at_once = 3, deadline = 60 s)
        report  = synthesize(results.completed,
                             missing = results.failed)   # say what's missing; don't hide it
    """), """
        More branches cost more, and the combined result waits for the slowest branch (see *Latency and the critical path*).
    """),
    section("When parallel is unsafe", """
        Look for shared data or a required order before running two actions together.
    """, table("Unsafe parallel actions", ["Run together", "What goes wrong", "Fix"], [
        ["Settle the balance; close the account", "Closing first leaves money stranded", "Run in order"],
        ["Two refunds on order 42", "Both pass the balance check", "The payment service checks the balance atomically"],
        ["Two agents edit the same file", "One overwrites the other", "One owner per file"],
        ["Two bookings for the last seat", "The seat is sold twice", "Reserve with a lock or a version check"],
    ], "Build the order into the scheduler or the service. Don't rely on two agents coordinating informally.")),
], "Merge the benefits and hazards of parallel tools so the safety precondition is taught with the optimization."),

lesson("refine-with-a-bounded-evaluator", "Generate, check, and revise", [25],
    "In the **evaluator–optimizer** pattern, one step produces an output and another scores it against a fixed list of criteria (a rubric), returning feedback. The first step revises until the output passes or a revision limit is reached. Use code for every criterion that code can check exactly.", [
    section("Revise with a cap", """
        Split the rubric into **hard checks** that code decides and **soft criteria** that need judgment. A persuasive critique never overrides a failed hard check.
    """, code("Bounded revision", """
        draft = generate(task)
        for attempt in 1..3:
            hard = run_checks(draft)       # code: the SQL runs, every claim has a citation
            soft = judge(draft, rubric)    # model: clear, complete, answers the question
            if hard.passed and soft.passed: return draft
            if attempt == 3: break         # out of revisions
            draft = revise(draft, hard.errors + soft.feedback)
        return draft.with_open_issues(hard.errors + soft.feedback)
    """, "When the limit is reached, return the draft with its open issues instead of pretending it passed.")),
    section("Limits of the pattern", """
        - Cap revisions, time, and cost; most of the improvement usually comes in the first one or two rounds.
        - A judge built on the same model shares the writer's blind spots. Two models agreeing doesn't make something true.
        - Test the judge against human ratings before trusting it (see *LLM-as-a-judge*).
    """),
], "Keep a distinct refinement lesson because generation/evaluation feedback is a different loop from action execution."),
]
