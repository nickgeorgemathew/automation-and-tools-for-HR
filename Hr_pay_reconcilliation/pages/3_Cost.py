# pages/3_Cost.py
import pandas as pd
import streamlit as st


def to_frame(rows):
    """List of dicts -> DataFrame with lower-case column names.

    The SQL in anomaly_detector returns Department / Employee_ID / Gross_Pay,
    so normalising here keeps the page working either way.
    """
    df = pd.DataFrame(rows)
    df.columns = [str(c).lower() for c in df.columns]
    return df


# Shared state set by app.py
from src.shared import sidebar_controls
conn, selected, insights = sidebar_controls()

st.title("Cost Intelligence")
st.caption(f"Pay Period: {selected}")

if not insights:
    st.warning("No data loaded. Select a pay period from the sidebar.")
    st.stop()

# -- 1. OVERTIME HOTSPOTS (Z-score across departments) --
st.subheader("Overtime Hotspots")
st.caption("Departments whose total overtime is far above the average department (Z-score).")

ot_df = to_frame(insights.get("ot_hotspots", []))
if ot_df.empty:
    st.info("No departments above the overtime threshold this period.")
else:
    st.bar_chart(ot_df.set_index("department")["z_score"])
    st.dataframe(
        ot_df[["department", "total_ot", "mean_ot", "z_score", "pct_above_avg"]].round(2),
        hide_index=True,
    )

st.divider()

# -- 2. OVERTIME INTENSITY (OT as % of gross, adjusts for department size) --
st.subheader("Overtime Intensity")
st.caption("Overtime as a % of gross pay. Total OT mostly flags big departments; this adjusts for size.")

dept_df = to_frame(insights.get("dept_costs", []))
if dept_df.empty:
    st.info("No department data for this period.")
else:
    gross = dept_df["total_gross"].where(dept_df["total_gross"] > 0)  # avoid divide-by-zero
    dept_df["ot_pct_of_gross"] = (dept_df["total_ot"] / gross * 100).round(1)
    dept_df = dept_df.sort_values("ot_pct_of_gross", ascending=False)
    st.bar_chart(dept_df.set_index("department")["ot_pct_of_gross"])

st.divider()

# -- 3. ESI BOUNDARY EMPLOYEES --
esi_df = to_frame(insights.get("esi_boundary", []))
st.subheader(f"ESI Boundary Employees ({len(esi_df)})")
st.caption(
    "A risk, not an error: gross pay is just under the ESI wage limit, "
    "so a small pay change flips eligibility. Smallest gap first."
)

if esi_df.empty:
    st.info("No employees near the ESI boundary this period.")
else:
    st.dataframe(
        esi_df.sort_values("gap")[["employee_id", "department", "gross_pay", "esi_limit", "gap"]].round(2),
        hide_index=True,
    )