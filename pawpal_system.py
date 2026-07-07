# pawpal_system.py — Logic layer: all backend classes for PawPal+ live here.
# This module holds the domain model and scheduling logic, kept separate from
# the Streamlit UI (app.py). No UI code should go in this file.

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import date, time, timedelta

# Numeric ranking for priorities (higher = more important). Used by sorting.
PRIORITY_ORDER = {"low": 1, "medium": 2, "high": 3}

# Default care window used when the owner hasn't set their availability.
DEFAULT_START = time(8, 0)
DEFAULT_END = time(20, 0)


def _to_minutes(t: time) -> int:
    """Convert a clock time into minutes since midnight (for easy arithmetic)."""
    return t.hour * 60 + t.minute


def _to_time(minutes: int) -> time:
    """Convert minutes-since-midnight back into a clock time (wraps at 24h)."""
    minutes %= 24 * 60
    return time(minutes // 60, minutes % 60)


@dataclass
class Task:
    """A single unit of pet care work that the user wants scheduled."""

    title: str
    duration_minutes: int
    priority: str = "medium"  # "low" | "medium" | "high"
    preferred_time: time | None = None
    recurring: str = "none"  # "none" | "daily" | "weekly"  (a.k.a. frequency)
    category: str = "other"  # walk | feed | meds | grooming | enrichment | other
    completed: bool = False
    due_date: date | None = None  # the day this occurrence is due; None = "any day"

    # How far ahead each frequency repeats. timedelta does the calendar math for us,
    # so month/year rollovers are handled correctly (e.g. 2026-01-31 + 1 day -> 02-01).
    RECUR_STEP = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}

    def priority_weight(self) -> int:
        """Return a numeric rank for this task's priority (higher = more important)."""
        return PRIORITY_ORDER.get(self.priority, PRIORITY_ORDER["medium"])

    def is_due_today(self, on_date: date | None = None) -> bool:
        """Return True if this task is a candidate for the given day (defaults to today).

        Two gates: (1) the frequency must be a known value, and (2) if the task has an
        explicit due_date it must not be in the future. A task with no due_date is
        treated as "due now" so freshly added tasks schedule immediately, while a
        regenerated recurring occurrence (dated tomorrow) is correctly held back.
        """
        if self.recurring not in ("none", "daily", "weekly"):
            return False
        if self.due_date is None:
            return True  # no explicit date -> treat as due now
        return self.due_date <= (on_date or date.today())

    def overlaps(self, other: "Task") -> bool:
        """Return True if this task's time window collides with another's.

        Untimed tasks (no preferred_time) never conflict. Two windows overlap when
        each starts before the other ends — the standard half-open interval test,
        so back-to-back tasks (one ends exactly when the next starts) don't count.
        """
        if self.preferred_time is None or other.preferred_time is None:
            return False
        a_start = _to_minutes(self.preferred_time)
        b_start = _to_minutes(other.preferred_time)
        a_end = a_start + self.duration_minutes
        b_end = b_start + other.duration_minutes
        return a_start < b_end and b_start < a_end

    def next_occurrence(self, from_date: date | None = None) -> "Task | None":
        """Return a fresh, uncompleted Task for the next occurrence, or None if one-off.

        Daily tasks recur one day later, weekly tasks seven days later. The step is
        computed with datetime.timedelta off a base date (the task's own due_date if
        set, otherwise today), so 'today + 1 day' is always a real calendar date.
        """
        step = self.RECUR_STEP.get(self.recurring)
        if step is None:  # recurring == "none" -> does not repeat
            return None
        base = from_date or self.due_date or date.today()
        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            preferred_time=self.preferred_time,
            recurring=self.recurring,
            category=self.category,
            completed=False,
            due_date=base + step,
        )

    def mark_complete(self) -> None:
        """Mark this task as done for today."""
        self.completed = True

    def reset(self) -> None:
        """Clear the completion status (e.g., at the start of a new day)."""
        self.completed = False


@dataclass
class Pet:
    """An animal being cared for. Tasks belong to a pet."""

    name: str
    species: str = "other"  # dog | cat | other
    age: int | None = None
    notes: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet (ignores exact duplicates)."""
        if task not in self.tasks:
            self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet, if present."""
        if task in self.tasks:
            self.tasks.remove(task)

    def list_tasks(self) -> list[Task]:
        """Return all tasks belonging to this pet."""
        return list(self.tasks)

    def complete_task(self, task: Task) -> Task | None:
        """Mark one of this pet's tasks done and, if it recurs, attach its next occurrence.

        Returns the newly created follow-up Task (daily/weekly), or None for one-offs.
        """
        task.mark_complete()
        upcoming = task.next_occurrence()
        if upcoming is not None:
            self.add_task(upcoming)
        return upcoming


