from authoring import lesson, section, table

CHAPTER = ("Platform and organization", "Choose infrastructure, share it across teams, and keep reviewing the design as things change.")

LESSONS = [

lesson("choose-build-versus-buy", "Build or buy", [19, 155],
    "List what your tasks require (crash recovery, acting on the user's behalf, data-location rules, duplicate-safe tools, testing, monitoring), then test candidate platforms against that list using your own failure cases. Buy what fits; build only where your business rules or security needs demand control. Count the ongoing cost of running whatever you build.", [
    section("Test what matters, not the feature list", """
        A demo of the happy path tells you little. Run one small end-to-end task on each candidate, and break it on purpose.
    """, table("Questions for an agent platform", ["Need", "Ask, then test"], [
        ["Crash recovery", "Kill a worker mid-task. Does it resume without repeating a tool call?"],
        ["Identity", "Can tools act for the end user, with limited, short-lived tokens?"],
        ["Data handling", "Where are prompts, logs, and memory stored? Can you choose the region and how long data is kept?"],
        ["Tools", "Can you put your own tool gateway and policy checks in the path?"],
        ["Versioning", "Are prompts, tools, and workflows versioned? What happens to running tasks during a release?"],
        ["Testing and monitoring", "Can you export traces and run your golden set automatically?"],
        ["Leaving", "Can you move workflows, data, and tests elsewhere if needed?"],
    ])),
    section("Build where control matters", """
        Reuse proven infrastructure where it fits: workflow engines, identity providers, secret managers, monitoring tools. Build what is specific to your business: your tools, policy rules, test cases, and the approval experience.

        Include the long-term cost: engineering time, being on call, upgrades, and who will maintain it in two years. Building your own crash recovery or key management is rarely worth it, and the cost never stops.
    """),
], "Merge managed-runtime selection and build-versus-buy, which repeated the same decision criteria."),

lesson("share-platform-contracts", "Shared platform and team ownership", [14, 151, 156, 159],
    "Split a shared platform into a **control plane**, which manages configuration (versions, permissions, routing, rollouts), and a **data plane**, which runs the tasks using that configuration. Share the common pieces (gateways, crash recovery, tracing, testing tools) and leave business tools, rules, and success criteria with product teams. Grow adoption through a few clearly successful workflows, not mandates.", [
    section("Control plane and data plane", """
        The control plane decides **what** may run; the data plane runs it. A running task can read its configuration but never change it, so a manipulated agent can't grant itself permissions.
    """, table("Two planes", ["Control plane", "Data plane"], [
        ["Publish prompt version 31", "Run a task using prompt version 31"],
        ["Set the refund agent's tool permissions", "Check each proposed call against them"],
        ["Set quotas and model-routing rules", "Use quota; route each model call"],
        ["Flip a kill switch", "Stop starting the affected work"],
    ])),
    section("Who owns what", """
        Shared services make the common protections easy to get right; product teams stay responsible for their results.
    """, table("Platform team vs. product team", ["Platform team owns", "Product team owns"], [
        ["Identity, model gateway, tool gateway", "Business tools and rules"],
        ["Crash recovery, queues, tracing", "Workflows, prompts, task contracts"],
        ["Testing tools, release checks", "Golden cases and success criteria"],
        ["Policy engine, kill switches", "Risk levels for their own actions"],
    ], "Write ownership down, including who is on call for each part, and revisit it as teams change.")),
    section("Growing adoption across teams", """
        - **Start with two or three workflows** that have clear owners and measured baselines, and share the results, including what failed.
        - **Make the safe way the easy way:** templates, examples, and default release checks.
        - **Name owners** for security review, platform operations, and incident response.
        - **Expand when results justify it.** Track migrations, support load, and cost alongside usage.
    """),
], "Merge control/data planes, platform reuse, organizational adoption, and ownership into practical ownership decisions."),

lesson("review-and-evolve-the-architecture", "Architecture review checklist", [20],
    "Review an agent design by following one real task from start to finish: where identity comes from, where each rule is enforced, what happens to every action on retry or crash, and how outcomes are confirmed. Then ask what can be removed, and what still needs evidence.", [
    section("The checklist", """
        Follow one task, such as "refund order 42", and ask:

        - **Contract:** is "done" defined and checkable? Who takes over a stuck task?
        - **Permissions:** where does identity come from? Is each permission and limit enforced in code, or only stated in a prompt?
        - **Actions:** for each action, what happens on a duplicate message, a lost response, a stale worker, or a changed permission?
        - **Sources:** for each source, how are access, freshness, corrections, and deletion handled?
        - **State:** can any worker crash at any point without losing progress or repeating an action?
        - **Testing:** is there a golden set with invariants? Do releases pass checks?
        - **Operations:** are there traces, SLOs, a kill switch, and an audit trail?
    """),
    section("Simplify, then prove the next step", """
        Compare the design with the simplest version that could work, and remove agents, steps, and tools without a measured purpose. Every part should have a reason you can point to in the test results.

        Record open risks, owners, planned experiments, and the conditions for rolling out and rolling back. Revisit them when the workload, a dependency, a policy, or the evidence changes.
    """),
], "Retain a closing architecture review that applies the learned boundaries to a complete task as a checklist.",
    related=["define-the-task-contract", "compare-designs-with-controlled-experiments", "gate-releases-and-canaries"]),
]
