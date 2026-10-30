"""
YottaFlex CLI Data Generation Orchestrator (Updated).
Seeds SQLite database with deterministic synthetic baseline data using two-pass hierarchy resolution.
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

from src.generator import (
    FULL_CONFIG,
    STARTER_CONFIG,
    GenerationConfig,
    YottaFlexDataGenerator,
)


def reset_database(conn: sqlite3.Connection, schema_path: Path) -> None:
    """Drops existing tables safely and re-executes clean DDL."""
    print("[*] Performing database schema reset...")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF;")

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    tables = [row[0] for row in cursor.fetchall()]
    for t in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {t};")

    with open(schema_path, "r", encoding="utf-8") as f:
        ddl = f.read()

    cursor.executescript(ddl)
    cursor.execute("PRAGMA foreign_keys = ON;")
    conn.commit()
    print("[+] Database reset complete with fresh schema.")


def insert_records(conn: sqlite3.Connection, data_dict: dict) -> None:
    """
    Inserts generated records across all tables inside a transaction.
    Uses two-pass insertion for employees to safely resolve self-referential manager_id keys.
    """
    cursor = conn.cursor()

    # 1. Insert independent catalog master tables first
    catalog_tables = ["departments", "roles", "access_roles"]
    for table in catalog_tables:
        records = data_dict.get(table, [])
        if records:
            cols = list(records[0].keys())
            placeholders = ", ".join(["?"] * len(cols))
            sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders});"
            rows = [[rec[c] for c in cols] for rec in records]
            cursor.executemany(sql, rows)
            print(f"    -> Inserted {len(rows):>6} rows into {table}")

    # 2. Employees: Pass 1 (Insert all employees with manager_id = NULL)
    emp_records = data_dict.get("employees", [])
    if emp_records:
        cols = list(emp_records[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO employees ({', '.join(cols)}) VALUES ({placeholders});"

        initial_rows = []
        mgr_updates = []
        for rec in emp_records:
            row_copy = dict(rec)
            target_mgr = row_copy["manager_id"]
            row_copy["manager_id"] = None  # Temporary NULL for initial insert
            initial_rows.append([row_copy[c] for c in cols])
            if target_mgr is not None:
                mgr_updates.append((target_mgr, rec["employee_id"]))

        cursor.executemany(sql, initial_rows)
        print(f"    -> Inserted {len(initial_rows):>6} rows into employees (Pass 1: base records)")

        # Employees: Pass 2 (Update manager_id now that all employees exist)
        if mgr_updates:
            cursor.executemany(
                "UPDATE employees SET manager_id = ? WHERE employee_id = ?;",
                mgr_updates,
            )
            print(f"    -> Updated  {len(mgr_updates):>6} employees with supervisory manager_id (Pass 2)")

    # 3. Insert remaining dependent transactional tables in strict topological order
    dependent_tables = [
        "managers",
        "onboarding_cases",
        "offboarding_cases",
        "tasks",
        "task_dependencies",
        "access_grants",
        "assets",
        "audit_events",
    ]

    for table in dependent_tables:
        records = data_dict.get(table, [])
        if not records:
            continue
        cols = list(records[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders});"
        rows = [[rec[c] for c in cols] for rec in records]
        cursor.executemany(sql, rows)
        print(f"    -> Inserted {len(rows):>6} rows into {table}")


def main():
    parser = argparse.ArgumentParser(description="YottaFlex Synthetic Relational Data Generator")
    parser.add_argument(
        "--mode",
        choices=["starter", "full"],
        default="starter",
        help="Dataset generation mode (starter=50 emps, full=1000 emps). Default: starter",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261022,
        help="Deterministic pseudorandom seed. Default: 20261022",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        default=True,
        help="Reset and recreate schema before generation (Default: True).",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="yottaflex.db",
        help="Path to target SQLite database. Default: yottaflex.db",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    db_path = project_root / args.db
    schema_path = project_root / "sql" / "schema.sql"

    print("=" * 70)
    print(f"YottaFlex Synthetic Relational Generator | Mode: {args.mode.upper()}")
    print(f"Random Seed: {args.seed} | Database Target: {db_path.name}")
    print("=" * 70)

    config: GenerationConfig = FULL_CONFIG if args.mode == "full" else STARTER_CONFIG
    config.seed = args.seed

    t0 = time.time()
    generator = YottaFlexDataGenerator(config)
    print("[*] Generating synthetic records in memory...")
    dataset = generator.generate_all()
    t_gen = time.time() - t0
    print(f"[+] Memory generation completed in {t_gen:.2f}s.")

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        if args.reset:
            reset_database(conn, schema_path)

        print("[*] Ingesting relational tables with PRAGMA foreign_keys = ON...")
        with conn:
            insert_records(conn, dataset)

        print("=" * 70)
        total_rows = sum(len(v) for v in dataset.values())
        total_time = time.time() - t0
        print(f"[SUCCESS] Ingested {total_rows:,} records in {total_time:.2f}s total.")
        print("=" * 70)
    except sqlite3.IntegrityError as ie:
        print(f"[FATAL INTEGRITY ERROR] Database insertion rolled back: {ie}")
        conn.rollback()
        sys.exit(1)
    except Exception as ex:
        print(f"[FATAL UNEXPECTED ERROR] {ex}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()