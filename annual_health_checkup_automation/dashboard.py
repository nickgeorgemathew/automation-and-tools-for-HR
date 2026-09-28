import streamlit as st
import yaml
import os
import json
import pandas as pd
from pathlib import Path
import utils
import numpy as np
from datetime import datetime, timedelta


def highlight_rows(row):
    status = row['checkup_status']
    if status == "Overdue":
        return ['background-color: #ffcccc; color: #800000;'] * len(row)
    elif status == "Due Soon":
        return ['background-color: #FFE5CC; color: #B35900;'] * len(row)
    elif status == "OK":
        return ['background-color: #E2EFDA; color: #2E5B2E;'] * len(row)
    return [''] * len(row)


with open(os.path.join(os.path.dirname(__file__), "config.yaml"), "r") as f:
    config = yaml.safe_load(f)
processed_path = Path(config["Path"]["processed_path"])

st.set_page_config(page_title="Notice Period Tracker", layout="wide")


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


if not processed_path.exists():
    st.error(f"{processed_path} not found.")        
    st.stop()

df = pd.read_json(processed_path)
df["Due Date"] = pd.to_datetime(df["Due Date"])
df["Checkup Date"] = pd.to_datetime(df["Checkup Date"])
df["Date of Joining (DOJ)"] = pd.to_datetime(df["Date of Joining (DOJ)"])


st.title("Annual Health Checkup Reminder ")

# --- DATA SUMMARIZATION FOR METRICS ---
department_selectbox = st.sidebar.multiselect("Department", options=df["Department"].unique())
selectbox_status=st.sidebar.multiselect("Status", options=["Overdue", "Due Soon", "OK"], default=["Overdue","Due Soon","OK"])

    

status_counts = df['checkup_status'].value_counts()
overdue_count = int(status_counts.get("Overdue", 0))
due_soon_count = int(status_counts.get("Due Soon", 0))
ok_count = int(status_counts.get("OK", 0))
total_count = len(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric(label="🚨 Overdue", value=overdue_count, border=True)
col2.metric(label="⏳ Due Soon", value=due_soon_count, border=True)
col3.metric(label="✅ OK", value=ok_count, border=True)
col4.metric(label="👥 Total Employees", value=total_count, border=True)

st.subheader("People in this week")

# --- DROPDOWN FILTER OPTIONS ---

selected_status = st.date_input(
    label="🔍 Filter by time",
)


# --- CONDITIONAL VIEWING FILTER ---

# Create the base mask using the date
mask = df['Due Date'] <= pd.to_datetime(selected_status)

# Only apply the Department filter if the user actually selected something
if department_selectbox:
    mask = mask & df['Department'].isin(department_selectbox)

# Only apply the Status filter if the user actually selected something
if selectbox_status:
    mask = mask & df['checkup_status'].isin(selectbox_status)

filtered_df = df[mask]

# --- RENDER TABLE CONDITIONALLY ---
if filtered_df.empty:
    st.info(f"No records found for: '{selected_status}'")
else:
    people_cols = filtered_df.columns.to_list()
    styled_df = filtered_df.style.apply(highlight_rows, axis=1).format({
            "Due Date": lambda x: x.strftime("%B %d, %Y") if pd.notnull(x) else "",
            "Checkup Date": lambda x: x.strftime("%B %d, %Y") if pd.notnull(x) else "",
            "Date of Joining (DOJ)": lambda x: x.strftime("%B %d, %Y") if pd.notnull(x) else ""
        })
    st.dataframe(styled_df, use_container_width=True)

st.divider()
