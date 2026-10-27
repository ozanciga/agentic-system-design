from authoring import code, lesson, section, table, timeline

CHAPTER = ("Reliability and recovery", "Survive crashes, retries, timeouts, cancellation, and new releases without repeating actions.")

LESSONS = [

lesson("separate-state-and-memory", "Conversation, task state, and memory", [15, 51, 53],
    "Keep three things apart: the **conversation** (what was said), the **task state** (where the task is, and which actions already happened), and **long-term memory** (facts useful to future tasks). With task state saved in a database, the programs running the task can crash and be replaced without losing progress.", [
    section("Three kinds of state", """
        A chat transcript is not a ledger: after a crash, it can't tell you whether the refund was actually sent. A **checkpoint**, a saved record of the task's progress, can.
    """, table("Conversation, task state, memory", ["", "Conversation", "Task state (checkpoint)", "Long-term memory"], [
        ["Example", "“I'd like $80 back for the jacket”", "Step 4 of 6; approval A-17 granted; refund op-42 sent, result unknown", "Customer prefers French"],
        ["Used for", "Showing history; building context", "Resuming **this** task correctly", "Helping **future** tasks"],
        ["Kept until", "The session ends or retention expires", "The task ends (plus audit retention)", "Changed, expired, or deleted"],
    ])),
    section("Replaceable workers, saved progress", """
        A **worker** is a running program that picks up tasks and executes their steps. Should it hold the task's state? No: the **task** has state, and that state lives in a database. A worker loads the task, claims one step, runs it, saves the result, and lets go. If the worker dies, another loads the same state and carries on.

        This only works if the database also records which actions happened (did refund op-42 go through?) and who may run the next step. The next lessons cover both.
    """),
], "Merge conversation/workflow/checkpoint distinctions with stateless-worker architecture; teach long-term memory later."),

lesson("checkpoint-and-replay", "Durable execution: survive crashes", [71, 72],
    "**Durable execution** saves each step's result, so a crashed task resumes where it stopped instead of starting over. Resuming is hard for two reasons: model calls and outside services don't give the same answer twice, and an action can go through just before a crash and leave no record.", [
    section("Resume from saved results", """
        Tools such as Temporal and Azure Durable Functions resume a task by running its code again from the top, but every step that already finished returns its **saved** result instead of running again. For this to work, the coordinating code must be **deterministic**, and anything unpredictable (model calls, API calls, the current time, random numbers) must run inside a step whose result is saved. AWS Step Functions works differently: it saves each move of a predefined state machine, so there is no code to re-run.
    """, code("Run a step at most once", """
        def run_step(step_id, operation_id):
            past = history.lookup(step_id)
            if past.completed: return past.value                 # finished before: reuse result
            if past.started:   return reconcile(operation_id)    # crashed mid-step: check first
            history.save_started(step_id, operation_id)          # before touching the outside world
            value = do_step(step_id, operation_id)               # model or tool call
            history.save_completed(step_id, value)
            return value
    """)),
    section("The crash window", """
        There is always a gap between an action going through and the task saving that fact. A crash in that gap leaves no result on record, even though the money moved.
    """, timeline("A refund goes through, then the worker crashes", [
        ("Worker", [(0, 2, "call refund"), (3, 4, "crash", "bad"), (5, 7, "look up op-42")]),
        ("Payment service", [(1, 3, "pays $80", "good")]),
        ("Saved history", [(0, 1, "started"), (7, 9, "R-981 saved", "good")]),
    ], "Example timing. Between seconds 3 and 7, the saved history doesn't know the refund happened. Calling refund again would pay twice.", markers=[(3, "result not saved")]), """
        So a missing result doesn't mean the step failed. A step marked started but never completed has an **unknown outcome**: look up what happened before doing anything else. The next lesson shows how.
    """),
], "Merge durability and replay, explicitly teaching the crash window that prevents checkpointing alone from guaranteeing external correctness.",
    references=[("Temporal: event history", "https://docs.temporal.io/encyclopedia/event-history", "How a workflow is rebuilt from its saved events.")]),

lesson("make-side-effects-idempotent", "Idempotency: retry without repeating an action", [39, 73, 78],
    "An action is **idempotent** if doing it twice has the same effect as doing it once. Make every action idempotent by giving it an **operation ID**, created before the first attempt and sent with every retry, so the receiving service can spot repeats. After an unclear result such as a timeout, **reconcile**: look up what actually happened before trying again.", [
    section("Create the ID before the first attempt", """
        Base the ID on the step itself, for example `task-9:step-4`, and save it with the request before sending. Any retry, any resumed worker, or a fresh model decision for the **same** step must reuse it. Services often call this an idempotency key.
    """, table("Same ID vs. new ID", ["Attempt", "Request", "Payment service"], [
        ["1", "Refund $80, ID `op-42`", "Pays; the response is lost in a timeout"],
        ["2 (retry)", "Refund $80, ID `op-42`", "Recognizes the ID; returns the original receipt R-981"],
        ["2 (bug: new ID)", "Refund $80, ID `op-43`", "Treats it as new; the customer is refunded twice"],
    ]), """
        A local "already sent" flag can't replace this, because the crash can come after the payment and before the flag is saved. Only the receiving service, checking the ID atomically, closes that gap.
    """),
    section("When a call times out", """
        A timeout doesn't tell you whether the action happened, so look before retrying.
    """, code("Reconcile, then retry only if safe", """
        op = operations.get_or_create(task.id, step.id)       # same ID every time
        status = payments.lookup(op.id)
        if status.succeeded:                 return status.receipt
        if status.pending or status.unknown: return check_again_later(op.id)
        if not status.confirmed_never_received: return escalate(op.id)  # "not found" may just be delay
        return payments.refund(op.request, operation_id = op.id)        # same ID: still safe
    """), """
        Can a system guarantee each action happens exactly once? Networks lose and duplicate messages, so delivery is at best **at-least-once**: every message arrives, some more than once. An action happens once only when, in addition:

        - the receiving service keeps IDs long enough to cover your retries (Stripe keeps them for 24 hours) and rejects a reused ID with different details;
        - you don't treat "not found" as "never happened", because a lookup can lag slightly behind the latest writes.
    """),
], "Merge duplicate effects, exactly-once claims, and timeout-after-success into one canonical recovery explanation.",
    references=[("Stripe: idempotent requests", "https://docs.stripe.com/api/idempotent_requests", "A real provider's rules for keys, retention, and repeated requests.")]),

lesson("coordinate-concurrent-workers", "Stop stale workers with fencing tokens", [],
    "A **lease** is a time-limited claim on a task: if a worker stops renewing it, another worker may take over. But the first worker may wake up and still try to write. A **fencing token**, a number that goes up with every new claim, solves this: storage rejects any write carrying an older number.", [
    section("Why a lease alone isn't enough", """
        A worker can freeze for longer than its lease (a long garbage-collection pause, a virtual machine being moved, a network stall) without noticing. When it resumes, it still believes it owns the task.
    """, timeline("A stale worker is blocked", [
        ("Worker A", [(0, 2, "claim #33"), (2, 7, "frozen (pause)", "bad"), (7, 9, "write #33 ✗", "bad")]),
        ("Worker B", [(4, 6, "claim #34"), (6, 8, "write #34 ✓", "good")]),
    ], "Storage has seen token 34, so it rejects A's write with 33. A can't catch this itself; it doesn't know it was frozen.", markers=[(4, "A's lease expires")]), code("Checking the token", """
        claim  = tasks.claim(task_id, lease = 30 s)   # atomically returns token = last + 1
        result = do_work(claim)
        store.write(key, result, token = claim.token)

        # Inside the store, as one atomic step with the write:
        if token < highest_token_seen[key]: reject("stale worker")
        highest_token_seen[key] = token
    """, "If an outside service can't check tokens, rely on its operation IDs and on reconciling instead.")),
    section("Three guards, three different problems", """
        These are often confused; many systems need all three.
    """, table("Which guard prevents what", ["Guard", "Prevents", "Example"], [
        ["Operation ID", "The same action applied twice", "A retry of refund op-42"],
        ["Fencing token", "An old owner writing after a takeover", "Worker A waking after B took over"],
        ["Version check (compare-and-swap)", "One edit silently erasing another", "Two agents editing the same memory record"],
    ]), """
        Prefer the coordination built into your workflow engine over a homemade lock, and test freezes, lease expiry, and takeovers on purpose.
    """),
], "Add the missing concurrency bridge between replaceable workers, at-least-once delivery, and regional failover.",
    questions=["How do you stop two workers from running the same step?"],
    related=["make-side-effects-idempotent", "fail-over-with-one-writer"],
    references=[("Martin Kleppmann: How to do distributed locking", "https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html", "The classic explanation of why leases need fencing tokens."),
                ("AWS Builders' Library: leader election", "https://aws.amazon.com/builders-library/leader-election-in-distributed-systems/", "Why a paused worker can wrongly believe it still holds a lease.")]),

lesson("bound-retries-and-failed-work", "Retries and dead-letter queues", [75, 79],
    "Retry only temporary failures, waiting longer each time (**exponential backoff**) with some randomness (**jitter**), and stop at the task's deadline. Never retry bad input or a denied permission. Move tasks that keep failing to a **dead-letter queue**: a holding area where a person can look at them with full context.", [
    section("Which errors to retry", """
        The kind of error decides.
    """, table("Retry or not?", ["Error", "Retry?"], [
        ["429: too many requests", "Yes, after the delay the service asks for"],
        ["503: service unavailable, or a dropped connection while reading", "Yes, with backoff"],
        ["Timeout while making a change", "Not yet: reconcile first"],
        ["400: bad request", "No: fix the input"],
        ["403: forbidden", "No"],
    ]), code("Bounded retry", """
        for attempt in 0..MAX_RETRIES:
            outcome = call(operation_id)              # same operation ID every attempt
            if outcome.ok:            return outcome
            if outcome.change_unknown: return reconcile(operation_id)
            if not outcome.retryable: return fail(outcome)
            if attempt == MAX_RETRIES: break
            delay = outcome.retry_after or random(0, min(CAP, BASE * 2^attempt))  # backoff + jitter
            if now + delay > task.deadline - RESERVE: return fail("deadline")
            sleep_cancellably(delay)
        return fail("retries used up")
    """, "Jitter spreads retries out, so a thousand clients don't all hit a recovering service at the same instant.")),
    section("Tasks that keep failing", """
        Some tasks fail every time: bad input, a bug, or a service that is gone for good. Retrying them just wastes capacity. Move them to the dead-letter queue:

        - Save the inputs, the versions in use, every attempt with its error, and any unresolved actions.
        - Assign an owner, and alert when the queue grows.
        - Send a task back for processing only with a reason: the input was fixed, the service recovered, a fix shipped, or a person decided.
    """),
], "Merge retry mechanics and repeatedly failing tasks so the end of the retry budget has a defined operational destination."),

lesson("budget-deadlines-and-cancellation", "Deadlines and cancellation", [76, 77],
    "Give the whole task one deadline for active work (time spent waiting for a person is budgeted separately), and give each step only the time that remains, minus a reserve for cleanup. Cancelling stops new work and new actions. Actions already completed stay completed and must be checked or reversed separately.", [
    section("One deadline for all steps", """
        If each step gets its own fixed 30-second timeout, a five-step task can take 150 seconds against a 20-second promise. Instead, each step gets what's left:
    """, timeline("A 20-second task budget", [
        ("Task", [(0, 2, "queue"), (2, 5, "context"), (5, 11, "model"), (11, 15, "tools"), (15, 17, "verify"), (17, 20, "reserve", "good")]),
    ], "Example. After second 17, don't start a new step; the reserve is for cleanup and the reply.", markers=[(17, "last start"), (20, "deadline")]), code("Each step's timeout", """
        remaining = task.deadline - now() - RESERVE
        if remaining < step.minimum_useful_time: return finish_with_what_we_have(task)
        timeout = min(step.typical_time * 2, remaining)
    """, "Time in the queue, retry delays, and waiting for parallel branches all count against the same deadline.")),
    section("Cancel stops the future, not the past", """
        A cancelled task must stop taking actions, but a refund the payment service already accepted doesn't vanish.
    """, code("Cancelling a task", """
        save_cancel_request(task)
        stop_scheduling_new_steps(task)
        block_new_actions(task)                 # the tool gateway rejects this task's calls
        ask_running_calls_to_cancel(task)       # where the tool supports it
        reconcile_unfinished_actions(task)
        save(task, CANCELLED, actions = {done: [...], unknown: [...]})
    """), """
        Undoing a completed action, such as refunding a charge, is a new action that needs its own permission (next lesson).
    """),
], "Teach deadline exhaustion and cancellation together while preserving the distinction between stopping and reversing."),

lesson("compensate-multi-step-actions", "Sagas: undo partly finished actions", [74, 96],
    "A **saga** is a multi-step action across several services in which every step has a matching undo action, called a **compensation**, run if a later step fails. A compensation is not a true rollback: it is a new action, such as a cancellation, that can itself fail, cost fees, or leave traces.", [
    section("Pair each step with its undo", """
        Decide each compensation when you design the step, not after something breaks.
    """, table("A travel-booking saga", ["Step", "Action", "Compensation"], [
        ["1", "Reserve hotel", "Cancel the reservation (free until 24 h before check-in)"],
        ["2", "Book flight", "Cancel the ticket (fee depends on the fare)"],
        ["3", "Charge card", "Refund the charge"],
    ]), """
        If step 2 **definitely** fails, run the compensations for the finished steps in reverse order: here, cancel the hotel. If step 2's result is **unknown** (a timeout), reconcile it first. Cancelling the hotel while the flight might still be booked leaves the traveler with a flight and nowhere to stay.

        Compensations are real actions too. Give them operation IDs, retries, records, approvals where needed, and a manual path when they fail.
    """),
    section("Rollback vs. compensation", """
        A rollback cancels changes that were never finalized. A compensation adds a new action that offsets a finalized one.
    """, table("Rollback vs. compensation", ["", "Rollback", "Compensation"], [
        ["Example", "Abort an unfinished database transaction", "Cancel a confirmed booking"],
        ["Result", "The changes never become visible", "A new action offsets an earlier one"],
        ["Leaves traces?", "No", "Possibly: fees, emails, records"],
    ], "A sent email shows the limit: a correction can follow it, but can't unsend it.")),
], "Merge Saga mechanics and rollback-versus-compensation so partial success and its limits are taught in one place."),

lesson("pin-and-migrate-workflow-versions", "Version prompts and upgrade running tasks", [80, 137],
    "Treat prompts, tool definitions, policy rules, and model settings as versioned code, and tie each task to the versions it started with. After a new release, finish old tasks on the old version or move them to the new one with a tested migration. If neither is possible, pause them.", [
    section("Version prompts like code", """
        Changing one sentence in a prompt can change which tool the model picks. That is a behavior change, so prompts deserve what code gets: review, testing on the golden set, a version number, and the ability to roll back.
    """, code("Tie each task to its versions", """
        release = {workflow: "refund@14", prompt: "refund-agent@31", tools: "orders-api@3",
                   model: "model-x-2026-09", policy: "P-7@5"}
        task = create_task(request, versions = release)
        log(task.id, release)     # explains any run later
    """)),
    section("Finish, migrate, or pause", """
        A task started on version 14 may still be waiting for approval when version 15 ships.
    """, code("What to do with a running task", """
        task = load(task_id)
        if workers.support(task.versions.workflow, task.state_format):
            resume(task)                          # old version still available
        elif migration_exists(task.versions.workflow, current):
            resume(migrate_and_check(task))       # tested conversion to the new version
        else:
            pause_for_review(task)
    """), """
        A migration must handle pending approvals and actions with unknown results. When the new version changes a rule on purpose, such as a security fix, apply the new rule to running tasks deliberately and ask for fresh approval if needed. Never mix old and new rules in one task without saying so.
    """),
], "Merge prompt versioning and workflow migration because both are part of a task's execution contract."),
]
