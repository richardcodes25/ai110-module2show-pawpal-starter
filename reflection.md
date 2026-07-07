# PawPal+ Project Reflection

## 1. System Design

**Core user actions**

These are the three things a user should be able to do in PawPal+:

1. **Add a pet care task.** The user enters a task (e.g., a morning walk, feeding, or medication) along with how long it takes and how important it is. This builds up the list of things that might need to happen during the day.

2. **Generate a daily plan.** With one action, the user asks PawPal+ to turn their tasks into an ordered schedule for the day, taking into account the time they have available and each task's priority so the most important care happens first.

3. **View today's plan and why it was chosen.** The user sees the resulting schedule laid out for the day, along with a short explanation of why each task was included and when it was placed — so they can trust and adjust the plan.

**a. Initial design**

My initial UML has six classes, split into "data" objects and "behavior" objects:

- **`Task`** — a single unit of care work. Holds `title`, `duration_minutes`, `priority`, `preferred_time`, `recurring`, and `category`. Responsible for knowing its own importance (`priority_weight()`) and whether it applies today (`is_due_today()`).
- **`Pet`** — the animal being cared for. Holds `name`, `species`, `age`, `notes`, and its list of `tasks`. Responsible for managing its own tasks (`add_task`, `remove_task`, `list_tasks`).
- **`Owner`** — the user. Holds their availability window and `preferences`, and owns one or more pets. Responsible for representing the constraints the scheduler must respect (`time_budget()`, `set_availability()`).
- **`Scheduler`** — the engine. Responsible for turning tasks + constraints into a plan (`build_plan()`), ordering candidates (`sort_tasks()`), enforcing the time budget (`fits_in_budget()`), handling overlaps (`resolve_conflicts()`), and explaining choices (`explain()`).
- **`DailyPlan`** — the output the user views. Holds the ordered `entries`, any `skipped_tasks`, and `total_minutes`. Responsible for presenting the plan (`to_display()`) and explaining it as a whole (`summary()`).
- **`PlanEntry`** — one task placed at a specific time slot. Holds the `task`, `start_time`, `end_time`, and the per-task `reason`. This is what makes the "explain each task" requirement possible.

I chose to make `Task`, `Pet`, `Owner`, `DailyPlan`, and `PlanEntry` Python **dataclasses** (they mostly hold data), and kept `Scheduler` a plain class because it owns behavior rather than being a data record. Relationships: an Owner owns many Pets, a Pet has many Tasks, the Scheduler reads the Owner and produces a DailyPlan, and a DailyPlan is composed of PlanEntry items.

**b. Design changes**

After building the skeleton I asked my AI assistant to review it for missing relationships and logic bottlenecks. Based on that feedback I made two changes and deferred a third:

1. **Gave tasks an explicit owning pet.** `Owner.add_task(task)` originally claimed to route a task to "the relevant pet," but nothing said *which* pet — tasks had no link back to a Pet. I changed the signature to `Owner.add_task(pet, task)` so the routing is unambiguous.
2. **Removed a second source of truth for tasks.** The `Scheduler` took its own `tasks` list, which could drift out of sync with the tasks already stored on each `Pet`. I made that argument optional and added `Owner.all_tasks()`; the scheduler now defaults to gathering tasks from the owner's pets, with the explicit list kept only as an override for filtering.
3. **Deferred (noted for implementation): time arithmetic.** Scheduling needs "start + duration → end time," but Python's `datetime.time` has no arithmetic. I chose not to change the representation yet and will decide between `datetime.datetime` and minutes-since-midnight when I implement `build_plan()`, so the choice is driven by the real logic rather than guessed up front.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

The clearest tradeoff my scheduler makes: it **detects time conflicts but does not
auto-resolve them.** `detect_conflicts()` compares every pair of timed tasks with a
half-open interval overlap test — `[start, start + duration)` — so it catches genuine
overlaps (a 09:00 nail trim colliding with a 09:00 litter cleanup), not just exact
start-time matches. But when `build_plan()` lays out the day, it still packs tasks
back-to-back in *priority* order and ignores each task's `preferred_time`. A detected
collision therefore becomes a **warning attached to the plan**, not an automatic
reshuffle — and the printed schedule and the preferred times can visibly disagree (the
plan may show the nail trim at 08:15 while warning that it wanted 09:00).

