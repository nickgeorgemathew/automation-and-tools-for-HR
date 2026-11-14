# report_generator.py
"""
Generates Excel and PDF reports from reconciliation and anomaly data.
Reads from DuckDB via run_insights(). Writes files to disk.
"""
import logging
import os
from datetime import datetime

import pandas as pd
from fpdf import FPDF
from fpdf.fonts import FontFace

from src.anomaly_detector import run_insights
from src.ingestion import get_connection
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


def _cfg(name, default):
    return getattr(settings, name, None) or default


# RGB equivalents of your original hex severity colors
SEVERITY_RGB = {
    "CRITICAL": (248, 9, 9),      # #f80909
    "HIGH":     (234, 129, 24),   # #ea8118
    "MEDIUM":   (221, 201, 23),   # #ddc917
    "LOW":      (19, 207, 26),    # #13cf1a
}


def _build_pdf(insights: dict, pay_period: str, output_path: str):
    """Build the Payroll Audit PDF using fpdf2."""
    hospital = _cfg("hospital_name", "Hospital HR System")

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_margins(left=15, top=15, right=15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 1. Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 54, 93)  # #1a365d
    # Using "-" instead of em-dash so standard Helvetica renders cleanly
    pdf.cell(0, 10, f"{hospital} - Payroll Audit", new_x="LMARGIN", new_y="NEXT")

    # Bottom border under header
    pdf.set_draw_color(26, 54, 93)
    pdf.set_line_width(0.6)
    pdf.line(15, pdf.get_y(), 280, pdf.get_y())
    pdf.ln(4)

    # Metadata
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(34, 34, 34)
    pdf.write(6, "Pay Period: ")
    pdf.set_font("Helvetica", "", 10)
    pdf.write(6, f"{pay_period}\n")

    pdf.set_font("Helvetica", "B", 10)
    pdf.write(6, "Generated: ")
    pdf.set_font("Helvetica", "", 10)
    pdf.write(6, f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    pdf.ln(5)

    # 2. Key Findings (Observations)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(26, 54, 93)
    pdf.cell(0, 8, "Key Findings", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(34, 34, 34)
    observations = insights.get("observations", [])
    if not observations:
        pdf.cell(0, 6, "No observations recorded.", new_x="LMARGIN", new_y="NEXT")
    else:
        for obs in observations:
            # Indent bullet point and wrap long lines automatically
            pdf.set_x(18)
            pdf.multi_cell(0, 6, f"-  {obs}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # 3. Risk Findings Table
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(26, 54, 93)
    pdf.cell(0, 8, "Risk Findings", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    df = pd.DataFrame(insights.get("risk_ranked", []))
    df = df.drop(columns=["severity_rank"], errors="ignore")
    if df.empty:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(34, 34, 34)
        pdf.cell(0, 6, "No risk findings recorded for this pay period.", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_draw_color(51, 51, 51)
        pdf.set_line_width(0.2)

        # Header styling (#2c3e50 background, white bold text)
        header_style = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=(44, 62, 80))

        with pdf.table(
            headings_style=header_style,
            text_align="LEFT",
            padding=2,
            line_height=5,
        ) as table:
            # Add Header Row
            header_row = table.row()
            for col in df.columns:
                header_row.cell(str(col))

            # Add Data Rows with Severity Highlighting
            for _, row_data in df.iterrows():
                severity = str(row_data.get("severity", "")).upper()
                bg_rgb = SEVERITY_RGB.get(severity, (255, 255, 255))
                row_style = FontFace(color=(20, 20, 20), fill_color=bg_rgb)

                table_row = table.row(style=row_style)
                for val in row_data:
                    # Convert None/NaN to empty string cleanly
                    cell_text = "" if pd.isna(val) else str(val)
                    table_row.cell(cell_text)

    pdf.output(output_path)


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
    insights = run_insights(conn, pay_period)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(insights["ot_hotspots"]).to_excel(writer, sheet_name="OT_Hotspots", index=False)
        pd.DataFrame(insights["esi_boundary"]).to_excel(writer, sheet_name="ESI_Boundary", index=False)
        pd.DataFrame(insights["dept_costs"]).to_excel(writer, sheet_name="Dept_Costs", index=False)
        pd.DataFrame(insights["risk_ranked"]).to_excel(writer, sheet_name="Risk_Findings", index=False)

    log.info("Excel report written to %s", output_path)
    return output_path


# ------------------------------------------------------------------
# 2. PDF REPORT
# ------------------------------------------------------------------
def generate_pdf_report(conn, pay_period: str, output_path: str) -> str:
    log = _get_logger()
    insights = run_insights(conn, pay_period)

    _build_pdf(insights, pay_period, output_path)

    log.info("PDF report written to %s", output_path)
    return output_path


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
    pay_period = pd.to_datetime(pay_period).strftime("%Y-%m-%d")

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
        except Exception as e:
            log.exception("%s report failed", name)
            results[name] = None
            print(f"{name} ERROR: {e}")  # temporary — remove after fixingt(output_dir)
    print(results)
    return results
if __name__ == "__main__":
    conn = get_connection(settings.database_path)
    generate_all_reports(conn, output_dir=settings.output_path, pay_period="2024-10")