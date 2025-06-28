import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="CFC Time Study Dashboard", layout="wide")
st.title("📦 CFC Time Study Dashboard")

# Input default time values
default_time_3 = {"Small": 2, "Medium": 3, "Large": 4}
default_time_2 = {"Small": 3, "Medium": 4, "Large": 5}

with st.sidebar:
    st.header("🔧 Time Configurations")
    st.markdown("**Time taken per CFC (in minutes)**")
    time_3_small = st.number_input("3 People - Small", value=default_time_3["Small"])
    time_3_medium = st.number_input("3 People - Medium", value=default_time_3["Medium"])
    time_3_large = st.number_input("3 People - Large", value=default_time_3["Large"])

    time_2_small = st.number_input("2 People - Small", value=default_time_2["Small"])
    time_2_medium = st.number_input("2 People - Medium", value=default_time_2["Medium"])
    time_2_large = st.number_input("2 People - Large", value=default_time_2["Large"])

# Upload Excel file
df = None
st.subheader("📋 Upload SKU Data Sheet (.xlsx)")
uploaded_file = st.file_uploader("Upload Excel file with columns: SKU, CFC per pallete, CFC Size", type="xlsx")

if uploaded_file:
    df = pd.read_excel(uploaded_file)

if df is not None:
    # Use existing CFC Size column for categorization
    df = df.dropna(subset=["CFC Size"])
    df["CFC Size"] = df["CFC Size"].str.strip().str.capitalize()

    category_counts = df["CFC Size"].value_counts()
    total_skus = len(df)
    percentages = (category_counts / total_skus * 100).round(2)

    # Compute time
    total_time_3 = (
        (df["CFC Size"] == "Small").sum() * time_3_small +
        (df["CFC Size"] == "Medium").sum() * time_3_medium +
        (df["CFC Size"] == "Large").sum() * time_3_large
    )
    total_time_2 = (
        (df["CFC Size"] == "Small").sum() * time_2_small +
        (df["CFC Size"] == "Medium").sum() * time_2_medium +
        (df["CFC Size"] == "Large").sum() * time_2_large
    )
    delta_time = total_time_2 - total_time_3

    st.subheader("📊 SKU Categorization Summary")
    st.dataframe(df, use_container_width=True)

    st.subheader("🔍 Category Breakdown")
    st.write(f"**Total SKUs**: {total_skus}")
    for cat in ["Small", "Medium", "Large"]:
        st.write(f"**{cat}**: {category_counts.get(cat, 0)} SKUs ({percentages.get(cat, 0.0)}%)")

    st.subheader("⏱️ Time Study Summary")
    st.metric("Total Time (3 People)", f"{total_time_3} min")
    st.metric("Total Time (2 People)", f"{total_time_2} min")
    st.metric("Time Delta (2 - 3 People)", f"{delta_time} min")

    # Optional: Display chart
    fig, ax = plt.subplots()
    category_counts.plot(kind='bar', color=["green", "orange", "red"], ax=ax)
    ax.set_ylabel("Number of SKUs")
    ax.set_title("SKU Category Distribution")
    st.pyplot(fig)
else:
    st.info("Please upload a valid Excel file to proceed.")