Why this is reasonable for the scenario: the user is a human owner who ultimately
controls their own day. Silently moving a task to honor a preferred time could bury a
high-priority feeding behind low-priority enrichment, or shift medication to a worse
time without the owner's consent. Surfacing "these two both want 09:00" and letting the
owner adjust keeps the tool trustworthy and keeps the placement logic simple and
predictable. For a single owner with a handful of pets that is an acceptable price; a
future iteration could seat timed tasks at their preferred slots first and fall back to
greedy packing only for the untimed ones.

A smaller, related tradeoff: `detect_conflicts()` uses O(n²) pairwise comparison rather
than a sorted O(n log n) sweep-line. At pet-care scale (a few pets, a dozen tasks) the
pairwise version is faster to read and verify, and the performance difference is
irrelevant — so I optimized for readability over asymptotic cleverness on purpose.

---

## 3. AI Collaboration

**a. How you used AI / most effective features**

I used the AI assistant differently in each phase: **design brainstorming** while drafting
the UML, **skeleton generation** to turn the diagram into class stubs, **incremental
implementation and refactoring** while filling in the scheduling logic, and **debugging +
test scaffolding** once behavior existed to verify.

The single most effective feature was **attaching a file and asking a targeted question
about it** rather than asking in the abstract. Two examples paid off repeatedly:

- Attaching the class skeleton and asking *"review this for missing relationships and logic
  bottlenecks"* surfaced the two structural fixes in Section 1b (unambiguous task ownership
  and the duplicate task list) before I had written any logic against the flawed shape.
- Attaching the finished `pawpal_system.py` and asking *"what updates should I make to my
  initial UML to accurately show how these classes interact?"* caught real drift — a method
  I had renamed (`resolve_conflicts` → `detect_conflicts`), new methods (`sort_by_time`,
  `filter_tasks`, `next_occurrence`), and a new relationship (a `Task` recurring into
  another `Task`).

Prompts that named a **concrete artifact and a concrete goal** ("does this diagram match
this code?") were far more useful than open-ended ones ("make my scheduler better"), because
the answers were verifiable against the file in front of me.

**b. Judgment and verification — a suggestion I modified**

The clearest example was **conflict handling**. My initial design (and an easy AI default)
was a `Scheduler.resolve_conflicts()` method that would *automatically reshuffle* overlapping
tasks to fix collisions. I rejected the auto-resolve behavior and modified it into
`detect_conflicts()`, which only *reports* overlaps as warning strings and leaves placement
alone (see the tradeoff in Section 2b). Auto-reshuffling would have silently buried a
high-priority feeding behind low-priority enrichment, or moved medication to a worse time
without the owner's consent — and it would have tangled the placement logic with the
conflict logic. Keeping detection separate from placement kept both simple and kept the
human in control.

A second modification: the AI-suggested `Scheduler` carried its own `tasks` list. I made
that argument optional and routed everything through `Owner.all_tasks()` so there was a
**single source of truth**, preventing the scheduler's copy from drifting out of sync with
the tasks stored on each pet.

I verified suggestions three ways: reading the code against the invariants I cared about
(one source of truth, no silent data changes), running `python main.py` to watch the actual
behavior end to end, and writing the 16-test suite so regressions in sorting, filtering,
recurrence, and conflict detection would fail loudly.

**c. Working in separate chat sessions per phase**

I kept a separate chat session for each phase — design/UML, skeleton, logic + tests, and
packaging. This helped in three concrete ways:

- **Focused context.** Each session only held what mattered for that phase, so the
  assistant wasn't reasoning over a stale early draft when I was deep in implementation.
- **The file, not the chat, was the source of truth.** Because I re-attached the *current*
  `pawpal_system.py` at the start of a new phase instead of relying on the AI's memory of
  earlier messages, its answers reflected what the code actually said — which is exactly how
  I caught the UML drift.
- **Clean checkpoints.** Ending a phase in its own session gave me a natural place to commit
  and to write down what changed, so the git history and the reflection track the phases.

**d. What I learned about being the "lead architect"**

The AI was fastest at producing *plausible* code, but plausible is not the same as coherent
with the rest of the system. My job as lead architect was to own the parts the AI couldn't
see: the **invariants** (single source of truth for tasks), the **boundaries** (detection
separate from placement; logic in `pawpal_system.py`, never in the UI), and the
**tradeoffs** (warn-don't-resolve, O(n²) for readability at this scale). The most valuable
thing I did was not writing code — it was *setting constraints and rejecting the suggestions
that violated them*. The AI accelerated the work enormously, but every accepted suggestion
was one I could explain and had verified against a test or a real run. Powerful tools raise
the bar on judgment rather than removing the need for it.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
