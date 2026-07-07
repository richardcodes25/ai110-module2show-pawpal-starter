# main.py — Temporary testing ground: run the PawPal+ logic in the terminal.
# Not part of the app; use `python main.py` to sanity-check the scheduler.

from datetime import time

from pawpal_system import Owner, Pet, Scheduler, Task


def main() -> None:
    # 1. Create an owner and set how much of the day they have for pet care.
    owner = Owner(name="Jordan")
    owner.set_availability(time(8, 0), time(12, 0))  # 8:00–12:00 window

    # 2. Create at least two pets and register them with the owner.
    mochi = Pet(name="Mochi", species="dog")
    luna = Pet(name="Luna", species="cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # 3. Add tasks OUT OF ORDER on purpose, so sort_by_time() has real work to do.
    #    (Evening play added first, morning walk last — deliberately scrambled.)
    owner.add_task(luna, Task("Play/enrichment", 20, priority="low",
                              preferred_time=time(17, 0), recurring="daily", category="enrichment"))
    owner.add_task(luna, Task("Litter cleanup", 15, priority="medium",
                              preferred_time=time(9, 0), category="grooming"))
    owner.add_task(mochi, Task("Feeding", 10, priority="high",
                               preferred_time=time(8, 30), category="feed"))
    owner.add_task(mochi, Task("Morning walk", 30, priority="high",
                               preferred_time=time(8, 0), recurring="daily", category="walk"))

    scheduler = Scheduler(owner)

    # 4. Sorting check: tasks should come back in chronological order by preferred_time.
    print("=" * 48)
    print("  Tasks sorted by time (Scheduler.sort_by_time)")
    print("=" * 48)
    for task in scheduler.sort_by_time():
        stamp = f"{task.preferred_time:%H:%M}" if task.preferred_time else "  --"
        print(f"  {stamp}  {task.title} ({task.duration_minutes} min, {task.priority})")

    # 5. Filtering check: narrow by pet name, then by completion status.
    print("\n" + "=" * 48)
    print("  Filtering (Owner.filter_tasks)")
    print("=" * 48)

    print("  Luna's tasks:")
    for task in owner.filter_tasks(pet_name="Luna"):
        print(f"    - {task.title}")

    # Mark one task done so the completion filter has something to separate.
    mochi.tasks[0].mark_complete()  # the first task attached to Mochi (Feeding, one-off)

    # 5b. Recurring regeneration: completing a "daily" task spawns tomorrow's copy.
    print("\n" + "=" * 48)
    print("  Recurring regeneration (Owner.mark_task_complete)")
    print("=" * 48)
    walk = next(t for t in mochi.tasks if t.title == "Morning walk")  # recurring="daily"
    print(f"  Mochi task count before completing the daily walk: {len(mochi.tasks)}")
    follow_up = owner.mark_task_complete(mochi, walk)
    print(f"  Mochi task count after:  {len(mochi.tasks)}  (a new occurrence was added)")
    if follow_up is not None:
        print(f"  New occurrence -> '{follow_up.title}', due {follow_up.due_date} "
              f"(completed={follow_up.completed}, still recurring={follow_up.recurring!r})")

    print("  Pending tasks (completed=False):")
    for task in owner.filter_tasks(completed=False):
        print(f"    - {task.title}")

    print("  Completed tasks (completed=True):")
    for task in owner.filter_tasks(completed=True):
        print(f"    - {task.title}")

    # 5c. Conflict detection: add a task at the SAME clock time as an existing one.
    #     Luna's "Litter cleanup" is at 09:00; give Mochi a "Nail trim" at 09:00 too.
    owner.add_task(mochi, Task("Nail trim", 15, priority="medium",
                               preferred_time=time(9, 0), category="grooming"))
    print("\n" + "=" * 48)
    print("  Conflict detection (Scheduler.detect_conflicts)")
    print("=" * 48)
    conflicts = Scheduler(owner).detect_conflicts()
    if conflicts:
        for warning in conflicts:
            print(f"  {warning}")
    else:
        print("  No time conflicts detected.")

    # 6. Build and print Today's Schedule (fresh Scheduler picks up all current tasks).
    plan = Scheduler(owner).build_plan()

    print("\n" + "=" * 48)
    print(f"  Today's Schedule for {owner.name}")
    print(f"  ({len(owner.pets)} pets, {len(owner.all_tasks())} tasks)")
    print("=" * 48)
    print(plan.to_display())
    print("-" * 48)
    print(plan.summary())


if __name__ == "__main__":
    main()
