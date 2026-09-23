"""
data_pipeline.py

Reads the raw employee_resignation.xlsx, derives Completion Date from
Resignation + Notice Period, and computes month/week labels for BOTH
the resignation date and the completion date independently (no shared
'relationship' needed, unlike Power BI).

Run manually, or on a schedule (cron) to refresh the processed file
that the Streamlit dashboard reads.

Usage:
    python data_pipeline.py --input employee_resignation.xlsx --output processed.parquet
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd


def month_week_columns(dates: pd.Series, prefix: str) -> pd.DataFrame:
    """
    Given a Series of dates, return a DataFrame with:
      {prefix}_month_name   -> 'February 2026'      (for display / dropdown)
      {prefix}_month_sort   -> 202602                (for chronological sort)
      {prefix}_week_number  -> 1, 2, 3, 4, (5)        (week-of-month, resets monthly)

    Week-of-month logic matches the DAX column from the Power BI model:
    week 1 starts on the 1st of the month, weeks run Mon-Sun.
    """
    month_start = dates.values.astype("datetime64[M]")
    month_start = pd.Series(month_start, index=dates.index)

    # weekday of the 1st of the month (Mon=0 ... Sun=6)
    first_weekday = month_start.dt.weekday

    week_number = ((dates - month_start).dt.days + first_weekday) // 7 + 1

    return pd.DataFrame({
        f"{prefix}_month_name": dates.dt.strftime("%B %Y"),
        f"{prefix}_month_sort": dates.dt.year * 100 + dates.dt.month,
        f"{prefix}_week_number": week_number,
    })


def process(input_path: str) -> pd.DataFrame:
    df = pd.read_excel(input_path)

    required = {"SI.no", "Emp Code", "Name", "Department", "Designation",
                "Resignation", "Notice Period"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input file is missing expected columns: {missing}")

    df = df.dropna(subset=["Emp Code", "Resignation", "Notice Period"]).copy()
    
    # 1. Parse your input string into datetime using the explicit format
    df["Resignation"] = pd.to_datetime(df["Resignation"], format="%d%m%Y", errors="coerce")
    df["Notice Period"] = df["Notice Period"].astype(int)
    
    # 2. Add notice period days to find the completion date
    df["Completion Date"] = df["Resignation"] + pd.to_timedelta(df["Notice Period"], unit="D")

    # 3. COMPUTE THE LABELS FIRST (while they are still true datetime objects)
    resign_cols = month_week_columns(df["Resignation"], "resignation")
    complete_cols = month_week_columns(df["Completion Date"], "completion")

    # 4. STRIP THE TIME COMPONENT (Convert columns to clean text strings last)
    df["Resignation"] = df["Resignation"].dt.strftime("%Y-%m-%d")
    df["Completion Date"] = df["Completion Date"].dt.strftime("%Y-%m-%d")

    # 5. Combine everything together into the final dataframe output
    out = pd.concat([df, resign_cols, complete_cols], axis=1)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="C:/Users/nikhi/Downloads/employee_resignation (1).xlsx")
    parser.add_argument("--output", default="processed.parquet")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = process(args.input)
    result.to_parquet(args.output, index=False)
    print(f"Processed {len(result)} rows -> {args.output}")


if __name__ == "__main__":
    main()
