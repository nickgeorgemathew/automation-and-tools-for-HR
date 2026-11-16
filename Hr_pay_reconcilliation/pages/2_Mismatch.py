# pages/2_Mismatch.py
import pandas as pd
import streamlit as st

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
COLUMN_ORDER = [
    "severity", "error_type", "employee_id", "pay_period",
    "expected", "actual", "message", "detected_at",
]

# Shared state set by app.py
from src.shared import sidebar_controls
conn, selected, insights = sidebar_controls()

st.title("Mismatch Drilldown")
st.caption(f"Pay Period: {selected}")

if not insights:
    st.warning("No data loaded. Select a pay period from the sidebar.")
    st.stop()

risk_df = pd.DataFrame(insights.get("risk_ranked", []))
if risk_df.empty:
    st.info(
        "No findings stored for this period. Either the data is clean, "
        "or reconciliation has not been run for it."
    )
    st.stop()

# severity_rank is only a sorting helper, not something to show
risk_df = risk_df.drop(columns=["severity_rank"], errors="ignore")
risk_df = risk_df[[c for c in COLUMN_ORDER if c in risk_df.columns]]

# -- OVERVIEW CHART --
st.subheader("Findings by type")
st.bar_chart(risk_df["error_type"].value_counts())

# -- FILTERS --
st.subheader("Findings")
f1, f2, f3 = st.columns(3)

present = set(risk_df["severity"])
severity = f1.selectbox("Severity", ["All"] + [s for s in SEVERITY_ORDER if s in present])
error_type = f2.selectbox("Error type", ["All"] + sorted(risk_df["error_type"].unique()))
emp_query = f3.text_input("Employee ID contains")

view = risk_df
if severity != "All":
    view = view[view["severity"] == severity]
if error_type != "All":
    view = view[view["error_type"] == error_type]
if emp_query.strip():
    # employee_id is None for headcount findings, so fill before matching
    view = view[
        view["employee_id"].fillna("").str.contains(emp_query.strip(), case=False, regex=False)
    ]

st.caption(f"Showing {len(view)} of {len(risk_df)} findings")

if view.empty:
    st.info("No findings match these filters.")
else:
    st.dataframe(view, hide_index=True)
    st.download_button(
        "Download these rows (CSV)",
        data=view.to_csv(index=False).encode("utf-8"),
        file_name=f"findings_{str(selected)[:10]}.csv",
        mime="text/csv",
    )