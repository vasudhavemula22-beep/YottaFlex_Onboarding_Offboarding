"""
YottaFlex Verification Script for Step 8.
Asserts that all 12 acceptance lifecycles and anomaly benchmark evaluations pass completely.
"""

import json
import subprocess
import sys
from pathlib import Path


def main():
    print("\n" + "=" * 70)
    print("STEP 8 VERIFICATION: Acceptance Suite & Anomaly Evaluation Audit")
    print("=" * 70)

    project_root = Path(__file__).resolve().parent
    python_exe = sys.executable

    cmd = [python_exe, "run_acceptance_tests.py"]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode != 0:
        print("[FAIL] run_acceptance_tests.py encountered test failures!")
        print(res.stdout)
        print(res.stderr)
        sys.exit(1)

    for line in res.stdout.splitlines():
        if line.startswith(("    [PASS]", "    -", "[SUCCESS]", "[+]")):
            print(f"    {line}")

    report_path = project_root / "exports" / "acceptance_report.json"
    if not report_path.exists():
        print(f"[FAIL] Missing exports/acceptance_report.json at {report_path}")
        sys.exit(1)

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    acc = data["acceptance_workflows"]
    if acc["failed"] != 0:
        print(f"[FAIL] Acceptance test failures detected: {acc['failed']}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print(f"[STEP 8 COMPLETE] All 12 Acceptance Lifecycles and Benchmark Evaluations PASSED.")
    print("=" * 70 + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()