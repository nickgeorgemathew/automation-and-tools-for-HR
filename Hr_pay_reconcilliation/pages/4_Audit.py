# pages/4_Audit.py
import os

import streamlit as st

from config import settings
from src.ingestion import get_connection
from src.report_generator import generate_all_reports

MIME = {
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}
LABEL = {"excel": "Excel", "pdf": "PDF"}


@st.cache_resource
def shared_connection():
    return get_connection(settings.database_path)


# Shared state set by app.py
from src.shared import sidebar_controls
conn, selected, insights = sidebar_controls()
st.title("Audit Trail")
st.caption(f"Pay Period: {selected}")

if not selected:
    st.warning("No pay period selected. Select one from the sidebar.")
    st.stop()

# A cursor per run: DuckDB connections should not be shared across Streamlit threads
conn = shared_connection().cursor()

# -- REPORTS --
st.subheader("Reports")

if st.button("Generate reports"):
    with st.spinner("Building reports..."):
        paths = generate_all_reports(conn, selected, output_dir=settings.output_path)
    st.session_state["report_files"] = {"period": str(selected), "paths": paths}

# Buttons live in session_state so the download buttons survive Streamlit reruns
state = st.session_state.get("report_files")
if state and state["period"] == str(selected):
    for key in ("excel", "pdf"):
        path = state["paths"].get(key)
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                st.download_button(
                    f"Download {LABEL[key]} report",
                    data=f.read(),
                    file_name=os.path.basename(path),
                    mime=MIME[key],
                    key=f"download_{key}",
                )
        else:
            # generate_all_reports returns None for a report that failed
            st.error(f"{LABEL[key]} report failed. Check logs/report_generator.log.")

st.divider()

# -- INGESTION HISTORY --
st.subheader("Ingestion History")
st.caption("Every file the pipeline has loaded, across all pay periods.")

try:
    audit_df = conn.execute(
        "SELECT filename, md5_hash, loaded_at, status FROM ingestion_audit ORDER BY loaded_at DESC"
    ).df()
except Exception as exc:
    st.info(f"Ingestion history is not available: {exc}")
else:
    if audit_df.empty:
        st.info("No files have been ingested yet.")
    else:
        audit_df["md5_hash"] = audit_df["md5_hash"].str[:12]
        st.dataframe(audit_df, hide_index=True)