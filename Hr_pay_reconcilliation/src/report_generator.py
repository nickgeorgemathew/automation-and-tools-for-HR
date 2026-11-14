# report_generator.py
"""
Generates Excel and PDF reports from reconciliation and anomaly data.
Reads from DuckDB via run_insights(). Writes files to disk.
"""
import logging
import os
from datetime import datetime

import pandas as pd
import weasyprint

from anomaly_detector import run_insights
from config import settings


def _get_logger():
    log = logging.getLogger("report_generator")
    if not log.handlers:
        os.makedirs("logs", exist_ok=True)
        h = logging.FileHandler("logs/report_generator.log")
        h.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        log.addHandler(h)
        log.setLevel(logging.INFO)
    return log



def _build_html(insights, pay_period):
    hospital = _cfg("hospital_name", "Hospital HR System")
    
    # header
    header = f"""
        <h1>{hospital} — Payroll Audit</h1>
        <p>Pay Period: {pay_period}</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    """
    
    # observations as bullet list
    obs_items = "".join(f"<li>{o}</li>" for o in insights["observations"])
    observations = f"<h2>Key Findings</h2><ul>{obs_items}</ul>"
    
    # risk table — your job: build this using df.style
    df = pd.DataFrame(insights["risk_ranked"])
    # apply colour per row based on severity column
    # use SEVERITY_COLORS dict
    # call .to_html() on the styled df
    risk_table = insights.to_html(index=False) # your job
    
    return f"<html><body>{header}{observations}{risk_table}</body></html>"



def _cfg(name, default):
    return getattr(settings, name, None) or default


SEVERITY_COLORS = SEVERITY_COLORS = {
    "CRITICAL": "#f80909",
    "HIGH":     "#ea8118",
    "MEDIUM":   "#ddc917",
    "LOW":      "#13cf1a",
}


# ------------------------------------------------------------------
# 1. EXCEL REPORT
# ------------------------------------------------------------------
def generate_excel_report(conn, pay_period: str, output_path: str) -> str:
    """
    Write a multi-sheet Excel file with all analyses for this pay period.
    Sheets: OT_Hotspots, ESI_Boundary, Dept_Costs, Risk_Findings

    Returns the output_path on success.
    """
    log = _get_logger()
    
    # Step 1: call run_insights() to get all five analyses
    # insights = run_insights(conn, pay_period)
    
    # Step 2: open an ExcelWriter with openpyxl engine
    # with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
    
    #   Step 3: for each sheet, convert the list of dicts to a DataFrame
    #   and write it to the named sheet
    #   pd.DataFrame(insights["ot_hotspots"]).to_excel(writer, sheet_name="OT_Hotspots", index=False)
    #   do the same for: esi_boundary → "ESI_Boundary"
    #                    dept_costs   → "Dept_Costs"
    #                    risk_ranked  → "Risk_Findings"
    
    # Step 4: log success and return output_path
    insights=run_insights(conn,pay_period)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(insights["ot_hotspots"]).to_excel(writer, sheet_name="OT_Hotspots", index=False)
        pd.DataFrame(insights["esi_boundary"]).to_excel(writer, sheet_name="esi_boundary", index=False)
        pd.DataFrame(insights["dept_costs"]).to_excel(writer, sheet_name="dept_costs", index=False)
        pd.DataFrame(insights["observations"],columns=["observations"]).to_excel(writer, sheet_name="observations", index=False)
        pd.DataFrame(insights["risk_ranked"]).to_excel(writer, sheet_name="risk_ranked", index=False)
    log.info("Success")
    return output_path


    



# ------------------------------------------------------------------
# 2. PDF REPORT
# ------------------------------------------------------------------
def generate_pdf_report(conn, pay_period, output_path):
    log = _get_logger()
    insights = run_insights(conn, pay_period)
    
    # build HTML string with header + observations + styled table
    html = _build_html(insights, pay_period)
    
    weasyprint.HTML(string=html).write_pdf(output_path)
    log.info("PDF report written to %s", output_path)
    return output_path   
    # Step 1: get insights
    # insights = run_insights(conn, pay_period)

    # Step 2: create the PDF document
    # doc = SimpleDocTemplate(output_path, pagesize=A4)
    # story = []   ← this is the list of elements that get rendered top to bottom

    # Step 3: add header
    # hospital_name = _cfg("hospital_name", "Hospital HR System")
    # story.append(Paragraph(f"{hospital_name} — Payroll Audit", styles["Title"]))
    # story.append(Paragraph(f"Pay Period: {pay_period}", styles["Normal"]))
    # story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    # story.append(Spacer(1, 20))

    # Step 4: add observations as bullet points
    # for obs in insights["observations"]:
    #     story.append(Paragraph(f"• {obs}", styles["Normal"]))
    # story.append(Spacer(1, 20))

    # Step 5: build the risk findings table
    # headers = ["Severity", "Error Type", "Employee", "Expected", "Actual", "Message"]
    # table_data = [headers]
    # for row in insights["risk_ranked"]:
    #     table_data.append([
    #         row.get("severity", ""),
    #         row.get("error_type", ""),
    #         row.get("employee_id", ""),
    #         row.get("expected", ""),
    #         row.get("actual", ""),
    #         row.get("message", ""),
    #     ])

    # Step 6: colour-code rows by severity
    # table_style = [("BACKGROUND", (0,0), (-1,0), colors.grey),  ← header row
    #                ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
    #                ("GRID",       (0,0), (-1,-1), 0.5, colors.black)]
    # for i, row in enumerate(insights["risk_ranked"], start=1):
    #     bg = SEVERITY_COLORS.get(row.get("severity"), colors.white)
    #     table_style.append(("BACKGROUND", (0,i), (-1,i), bg))

    # Step 7: add table to story and build PDF
    # t = Table(table_data)
    # t.setStyle(TableStyle(table_style))
    # story.append(t)
    # doc.build(story)

    # Step 8: log and return output_path
    



# ------------------------------------------------------------------
# RUNNER
# ------------------------------------------------------------------
def generate_all_reports(conn, pay_period: str, output_dir: str = "reports") -> dict:
    """
    Generate both reports. One failing must not stop the other.
    Returns dict with paths to generated files.
    """
    log = _get_logger()
    os.makedirs(output_dir, exist_ok=True)
    
    results = {}
    tasks = {
        "excel": lambda: generate_excel_report(
            conn, pay_period,
            os.path.join(output_dir, f"payroll_audit_{pay_period}.xlsx")
        ),
        "pdf": lambda: generate_pdf_report(
            conn, pay_period,
            os.path.join(output_dir, f"payroll_audit_{pay_period}.pdf")
        ),
    }
    
    for name, fn in tasks.items():
        try:
            results[name] = fn()
            log.info("%s report complete", name)
        except Exception:
            log.exception("%s report failed", name)
            results[name] = None
    
    return results