import os
import sys
import subprocess
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FEEDS = ROOT / "src" / "data" / "incoming_feeds"

def run_cmd(command, cwd=ROOT):
    print(f"\n==== RUNNING: {command} ====")
    result = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    print(f"Exit code: {result.returncode}")
    return result.returncode

def ensure_dependencies():
    try:
        import duckdb, pytest
        print("Dependencies already available.")
        return 0
    except Exception:
        print("Missing Python packages. Installing from requirements.txt...")
        return run_cmd("python -m pip install -r requirements.txt")

def run_compile_check():
    return run_cmd("python -m compileall .")

def run_pytest():
    return run_cmd("python -m pytest -q")

def run_smoke_test():
    try:
        import duckdb
        from src import mock_generator, reconciliation

        FEEDS.mkdir(parents=True, exist_ok=True)

        print("\n==== GENERATING MOCK PAYROLL DATA ====")
        manifest = mock_generator.generate_all(
            employees=20,
            last_month="2024-10",
            months=3,
            seed=42,
            output_dir=str(FEEDS),
        )

        print("Generated manifest keys:", list(manifest.keys()))
        print("Files created:", [p.name for p in FEEDS.iterdir() if p.is_file()])

        conn = duckdb.connect(":memory:")

        conn.execute(
            "CREATE TABLE dim_employees AS SELECT * FROM read_csv_auto(?)",
            [str(FEEDS / "hris_export.csv")],
        )
        conn.execute(
            "CREATE TABLE fact_payroll AS SELECT * FROM read_csv_auto(?)",
            [str(FEEDS / "payroll_register.csv")],
        )
        conn.execute(
            "CREATE TABLE fact_gl AS SELECT * FROM read_csv_auto(?)",
            [str(FEEDS / "gl_dump.csv")],
        )

        print("\n==== RUNNING RECONCILIATION ====")
        summary = reconciliation.run_reconciliation(conn, "2024-10-01")
        print("Reconciliation summary:", summary)

        rows = conn.execute(
            "SELECT error_type, severity, employee_id, message FROM fact_reconciliation ORDER BY error_type"
        ).fetchall()
        print("\nStored findings:")
        for r in rows:
            print(r)

        conn.close()
        print("\nSMOKE TEST OK")
        return 0

    except Exception:
        traceback.print_exc()
        print("\nSMOKE TEST FAILED")
        return 1

def main():
    print("Project root:", ROOT)
    print("Checking project health...")

    dep_code = ensure_dependencies()
    if dep_code != 0:
        print("Dependency installation failed.")
        return dep_code

    compile_code = run_compile_check()
    pytest_code = run_pytest()
    smoke_code = run_smoke_test()

    print("\n==== FINAL RESULT ====")
    print(f"compileall exit code: {compile_code}")
    print(f"pytest exit code: {pytest_code}")
    print(f"smoke test exit code: {smoke_code}")

    if compile_code == 0 and pytest_code == 0 and smoke_code == 0:
        print("Everything looks healthy.")
        return 0
    else:
        print("There are errors or logic issues to fix.")
        return 1

if __name__ == "__main__":
    sys.exit(main())