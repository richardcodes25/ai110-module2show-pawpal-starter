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

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

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
