# src/shared.py
import streamlit as st
from src.anomaly_detector import run_insights
from src.ingestion import get_connection
from config import settings

@st.cache_resource
def get_conn():
    return get_connection(settings.database_path)

@st.cache_data
def load_insights(pay_period: str) -> dict:
    conn = get_conn()
    return run_insights(conn, pay_period)

def sidebar_controls() -> tuple:
    conn = get_conn()
    periods = [row[0] for row in conn.execute(
        "SELECT DISTINCT pay_period FROM fact_reconciliation ORDER BY pay_period DESC"
    ).fetchall()]

    with st.sidebar:
        st.title("HR Pay Reconciliation")
        selected = st.selectbox("Select Pay Period", periods)

    insights = load_insights(str(selected))
    return conn, selected, insights