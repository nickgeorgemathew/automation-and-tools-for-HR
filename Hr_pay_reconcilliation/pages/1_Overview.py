# pages/1_Overview.py
import streamlit as st
import pandas as pd

# Get shared state from app.py
from src.shared import sidebar_controls
conn, selected, insights = sidebar_controls()

st.title("Payroll Overview")
st.caption(f"Pay Period: {selected}")

if not insights:
    st.warning("No data loaded. Select a pay period from the sidebar.")
    st.stop()

# -- KPI TILES --
dept_df = pd.DataFrame(insights.get("dept_costs", []))
risk_df = pd.DataFrame(insights.get("risk_ranked", []))

total_gross   = dept_df["total_gross"].sum() if not dept_df.empty else 0
headcount     = dept_df["headcount"].sum()   if not dept_df.empty else 0
flagged_amt   = risk_df["actual"].sum()      if not risk_df.empty else 0
critical_cnt  = len(risk_df[risk_df["severity"] == "CRITICAL"]) if not risk_df.empty else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Payroll",    f"Rs.{total_gross:,.0f}")
col2.metric("Headcount",        str(int(headcount)))
col3.metric("Flagged Amount",   f"Rs.{flagged_amt:,.0f}")
col4.metric("Critical Flags",   str(critical_cnt))

st.divider()

# -- DEPARTMENT COST CHART --
st.subheader("Department Cost Breakdown")
if dept_df.empty:
    st.info("No department data for this period.")
else:
    st.bar_chart(dept_df.set_index("department")[["total_gross", "total_net", "total_ot"]])