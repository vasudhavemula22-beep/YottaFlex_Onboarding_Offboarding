"""
YottaFlex Database Initialization Script.
Reads sql/schema.sql and instantiates yottaflex.db with foreign keys enabled.
"""

import os
import sqlite3
import sys
from pathlib import Path


def initialize_database(db_path: Path, schema_path: Path) -> None:
    """
    Executes DDL statements from schema_path to instantiate SQLite database at db_path.
    """
    print("=" * 70)
    print("YottaFlex Workflow Automation - Database Provisioning Engine")
    print("=" * 70)

    if not schema_path.exists():
        print(f"[FATAL ERROR] Schema file not found at: {schema_path}")
        sys.exit(1)

    print(f"[*] Reading schema definition: {schema_path.resolve()}")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Connecting to SQLite database: {db_path.resolve()}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Enforce foreign key constraints inside SQLite
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Verify foreign keys are enabled
        cursor.execute("PRAGMA foreign_keys;")
        fk_status = cursor.fetchone()[0]
        if fk_status != 1:
            raise RuntimeError("Failed to enable PRAGMA foreign_keys on SQLite connection.")
        print("[+] SQLite PRAGMA foreign_keys = ON verified successfully.")

        # Execute DDL batch
        cursor.executescript(schema_sql)
        conn.commit()
        print("[+] Schema DDL executed successfully.")

        # Count tables
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"
        )
        table_count = cursor.fetchone()[0]
        print(f"[+] Total tables provisioned: {table_count}")

    except sqlite3.Error as e:
        print(f"[FATAL DATABASE ERROR] SQLite error encountered: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

    print("=" * 70)
    print(f"[SUCCESS] Database successfully initialized at: {db_path.name}")
    print("=" * 70)


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent
    SCHEMA_FILE = PROJECT_ROOT / "sql" / "schema.sql"
    DATABASE_FILE = PROJECT_ROOT / "yottaflex.db"

    initialize_database(DATABASE_FILE, SCHEMA_FILE)