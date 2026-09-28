import streamlit as st
import yaml
import os
import json
import pandas as pd
from pathlib import Path
import utils
import numpy as np
from datetime import datetime, timedelta
import utils
import importlib
importlib.reload(utils)

config=utils.load_config(config_path="config.yaml")
log_path=Path(config["Path"]["reminder_log"])

if "log_history" not in st.session_state:
    st.session_state.log_history = []


def save_log_with_history(updated_log: dict):
    """Saves current state to history stack before writing new changes."""
    current_log = utils.load_reminder_log(file_path=log_path)
    st.session_state.log_history.append(current_log)
    utils.save_reminder_log_atomic(updated_log, log_path)


def undo_last_change():
    """Pops the previous log state from history and restores it."""
    if st.session_state.log_history:
        previous_log = st.session_state.log_history.pop()
        utils.save_reminder_log_atomic(previous_log,log_path )
        st.toast("Restored previous reminder log!", icon="↩️")
    else:
        st.toast("Nothing to undo!", icon="⚠️")




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
df["Employee ID"] = df["Employee ID"].astype(str)
df["reminder_key"] = df.apply(
    lambda r: utils.build_reminder_key(r["Employee ID"], r["Due Date"]), axis=1
)


st.title("Annual Health Checkup Reminder ")

# --- DATA SUMMARIZATION FOR METRICS ---
department_selectbox = st.sidebar.multiselect("Department", options=df["Department"].unique())
selectbox_status=st.sidebar.multiselect("Status", options=["Overdue", "Due Soon", "OK"], default=["Overdue","Due Soon","OK"])

    
st.subheader("People in this week")



# --- DROPDOWN FILTER OPTIONS ---

selected_status = st.date_input(
    label="🔍 Filter by time",max_value="today"
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

show_already_reminded = st.sidebar.checkbox("Show Already Reminded Rows", value=False)

reminder_log = utils.load_reminder_log(log_path)
if not show_already_reminded:
    mask = mask & (~df["reminder_key"].isin(reminder_log.keys()))

filtered_df = df[mask]
status_counts = filtered_df['checkup_status'].value_counts()
overdue_count = int(status_counts.get("Overdue", 0))
due_soon_count = int(status_counts.get("Due Soon", 0))
ok_count = int(status_counts.get("OK", 0))
total_count = len(filtered_df)

col1, col2, col3, col4 = st.columns(4)
col1.metric(label="🚨 Overdue", value=overdue_count, border=True)
col2.metric(label="⏳ Due Soon", value=due_soon_count, border=True)
col3.metric(label="✅ OK", value=ok_count, border=True)
col4.metric(label="👥 Total Employees", value=total_count, border=True)





col1, col2 = st.columns([4, 1])
with col1:
    st.subheader("Actionable Reminders")
with col2:
    # Disable Undo button if history stack is empty
    can_undo = len(st.session_state.log_history) > 0
    if st.button("↩️ Undo Last", disabled=not can_undo, use_container_width=True):
        undo_last_change()
        st.rerun()

# --- TABLE RENDER & SELECTION ---
# Set on_select="rerun" to capture selections (or pass function reference without parentheses)
display_df = filtered_df.drop(columns=["reminder_key"])
styled_df = filtered_df.style.apply(highlight_rows, axis=1).format({
            "Due Date": lambda x: x.strftime("%B %d, %Y") if pd.notnull(x) else "",
            "Checkup Date": lambda x: x.strftime("%B %d, %Y") if pd.notnull(x) else "",
            "Date of Joining (DOJ)": lambda x: x.strftime("%B %d, %Y") if pd.notnull(x) else ""
        })

event = st.dataframe(
    styled_df,
    use_container_width=True,
    selection_mode="multi-row",
    on_select="rerun",
    key="reminder_table",
)

selected_positions = event.selection.rows

if selected_positions:
    st.info(f"{len(selected_positions)} row(s) selected.")

    if st.button("Mark Selected as Reminded", type="primary"):
        selected_rows = filtered_df.iloc[selected_positions]
        fresh_log = utils.load_reminder_log(log_path)

        for _, row in selected_rows.iterrows():
            key = row["reminder_key"]
            fresh_log[key] = {
                "Employee ID": row["Employee ID"],
                "due_date": str(row["Due Date"]),
                "reminded_on": datetime.now().isoformat(),
                "source": "dashboard_manual",
            }

        # Save with history snapshot
        save_log_with_history(fresh_log)
        st.success("Log updated successfully!")
        st.rerun()





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


st.divider()