@dataclass
class PlanEntry:
    """One task placed at a specific time slot within a daily plan."""

    task: Task
    start_time: time
    end_time: time
    reason: str = ""

    def __str__(self) -> str:
        return (
            f"{self.start_time:%H:%M} — {self.task.title} "
            f"({self.task.duration_minutes} min) [{self.task.priority}]"
        )


@dataclass
class DailyPlan:
    """The output the user views: an ordered, time-stamped set of tasks plus reasoning."""

    plan_date: date
    entries: list[PlanEntry] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_minutes: int = 0

    def add_entry(self, task: Task, start_time: time, reason: str = "") -> PlanEntry:
        """Add a scheduled task to the plan starting at the given time."""
        end_time = _to_time(_to_minutes(start_time) + task.duration_minutes)
        entry = PlanEntry(task=task, start_time=start_time, end_time=end_time, reason=reason)
        self.entries.append(entry)
        self.total_minutes += task.duration_minutes
        return entry

    def to_display(self) -> str:
        """Return a human-readable, formatted version of the plan."""
        header = f"Daily plan for {self.plan_date:%Y-%m-%d}:"
        if not self.entries:
            return header + "\n  (no tasks scheduled)"
        lines = [header]
        for entry in self.entries:
            lines.append(f"  {entry}")
            if entry.reason:
                lines.append(f"      ↳ {entry.reason}")
        if self.skipped_tasks:
            skipped = ", ".join(t.title for t in self.skipped_tasks)
            lines.append(f"  Skipped (no time / not due): {skipped}")
        for warning in self.warnings:
            lines.append(f"  {warning}")
        return "\n".join(lines)

    def summary(self) -> str:
        """Return a one-line explanation of the plan overall."""
        return (
            f"Scheduled {len(self.entries)} task(s) using {self.total_minutes} min; "
            f"skipped {len(self.skipped_tasks)}."
        )


@dataclass
class Owner:
    """The person using the app; carries constraints and preferences."""

    name: str
    available_minutes: int = 0
    available_from: time | None = None
    available_until: time | None = None
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        if pet not in self.pets:
            self.pets.append(pet)

    def add_task(self, pet: Pet, task: Task) -> None:
        """Add a task to one of this owner's pets (explicit pet avoids ambiguity)."""
        if pet not in self.pets:
            self.add_pet(pet)
        pet.add_task(task)

    def mark_task_complete(self, pet: Pet, task: Task) -> Task | None:
        """Complete a task for one of this owner's pets; spawns the next occurrence if recurring.

        Mirrors add_task(pet, task): the explicit pet avoids ambiguity about who owns
        the task. Returns the follow-up Task for daily/weekly frequencies, else None.
        """
        if pet not in self.pets:
            self.add_pet(pet)
        return pet.complete_task(task)

    def all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets (single source of truth)."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.list_tasks())
        return tasks

    def filter_tasks(
        self, *, pet_name: str | None = None, completed: bool | None = None
    ) -> list[Task]:
        """Return tasks narrowed by pet name and/or completion status.

        Both filters are optional (keyword-only) — any argument left as None means
        "don't filter on that dimension":
        - pet_name: keep only tasks belonging to the pet with this name (case-insensitive)
        - completed: True -> only done tasks, False -> only pending, None -> either
        """
        results: list[Task] = []
        for pet in self.pets:
            if pet_name is not None and pet.name.lower() != pet_name.lower():
                continue
            for task in pet.tasks:
                if completed is not None and task.completed != completed:
                    continue
                results.append(task)
        return results

    def set_availability(self, start: time, end: time) -> None:
        """Set the daily time window the owner has for pet care."""
        self.available_from = start
        self.available_until = end
        self.available_minutes = max(0, _to_minutes(end) - _to_minutes(start))

    def time_budget(self) -> int:
        """Return the total minutes available today (explicit budget, else the window)."""
        if self.available_minutes > 0:
            return self.available_minutes
        start = self.available_from or DEFAULT_START
        end = self.available_until or DEFAULT_END
        return max(0, _to_minutes(end) - _to_minutes(start))


