"""Basic tests for the PawPal+ logic layer (pawpal_system.py)."""

from pawpal_system import Pet, Task


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
