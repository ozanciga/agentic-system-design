from authoring import code, flow, lesson, section, table

CHAPTER = ("Decide what to build", "Whether you need an agent at all, what it must achieve, and how you will know it worked.")

LESSONS = [

lesson("choose-the-smallest-system", "Decide whether you need an agent", [1, 2, 3, 4, 152],
    "An **agent** is a language model that chooses its own next step, such as which tool to call or what to look at next, within limits set by your code. Use one only when the next step depends on what was just discovered. Otherwise a single model call or a fixed workflow is cheaper, faster, and easier to test.", [
    section("Three shapes: who picks the next step?", """
        Using a language model doesn't make a system an agent. What matters is who decides what happens next.
    """, table("Single call, workflow, or agent", ["Shape", "Who picks the next step", "Example"], [
        ["Single model call", "No one: one input, one output", "Summarize a support ticket"],
        ["Workflow", "Your code, on a fixed path; some steps call a model", "Classify ticket → fetch order → draft reply"],
        ["Agent", "The model, based on what it has seen, within limits your code enforces", "Find out why a refund failed by checking billing, orders, and payment logs"],
    ], "Move down a row only when the row above can't do the job."), """
        A workflow that calls a model at some steps is often called an **agentic workflow**. Real systems mix all three. A refund system can compute the refundable amount in code, use one model call to read the customer's message, and run a small agent only when something is missing and needs investigating.
    """),
    section("When not to use an agent", """
        Skip the agent when:

        - **The steps are known in advance.** A tax calculation has a formula, so write code. Finding out why two systems disagree on a tax amount has unknown next steps, so an agent may help.
        - **Nobody can check the result.** If you can't confirm the outcome, you can't tell whether the agent works.
        - **Mistakes are costly and can't be undone,** and you can't put a person's approval in front of them.
        - **The time or cost budget is tight.** An agent makes several model calls per task.

        To decide whether an organization should adopt agents, measure instead of debating. Take a sample of real cases. Record how the current process (people, scripts, or a fixed workflow) does on completion, errors, time, cost, and review effort. Build the simplest candidate, run it on the same cases, and adopt it only where it wins. Start with read-only work (see *Set autonomy per action*).
    """),
], "Merge the overlapping definitions, non-agent cases, hybrid-workflow distinction, and adoption question into one initial design decision.",
    references=[("Anthropic: Building effective agents", "https://www.anthropic.com/engineering/building-effective-agents", "Workflows versus agents, and the patterns used in chapter 4.")]),

lesson("define-the-task-contract", "Define the task and what counts as done", [7, 160],
    "Before designing anything, write a **task contract**: what the agent must achieve, what it may touch, what counts as done, and what happens when information is missing. Every later choice (tools, stored state, tests, who handles stuck work) follows from it.", [
    section("Questions to settle first", """
        - **Outcome:** what result counts as success, and which system confirms it?
        - **Users and data:** who uses the agent, what data can it see, and do several customer organizations share it?
        - **Actions:** which actions are allowed, which need approval, and which are forbidden?
        - **Limits:** how fast and how cheap must each task be, and how many tasks per day?
        - **Failure:** what happens when information is missing, a tool fails, or only part of the work succeeds? Who takes over a stuck task?
        - **Testing:** which test cases will show it works before launch?
    """),
    section("The contract for the running example", """
        Throughout this guide, a customer asks for $80 back on order 42, a $120 jacket. "Handle this refund" can't be finished or checked. This can:
    """, code("A task contract", """
        task = {
            goal:       "Decide on the refund request for order 42 and issue it if eligible",
            scope:      {user: <from the logged-in session>, order: 42},
            may:        [get_order, get_refund_policy, issue_refund],
            may_not:    [change_shipping_address, refund_other_orders],
            done_when:  one of [refund receipt from the payment service,
                                written reason why it is not eligible,
                                handed to a named person],
            limits:     {active_time: 10 min, approval_wait: 24 h,
                         max_steps: 15, max_model_spend: $0.50},
            if_missing: ask the customer; never guess an amount or an account,
            owner:      support-escalations queue
        }
    """, "The user and scope come from the logged-in session, never from text the model writes."), """
        - **"Done" needs proof.** A reply saying "Your refund is processed" is not completion; a payment receipt is. A justified refusal or a handoff to a person also counts, because the contract says so.
        - **Missing information has a path.** If the customer has two open orders, ask which one instead of guessing. Lookups that don't depend on the answer can continue meanwhile.
    """),
    section("From contract to rollout", """
        A typical build order, with the chapter that covers each step:

        1. Contract and success measure (this chapter).
        2. Test cases with expected outcomes (this chapter).
        3. A minimal agent loop (chapter 2).
        4. Tools with permission checks (chapter 3).
        5. Saved progress and safe retries, so crashes don't repeat payments (chapter 5).
        6. Offline tests, then a trial on copied traffic, then a small live release (chapter 7).
        7. Monitoring, alerts, and an emergency stop (chapter 11).
    """),
], "Turn the requirements checklist into a concrete task contract and a build sequence."),

lesson("measure-real-outcomes", "Measure real outcomes, not good-sounding replies", [6, 104, 153],
    "Success means the requested result actually happened, safely, as confirmed by the system that owns the data. A well-written reply is not evidence. The best single summary metric is **cost per verified outcome**, tracked next to safety and user metrics it can't replace.", [
    section("A good reply is not a done task", """
        Check the order system, not the agent's words:
    """, table("One reply, three outcomes", ["Order system shows", "Reply “Your order is cancelled” is", "Task"], [
        ["Order 42: `CANCELLED`", "True", "Success"],
        ["Order 42: still `ACTIVE`", "False, though it reads perfectly", "Failure"],
        ["Cancel call returned `FORBIDDEN`", "Misleading", "Failure"],
    ]), """
        Say what a rate is out of. "Success out of all requests", "out of eligible requests", and "out of attempted tasks" are three different numbers. Count escalated and unresolved tasks as their own categories instead of leaving them out.
    """),
    section("Cost per verified outcome", """
        Divide everything you spent, on **all** attempts including failures, retries, and human review, by the number of outcomes that were verified and followed policy.
    """, table("Cheaper attempts, more expensive results", ["100 tasks each (illustrative)", "Total spend", "Verified successes", "Cost per success"], [
        ["Design A", "$100", "80", "$1.25"],
        ["Design B", "$80", "40", "$2.00"],
    ]), """
        One ratio can't capture everything, so track these next to it:

        - **Policy violations.** One unauthorized refund is an incident, not a cost to average away.
        - **End-to-end time,** typical and slowest (p50 and p95).
        - **Escalation rate** and time spent by people reviewing.
        - **User outcome,** such as satisfaction or repeat contacts.
    """),
], "Combine the repeated success, response-versus-outcome, and primary-efficiency-metric explanations; keep SLO mechanics for operations."),

lesson("build-golden-task-cases", "Build a golden test set", [102],
    "A **golden set** is a versioned collection of realistic test tasks. Each task has a fixed starting state, the expected outcome, and the effects that must never happen. Tests check what the agent did and the resulting state, not its exact wording.", [
    section("What one test case contains", """
        A case runs automatically and is scored by inspecting state.
    """, code("A golden case", """
        case "duplicate-invoice":
            input:    "Please process invoice INV-42"
            setup:    the test ledger already contains INV-42
            expect:   no new ledger entry; the reply says it is a duplicate
            never:    change the vendor's bank details
            check:    query the test ledger after the run
    """), """
        The `never` line is an **invariant**: a rule that must hold whatever else happens. Cover more than the easy path:

        - normal requests, in proportion to real traffic;
        - unclear requests that should lead to a question;
        - invalid input, duplicates, and missing fields;
        - permissions that change mid-task;
        - every failure you have seen in production.
    """),
    section("Keep scores honest", """
        - **Version** the cases and the scoring rules, so every score refers to a known test.
        - **Keep a held-out set.** Tune prompts on one set of cases and report results on another that you never tune against. Otherwise the test set slowly becomes training data.
        - **Keep a fixed core** for comparisons over time, and add fresh samples of recent real traffic.
        - **Report by category.** A 95% average can hide 0% on rare but serious cases.
    """),
], "Expand the dataset definition into a usable fixture contract and add held-out evaluation and contamination prevention."),

lesson("set-risk-and-autonomy", "Set autonomy per action", [5, 92, 93, 154],
    "Decide autonomy action by action, not for the whole agent. Low-risk, reversible actions can run automatically. Costly or irreversible ones need a person to approve the exact action, and some should never be available. Give the agent more freedom in stages, and only when measured results support it.", [
    section("Rate each action's risk", """
        Ask four questions about each action: can it be undone; how much damage can one mistake do (its **blast radius**: money, records, or people affected); how sensitive is the data; and can the result be checked automatically?

        Put a person in the loop (**human-in-the-loop**) when an action is costly, hard to undo, or can't be checked automatically. Approval can't grant something the user isn't allowed to do anyway.
    """, table("Risk levels for the refund agent", ["Action", "Risk", "Control"], [
        ["Read the status of order 42", "Low", "Automatic"],
        ["Refund up to $50 on an eligible order", "Moderate", "Automatic, logged"],
        ["Refund over $50 on an eligible order", "High", "A support lead approves the exact refund"],
        ["Delete a customer account", "Critical", "Not available to the agent"],
    ], "Thresholds are examples; set yours from the cost of a mistake.")),
    section("Increase autonomy in stages", """
        Each stage needs evidence before the next.
    """, table("A phased rollout", ["Stage", "The agent may", "Move on when"], [
        ["1. Read-only assistant", "Look things up, draft suggestions", "Offline tests meet the quality target"],
        ["2. Narrow tools", "Run read tools, propose changes", "Proposals are correct on the test set; actions are logged"],
        ["3. Approved actions", "Make a change after a person approves that exact change", "Reviewers rarely edit proposals; recovery from failed changes is tested"],
        ["4. Limited autonomy", "Make low-risk changes on its own", "The error rate stays below its limit in production"],
    ]), """
        Plan the way back too: if the error rate crosses its limit, drop back to stage 3 automatically. Time spent in a stage proves nothing; results do.
    """),
], "Merge the autonomy ladder, risk tiers, approval triggers, and phased roadmap; reserve approval implementation for its own lesson."),

lesson("separate-proposals-from-authority", "The model proposes; code decides", [8, 18, 91, 97],
    "The model suggests actions. Plain, **deterministic** code (code that always gives the same answer for the same input) decides whether each action is allowed, and enforces it. Identity, permissions, limits, and business rules are checked in code right before every action, because a model can misread, ignore, or be tricked out of instructions in a prompt.", [
    section("Check right before the action", """
        Suppose the model proposes `issue_refund(order=42, amount=80)`. Before any money moves, code checks:

        - Does the logged-in user own order 42?
        - Is `issue_refund` one of this task's allowed actions?
        - Is $80 no more than what is still refundable?
        - Is $80 under the automatic limit, or does it need approval?

        The payment service checks the balance once more when it pays, in case another refund landed in between.
    """, table("Model or code?", ["Leave to the model", "Keep in code"], [
        ["Understanding the customer's message", "Who the user is and what they may do"],
        ["Choosing among allowed tools", "Amounts, totals, and limits"],
        ["Writing replies and summaries", "Policy rules and approval requirements"],
        ["Suggesting a plan", "Task state changes, retries, duplicate protection"],
    ], "Rule of thumb: if a rule can be written as code and a wrong call is costly, write it as code.")),
    section("A separate policy check", """
        A **policy engine** checks each proposed action against rules stored as data, outside any prompt. Open Policy Agent and Cedar are examples. It answers allow, deny, or needs approval. Record each answer with the rule version, so you can explain the decision later.
    """, code("Policy decides, then the tool runs", """
        decision = policy.evaluate(user, task.scope, proposal, current_state)
        audit.record(proposal, decision, policy.version)
        match decision:
            DENY:           return refuse(decision.reason)
            NEEDS_APPROVAL: return pause_for_approval(proposal)   # for this exact proposal
            ALLOW:          return tools.execute(proposal)        # the service rechecks its own rules
    """)),
    section("Spot an agent going off task", """
        Since every action passes through the policy check, straying becomes visible:

        - Calls to tools outside the task are denied and logged; a rising denial rate raises an alert.
        - Unusual targets are flagged, such as a refund agent reading many unrelated customers.
        - Step counts or costs far above normal suggest the agent has lost its way.
        - People regularly review a sample of complete runs (chapter 7).
    """),
], "Bring deterministic enforcement, policy engines, critical-code boundaries, and objective checking together before tool use is introduced."),

lesson("map-the-system", "The parts of a production agent", [9, 10, 11],
    "A production agent is an ordinary application built around a model. Its main parts are an orchestrator that runs the loop and enforces limits, a context builder, a model gateway, a tool gateway that checks permissions, a durable store, and monitoring. Most production failures come from one of these parts, not from the model.", [
    section("Follow one request", """
        1. The **API gateway** (the front door) checks who the user is and applies usage quotas.
        2. The **orchestrator** (the program that runs the agent loop) creates a task record in the **durable store**, a database that survives crashes.
        3. The **context builder** gathers what the model needs for its next decision.
        4. The **model gateway** sends the request to a suitable model and returns its decision.
        5. If the model proposes a tool call, the **tool gateway** checks it and, if allowed, passes it to the service that does the work.
        6. The result is saved, and the loop repeats until the outcome is verified.
    """, flow("How the parts connect", [
        ("api", 1, 0, "API gateway\nidentity · quotas", "start"),
        ("context", 0, 1, "Context builder\npermitted information"),
        ("orch", 1, 1, "Orchestrator\nloop · state · limits"),
        ("model", 2, 1, "Model gateway\nchoose model · fallback"),
        ("store", 0, 2, "Durable store\ntasks · actions taken"),
        ("tools", 1, 2, "Tool gateway\ncheck · authorize"),
        ("services", 2, 2, "Services\nown business rules"),
    ], [
        ("api", "orch", "request"),
        ("context", "orch", "context"),
        ("orch", "model", "prompt"),
        ("model", "orch", "decision"),
        ("orch", "store", "save"),
        ("orch", "tools", "proposed call"),
        ("tools", "services", "allowed call"),
    ], "These are roles, not separate deployments; a small system can run several in one service. Every part reports logs and metrics.")),
    section("Common failures and where to fix them", """
        Fix the part that failed, rather than adding another sentence to the prompt.
    """, table("Symptom, cause, fix", ["Symptom", "Usual cause", "Fix in"], [
        ["Wrong tool chosen", "Vague tool descriptions; too many tools", "Tool design, routing"],
        ["Customer refunded twice", "A retry without duplicate protection", "Operation IDs (chapter 5)"],
        ["Task lost after a restart", "Progress kept only in memory", "Durable store"],
        ["Another customer's data in an answer", "Search not filtered by user", "Permission checks (chapters 3 and 6)"],
        ["Endless loop and a large bill", "No step or cost limit", "Orchestrator limits"],
        ["Confident but wrong answer", "No verification", "Verification step (chapter 2)"],
        ["Quality drops after a release", "Prompt or model changed without tracking", "Versioning, release checks"],
    ])),
], "Merge component lists, the reference architecture, and the production-failure overview into one system map."),
]
