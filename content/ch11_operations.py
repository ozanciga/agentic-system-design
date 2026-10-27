from authoring import code, lesson, section, table

CHAPTER = ("Operations", "Watch the system in production, catch quality drops, stop failures fast, and keep a record of what happened.")

LESSONS = [

lesson("connect-logs-metrics-and-traces", "Logs, metrics, and traces", [131, 132],
    "**Metrics** are counts and rates over time, showing how widespread a problem is. **Logs** record individual events. A **trace** follows one task across every model, policy, and tool call. Link all three with task and operation IDs, and record what the agent decided and did, not its internal reasoning.", [
    section("Three views of one failure", """
        Each answers a different question.
    """, table("Metrics, logs, traces", ["Signal", "Example", "Answers"], [
        ["Metric", "Tool timeout rate rose to 8%", "How widespread is it?"],
        ["Log", "`inventory.get` timed out for operation op-42", "What happened in this one event?"],
        ["Trace", "task → model → inventory → retry → timeout", "Where did this task spend its time, and where did it fail?"],
    ])),
    section("What a trace records", """
        A trace is made of **spans**: one timed entry per step, such as a model call, a policy check, or a tool call.
    """, code("One task's trace", """
        task t-9  refund@14  refund-agent@31  model-x-2026-09          8.4 s
        ├─ model.decide        3.1k in / 120 out tokens                    1.2 s
        ├─ tool get_order(42)  op-5   OK                                   0.3 s
        ├─ model.decide        3.4k in / 90 out                            1.1 s
        ├─ policy.check        issue_refund $80 → NEEDS_APPROVAL           0.02 s
        │   … waiting for approval (not counted as active time)
        └─ tool issue_refund   op-42  TIMEOUT → lookup → OK, receipt R-981  5.6 s
    """), """
        For each span, record the versions in use, token counts, duration, error codes, the decision, the proposed call, the policy result, and links to sources. Connect spans across agents with the parent task ID.

        Prefer IDs and summaries over full prompts and documents (see *Audit trails without leaking data*). Monitor the decisions and actions you can observe; don't build monitoring that depends on reading a model's internal reasoning.
    """),
], "Merge telemetry signals and tracing, with a concrete trace and the distinction between execution evidence and private model reasoning."),

lesson("set-slos-and-operating-thresholds", "SLOs and what to do when they're missed", [133],
    "An **SLO** (service-level objective) is a target for something you measure (speed, verified success, uptime, how quickly people pick up escalations) over a set group of requests and time window. Each missed target triggers an action decided in advance. Safety violations are not SLOs: their target is zero, and every single one is an incident.", [
    section("Example SLOs", """
        Define exactly what counts: which tasks are included, what "success" means, how tasks waiting on users or approvals are handled, and over what period.
    """, table("Example SLOs", ["Measure", "Target", "Period"], [
        ["Interactive reply time, p95", "Under 8 s", "28 days"],
        ["Verified task success, eligible requests", "At least 90%", "7 days"],
        ["Task service uptime", "99.9%", "30 days"],
        ["Escalations picked up by a person", "95% within 1 hour", "7 days"],
        ["Unauthorized actions", "Zero: each one is an incident", "Always"],
    ], "Set targets from what the product needs and from what you measure today. Background jobs and interactive requests need different measures.")),
    section("Decide the response in advance", """
        A 99.9% uptime target allows 0.1% failure in its period; that allowance is the **error budget**. Using it up fast is a signal to act. Missing a target should trigger a decision made beforehand, not a debate:

        - **Error budget burning fast:** alert the owner and pause any rollout in progress.
        - **Success below target on one route:** switch that route back to the previous version or a backup.
        - **Too slow because of load:** accept less batch work.
        - **Any unauthorized action:** start incident response and use the kill switch for that action (see *Kill switches and incident response*).

        Link every alert to example traces, so investigation starts from evidence.
    """),
], "Keep operational SLO definitions distinct from the earlier business-outcome measures and release gates."),

lesson("detect-drift-and-debug-regressions", "Quality drift and debugging regressions", [134, 136, 158],
    "Quality can slowly change (drift) as models, prompts, tools, documents, and users change. Test continuously on two sets: a fixed set, which shows whether **your system** changed, and fresh samples of real traffic, which show whether **the work** changed. When success drops after a release, limit the damage first, then find what changed and reproduce the failure safely.", [
    section("Watch fixed and fresh cases", """
        Many things drift: the model (a provider update), prompts, tools, source documents, permissions, and what users ask for.

        - Run the **fixed set** on a schedule to see whether your system changed on the same work.
        - Score **sampled real tasks** with the same checks to see whether the work changed.

        Break both down by task type and version, so you can see where a drop is.
    """),
    section("Example: success drops right after a release", """
        1. **Check it's real.** Is the sample big enough? Did the measurement itself change?
        2. **Limit the damage.** If the impact is serious, roll back or send traffic to the previous version now, and investigate afterwards.
        3. **Find what changed:** prompt, model, tools, policy, data, or the mix of requests. Break success down by version and task type.
        4. **Compare traces.** Put failing and passing runs side by side, and find the first step where they differ.
        5. **Reproduce** in a test environment using recorded tool results, so nothing real is changed.
        6. **Fix and protect.** Add the failing cases to the golden set, then release again through the release checks.
    """),
    section("Debugging failures that come and go", """
        The same input can pass once and fail the next time, because model output varies.

        - Record what's needed to re-run a task: inputs, versions, model outputs, and tool results.
        - Re-run with the recorded tool results, so only the model varies.
        - Run the failing case many times to measure **how often** it fails; one passing re-run proves nothing.
        - If the model or outside data has changed since, exact reproduction may be impossible. Capture the failure pattern in a new test instead.
    """),
], "Merge drift monitoring, nondeterministic debugging, and the deployment-regression scenario into one detection-to-repair workflow."),

lesson("contain-incidents-and-stop-actions", "Kill switches and incident response", [138, 139],
    "A **kill switch** is a setting, outside the model, that immediately stops a capability or workflow from taking new actions. The scheduler checks it before starting work, and the tool gateway checks it before every action, so the model doesn't need to cooperate. Incident response then keeps the evidence, reconciles actions already in progress, fixes the cause, and restarts gradually.", [
    section("Where the switch is checked", """
        Check it at two points: before work starts, and right before every action.
    """, code("Kill-switch checks", """
        scheduler.before_start(task):
            require settings.enabled(task.workflow, task.tenant)

        tool_gateway.before_action(call):
            require settings.enabled(call.capability)     # e.g. "issue_refund"
            require fence_is_current(call.task_id)
    """, "If the settings service can't be reached, block actions (“fail closed”). A payment already accepted still needs reconciling."), """
        Make switches fine-grained: one action (refunds), one workflow, one tenant, or everything. A switch that can only stop everything gets used too late, because flipping it costs too much.
    """),
    section("Incident response steps", """
        1. **Find the scope:** which tasks, tenants, data, and actions are affected?
        2. **Contain:** flip the right switch; stop accepting new work if needed.
        3. **Keep evidence:** traces, audit records, versions.
        4. **Reconcile** in-progress and uncertain actions by operation ID.
        5. **Fix the cause** and add tests for it.
        6. **Restart gradually,** with an owner and clear conditions, watching the rule that broke.
    """),
], "Merge kill switches and incident response into a concrete containment-and-recovery sequence."),

lesson("observe-without-exposing-payloads", "Audit trails without leaking data", [99, 140],
    "An **audit trail** is an append-only record of who asked for what, what was proposed, what the policy and approvers decided, and what actually happened, with versions and times. Keep it complete enough to reconstruct events but lean: by default record IDs and summaries rather than content, never keys or passwords, and send any sensitive content through a separate, restricted path that is deleted quickly.", [
    section("What an audit record contains", """
        Enough to answer "why did this money move?" months later.
    """, code("An audit record", """
        audit.append({
            time, task_id, operation_id,
            actor: {user_id, agent_service}, tenant_id,
            versions: {workflow, prompt, model, policy},
            proposal_fingerprint, policy_decision, approval_id,
            observed_outcome               # e.g. receipt R-981, or "unknown, reconciling"
        })
    """, "Store it so entries can be added but never changed, and restrict who can read it. It records what was proposed, allowed, and observed, not merely what was intended.")),
    section("Monitoring without exposing data", """
        Logging full prompts by default turns your monitoring system into a second copy of all customer data.
    """, code("Monitoring events without content", """
        event = only_listed_fields(task_id, operation_id, duration, error_code, token_counts)
        event += versions(prompt, model, workflow)
        require not contains_secrets_or_personal_data(event)       # a scanner as a backstop
        monitoring.write(event, readers = "ops-team", keep_for = 30 days)
        # Full-content debug capture: separate store, needs approval, deleted quickly
    """), """
        Decide who can read each kind of monitoring data, and apply the same retention and deletion rules to search indexes and exports. Removing sensitive parts after the fact is a backstop; not collecting them is the real protection.
    """),
], "Merge audit content and privacy-preserving telemetry so evidence quality and data minimization are designed together."),
]
