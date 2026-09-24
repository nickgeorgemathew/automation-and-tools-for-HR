"""
app.py

Streamlit dashboard for the notice period tracker.
Reads the already-processed parquet file (produced by data_pipeline.py)
-- does NOT touch the raw Excel or recompute anything, so it stays fast
even if this gets opened many times a day.

Run with:
    streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

PROCESSED_FILE = "processed.parquet"

st.set_page_config(page_title="Notice Period Tracker", layout="wide")


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


if not Path(PROCESSED_FILE).exists():
    st.error(
        f"'{PROCESSED_FILE}' not found. Run data_pipeline.py first:\n\n"
        f"    python data_pipeline.py --input employee_resignation.xlsx --output {PROCESSED_FILE}"
    )
    st.stop()

df = load_data(PROCESSED_FILE)

st.title("Notice Period Tracker")

# -----------------------------------------------------------------
# Sidebar: which date to filter by, then month/week dropdowns
# -----------------------------------------------------------------
st.sidebar.header("Filters")

view_by = st.sidebar.radio(
    "View by",
    ["Completion Date", "Resignation Date"],
    help="Completion Date = who is finishing notice in this window. "
         "Resignation Date = who resigned in this window.",
)
prefix = "completion" if view_by == "Completion Date" else "resignation"
date_col = "Completion Date" if view_by == "Completion Date" else "Resignation"

month_options = (
    df[[f"{prefix}_month_sort", f"{prefix}_month_name"]]
    .drop_duplicates()
    .sort_values(f"{prefix}_month_sort")[f"{prefix}_month_name"]
    .tolist()
)
selected_month = st.sidebar.selectbox("Month", month_options)

month_df = df[df[f"{prefix}_month_name"] == selected_month]
week_options = sorted(month_df[f"{prefix}_week_number"].unique().tolist())
selected_week = st.sidebar.selectbox("Week", week_options, format_func=lambda w: f"Week {w}")

filtered = month_df[month_df[f"{prefix}_week_number"] == selected_week]

# -----------------------------------------------------------------
# Top metrics
# -----------------------------------------------------------------
col1, col2, col3 = st.columns(3)
col1.metric(f"{view_by} — this week", len(filtered))
col1.caption(f"{selected_month}, Week {selected_week}")

month_total = len(month_df)
col2.metric(f"{view_by} — this month", month_total)
col2.caption(selected_month)

# always show both totals for the same window, regardless of which
# view is selected, so you can compare resignations vs completions
other_prefix = "resignation" if prefix == "completion" else "completion"
other_label = "Resignation Date" if other_prefix == "resignation" else "Completion Date"
other_week_total = len(
    df[
        (df[f"{other_prefix}_month_name"] == selected_month)
        & (df[f"{other_prefix}_week_number"] == selected_week)
    ]
)
col3.metric(f"{other_label} — same window", other_week_total)
col3.caption("For comparison")

st.divider()


# -----------------------------------------------------------------
# Who exactly — the actual people list
# -----------------------------------------------------------------
st.subheader("People in this week")
people_cols = ["Name", "Department", "Designation", "Emp Code",
               "Resignation", "Notice Period", "Completion Date"]
st.dataframe(
    filtered[people_cols].sort_values(date_col),
    hide_index=True,
    use_container_width=True,
)

st.divider()

# -----------------------------------------------------------------
# By department, for the selected week
# -----------------------------------------------------------------
st.subheader(f"By Department — {selected_month}, Week {selected_week}")
by_dept = (
    filtered.groupby("Department")
    .size()
    .reset_index(name="Count")
    .sort_values("Count", ascending=False)
)
c1, c2 = st.columns([1, 1])
c1.dataframe(by_dept, hide_index=True, use_container_width=True)
c2.bar_chart(by_dept.set_index("Department")["Count"])

st.divider()



# -----------------------------------------------------------------
# Month-level trend across all weeks, by department
# -----------------------------------------------------------------
st.subheader(f"All weeks in {selected_month} — by Department")
month_by_dept_week = (
    month_df.groupby([f"{prefix}_week_number", "Department"])
    .size()
    .reset_index(name="Count")
    .pivot(index=f"{prefix}_week_number", columns="Department", values="Count")
    .fillna(0)
    .astype(int)
)
st.dataframe(month_by_dept_week, use_container_width=True)
# -----------------------------------------------------------------
# Month-level trend across all weeks, by department
# -----------------------------------------------------------------
st.subheader(f"All weeks in {selected_month} — by Department")
month_by_dept_week = (
    month_df.groupby([f"{prefix}_week_number", "Department"])
    .size()
    .reset_index(name="Count")
    .pivot(index=f"{prefix}_week_number", columns="Department", values="Count")
    .fillna(0)
    .astype(int)
)
st.dataframe(month_by_dept_week, use_container_width=True,)
 
st.divider()
 
# -----------------------------------------------------------------
# Full-history trend: Resignations vs Completions, by month
# (independent of the sidebar filters above — this shows everything)
# -----------------------------------------------------------------
st.subheader("Trend Over Time — Resignations vs Completions")
 
trend_departments = st.multiselect(
    "Filter trend by department (optional)",
    options=sorted(df["Department"].unique()),
    default=[],
    help="Leave empty to include all departments.",
)
trend_source = (
    df if not trend_departments else df[df["Department"].isin(trend_departments)]
)
 
resign_trend = (
    trend_source.groupby(["resignation_month_sort", "resignation_month_name"])
    .size()
    .reset_index(name="Resignations")
    .rename(columns={"resignation_month_sort": "month_sort",
                      "resignation_month_name": "month_name"})
)
complete_trend = (
    trend_source.groupby(["completion_month_sort", "completion_month_name"])
    .size()
    .reset_index(name="Completions")
    .rename(columns={"completion_month_sort": "month_sort",
                      "completion_month_name": "month_name"})
)
 
trend = pd.merge(
    resign_trend, complete_trend, on=["month_sort", "month_name"], how="outer"
).fillna(0)
trend[["Resignations", "Completions"]] = trend[["Resignations", "Completions"]].astype(int)
trend = trend.sort_values("month_sort")
 
if trend.empty:
    st.info("No data to plot for this selection.")
else:
    st.line_chart(trend.set_index("month_name")[["Resignations", "Completions"]])
    st.caption(
        "X-axis is chronological by month (not alphabetical) since it's sorted "
        "by month_sort before the month_name index is set."
    )

