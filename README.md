# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## ✨ Features

PawPal+ is more than a to-do list — the logic layer in `pawpal_system.py` implements
real scheduling algorithms, and the Streamlit UI (`app.py`) surfaces every one of them.

### Scheduling algorithms

- **Priority-first planning** — `build_plan()` greedily places tasks highest-priority-first
  (ties broken by shortest duration), fitting each into the owner's available time window
  and time budget, and skipping any that don't fit.
- **Sorting by time** — `sort_by_time()` reorders tasks chronologically by `preferred_time`;
  untimed tasks sink to the end without crashing on a `None` comparison.
- **Conflict warnings** — `detect_conflicts()` compares every pair of timed tasks with a
  half-open interval test and returns human-readable warnings (never raises), catching real
  overlaps across the same pet *or* different pets.
- **Daily / weekly recurrence** — completing a recurring task auto-spawns its next occurrence
  (`+1 day` or `+7 days` via `timedelta`); `is_due_today()` holds future occurrences back
  until their date arrives.
- **Filtering** — `Owner.filter_tasks()` narrows tasks by pet (case-insensitive) and/or
  completion status; each dimension is optional.
- **Explainable plans** — every scheduled task carries a plain-language `reason` for why it
  was chosen and where it landed.

### App capabilities

- Add owners, pets, and care tasks (duration, priority, frequency, optional preferred time)
- Generate and view a time-stamped daily schedule with per-task reasoning
- See conflict warnings and filter the task list, all from the browser UI
- Run the same logic headlessly via `python main.py` for a quick terminal demo

