import streamlit as st
from datetime import datetime
import uuid
import sqlite3
import os
import pandas as pd
import io

# --- AUTH SETUP ---
USERS = {
    "admin@example.com": "admin123",
    "user1@example.com": "pass123",
}

def login():
    st.sidebar.title("🔐 Login")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if USERS.get(email) == password:
            st.session_state.user = email
            st.rerun()
        else:
            st.sidebar.error("Invalid credentials")

if "user" not in st.session_state:
    login()
    st.stop()

USER = st.session_state.user

# --- DB SETUP ---
def get_db():
    return sqlite3.connect("task_manager.db", check_same_thread=False)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY,
            user TEXT,
            members TEXT,
            status TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            user TEXT,
            vehicle_id TEXT,
            vehicle_type TEXT,
            task_type TEXT,
            docks TEXT,
            batch_id TEXT,
            status TEXT,
            start_time TEXT,
            end_time TEXT
        )
    """)
    conn.commit()
init_db()

# --- DB HELPERS ---
def save_batch(user, batch):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO batches VALUES (?, ?, ?, ?)",
                (batch["id"], user, ",".join(batch["members"]), batch["status"]))
    conn.commit()

def update_batch_status(batch_id, status):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE batches SET status=? WHERE id=?", (status, batch_id))
    conn.commit()

def load_batches(user):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, members, status FROM batches WHERE user=?", (user,))
    return [{"id": r[0], "members": r[1].split(","), "status": r[2]} for r in cur.fetchall()]

def save_task(user, task):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (task["id"], user, task["vehicle_id"], task["vehicle_type"], task["task_type"], ",".join(map(str, task["docks"])),
                 task["batch_id"], task["status"], task["start_time"], task.get("end_time", "")))
    conn.commit()

def update_task_end_time(task_id, end_time):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET end_time=?, status='completed' WHERE id=?", (end_time, task_id))
    conn.commit()

def load_tasks(user):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE user=?", (user,))
    rows = cur.fetchall()
    return [
        {
            "id": r[0], "vehicle_id": r[2], "vehicle_type": r[3], "task_type": r[4],
            "docks": list(map(int, r[5].split(","))), "batch_id": r[6], "status": r[7],
            "start_time": r[8], "end_time": r[9]
        } for r in rows if r[7] == "active"
    ]

def load_completed_tasks(user):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE user=? AND status='completed'", (user,))
    rows = cur.fetchall()
    return [
        {
            "id": r[0], "vehicle_id": r[2], "vehicle_type": r[3], "task_type": r[4],
            "docks": list(map(int, r[5].split(","))), "batch_id": r[6], "status": r[7],
            "start_time": r[8], "end_time": r[9]
        } for r in rows
    ]

# --- SESSION INIT ---
st.session_state.batches = load_batches(USER)
st.session_state.tasks = load_tasks(USER)
st.session_state.completed_tasks = load_completed_tasks(USER)

# --- UI ---
st.title("🚚 Vehicle Loading/Unloading Task Manager")
tab1, tab2, tab3 = st.tabs(["1️⃣ Setup Batches", "2️⃣ Assign Task", "3️⃣ Ongoing Tasks"])

# --- TAB 1 ---
with tab1:
    st.header("Create Labor Batches")

    if "batch_members" not in st.session_state:
        st.session_state.batch_members = [""]
    if "confirm_delete_id" not in st.session_state:
        st.session_state.confirm_delete_id = None

    def delete_batch(batch_id):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM batches WHERE id=?", (batch_id,))
        cur.execute("DELETE FROM tasks WHERE batch_id=?", (batch_id,))  # Optional
        conn.commit()

    with st.form("batch_form"):
        new_members = []
        for i, name in enumerate(st.session_state.batch_members):
            new_name = st.text_input(f"Laborer {i+1}", value=name, key=f"member_{i}")
            new_members.append(new_name)
        st.session_state.batch_members = new_members
        if st.form_submit_button("➕ Add More"):
            st.session_state.batch_members.append("")
        if st.form_submit_button("✅ Add Batch"):
            valid = [n.strip() for n in st.session_state.batch_members if n.strip()]
            if valid:
                batch = {"id": str(uuid.uuid4()), "members": valid, "status": "available"}
                st.session_state.batches.append(batch)
                save_batch(USER, batch)
                st.success(f"Batch added: {', '.join(valid)}")
                st.session_state.batch_members = [""]
            else:
                st.error("Enter at least one name")

    for idx, batch in enumerate(st.session_state.batches):
        cols = st.columns([6, 1])
        with cols[0]:
            st.write(f"**Batch {idx+1}** - {', '.join(batch['members'])} - Status: `{batch['status']}`")
        with cols[1]:
            if st.button("🗑️", key=f"del_{batch['id']}"):
                st.session_state.confirm_delete_id = batch["id"]

    # Confirmation dialog
    if st.session_state.confirm_delete_id:
        with st.expander("⚠️ Confirm Batch Deletion", expanded=True):
            batch_id = st.session_state.confirm_delete_id
            batch = next((b for b in st.session_state.batches if b["id"] == batch_id), None)
            if batch:
                st.warning(f"Are you sure you want to delete batch: {', '.join(batch['members'])}?")
                confirm_cols = st.columns([1, 1])
                if confirm_cols[0].button("✅ Yes, Delete"):
                    delete_batch(batch_id)
                    st.session_state.batches = [b for b in st.session_state.batches if b["id"] != batch_id]
                    st.session_state.confirm_delete_id = None
                    st.success("Batch deleted successfully.")
                    st.rerun()
                if confirm_cols[1].button("❌ Cancel"):
                    st.session_state.confirm_delete_id = None
                    st.info("Deletion cancelled.")


# --- TAB 2 ---
with tab2:
    st.header("Assign Task to a Batch")
    available_batches = [b for b in st.session_state.batches if b["status"] == "available"]
    if not available_batches:
        st.warning("No available batches")
    else:
        with st.form("assign_form"):
            vehicle_id = st.text_input("Vehicle ID")
            vehicle_type = st.selectbox("Vehicle Type", ["Small", "Medium", "Large"])
            task_type = st.selectbox("Task Type", ["Loading", "Unloading"])
            docks = st.multiselect("Docks (2-17)", list(range(2, 18)))
            batch_options = {
                f"Batch {i+1}: {', '.join(batch['members'])}": batch["id"]
                for i, batch in enumerate(available_batches)
            }
            selected_label = st.selectbox("Select Batch", list(batch_options.keys()))
            if st.form_submit_button("✅ Assign Task") and vehicle_id and docks:
                selected_id = batch_options[selected_label]
                selected_batch = next(b for b in st.session_state.batches if b["id"] == selected_id)
                selected_batch["status"] = "busy"
                update_batch_status(selected_id, "busy")  # <-- persist in DB
                task = {
                    "id": str(uuid.uuid4()),
                    "vehicle_id": vehicle_id,
                    "vehicle_type": vehicle_type,
                    "task_type": task_type,
                    "docks": docks,
                    "batch_id": selected_id,
                    "status": "active",
                    "start_time": datetime.now().strftime("%H:%M:%S")
                }
                st.session_state.tasks.append(task)
                save_task(USER, task)
                st.success(f"Task assigned to batch: {', '.join(selected_batch['members'])}")

# --- TAB 3 ---
with tab3:
    st.header("Ongoing Tasks")
    to_remove = []
    for task in st.session_state.tasks:
        batch = next(b for b in st.session_state.batches if b["id"] == task["batch_id"])
        cols = st.columns([2, 2, 2, 2, 1])
        cols[0].write(f"**Vehicle:** {task['vehicle_id']}")
        cols[1].write(f"**Docks:** {', '.join(map(str, task['docks']))}")
        cols[2].write(f"**Batch:** {', '.join(batch['members'])}")
        cols[3].write(f"**Task:** {task['task_type']} ({task['vehicle_type']})")
        if cols[4].button("✅ Complete", key=task["id"]):
            batch["status"] = "available"
            update_batch_status(batch["id"], "available")  # <-- persist in DB
            end_time = datetime.now().strftime("%H:%M:%S")
            task["end_time"] = end_time
            task["status"] = "completed"
            st.session_state.completed_tasks.append(task)
            update_task_end_time(task["id"], end_time)
            to_remove.append(task["id"])
    st.session_state.tasks = [t for t in st.session_state.tasks if t["id"] not in to_remove]

    # Export
    all_tasks = st.session_state.tasks + st.session_state.completed_tasks
    export_data = []
    for task in all_tasks:
        batch = next(b for b in st.session_state.batches if b["id"] == task["batch_id"])
        export_data.append({
            "Vehicle ID": task["vehicle_id"],
            "Vehicle Type": task["vehicle_type"],
            "Task Type": task["task_type"],
            "Docks": ", ".join(map(str, task["docks"])),
            "Batch Members": ", ".join(batch["members"]),
            "Task Status": task["status"],
            "Start Time": task["start_time"],
            "End Time": task.get("end_time", "")
        })
    df = pd.DataFrame(export_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Tasks')
    st.download_button(
        label="📥 Download Excel",
        data=output.getvalue(),
        file_name="tasks.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
