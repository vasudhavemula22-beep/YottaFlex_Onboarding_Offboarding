
"""
YottaFlex Verification Script for Step 7.
Asserts that the 10-dimension validation module and edge-case unit tests pass completely.
"""

import json
import subprocess
import sys
from pathlib import Path


def main():
    print("\n" + "=" * 70)
    print("STEP 7 VERIFICATION: Data Validation & Integrity Test Suite")
    print("=" * 70)

    project_root = Path(__file__).resolve().parent
    python_exe = sys.executable

    # 1. Run Edge-Case Unit Tests
    print("\n[*] Step 7.1: Running Edge-Case Unit Tests...")
    cmd1 = [python_exe, "test_validation_edge_cases.py"]
    res1 = subprocess.run(cmd1, capture_output=True, text=True)
    if res1.returncode != 0:
        print("[FAIL] test_validation_edge_cases.py failed!")
        print(res1.stdout)
        print(res1.stderr)
        sys.exit(1)
    else:
        print("[PASS] Edge-case unit tests passed.")

    # 2. Run CLI Validation Runner against current yottaflex.db
    print("\n[*] Step 7.2: Running Full 10-Dimension Validation against yottaflex.db...")
    cmd2 = [python_exe, "run_validation.py"]
    res2 = subprocess.run(cmd2, capture_output=True, text=True)
    if res2.returncode != 0:
        print("[FAIL] run_validation.py reported baseline defects!")
        print(res2.stdout)
        print(res2.stderr)
        sys.exit(1)
    else:
        print("[PASS] 10-dimension validation passed.")
        for line in res2.stdout.splitlines():
            if line.startswith(("[*]", "[PASS]", "    -")):
                print(f"       {line}")

    # 3. Assert JSON Export Exists and has valid structure
    json_path = project_root / "exports" / "validation_summary.json"
    if not json_path.exists():
        print(f"[FAIL] Missing exports/validation_summary.json at {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("baseline_defects_count") != 0:
        print(f"[FAIL] Expected 0 baseline defects in JSON, found {data.get('baseline_defects_count')}")
        sys.exit(1)

    print(f"\n[PASS] Verified machine-readable JSON export: {len(data['findings'])} total findings recorded.")
    print("\n" + "=" * 70)
    print("[STEP 7 COMPLETE] All validation modules and integrity tests PASSED.")
    print("=" * 70 + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()