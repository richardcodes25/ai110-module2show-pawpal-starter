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

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
