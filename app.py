import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pandas as pd
import json

# Firebase Initialization
if not firebase_admin._apps:
    firebase_key = json.loads(st.secrets["FIREBASE_KEY"])
    cred = credentials.Certificate(firebase_key)
    firebase_admin.initialize_app(cred)
    
db = firestore.client()

def get_today_doc():
    doc_ref = db.collection("shifts").document("today")
    doc = doc_ref.get()
    if doc.exists:
        return doc_ref, doc.to_dict()
    else:
        default_data = {
            "availableLabors": [],
            "assignedTasks": [],
            "initialLabors": []
        }
        doc_ref.set(default_data)
        return doc_ref, default_data

def save_doc(doc_ref, data):
    doc_ref.set(data)

# Streamlit UI
st.title("🚚 Vehicle Labor Assignment System")

doc_ref, data = get_today_doc()

# --- Section 1: Add Available Labors ---
st.header("Add Available Labors")
with st.form("add_labors"):
    labor_input = st.text_input("Enter labor names (comma-separated):")
    submitted = st.form_submit_button("Add to Pool")
    if submitted:
        new_labors = [l.strip() for l in labor_input.split(",") if l.strip()]
        for name in new_labors:
            data["availableLabors"].append({"name": name, "busy": False})
            data["initialLabors"].append(name)
        save_doc(doc_ref, data)
        st.success("Added laborers to today's pool.")

# --- Section 2: Assign Task ---
st.header("Assign Task to Vehicle")
with st.form("assign_task"):
    vehicle_number = st.text_input("Vehicle Number")
    operation_type = st.selectbox("Operation", ["loading", "unloading"])
    size = st.selectbox("Size", ["small", "medium", "large"])
    labor_count = st.number_input("Required Labor Count", min_value=1, step=1)
    assign = st.form_submit_button("Assign")

    if assign:
        free_labors = [l for l in data["availableLabors"] if not l["busy"]]
        if len(free_labors) < labor_count:
            st.error("Not enough free laborers")
        else:
            selected = free_labors[:labor_count]
            for l in selected:
                l["busy"] = True

            task = {
                "vehicleNumber": vehicle_number,
                "operationType": operation_type,
                "size": size,
                "assignedLabors": [l["name"] for l in selected],
                "timestamp": datetime.now().isoformat()
            }
            data["assignedTasks"].append(task)
            save_doc(doc_ref, data)
            st.success(f"Assigned {labor_count} laborers to vehicle {vehicle_number}.")

# --- Section 3: Task Table ---
st.header("📄 Assigned Tasks")
if data["assignedTasks"]:
    df = pd.DataFrame(data["assignedTasks"])
    st.dataframe(df)
    csv = df.to_csv(index=False)
    st.download_button("Download Task Log as CSV", csv, "task_log.csv")
else:
    st.info("No tasks assigned yet.")

# --- Section 4: Reset Shift ---
st.header("⚠️ Admin Controls")
if st.button("Reset Today's Shift"):
    doc_ref.set({
        "availableLabors": [],
        "assignedTasks": [],
        "initialLabors": []
    })
    st.success("Shift reset.")

# --- Section 5: View Available/Busy Labors ---
st.header("🛌 Labor Status")
free = [l["name"] for l in data["availableLabors"] if not l["busy"]]
busy = [l["name"] for l in data["availableLabors"] if l["busy"]]

st.subheader("Free Labors")
st.write(free if free else "No free labors")

st.subheader("Busy Labors")
st.write(busy if busy else "No busy labors")
