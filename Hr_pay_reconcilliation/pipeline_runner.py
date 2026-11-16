import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FEEDS_DIR = ROOT / "src" / "data" / "incoming_feeds"
LOG_DIR = ROOT / "logs"


def print_section(title: str):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def run_command(command, cwd=None, env=None, capture_output=True):
    cwd = str(cwd or ROOT)
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        shell=True,
        text=True,
        capture_output=capture_output,
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
        import duckdb  # noqa: F401
        import pytest  # noqa: F401
        import pandas  # noqa: F401
        print("Dependencies already present.")
        return 0
    except Exception:
        print_section("INSTALLING DEPENDENCIES")
        return run_command(f'"{sys.executable}" -m pip install -r requirements.txt')


def run_compile_check():
    print_section("RUNNING PYTHON SYNTAX CHECK")
    return run_command(f'"{sys.executable}" -m compileall .')


def run_pytest():
    print_section("RUNNING TEST SUITE")
    return run_command(f'"{sys.executable}" -m pytest -q')


def run_reconciliation_smoke_check():
    print_section("RUNNING RECONCILIATION SMOKE TEST")
    try:
        import duckdb
        from src import mock_generator, reconciliation

        FEEDS_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        print("Generating mock payroll data...")
        manifest = mock_generator.generate_all(
            employees=20,
            last_month="2024-10",
            months=3,
            seed=42,
            output_dir=str(FEEDS_DIR),
        )
        print("Manifest keys:", list(manifest.keys()))
        print("Generated files:", [p.name for p in FEEDS_DIR.iterdir() if p.is_file()])

        conn = duckdb.connect(":memory:")

        conn.execute(
            "CREATE TABLE dim_employees AS SELECT * FROM read_csv_auto(?)",
            [str(FEEDS_DIR / "hris_export.csv")],
        )
        conn.execute(
            "CREATE TABLE fact_payroll AS SELECT * FROM read_csv_auto(?)",
            [str(FEEDS_DIR / "payroll_register.csv")],
        )
        conn.execute(
            "CREATE TABLE fact_gl AS SELECT * FROM read_csv_auto(?)",
            [str(FEEDS_DIR / "gl_dump.csv")],
        )

        summary = reconciliation.run_reconciliation(conn, "2024-10-01")
        print("Reconciliation summary:", summary)

        rows = conn.execute(
            "SELECT error_type, severity, employee_id, message FROM fact_reconciliation ORDER BY error_type"
        ).fetchall()
        print("Stored findings:")
        for row in rows:
            print(row)

        conn.close()
        print("Smoke test completed successfully.")
        return 0
    except Exception:
        traceback.print_exc()
        return 1


def main():
    print_section("PROJECT PIPELINE START")
    print(f"Project root: {ROOT}")
    print(f"Python executable: {sys.executable}")

    dep_result = ensure_dependencies()
    if dep_result != 0:
        print("Dependency install failed. Stopping pipeline.")
        return dep_result

    results = {
        "compileall": run_compile_check(),
        "pytest": run_pytest(),
        "smoke_check": run_reconciliation_smoke_check(),
    }

    print_section("PIPELINE SUMMARY")
    for step, code in results.items():
        status = "PASS" if code == 0 else "FAIL"
        print(f"{step}: {status} (exit code {code})")

    if any(code != 0 for code in results.values()):
        print("Pipeline finished with errors or logic issues.")
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
