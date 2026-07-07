"""Basic tests for the PawPal+ logic layer (pawpal_system.py)."""

from datetime import date, timedelta

from datetime import time

from pawpal_system import Owner, Pet, Scheduler, Task


def test_mark_complete_changes_status():
    """Calling mark_complete() should flip a task from not-done to done."""
    task = Task("Morning walk", 30, priority="high")

    assert task.completed is False  # tasks start incomplete

    task.mark_complete()

    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    """Adding a task to a Pet should grow that pet's task list by one."""
    pet = Pet(name="Mochi", species="dog")

    assert len(pet.tasks) == 0  # no tasks to begin with

    pet.add_task(Task("Feeding", 10, priority="high"))

    assert len(pet.tasks) == 1


def test_completing_daily_task_spawns_next_day():
    """Completing a daily task should add a fresh occurrence due one day later."""
    pet = Pet(name="Mochi", species="dog")
    today = date(2026, 7, 7)
    walk = Task("Morning walk", 30, priority="high", recurring="daily", due_date=today)
    pet.add_task(walk)

    follow_up = pet.complete_task(walk)

    assert walk.completed is True
    assert follow_up is not None
    assert follow_up.completed is False
    assert follow_up.due_date == today + timedelta(days=1)
    assert len(pet.tasks) == 2  # original (done) + tomorrow's copy


def test_completing_weekly_task_spawns_seven_days_later():
    """A weekly task's next occurrence should be seven days out."""
    pet = Pet(name="Luna", species="cat")
    today = date(2026, 7, 7)
    task = Task("Deep clean", 45, recurring="weekly", due_date=today)
    pet.add_task(task)

    follow_up = pet.complete_task(task)

    assert follow_up.due_date == today + timedelta(days=7)


def test_completing_one_off_task_does_not_recur():
    """A non-recurring task should not spawn a follow-up when completed."""
    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi", species="dog")
    task = Task("Vet visit", 60, recurring="none")
    owner.add_task(pet, task)

    follow_up = owner.mark_task_complete(pet, task)

    assert follow_up is None
    assert len(pet.tasks) == 1


def test_detect_conflicts_flags_same_time_tasks():
    """Two tasks whose preferred times overlap should produce a warning, not a crash."""
    owner = Owner(name="Jordan")
    mochi = Pet(name="Mochi", species="dog")
    luna = Pet(name="Luna", species="cat")
    owner.add_task(mochi, Task("Nail trim", 15, preferred_time=time(9, 0)))
    owner.add_task(luna, Task("Litter cleanup", 15, preferred_time=time(9, 0)))

    conflicts = Scheduler(owner).detect_conflicts()

    assert len(conflicts) == 1
    assert "Nail trim" in conflicts[0] and "Litter cleanup" in conflicts[0]


def test_detect_conflicts_ignores_non_overlapping_tasks():
    """Back-to-back tasks that don't overlap should produce no warnings."""
    owner = Owner(name="Jordan")
    mochi = Pet(name="Mochi", species="dog")
    owner.add_task(mochi, Task("Walk", 30, preferred_time=time(8, 0)))   # 08:00–08:30
    owner.add_task(mochi, Task("Feed", 10, preferred_time=time(8, 30)))  # 08:30–08:40

    assert Scheduler(owner).detect_conflicts() == []


def test_task_overlaps_interval_boundaries():
    """Task.overlaps() uses half-open intervals: touching edges don't count."""
    walk = Task("Walk", 30, preferred_time=time(8, 0))   # 08:00–08:30
    feed = Task("Feed", 10, preferred_time=time(8, 30))  # 08:30–08:40 (touches, no overlap)
    meds = Task("Meds", 10, preferred_time=time(8, 20))  # 08:20–08:30 (overlaps walk)
    anytime = Task("Play", 15)                           # no preferred_time

    assert walk.overlaps(feed) is False
    assert walk.overlaps(meds) is True
    assert walk.overlaps(anytime) is False  # untimed tasks never conflict
