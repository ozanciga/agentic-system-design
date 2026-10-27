from authoring import code, lesson, section, table

CHAPTER = ("Multi-agent systems", "Add agents only where they clearly help, and keep the work they hand to each other limited.")

LESSONS = [

lesson("justify-multiple-agents", "When to use multiple agents", [61, 69],
    "Start with one agent and good tools. Split the work across several agents only when a clear, measured reason exists: different permissions, a distinct skill, or independent work that benefits from running in parallel. Multi-agent systems often do worse than one agent, because information is lost between agents, calls multiply, and mistakes spread.", [
    section("Good and bad reasons to split", """
        Compare any split against a single agent on the same golden set (chapter 7).
    """, table("When a second agent earns its place", ["Good reason", "Example"], [
        ["Different permissions", "A legal-review agent may read privileged documents; the support agent may not"],
        ["A distinct skill or tool set", "A data-analysis agent with a sandboxed Python environment"],
        ["Independent parallel work", "Researching ten companies at once to meet a deadline"],
        ["Different owners", "Another team runs, and answers for, the finance agent"],
    ], "Weak reasons: “the prompt is long”, “it mirrors our org chart”, “more agents seem smarter”.")),
    section("Why more agents can do worse", """
        - **Information is lost at each handoff:** the second agent never sees what the user actually said.
        - **Calls multiply:** cost and time often grow several times over, for a small quality gain.
        - **Mistakes spread together:** agents on the same model share the same blind spots, so their agreement doesn't confirm anything.
        - **Coordination breaks:** duplicated work, conflicting results, agents waiting on each other in circles.
        - **Debugging is harder,** because one failure is spread over several agents' records.

        If you do split, give each agent a limited job: a goal, inputs, permissions, an output format, a deadline, and an owner. The agent that delegated stays responsible for checking the result.
    """),
], "Merge multi-agent selection and its failure costs into one evidence-based architecture decision."),

lesson("supervise-bounded-specialists", "The supervisor pattern", [24, 62],
    "In the **orchestrator–worker** pattern, also called the supervisor pattern, one agent breaks a task into pieces, gives each to a worker agent with clear limits and an output format, checks what comes back, and writes the final result. The supervisor answers for the whole task; each worker answers only for its piece.", [
    section("Assign work with clear terms", """
        Unlike a fixed parallel workflow, the pieces aren't known in advance: the supervisor decides them from the request. Each assignment states what to return and how it will be checked.
    """, table("A due-diligence report, split up", ["Worker", "Assignment", "Returns", "Supervisor checks"], [
        ["Research", "Find the company's last 3 years of public filings", "Claims with citations", "Every citation opens"],
        ["Analysis", "Compute revenue growth and margin from the filings", "Numbers and how they were computed", "Recompute in code"],
        ["Review", "List risks and contradictions in the findings", "A list of issues", "Each issue points to a finding"],
    ], "These three run in order, since each needs the previous output. Independent pieces, such as one research worker per year, can run in parallel."), """
        When workers edit shared files, give each file one owner so workers don't overwrite each other.
    """),
    section("Check before combining", """
        - Check each result's format, sources, and coverage before using it.
        - A worker that fails or times out leaves a visible "missing" entry; it must not silently vanish from the report.
        - Running the team gives the supervisor no extra permissions. Its actions still pass through the tool gateway.
    """),
], "Merge orchestrator-worker and supervisor architecture, which described the same coordination shape."),

lesson("choose-handoffs-and-peer-messages", "Handoffs, agents as tools, and peer-to-peer", [63, 64],
    "In an **agent-as-tool** design, one agent calls another like a tool, gets a result, and stays in charge. In a **handoff**, the second agent takes over the conversation with the user. In a **peer-to-peer** design, agents message each other directly with no one in charge, which still needs clear rules on ownership, deadlines, and when to stop.", [
    section("Handoff or agent-as-tool?", """
        The difference is who talks to the user next.
    """, table("Handoff vs. agent-as-tool", ["", "Agent as a tool", "Handoff"], [
        ["Flow", "First agent → second → back to first", "First agent → second (stays)"],
        ["Talks to the user next", "The first agent", "The second agent"],
        ["Example", "Ask a reviewer agent to check a contract clause", "Pass a support chat to the billing agent"],
        ["Information passed", "Just the sub-task", "A conversation summary and the user's permissions"],
    ])),
    section("Peer-to-peer", """
        Each agent owns its own work and messages the others directly: A asks B, B asks C, C answers A. This suits work spread across teams or organizations. It fits poorly when a business process needs one result that someone answers for.

        Having no one in charge doesn't remove the need for rules. Before allowing open-ended messaging, decide:

        - who owns the overall task and declares it done;
        - deadlines on every request, and what happens when an agent doesn't answer;
        - how disagreements are settled;
        - a limit on message rounds, so two agents can't go back and forth forever.
    """),
], "Combine interaction ownership and peer topology while keeping their distinct tradeoffs as separate sections."),

lesson("define-agent-message-contracts", "MCP vs. A2A, and agent-to-agent messages", [65, 66],
    "**MCP** connects an agent to tools and data: the server does what it is asked. **A2A** (Agent2Agent) connects independent agents: the receiving agent accepts a task, decides how to do it, and reports progress and results, sometimes over hours. Either way, send a limited task rather than the whole conversation, and take permissions from verified credentials, never from what the message claims.", [
    section("Different jobs", """
        The two overlap at the edges (an agent can be offered as an MCP tool), but the key difference is who decides how the work gets done.
    """, table("MCP vs. A2A", ["", "MCP", "A2A"], [
        ["Connects", "Agent ↔ tools and data", "Agent ↔ independent agent"],
        ["Unit of work", "A tool call or data read, usually quick", "A task with status updates and results; can run long"],
        ["The other side", "Does exactly what it's asked", "Decides how to do the task"],
        ["Example", "Look up customer records", "Ask the finance team's agent to match an invoice to its order"],
    ])),
    section("What a message to another agent contains", """
        A limited task, not the whole conversation:
    """, code("A delegation message", """
        message = {
            task_id, parent_task_id, correlation_id,
            sender, recipient,
            goal:            "Match invoice INV-42 to purchase order PO-7",
            inputs:          ["doc://invoices/INV-42", "erp://po/7"],
            allowed:         {items: [INV-42, PO-7], actions: [read]},
            expected_output: MatchResult format,
            deadline:        2026-10-26T14:00Z
        }
        permissions = from the verified connection (mTLS) or a signed token, never from `allowed`
    """, "`allowed` tells the receiving agent its limits. Enforcement comes from credentials it can't edit. mTLS is a connection where both sides prove who they are with certificates.")),
], "Merge protocol comparison and message structure, adding long-running task status and avoiding an overly absolute MCP/A2A distinction.",
    references=[("A2A key concepts", "https://a2a-protocol.org/latest/topics/key-concepts/", "Tasks, messages, results, and authenticated communication between agents.")]),

lesson("constrain-delegation-and-cycles", "Safe delegation without loops", [67, 70],
    "A task handed to another agent may receive only part of its parent's permissions and budget, never more. Track each task's parent, depth, and deadline, so circular waits (A waits for B while B waits for A) are refused before they start, and endless re-delegation is stopped.", [
    section("Delegate less, never more", """
        The risk is a child agent receiving wider permissions than its parent had: "it's just reading invoices" turns into permission to change the accounting ledger.
    """, code("Narrowing permissions when delegating", """
        require child.requested_scope ⊆ parent.scope
        child_scope = child.requested_scope ∩ caller.permissions ∩ worker.policy
        token       = issue_delegated_token(child_scope, expires = child.deadline)
        worker.run(child, token)            # every tool checks the token on every call
    """)),
    section("Prevent circular waits and loops", """
        Give every task a fixed ID and a link to its parent, and check for a cycle before adding a new dependency.
    """, code("Checks before delegating", """
        require child.depth <= MAX_DEPTH                     # e.g. 3
        require child.deadline <= parent.deadline            # delegating can't add time
        require child.budget  <= parent.remaining_budget
        if graph.would_create_cycle(parent, child): reject("cycle")
        if reassigned_repeatedly_without_progress(child): escalate(parent)
        graph.add_dependency(parent, child, owner = parent.owner)
    """, "Detect cycles by task ID, not by comparing prompt wording: two differently worded requests can be the same work.")),
], "Merge security and termination constraints of delegation because both must travel with the same child task."),
]
