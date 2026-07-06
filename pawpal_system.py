# pawpal_system.py — Logic layer: all backend classes for PawPal+ live here.
# This module holds the domain model and scheduling logic, kept separate from
# the Streamlit UI (app.py). No UI code should go in this file.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time


@dataclass
class Task:
    """A single unit of pet care work that the user wants scheduled."""

    title: str
    duration_minutes: int
    priority: str = "medium"  # "low" | "medium" | "high"
    preferred_time: time | None = None
    recurring: str = "none"  # "none" | "daily" | "weekly"
    category: str = "other"  # walk | feed | meds | grooming | enrichment | other

    def priority_weight(self) -> int:
        """Return a numeric rank for this task's priority (higher = more important)."""
        raise NotImplementedError

    def is_due_today(self) -> bool:
        """Return True if this task should be considered for today's plan."""
        raise NotImplementedError


@dataclass
class Pet:
    """An animal being cared for. Tasks belong to a pet."""

    name: str
    species: str = "other"  # dog | cat | other
    age: int | None = None
    notes: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        raise NotImplementedError

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        raise NotImplementedError

    def list_tasks(self) -> list[Task]:
        """Return all tasks belonging to this pet."""
        raise NotImplementedError


@dataclass
class PlanEntry:
    """One task placed at a specific time slot within a daily plan."""

    task: Task
    start_time: time
    end_time: time
    reason: str = ""


@dataclass
class DailyPlan:
    """The output the user views: an ordered, time-stamped set of tasks plus reasoning."""

    plan_date: date
    entries: list[PlanEntry] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)
    total_minutes: int = 0

    def add_entry(self, task: Task, start_time: time) -> None:
        """Add a scheduled task to the plan at the given start time."""
        raise NotImplementedError

    def to_display(self) -> str:
        """Return a human-readable, formatted version of the plan."""
        raise NotImplementedError

    def summary(self) -> str:
        """Return an explanation of the plan (why tasks were chosen/ordered)."""
        raise NotImplementedError


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
        raise NotImplementedError

    def add_task(self, task: Task) -> None:
        """Convenience helper to add a task (routed to the relevant pet)."""
        raise NotImplementedError

    def set_availability(self, start: time, end: time) -> None:
        """Set the daily time window the owner has for pet care."""
        raise NotImplementedError

    def time_budget(self) -> int:
        """Return the remaining minutes the owner has available."""
        raise NotImplementedError


class Scheduler:
    """The engine that turns tasks + constraints into a DailyPlan.

    Not a dataclass — this object owns behavior (the scheduling logic) rather
    than being a simple data record.
    """

    def __init__(self, owner: Owner, tasks: list[Task], strategy: str = "priority-first") -> None:
        self.owner = owner
        self.tasks = tasks
        self.strategy = strategy

    def build_plan(self) -> DailyPlan:
        """Produce a DailyPlan from the owner's constraints and candidate tasks."""
        raise NotImplementedError

    def sort_tasks(self) -> list[Task]:
        """Return the candidate tasks ordered for scheduling (e.g., by priority/duration)."""
        raise NotImplementedError

    def fits_in_budget(self, task: Task, remaining: int) -> bool:
        """Return True if the task fits within the remaining time budget."""
        raise NotImplementedError

    def resolve_conflicts(self) -> None:
        """Handle overlapping time slots or competing preferred times."""
        raise NotImplementedError

    def explain(self, task: Task) -> str:
        """Return a short reason for why this task was chosen/placed where it is."""
        raise NotImplementedError