class Scheduler:
    """The engine that turns tasks + constraints into a DailyPlan.

    Not a dataclass — this object owns behavior (the scheduling logic) rather
    than being a simple data record.
    """

    def __init__(
        self, owner: Owner, tasks: list[Task] | None = None, strategy: str = "priority-first"
    ) -> None:
        self.owner = owner
        # Single source of truth: default to the tasks already attached to the
        # owner's pets. An explicit list can still be passed to override/filter.
        self.tasks = tasks if tasks is not None else owner.all_tasks()
        self.strategy = strategy

    def candidate_tasks(self) -> list[Task]:
        """Return tasks eligible for today: due and not already completed."""
        return [t for t in self.tasks if t.is_due_today() and not t.completed]

    def sort_tasks(self) -> list[Task]:
        """Order candidates by highest priority first, then shortest duration to break ties."""
        return sorted(
            self.candidate_tasks(),
            key=lambda t: (-t.priority_weight(), t.duration_minutes, t.title),
        )

    def sort_by_time(self) -> list[Task]:
        """Order candidate tasks chronologically by their preferred_time.

        Uses sorted() with a lambda `key`. The key is a (has_no_time, time) tuple:
        tasks with no preferred_time sort to the very end (treated as "any time"),
        and the rest sort by clock time. Because datetime.time objects already
        compare chronologically, no manual parsing is needed.

        Note on "HH:MM" strings: if preferred_time were stored as a string like
        "08:30" instead of a time object, the exact same lambda-key approach works —
        zero-padded "HH:MM" strings sort lexicographically in clock order, so
        `key=lambda t: t.preferred_time` would already be chronological.
        """
        return sorted(
            self.candidate_tasks(),
            key=lambda t: (t.preferred_time is None, t.preferred_time or time(0, 0)),
        )

    def fits_in_budget(self, task: Task, remaining: int) -> bool:
        """Return True if the task fits within the remaining time budget."""
        return task.duration_minutes <= remaining

    def build_plan(self, plan_date: date | None = None) -> DailyPlan:
        """Greedily place sorted tasks into the owner's window, skipping any that don't fit."""
        plan = DailyPlan(plan_date=plan_date or date.today())

        window_start = self.owner.available_from or DEFAULT_START
        window_end = self.owner.available_until or DEFAULT_END
        cursor = _to_minutes(window_start)
        window_limit = _to_minutes(window_end)
        budget = self.owner.time_budget()

        for task in self.sort_tasks():
            remaining_budget = budget - plan.total_minutes
            fits_window = cursor + task.duration_minutes <= window_limit
            if self.fits_in_budget(task, remaining_budget) and fits_window:
                plan.add_entry(task, _to_time(cursor), reason=self.explain(task))
                cursor += task.duration_minutes
            else:
                plan.skipped_tasks.append(task)

        # Surface any preferred-time collisions on the plan (non-fatal warnings).
        plan.warnings = self.detect_conflicts()
        return plan

    def detect_conflicts(self) -> list[str]:
        """Return warning strings for tasks whose preferred times overlap (never raises).

        Lightweight strategy: each timed task occupies the interval
        [preferred_time, preferred_time + duration). Any two intervals that overlap are
        reported as a warning — so the program keeps running and simply tells the owner
        which tasks collide, rather than crashing or silently double-booking. Works for
        two tasks on the same pet or on different pets.
        """
        # id(task) -> pet name, so warnings can say who each task belongs to.
        pet_of = {id(t): pet.name for pet in self.owner.pets for t in pet.tasks}
        timed = [t for t in self.candidate_tasks() if t.preferred_time is not None]

        warnings: list[str] = []
        for a, b in itertools.combinations(timed, 2):
            if a.overlaps(b):  # interval math lives on Task.overlaps()
                pet_a, pet_b = pet_of.get(id(a), "?"), pet_of.get(id(b), "?")
                who = f"both for {pet_a}" if pet_a == pet_b else f"{pet_a} vs {pet_b}"
                warnings.append(
                    f"⚠ Time conflict ({who}): '{a.title}' at {a.preferred_time:%H:%M} "
                    f"overlaps '{b.title}' at {b.preferred_time:%H:%M}"
                )
        return warnings

    def explain(self, task: Task) -> str:
        """Return a short reason for why this task was chosen/placed where it is."""
        return (
            f"{task.priority.capitalize()} priority (weight {task.priority_weight()}), "
            f"{task.duration_minutes} min — fits the available time."
        )
