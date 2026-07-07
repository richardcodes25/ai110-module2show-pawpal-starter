from datetime import time

import streamlit as st

# Bridge to the logic layer: bring the backend classes into the UI.
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# --- Persistence ---------------------------------------------------------
# Streamlit reruns this whole script on every click, so a plain `owner = Owner()`
# would be recreated (and emptied) each time. Store it in st.session_state — a
# dict that survives reruns — and only build it once, guarded by this check.
if "owner" not in st.session_state:
    owner = Owner(name="Jordan")
    owner.add_pet(Pet(name="Mochi", species="dog"))
    st.session_state.owner = owner

# From here on, always read/mutate the persisted instance, never a fresh one.
owner = st.session_state.owner

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to **PawPal+** — a pet care planning assistant.

Add your pets and their care tasks below, then generate a daily schedule. The UI is wired
to the logic layer in `pawpal_system.py`: every action here creates and updates real
`Owner`, `Pet`, and `Task` objects that persist in this session.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

# --- Add a pet -----------------------------------------------------------
st.subheader("🐕 Add a Pet")
with st.form("add_pet_form", clear_on_submit=True):
    pet_name = st.text_input("Pet name", value="")
    species = st.selectbox("Species", ["dog", "cat", "other"])
    if st.form_submit_button("Add pet"):
        if pet_name.strip():
            # A submitted pet form is handled by Owner.add_pet(), which stores a
            # real Pet object on the persisted owner. Because `owner` points at
            # st.session_state.owner, the change survives the rerun.
            owner.add_pet(Pet(name=pet_name.strip(), species=species))
            st.success(f"Added {pet_name.strip()} the {species}.")
        else:
            st.warning("Please enter a pet name.")

# Streamlit reruns after the button click, so reading owner.pets now reflects
# the new pet — that's how the UI updates to show the change.
if owner.pets:
    st.write("Current pets:", ", ".join(f"{p.name} ({p.species})" for p in owner.pets))
else:
    st.info("No pets yet. Add one above.")

st.divider()

# --- Add a task to a pet -------------------------------------------------
st.subheader("📋 Add a Task")
if not owner.pets:
    st.info("Add a pet first, then you can give it tasks.")
else:
    with st.form("add_task_form", clear_on_submit=True):
        pet_names = [p.name for p in owner.pets]
        target_pet_name = st.selectbox("For which pet?", pet_names)
        task_title = st.text_input("Task title", value="Morning walk")
        col1, col2, col3 = st.columns(3)
        with col1:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        with col2:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        with col3:
            recurring = st.selectbox("Frequency", ["none", "daily", "weekly"])

        # Preferred start time is optional. Inside an st.form, widgets don't rerun
        # the script until submit, so we can't conditionally reveal the time picker.
        # Instead we always show both and only read the time if the box is checked —
        # a None preferred_time means "any time" and never triggers a conflict.
        time_col, pick_col = st.columns([1, 2])
        with time_col:
            has_time = st.checkbox("Set a start time", value=False)
        with pick_col:
            preferred = st.time_input("Preferred start", value=time(8, 0), step=900)

        if st.form_submit_button("Add task"):
            # Look up the chosen Pet object, then route the new Task through
            # Owner.add_task(pet, task) — the single entry point from Phase 2.
            target_pet = next(p for p in owner.pets if p.name == target_pet_name)
            owner.add_task(
                target_pet,
                Task(
                    title=task_title.strip() or "Untitled task",
                    duration_minutes=int(duration),
                    priority=priority,
                    recurring=recurring,
                    preferred_time=preferred if has_time else None,
                ),
            )
            st.success(f"Added '{task_title}' for {target_pet_name}.")

# Show the live task list. Filtering is delegated to Owner.filter_tasks() so the
# UI stays a thin view over the logic layer rather than re-implementing the query.
if owner.all_tasks():
    st.write("Current tasks:")
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        pet_filter = st.selectbox("Filter by pet", ["All"] + [p.name for p in owner.pets])
    with fcol2:
        status_filter = st.selectbox("Filter by status", ["All", "Pending", "Done"])

    # Translate the UI choices into Owner.filter_tasks() keyword arguments; None on a
    # dimension means "don't filter on it" (matches the method's contract).
    status_map = {"All": None, "Pending": False, "Done": True}
    shown_tasks = owner.filter_tasks(
        pet_name=None if pet_filter == "All" else pet_filter,
        completed=status_map[status_filter],
    )

    if shown_tasks:
        st.table(
            [
                {
                    "title": t.title,
                    "duration (min)": t.duration_minutes,
                    "priority": t.priority,
                    "preferred time": f"{t.preferred_time:%H:%M}" if t.preferred_time else "any",
                    "frequency": t.recurring,
                    "done": "✅" if t.completed else "—",
                }
                for t in shown_tasks
            ]
        )
    else:
        st.info("No tasks match the current filters.")
else:
    st.info("No tasks yet. Add one above.")

st.divider()

# --- Build the schedule --------------------------------------------------
st.subheader("🗓️ Build Schedule")
minutes = st.slider("Minutes available today", min_value=30, max_value=720, value=240, step=15)

if st.button("Generate schedule"):
    owner.available_minutes = minutes
    scheduler = Scheduler(owner)  # gathers tasks via owner.all_tasks()
    plan = scheduler.build_plan()

    # --- Conflict warnings come FIRST -----------------------------------
    # A time conflict is advisory, not fatal: the owner may knowingly double-book
    # (e.g. feed two pets at once), so we still render the full schedule below.
    # We surface each warning as its own amber st.warning box — placed above the
    # plan so the owner reads the caution before the schedule it affects. The
    # message text (which tasks, which times, which pets) comes straight from
    # Scheduler.detect_conflicts() via plan.warnings.
    if plan.warnings:
        st.warning(f"⚠️ Found {len(plan.warnings)} time conflict(s) — review before your day:")
        for warning in plan.warnings:
            st.warning(warning)

    # --- The schedule itself, as a professional table -------------------
    if plan.entries:
        st.markdown("**Today's Schedule**")
        st.table(
            [
                {
                    "⏰ time": f"{e.start_time:%H:%M}–{e.end_time:%H:%M}",
                    "task": e.task.title,
                    "duration": f"{e.task.duration_minutes} min",
                    "priority": e.task.priority,
                    "why chosen": e.reason,
                }
                for e in plan.entries
            ]
        )
        st.success(plan.summary())
    else:
        st.warning("No tasks could be scheduled. Add tasks or increase available time.")

    if plan.skipped_tasks:
        st.caption("Skipped (didn't fit): " + ", ".join(t.title for t in plan.skipped_tasks))

    # --- Explain the ordering -------------------------------------------
    # Expose both Scheduler ordering strategies so the owner can see *why* the plan
    # is ordered the way it is (priority-first) and preview an alternative (by time).
    with st.expander("How were these tasks ordered?"):
        st.caption("Priority-first (the strategy used above): highest priority, then shortest task.")
        st.markdown(
            "\n".join(f"1. **{t.title}** — {t.priority}, {t.duration_minutes} min"
                      for t in scheduler.sort_tasks())
            or "_No candidate tasks today._"
        )
        st.caption("Alternative — chronological by preferred start time:")
        st.markdown(
            "\n".join(
                f"1. **{t.title}** — {t.preferred_time:%H:%M}" if t.preferred_time
                else f"1. **{t.title}** — any time"
                for t in scheduler.sort_by_time()
            )
            or "_No candidate tasks today._"
        )