> See the [📐 Smarter Scheduling](#-smarter-scheduling) table below for the exact method
> behind each feature.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...

================================================
  Today's Schedule for Jordan
  (2 pets, 4 tasks)
================================================
Daily plan for 2026-07-07:
  08:00 — Feeding (10 min) [high]
      ↳ High priority (weight 3), 10 min — fits the available time.
  08:10 — Morning walk (30 min) [high]
      ↳ High priority (weight 3), 30 min — fits the available time.
  08:40 — Litter cleanup (15 min) [medium]
      ↳ Medium priority (weight 2), 15 min — fits the available time.
  08:55 — Play/enrichment (20 min) [low]
      ↳ Low priority (weight 1), 20 min — fits the available time.
------------------------------------------------
Scheduled 4 task(s) using 75 min; skipped 0.
```

## 🧪 Testing PawPal+

Run the full test suite from the project root:

```bash
python -m pytest
```

**What the tests cover** (`tests/test_pawpal.py`, 16 tests):

- **Sorting** — `sort_by_time()` returns tasks in chronological order, and untimed tasks sort to the end without crashing on a `None` comparison.
- **Filtering** — `Owner.filter_tasks()` narrows by pet name (case-insensitive) and completion status; a pet with no tasks or an unknown name returns `[]`.
- **Recurrence** — completing a daily task spawns tomorrow's copy, weekly spawns +7 days, one-off tasks don't recur, `timedelta` rolls over month boundaries (Jan 31 → Feb 1), and future-dated occurrences aren't due today.
- **Conflict detection** — `detect_conflicts()` flags overlapping/same-time tasks and stays quiet for back-to-back ones; `Task.overlaps()` respects half-open interval boundaries.
- **Plan building** — `build_plan()` skips a task larger than the time budget and returns an empty plan (no crash) when there are no tasks.
- **Core model** — marking a task complete flips its status, and adding a task grows the pet's task list.

Successful run:

```text
==================================================================================== test session starts =====================================================================================
platform darwin -- Python 3.11.11, pytest-8.3.4, pluggy-1.5.0
rootdir: /Users/nguyendo/Codepath/Pawpal/ai110-module2show-pawpal-starter
plugins: anyio-4.6.2
collected 16 items

tests/test_pawpal.py ................                                                                                                                                                  [100%]

===================================================================================== 16 passed in 0.02s =====================================================================================
```

### Confidence Level: ★★★★☆ (4 / 5)

All 16 tests pass and cover every scheduling feature — sorting, filtering, recurrence, conflict detection, and plan building — across both happy paths and edge cases (empty pets, oversized tasks, month rollover, untimed tasks). I hold back the fifth star because the tests exercise the logic layer directly rather than the Streamlit UI, and a few behaviors remain untested: the priority-first `build_plan` ordering and tie-breaking, weekly `is_due_today` weekday semantics, and preferred-time placement (which is currently advisory only).

## 📐 Smarter Scheduling

PawPal+ goes beyond a flat to-do list with four pieces of scheduling logic. Each row
names the exact method that implements it (all in `pawpal_system.py`).

| Feature | Method(s) | What it does |
| --- | --- | --- |
| **Sorting by time** | `Scheduler.sort_by_time()` | Orders candidate tasks chronologically by `preferred_time` using `sorted()` with a `(has_no_time, time)` lambda key — untimed tasks sink to the end, everything else is in clock order. (`Scheduler.sort_tasks()` still offers the priority-first ordering used by `build_plan()`.) |
| **Filtering** | `Owner.filter_tasks(pet_name=..., completed=...)` | Narrows tasks by pet name (case-insensitive) and/or completion status; each filter is optional (`None` = don't filter on that dimension). `Scheduler.candidate_tasks()` applies the scheduling filter — due today and not yet completed. |
| **Conflict detection** | `Scheduler.detect_conflicts()` + `Task.overlaps()` | Compares every pair of timed tasks with a half-open interval test (`[start, start+duration)`) and returns human-readable **warning strings** — never raises. Catches real overlaps (not just exact start-time matches), across the same pet or different pets. Warnings are attached to `DailyPlan.warnings`. |
| **Recurring tasks** | `Task.next_occurrence()`, `Pet.complete_task()`, `Owner.mark_task_complete()`, `Task.is_due_today()` | Completing a `daily`/`weekly` task auto-spawns a fresh, uncompleted occurrence with `due_date` advanced by `timedelta` (daily → +1 day, weekly → +7 days). `is_due_today()` then holds future occurrences back until their date arrives. One-off (`none`) tasks don't recur. |

### Sample conflict warning

```text
⚠ Time conflict (Mochi vs Luna): 'Nail trim' at 09:00 overlaps 'Litter cleanup' at 09:00
```

### Trying it in the terminal

`python main.py` exercises all four features end to end: it adds tasks out of order (to
show sorting), filters by pet and status, completes a daily task (to show regeneration),
and adds a colliding task (to show conflict detection) before printing the day's plan.

## 📸 Demo Walkthrough

Launch the browser app with `streamlit run app.py`, or run the headless terminal demo
with `python main.py` (sample output below).

### What you can do in the UI

The Streamlit app (`app.py`) is organized top-to-bottom into four sections:

- **🐕 Add a Pet** — enter a name and species; the pet is stored on a persistent `Owner`
  that survives Streamlit's reruns via `st.session_state`.
- **📋 Add a Task** — pick the pet, then set a title, duration, priority, frequency
  (`none` / `daily` / `weekly`), and an optional **preferred start time**. The live task
  table can be **filtered by pet and by status** (All / Pending / Done).
- **🗓️ Build Schedule** — choose how many minutes you have today and click *Generate
  schedule*. Any **time conflicts appear first as amber warnings**, followed by a clean
  table of the day's plan (time range, task, duration, priority, and *why* it was chosen).
- **How were these tasks ordered?** — an expander that shows both the priority-first order
  actually used and the chronological (`sort_by_time`) alternative, so the ordering logic
  is transparent.

### Example workflow

1. **Add a pet** — e.g. "Mochi" the dog.
2. **Add tasks** — a high-priority "Morning walk" (30 min, daily, preferred 08:00) and a
   medium "Litter cleanup" (15 min, preferred 09:00) for a second pet, "Luna".
3. **Set availability** — drag the slider to the minutes you actually have today.
4. **Generate the schedule** — PawPal+ sorts by priority, places each task in your time
   window with a start–end time, and explains its reasoning per task.
5. **Complete a recurring task** — finishing the daily walk automatically queues tomorrow's
   copy, which is correctly held back from *today's* plan.
6. **Watch for conflicts** — add a task that overlaps an existing timed one and a warning
   surfaces above the schedule (the plan still generates — conflicts are advisory).

### Key Scheduler behaviors shown below

Running `python main.py` exercises all four algorithms end to end:

- **Sorting by time** — tasks are added out of order, then `sort_by_time()` returns them
  in clock order (08:00 → 17:00).
- **Filtering** — `filter_tasks()` narrows by pet ("Luna's tasks") and by completion status.
- **Daily recurrence** — completing the daily "Morning walk" spawns a fresh occurrence due
  the next day, so Mochi's task count grows from 2 → 3.
- **Conflict warnings** — a "Nail trim" added at 09:00 collides with the 09:00 "Litter
  cleanup" and `detect_conflicts()` reports it.
- **Priority-first plan** — `build_plan()` schedules the remaining due tasks into the
  08:00–12:00 window with a reason for each.

### Sample CLI output (`python main.py`)

```text
================================================
  Tasks sorted by time (Scheduler.sort_by_time)
================================================
  08:00  Morning walk (30 min, high)
  08:30  Feeding (10 min, high)
  09:00  Litter cleanup (15 min, medium)
  17:00  Play/enrichment (20 min, low)

================================================
  Filtering (Owner.filter_tasks)
================================================
  Luna's tasks:
    - Play/enrichment
    - Litter cleanup

================================================
  Recurring regeneration (Owner.mark_task_complete)
================================================
  Mochi task count before completing the daily walk: 2
  Mochi task count after:  3  (a new occurrence was added)
  New occurrence -> 'Morning walk', due 2026-07-08 (completed=False, still recurring='daily')
  Pending tasks (completed=False):
    - Morning walk
    - Play/enrichment
    - Litter cleanup
  Completed tasks (completed=True):
    - Feeding
    - Morning walk

================================================
  Conflict detection (Scheduler.detect_conflicts)
================================================
  ⚠ Time conflict (Mochi vs Luna): 'Nail trim' at 09:00 overlaps 'Litter cleanup' at 09:00

================================================
  Today's Schedule for Jordan
  (2 pets, 6 tasks)
================================================
Daily plan for 2026-07-07:
  08:00 — Litter cleanup (15 min) [medium]
      ↳ Medium priority (weight 2), 15 min — fits the available time.
  08:15 — Nail trim (15 min) [medium]
      ↳ Medium priority (weight 2), 15 min — fits the available time.
  08:30 — Play/enrichment (20 min) [low]
      ↳ Low priority (weight 1), 20 min — fits the available time.
  ⚠ Time conflict (Mochi vs Luna): 'Nail trim' at 09:00 overlaps 'Litter cleanup' at 09:00
------------------------------------------------
Scheduled 3 task(s) using 50 min; skipped 0.
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
