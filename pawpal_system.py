# pawpal_system.py — Logic layer: all backend classes for PawPal+ live here.
# This module holds the domain model and scheduling logic, kept separate from
# the Streamlit UI (app.py). No UI code should go in this file.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time

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

    def priority_weight(self) -> int:
        """Return a numeric rank for this task's priority (higher = more important)."""
        return PRIORITY_ORDER.get(self.priority, PRIORITY_ORDER["medium"])

    def is_due_today(self) -> bool:
        """Return True if this task's frequency makes it a candidate for today."""
        return self.recurring in ("none", "daily", "weekly")

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

    def all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets (single source of truth)."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.list_tasks())
        return tasks

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

        return plan

    def resolve_conflicts(self) -> None:
        """Reserved hook for honoring preferred times; unused by the greedy strategy."""
        return None

    def explain(self, task: Task) -> str:
        """Return a short reason for why this task was chosen/placed where it is."""
        return (
            f"{task.priority.capitalize()} priority (weight {task.priority_weight()}), "
            f"{task.duration_minutes} min — fits the available time."
        )
