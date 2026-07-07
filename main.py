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

    # 3. Add several tasks with different preferred times and priorities.
    owner.add_task(mochi, Task("Morning walk", 30, priority="high",
                               preferred_time=time(8, 0), recurring="daily", category="walk"))
    owner.add_task(mochi, Task("Feeding", 10, priority="high",
                               preferred_time=time(8, 30), category="feed"))
    owner.add_task(luna, Task("Litter cleanup", 15, priority="medium",
                              preferred_time=time(9, 0), category="grooming"))
    owner.add_task(luna, Task("Play/enrichment", 20, priority="low",
                              preferred_time=time(17, 0), recurring="daily", category="enrichment"))

    # 4. Build and print Today's Schedule.
    plan = Scheduler(owner).build_plan()

    print("=" * 48)
    print(f"  Today's Schedule for {owner.name}")
    print(f"  ({len(owner.pets)} pets, {len(owner.all_tasks())} tasks)")
    print("=" * 48)
    print(plan.to_display())
    print("-" * 48)
    print(plan.summary())


if __name__ == "__main__":
    main()
