"""Basic tests for the PawPal+ logic layer (pawpal_system.py)."""

from datetime import date, time, timedelta

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


# --- Sorting correctness -------------------------------------------------

def test_sort_by_time_returns_chronological_order():
    """sort_by_time() should return tasks ordered by preferred_time, regardless of insert order."""
    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi", species="dog")
    # Add deliberately OUT of order.
    owner.add_task(pet, Task("Evening play", 20, preferred_time=time(17, 0)))
    owner.add_task(pet, Task("Morning walk", 30, preferred_time=time(8, 0)))
    owner.add_task(pet, Task("Midday feed", 10, preferred_time=time(12, 0)))

    ordered = Scheduler(owner).sort_by_time()
    times = [t.preferred_time for t in ordered]

    assert times == [time(8, 0), time(12, 0), time(17, 0)]


def test_sort_by_time_places_untimed_tasks_last():
    """Tasks without a preferred_time should sort to the end, not crash on None comparison."""
    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi", species="dog")
    owner.add_task(pet, Task("Anytime brushing", 10))  # no preferred_time
    owner.add_task(pet, Task("Morning walk", 30, preferred_time=time(8, 0)))

    ordered = Scheduler(owner).sort_by_time()

    assert ordered[0].title == "Morning walk"      # timed task first
    assert ordered[-1].preferred_time is None       # untimed sinks to the end


# --- Filtering -----------------------------------------------------------

def test_filter_tasks_by_pet_and_status():
    """filter_tasks() should narrow by pet name (case-insensitive) and completion status."""
    owner = Owner(name="Jordan")
    mochi = Pet(name="Mochi", species="dog")
    luna = Pet(name="Luna", species="cat")
    walk = Task("Walk", 30)
    owner.add_task(mochi, walk)
    owner.add_task(luna, Task("Litter", 15))
    walk.mark_complete()

    assert [t.title for t in owner.filter_tasks(pet_name="luna")] == ["Litter"]  # case-insensitive
    assert [t.title for t in owner.filter_tasks(completed=True)] == ["Walk"]
    assert [t.title for t in owner.filter_tasks(completed=False)] == ["Litter"]


def test_filter_tasks_empty_pet_returns_empty_list():
    """A pet with no tasks (or an unknown pet name) should return an empty list, not error."""
    owner = Owner(name="Jordan")
    owner.add_pet(Pet(name="Mochi", species="dog"))  # no tasks added

    assert owner.filter_tasks(pet_name="Mochi") == []
    assert owner.filter_tasks(pet_name="Nonexistent") == []


# --- Plan building -------------------------------------------------------

def test_build_plan_skips_task_larger_than_budget():
    """A task longer than the available window should be skipped, not crash the plan."""
    owner = Owner(name="Jordan")
    owner.set_availability(time(8, 0), time(8, 30))  # only 30 minutes
    pet = Pet(name="Mochi", species="dog")
    owner.add_task(pet, Task("Quick feed", 10))
    owner.add_task(pet, Task("Long grooming", 90))  # can't fit in 30 min

    plan = Scheduler(owner).build_plan()

    scheduled = [e.task.title for e in plan.entries]
    skipped = [t.title for t in plan.skipped_tasks]
    assert "Quick feed" in scheduled
    assert "Long grooming" in skipped


def test_build_plan_empty_when_no_tasks():
    """With no pets/tasks, build_plan() should return an empty plan and not raise."""
    owner = Owner(name="Jordan")

    plan = Scheduler(owner).build_plan()

    assert plan.entries == []
    assert "(no tasks scheduled)" in plan.to_display()


# --- Recurrence edge cases -----------------------------------------------

def test_daily_task_rolls_over_month_boundary():
    """timedelta math should roll a Jan 31 daily task to Feb 1, not an invalid Jan 32."""
    pet = Pet(name="Mochi", species="dog")
    task = Task("Meds", 5, recurring="daily", due_date=date(2026, 1, 31))
    pet.add_task(task)

    follow_up = pet.complete_task(task)

    assert follow_up.due_date == date(2026, 2, 1)


def test_future_dated_task_is_not_due_today():
    """A regenerated occurrence dated in the future must not count as due today."""
    today = date(2026, 7, 7)
    tomorrow = Task("Walk", 30, recurring="daily", due_date=today + timedelta(days=1))

    assert tomorrow.is_due_today(on_date=today) is False
    assert tomorrow.is_due_today(on_date=today + timedelta(days=1)) is True
