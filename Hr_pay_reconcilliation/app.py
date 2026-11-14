import streamlit as st
import pandas as pd
from config import settings
import duckdb
from src.anomaly_detector import run_insights
from src.ingestion import get_connection

st.set_page_config(page_title="Payroll Reconciliation", layout="wide")

st.title("HR Pay Reconciliation")
@st.cache_resource
def get_conn():
    conn=duckdb.connect(settings.database_path)
    return conn
    

@st.cache_data
def load_insights(pay_period: str) -> dict:
    conn = get_conn()
    insights=run_insights(conn=conn,pay_period=pay_period)
    return insights



# query available pay periods
conn = get_conn()
periods = [row[0] for row in conn.execute("SELECT DISTINCT pay_period FROM fact_reconciliation ORDER BY pay_period DESC").fetchall()]

# sidebar selector
with st.sidebar:
    st.title("HR Pay Reconciliation")
    selected = st.selectbox("Select Pay Period", periods)


# load insights for selected period
insights = load_insights(selected)

st.caption(f"Pay Period: {selected}")

if insights:
    dept_df = pd.DataFrame(insights.get("dept_costs", []))
    risk_df = pd.DataFrame(insights.get("risk_ranked", []))

    total_gross  = dept_df["total_gross"].sum() if not dept_df.empty else 0
    headcount    = dept_df["headcount"].sum()   if not dept_df.empty else 0
    flagged_amt  = risk_df["actual"].sum()      if not risk_df.empty else 0
    critical_cnt = len(risk_df[risk_df["severity"] == "CRITICAL"]) if not risk_df.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Payroll",  f"Rs.{total_gross:,.0f}")
    col2.metric("Headcount",      str(int(headcount)))
    col3.metric("Flagged Amount", f"Rs.{flagged_amt:,.0f}")
    col4.metric("Critical Flags", str(critical_cnt))

    st.divider()
    st.subheader("Department Cost Breakdown")
    if not dept_df.empty:
        st.bar_chart(dept_df.set_index("department")[["total_gross", "total_net", "total_ot"]])

    st.subheader("Key Observations")
    for obs in insights.get("observations", []):
        st.write(f"- {obs}")
else:
    st.info("Select a pay period from the sidebar.")

