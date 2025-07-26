import streamlit as st
from datetime import datetime
import uuid
import pandas as pd
import io

# --- SESSION STATE SETUP ---
if "batches" not in st.session_state:
    st.session_state.batches = []

if "tasks" not in st.session_state:
    st.session_state.tasks = []

if "batch_members" not in st.session_state:
    st.session_state.batch_members = [""]  # Start with one input field


# --- HEADER ---
st.title("🚚 Vehicle Loading/Unloading Task Manager")

# --- TAB SELECTION ---
tab1, tab2, tab3 = st.tabs(["1️⃣ Setup Batches", "2️⃣ Assign Task", "3️⃣ Ongoing Tasks"])

# --- TAB 1: SETUP BATCHES ---
with tab1:
    st.header("Create Labor Batches (Flexible size)")

    with st.form("batch_form"):
        st.subheader("Enter Laborer Names")

        # Display all current input fields
        new_members = []
        for i, name in enumerate(st.session_state.batch_members):
            new_name = st.text_input(f"Laborer {i + 1}", value=name, key=f"member_{i}")
            new_members.append(new_name)

        # Store back the updated names
        st.session_state.batch_members = new_members

        # Add new input field on button click
        if st.form_submit_button("➕ Add More"):
            st.session_state.batch_members.append("")

        # Submit the batch
        submitted = st.form_submit_button("✅ Add Batch")
        if submitted:
            valid_names = [name.strip() for name in st.session_state.batch_members if name.strip()]
            if len(valid_names) >= 1:
                batch_id = str(uuid.uuid4())
                st.session_state.batches.append({
                    "id": batch_id,
                    "members": valid_names,
                    "status": "available"
                })
                st.success(f"Batch added: {', '.join(valid_names)}")
                st.session_state.batch_members = [""]  # Reset form
            else:
                st.error("Please enter at least one name.")

    if st.session_state.batches:
        st.subheader("Current Batches")
        for idx, batch in enumerate(st.session_state.batches):
            members = ", ".join(batch["members"])
            st.write(f"**Batch {idx + 1}** - {members} - Status: `{batch['status']}`")


# --- TAB 2: ASSIGN TASK ---
with tab2:
    st.header("Assign Task to Next Available Batch")

    if not any(batch["status"] == "available" for batch in st.session_state.batches):
        st.warning("⚠️ No available batches. Please add more or mark tasks complete.")
    else:
        with st.form("assign_task"):
            vehicle_id = st.text_input("Vehicle ID")
            vehicle_type = st.selectbox("Vehicle Type", ["Small", "Medium", "Large"])
            task_type = st.selectbox("Task Type", ["Loading", "Unloading"])
            docks = st.multiselect("Select Docks (2–17)", list(range(2, 18)))
            assign_btn = st.form_submit_button("✅ Assign Task")

            if assign_btn and vehicle_id and docks:
                # Get the first available batch
                for batch in st.session_state.batches:
                    if batch["status"] == "available":
                        batch["status"] = "busy"
                        task_id = str(uuid.uuid4())
                        st.session_state.tasks.append({
                            "id": task_id,
                            "vehicle_id": vehicle_id,
                            "vehicle_type": vehicle_type,
                            "task_type": task_type,
                            "docks": docks,
                            "batch_id": batch["id"],
                            "status": "active",
                            "start_time": datetime.now().strftime("%H:%M:%S")
                        })
                        members = ", ".join(batch["members"])
                        st.success(f"Task assigned to Batch: {members}")
                        break

# --- TAB 3: ONGOING TASKS ---
with tab3:
    st.header("Ongoing Tasks")

    if not st.session_state.tasks:
        st.info("No active tasks currently.")
    else:
        to_remove = []
        for task in st.session_state.tasks:
            batch = next(b for b in st.session_state.batches if b["id"] == task["batch_id"])
            batch_members = ", ".join(batch["members"])
            cols = st.columns([2, 2, 2, 2, 1])
            with cols[0]:
                st.write(f"**Vehicle:** {task['vehicle_id']}")
            with cols[1]:
                st.write(f"**Docks:** {', '.join(map(str, task['docks']))}")
            with cols[2]:
                st.write(f"**Batch:** {batch_members}")
            with cols[3]:
                st.write(f"**Task:** {task['task_type']} ({task['vehicle_type']})")
            with cols[4]:
                if st.button("✅ Complete", key=task["id"]):
                    to_remove.append(task["id"])
                    batch["status"] = "available"

        # Remove completed tasks
        st.session_state.tasks = [t for t in st.session_state.tasks if t["id"] not in to_remove]

        # --- Export to Excel ---
        import pandas as pd
        import io

        st.subheader("📤 Export Tasks to Excel")

        # Convert tasks to DataFrame
        export_data = []
        for task in st.session_state.tasks:
            batch = next(b for b in st.session_state.batches if b["id"] == task["batch_id"])
            export_data.append({
                "Vehicle ID": task["vehicle_id"],
                "Vehicle Type": task["vehicle_type"],
                "Task Type": task["task_type"],
                "Docks": ", ".join(map(str, task["docks"])),
                "Batch Members": ", ".join(batch["members"]),
                "Task Status": task["status"],
                "Start Time": task["start_time"]
            })

        df = pd.DataFrame(export_data)

        # Convert to Excel in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='OngoingTasks')

        # Download button
        st.download_button(
            label="📥 Download Excel",
            data=output.getvalue(),
            file_name="ongoing_tasks.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

