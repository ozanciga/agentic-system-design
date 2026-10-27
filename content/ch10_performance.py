from authoring import code, lesson, section, table, timeline

CHAPTER = ("Latency, cost, and scale", "Make the whole task fast and affordable without giving up correctness or isolation.")

LESSONS = [

lesson("measure-critical-path-latency", "Latency and the critical path", [111, 112, 113],
    "A task's total time (its latency) is set by its **critical path**: the longest chain of steps that must happen one after another, including queueing, model and tool calls, retries, and checks. Steps running in parallel count only as long as the slowest one. To cut latency, first remove calls, then run independent steps in parallel, cache, stream the reply, and use smaller models where quality allows.", [
    section("Add up the critical path", """
        `total = queue + sum(steps in sequence) + slowest(parallel steps) + coordination`

        Below, the two reads don't depend on each other. Running them together saves 2 seconds (the shorter read), not 6, because the model step still waits for the slower read.
    """, timeline("One task, reads in sequence vs. in parallel", [
        ("In sequence", [(0, 1, "queue"), (1, 3, "read A"), (3, 7, "read B"), (7, 11, "model"), (11, 12, "check")]),
        ("Parallel, branch 1", [(0, 1, "queue"), (1, 3, "read A")]),
        ("Parallel, branch 2", [(1, 5, "read B"), (5, 9, "model", "alt"), (9, 10, "check")]),
    ], "Example seconds. Parallel: 1 + max(2, 4) + 4 + 1 = 10 s, versus 12 s in sequence.", markers=[(10, "parallel"), (12, "sequence")]), """
        To reduce latency, roughly in this order:

        1. **Remove work:** drop unneeded model calls, merge small ones, stop resending repeated context.
        2. **Run independent steps in parallel.**
        3. **Cache** what is safe to reuse (see *Caching safely*).
        4. **Use a smaller, faster model** where it meets the quality bar.
        5. **Stream** the final reply, so the user sees it as it's written.
    """),
    section("Why many parallel branches hurt the slowest requests", """
        Averages hide the slow cases, so measure **percentiles**. **p95** is the time that 95% of requests finish within; the slowest few percent are the **tail latency**.

        Parallel work finishes when its slowest branch does, and the more branches you start, the likelier one is slow. If each branch has a 1% chance of being slow, the chance that at least one of 10 is slow is 1 − 0.99^10 ≈ 9.6%.
    """, timeline("Combining results waits for the slowest branch", [
        ("Worker A", [(0, 2, "done")]),
        ("Worker B", [(0, 3, "done")]),
        ("Worker C", [(0, 9, "slow branch", "bad")]),
        ("Combine", [(9, 11, "combine")]),
    ], "The average branch takes about 4.7 s, but combining can't start until 9 s.", markers=[(9, "starts")]), """
        To control the tail: cap the number of branches, give each a deadline, and return a clearly labeled partial result when the task allows it. For slow **reads** only, you can send a **hedged request**: a duplicate sent to another server, keeping whichever reply arrives first.
    """),
], "Merge sequential latency, optimization advice, and parallel tail latency into one critical-path lesson."),

lesson("budget-total-cost", "Cost per task", [121, 130],
    "Add up everything a task costs (model tokens, tool and search calls, infrastructure, retries, and human review), then divide total spending by the number of verified successful outcomes. Human review and failed attempts often cost more than the tokens, so optimize the whole process, not the price of each call.", [
    section("A worked estimate", """
        The prices below are made up; use your provider's current prices and your own measured usage.
    """, code("Cost per verified outcome (example)", """
        per attempt:
          model:  6 calls, 18k input + 2.4k output tokens
                  at $3 per million input, $15 per million output  = $0.054 + $0.036 = $0.090
          tools and search                                         = $0.010
          servers, storage, monitoring                             = $0.005
                                                                   ≈ $0.105

        per 100 attempts:
          attempts           100 × $0.105              = $10.50
          human review        10 escalations × $4.00    = $40.00
          verified outcomes  85 automatic + 10 reviewed = 95
          cost per outcome   $50.50 / 95                ≈ $0.53
    """, "Human review is about 80% of the cost here: halving escalations saves more than halving the token bill.")),
    section("Optimize the whole process", """
        For example, in a research workflow:
    """, table("Where strong models are worth it", ["Step", "Before", "After"], [
        ["Classify the request", "Large model", "Rules or a tested small model"],
        ["Search independent topics", "One after another", "In parallel, within limits"],
        ["Prepare context", "Full history on every call", "Selected passages and links"],
        ["Write the report", "Large model", "Large model, given checked sources"],
    ]), """
        After each change, confirm the verified success rate held. A smaller token bill isn't a saving if more results need fixing by hand.
    """),
], "Merge cost estimation and the system-level optimization example; add a worked estimate showing human review dominating."),

lesson("cache-with-permission-and-freshness", "Caching safely", [123],
    "Many things can be cached: the fixed start of a prompt, document embeddings, stable tool results, and some search results. Whether a cached value is still valid depends on its sources, the user's permissions, and the prompt and model versions, so build these into the cache key and the rules for discarding entries. Never treat a cached confirmation as proof that a new action happened.", [
    section("What to cache, and how", """
        Each cache needs a key that captures what makes the value valid, and a rule for when to throw it away. A **TTL** (time to live) is how long an entry stays valid before it expires.
    """, table("What can be cached", ["Item", "Cache?", "Key includes / discard when"], [
        ["Fixed prompt start (system prompt, tool list)", "Yes, with prompt caching", "Prompt version"],
        ["Document embeddings", "Yes", "Document version"],
        ["Stable tool results (product catalog)", "Yes, with a short TTL", "Source version or TTL"],
        ["Search results", "Carefully", "Query, **user's permissions**, index version"],
        ["Final answers", "Rarely", "User's permissions, sources, prompt and model version"],
        ["Payment or booking confirmations", "Never as proof of a new action", "—"],
    ])),
    section("A cache hit still needs a permission check", """
        A cache keyed only by tenant and query will serve one user's answer to a colleague who isn't allowed to see its sources.
    """, code("Permission-aware cache", """
        key   = (tenant, permissions_version, normalize(query),
                 source_versions, prompt_version, model_version)
        entry = cache.get(key)
        if entry and not entry.expired and acl.can_read_all(user, entry.sources):
            return entry.value
        value = compute_from_allowed_sources()
        cache.put(key, value, ttl = freshness_limit)
    """, "Discard entries when sources, permissions, or policies change. A TTL alone reacts too slowly to removed access.")),
], "Retain caching as a correctness and access-control lesson, not only a performance recommendation."),

lesson("schedule-fairly-under-limits", "Rate limits and fair scheduling", [125, 127],
    "Model providers impose **rate limits**: caps on requests and tokens per minute. Track every limit a call can hit, and reserve capacity before calling. Stop one tenant from starving the others with a queue per tenant, fair turn-taking, and capacity set aside for interactive users.", [
    section("Reserve capacity before calling", """
        Staying under the request limit isn't enough, because a few very long prompts can use up the token limit. And with many workers, each sees the same "remaining capacity" and they all spend it at once, so reserve it atomically.
    """, code("Reserving rate-limit capacity", """
        provider    = choose_allowed_provider(task)            # privacy and quality first
        reservation = limiter.reserve(provider, tenant,
                                      requests = 1, tokens = estimate_tokens(task))  # atomic
        if not reservation: return queue_with_deadline(task)
        result = provider.call(task, max_output_tokens = task.output_cap)
        limiter.settle(reservation, actual = result.usage)     # correct the estimate
    """, "Still obey the provider's “too many requests” (429) replies and the wait time they ask for; estimates drift from reality.")),
    section("One tenant must not take everything", """
        Tenant A submits 10,000 batch tasks. A moment later, tenant B sends one interactive request. With a single first-come, first-served queue, B waits behind all 10,000. Instead:

        - **A queue per tenant,** served in fair turns.
        - **Per-tenant caps** on parallel calls, tokens, and spending.
        - **Capacity reserved for interactive work,** so batch jobs can't take all of it.
        - **A clear overload rule:** reject, postpone, or queue with a deadline. Never wait forever.

        Watch the **age** of the oldest queued task, not just the queue's length: 100 queued tasks are fine if the oldest is 2 seconds old.
    """),
], "Merge provider rate limits and tenant fairness around a single admission-control boundary."),

lesson("scale-workers-and-plan-capacity", "Scaling and capacity planning", [126, 128],
    "Scale by adding replaceable workers that take tasks from a durable queue, and add or remove workers based on queue age and backlog. Worker count is rarely the real bottleneck, though; model rate limits, other services, and the database usually are. Estimate the load with **Little's law**, then confirm with load tests.", [
    section("Adding workers", """
        - Workers keep no state of their own (chapter 5), so you can add or remove them at any time.
        - Keep cheap coordinating workers separate from expensive environments such as sandboxes or GPUs; they grow differently.
        - Scale on **queue age** and backlog, not CPU use. An agent worker mostly waits on other services.
        - A task waiting for approval or a slow tool should release its worker, not hold it.
        - Adding workers without more capacity downstream just turns waiting into timeouts and retries.
    """),
    section("Estimating capacity", """
        Little's law: average number of tasks in the system = arrival rate × average time each task spends in it.
    """, code("A first estimate", """
        arrival rate            = 2 tasks per second
        average time in system  = 15 s
        tasks in the system     = 2 × 15 = 30            # on average, under steady load

        model calls per task    = 6, each about 1 s
        model calls in progress ≈ 2 tasks/s × 6 calls × 1 s = 12 at a time, on average
    """, "These are averages. Plan headroom for bursts and long tasks."), """
        Averages don't tell you how many workers meet a p95 target. Load-test with realistic bursts, long tasks, large prompts, many tool calls, and failures. Then decide what happens when capacity runs out: turn work away, queue it with a deadline, or offer reduced service.
    """),
], "Merge horizontal scaling and capacity planning; keep the distinction between average concurrency and required capacity."),

lesson("degrade-during-provider-outages", "Provider outages and graceful degradation", [117, 118],
    "When a model provider fails, notice quickly, save the task's progress, and switch only to a backup that meets the same privacy, location, and quality requirements. If none does, postpone the task. **Graceful degradation** means keeping the parts that still work running, and saying clearly what can't be done right now.", [
    section("Switch without lowering the bar", """
        A **circuit breaker** stops calling a failing service for a while, instead of waiting on it again and again. A backup that is available but sends EU data outside the EU isn't a backup; it's an incident.
    """, code("Fallback that keeps the rules", """
        save_progress(task)
        if primary.circuit_open or primary.timed_out:
            options = providers.allowed_for(task.data_type, task.region)
            options = options.meeting(task.quality_bar)
            if not options: return postpone(task, status = "waiting for provider")
            resume_model_step(task, with = healthiest(options))
    """, "If a timed-out call might have done something, reconcile it before starting replacement work.")),
    section("Degrade honestly", """
        Keep the parts whose services still work, and say plainly which parts don't.
    """, table("What still works as services fail", ["Service state", "Still useful", "Never claim"], [
        ["Booking service up", "Compare options and book with approval", "“Booked” before a receipt arrives"],
        ["Booking service down", "Compare options; save a proposed trip", "“Your reservation is confirmed”"],
        ["Model provider down", "Show order status from the orders system; queue the request", "An answer from a model that isn't allowed"],
    ])),
], "Merge provider outages and graceful degradation, preserving privacy and honest outcome reporting through failure."),

lesson("fail-over-with-one-writer", "Multi-region failover", [129],
    "When moving work to a backup region, move ownership as well as data. Before the backup resumes tasks, block the old region from writing, accept that the last few seconds of copied data may be missing, and reconcile actions that were in progress. Data-location rules apply to the backup region too.", [
    section("A failover procedure", """
        A broken network link doesn't stop the old region. It may still be running and writing, which is exactly how two regions end up issuing the same refund.

        1. **Detect** that region A has failed or can't be reached.
        2. **Block** region A: raise the ownership number so services reject A's writes (the fencing idea from *Stop stale workers with fencing tokens*).
        3. **Load** the copied state in region B. Recent changes may be missing, up to your RPO (see below).
        4. **Reconcile** in-progress actions by operation ID with each provider. Treat "unknown" as unknown.
        5. **Resume** unfinished tasks. Pending approvals stay pending.
    """),
    section("Set targets and rehearse", """
        Set two targets. The **RPO** (recovery point objective) is how much recent data you can afford to lose, such as the last 5 seconds. The **RTO** (recovery time objective) is how long recovery may take. Then rehearse failover with pending approvals, payments in progress, copy delays, and a dependency that's down.

        If ownership can't be established safely, pausing all writes is the right outcome. An uptime target never justifies paying twice, or processing data in a region where it isn't allowed.
    """),
], "Retain regional recovery as a distinct application of ownership, replication, residency, and reconciliation."),
]
