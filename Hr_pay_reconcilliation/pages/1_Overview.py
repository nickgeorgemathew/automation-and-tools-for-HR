# pages/1_Overview.py
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from config import settings
from src.reconciliation import run_reconciliation
from src.shared import sidebar_controls
from src.validator import run_main
import pandas as pd
from config import settings
cols = pd.read_csv(settings.incoming_feeds).columns.tolist()
exp = settings.EXPECTED_COLUMNS["hris_export"]
print("missing:", [c for c in exp if c not in cols])
print("extra:  ", [c for c in cols if c not in exp])
print(repr(cols[0]))   # a BOM shows up here

# Only these findings store money that was paid out and should not have been.
# Other error types keep counts, thresholds or gross pay in `actual`, so adding
# them into one rupee figure would be meaningless.
PAID_IN_ERROR = {"CRITICAL_TERMINATED_PAID", "ORPHAN_PAYROLL_RECORD"}


def feed_status(results, filename):
    """Turn run_main()'s return dict into (status, detail) for one feed file.

    status is "loaded", "skipped" or "failed". run_main() has three different
    ways of reporting a problem, and this is the one place that knows them all.
    """
    entry = results.get(filename)
    if entry is None:
        # validate_cols() failed: wrong name, wrong columns, or unreadable CSV.
        # run_main() only logs this case, it adds nothing to its result.
        return "failed", "Rejected before loading (bad columns or name). See logs/pipeline_errors.log."
    if isinstance(entry, str):
        # an exception inside run_main()'s loop for this file
        return "failed", entry

    ingest = entry["ingest"]
    audit_row, row_data = ingest.get("audit_row"), ingest.get("row_data")
    if isinstance(audit_row, str):
        # brittle: matches the message text written by run_ingestion()
        if "already uploaded" in audit_row:
            return "skipped", "Identical file was loaded before. Nothing new inserted."
        return "failed", audit_row
    if isinstance(row_data, str):
        # load_records() reports its own errors as a string
        return "failed", row_data

    loaded = len(row_data["valid_rows"])
    rejected = len(entry["df"]) - loaded
    return "loaded", f"{loaded} rows loaded, {rejected} rejected by row validation."


# Get shared state (connection, chosen pay period, insights) from src/shared.py
conn, selected, insights = sidebar_controls()

# Pages 2-4 read these keys
st.session_state["insights"] = insights
st.session_state["selected_period"] = selected

st.title("Payroll Overview")
st.caption(f"Pay Period: {selected}")

# -- UPLOAD FEEDS + RUN PIPELINE --
# Changing the widget keys after a successful run clears the three uploaders,
# so a second click cannot silently re-run the same files.
round_id = st.session_state.get("upload_round", 0)
run_finished = False
reconciled = False

with st.expander("Upload feed files and run pipeline", expanded=not insights):
    st.caption("Files are saved under the names the pipeline expects. The names you upload are ignored.")
    hris_file = st.file_uploader("HRIS Feed (CSV)", type="csv", key=f"hris_{round_id}")
    payroll_file = st.file_uploader("Payroll Feed (CSV)", type="csv", key=f"payroll_{round_id}")
    gl_file = st.file_uploader("GL Dump (CSV)", type="csv", key=f"gl_{round_id}")
    # date_input always returns a valid date, unlike free text
    pay_period = st.date_input("Pay period to reconcile", value=date.today().replace(day=1))

    if st.button("Run Pipeline"):
        uploads = {
            "HRIS": (settings.name_hris, hris_file),
            "Payroll": (settings.name_payroll, payroll_file),
            "GL": (settings.name_gl, gl_file),
        }
        missing = [label for label, (_, f) in uploads.items() if f is None]

        if missing:
            st.error("Upload all three files first. Missing: " + ", ".join(missing))
        else:
            period_str = pay_period.isoformat()
            try:
                with st.spinner("Running pipeline..."):
                    # 1. save each upload into the incoming folder, under the exact
                    #    name validator.py expects (it quarantines anything else)
                    incoming = Path(settings.incoming_feeds)
                    incoming.mkdir(parents=True, exist_ok=True)
                    for label, (filename, f) in uploads.items():
                        (incoming / filename).write_bytes(f.getvalue())

                    # 2. validate + ingest every file in the incoming folder
                    results = run_main()
                    feeds = {
                        label: feed_status(results, filename)
                        for label, (filename, _) in uploads.items()
                    }

                    # 3. reconcile, but only if every feed is usable and the period has data
                    findings, reason = None, None
                    failed = [label for label, (status, _) in feeds.items() if status == "failed"]
                    if failed:
                        reason = "Reconciliation not run: " + ", ".join(failed) + " failed to load."
                    else:
                        n_rows = conn.execute(
                            "SELECT COUNT(*) FROM fact_payroll WHERE Pay_Period = ?", [period_str]
                        ).fetchone()[0]
                        if n_rows == 0:
                            reason = f"Reconciliation not run: no payroll rows exist for {period_str}. Check the pay period."
                        else:
                            findings = run_reconciliation(conn, period_str)

                # 4. keep the outcome in session_state so it survives st.rerun()
                st.session_state["pipeline_report"] = {
                    "period": period_str,
                    "feeds": feeds,
                    "findings": findings,
                    "reason": reason,
                }
                run_finished = True
                reconciled = findings is not None
            except Exception as exc:
                st.error(f"Pipeline crashed: {exc}")

# Run after the expander block so st.rerun() is not inside the try/except
if run_finished:
    st.cache_data.clear()  # make load_insights re-run against the new data
    if reconciled:
        st.session_state["upload_round"] = round_id + 1  # reset the uploaders
    st.rerun()

# -- LAST PIPELINE RUN --
report = st.session_state.get("pipeline_report")
if report:
    st.subheader(f"Last pipeline run ({report['period']})")
    show = {"loaded": st.success, "skipped": st.info, "failed": st.error}
    for label, (status, detail) in report["feeds"].items():
        show[status](f"{label}: {detail}")

    if report["findings"] is None:
        st.warning(report["reason"])
    else:
        total = sum(report["findings"].values())
        st.success(f"Reconciliation complete: {total} findings across {len(report['findings'])} error types.")
        st.caption("A rule that crashed is logged in logs/reconciliation.log. It does not appear in these counts.")

st.divider()

if not insights:
    st.warning("No data loaded. Upload feeds above or select a pay period from the sidebar.")
    st.stop()

# -- KPI TILES --
dept_df = pd.DataFrame(insights.get("dept_costs", []))
dept_df.columns = [str(c).lower() for c in dept_df.columns]  # normalize to lowercase
dept_df = dept_df.rename(columns={"head_count": "headcount"})  # SQL alias is head_count
risk_df = pd.DataFrame(insights.get("risk_ranked", []))

total_gross = dept_df["total_gross"].sum() if not dept_df.empty else 0
headcount = dept_df["headcount"].sum() if not dept_df.empty else 0
paid_in_error = (
    risk_df.loc[risk_df["error_type"].isin(PAID_IN_ERROR), "actual"].sum()
    if not risk_df.empty else 0
)
critical_cnt = len(risk_df[risk_df["severity"] == "CRITICAL"]) if not risk_df.empty else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Payroll", f"Rs.{total_gross:,.0f}")
col2.metric("Headcount", str(int(headcount)))
col3.metric("Paid in Error", f"Rs.{paid_in_error:,.0f}")
col4.metric("Critical Flags", str(critical_cnt))

st.divider()

# -- DEPARTMENT COST CHART --
st.subheader("Department Cost Breakdown")
if dept_df.empty:
    st.info("No department data for this period.")
else:
    st.bar_chart(dept_df.set_index("department")[["total_gross", "total_net", "total_ot"]])