
"""
YottaFlex Multi-Format Data Export and Provenance Engine.
Exports SQLite database entities to CSV, JSON, and SQL seed scripts.
Computes SHA-256 cryptographic checksums and records generator provenance metadata.
"""

import csv
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

CORE_TABLES = [
    "departments",
    "roles",
    "access_roles",
    "employees",
    "managers",
    "onboarding_cases",
    "offboarding_cases",
    "tasks",
    "task_dependencies",
    "access_grants",
    "assets",
    "audit_events",
]


class DataExporter:
    """Manages transactional file exports, cryptographic hashing, and provenance manifests."""

    def __init__(self, db_path: Path, export_root: Path):
        self.db_path = db_path
        self.export_root = export_root
        self.csv_dir = export_root / "csv"
        self.json_dir = export_root / "json"
        self.sql_dir = export_root / "sql"

        for d in (self.csv_dir, self.json_dir, self.sql_dir):
            d.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def export_all(self, seed: int = 20261022, mode: str = "full") -> Dict[str, Any]:
        """Executes full multi-format export pipeline."""
        table_counts: Dict[str, int] = {}

        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # 1. Export CSV and JSON for all 12 core tables
            for tbl in CORE_TABLES:
                cursor.execute(f"SELECT * FROM {tbl};")
                rows = cursor.fetchall()
                table_counts[tbl] = len(rows)

                # Export CSV
                csv_path = self.csv_dir / f"{tbl}.csv"
                if rows:
                    cols = rows[0].keys()
                    with open(csv_path, "w", newline="", encoding="utf-8") as cf:
                        writer = csv.writer(cf)
                        writer.writerow(cols)
                        writer.writerows([tuple(r) for r in rows])
                else:
                    csv_path.touch()

                # Export JSON
                json_path = self.json_dir / f"{tbl}.json"
                dict_rows = [dict(r) for r in rows]
                with open(json_path, "w", encoding="utf-8") as jf:
                    json.dump(dict_rows, jf, indent=2)

            # 2. Export SQL Seed Script (DDL + Data)
            self._export_sql_seed_dump(conn)

            # 3. Export Source Manifest
            manifest = self._generate_source_manifest(seed, mode, table_counts)

            # 4. Compute Checksum Ledger
            checksums = self._generate_checksums()

        finally:
            conn.close()

        return {
            "tables_exported": len(CORE_TABLES),
            "table_counts": table_counts,
            "manifest": manifest,
            "checksums_count": len(checksums),
        }

    def _export_sql_seed_dump(self, conn: sqlite3.Connection) -> Path:
        """Generates self-contained SQL seed script that recreates tables and rows."""
        sql_path = self.sql_dir / "seed_data.sql"
        cursor = conn.cursor()

        project_root = self.db_path.parent
        schema_path = project_root / "sql" / "schema.sql"

        with open(sql_path, "w", encoding="utf-8") as sf:
            sf.write("-- ============================================================================\n")
            sf.write("-- YottaFlex Portable Database Seed Script (DDL + Relational Data)\n")
            sf.write(f"-- Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            sf.write("-- ============================================================================\n\n")

            # Write canonical DDL
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as scf:
                    sf.write(scf.read())
                    sf.write("\n\n")

            sf.write("-- ----------------------------------------------------------------------------\n")
            sf.write("-- DATA INSERTION STATEMENTS\n")
            sf.write("-- ----------------------------------------------------------------------------\n")

            for tbl in CORE_TABLES:
                cursor.execute(f"SELECT * FROM {tbl};")
                rows = cursor.fetchall()
                if not rows:
                    continue

                cols = rows[0].keys()
                cols_str = ", ".join(cols)
                sf.write(f"\n-- Table: {tbl} ({len(rows)} records)\n")

                for r in rows:
                    val_list = []
                    for v in r:
                        if v is None:
                            val_list.append("NULL")
                        elif isinstance(v, (int, float)):
                            val_list.append(str(v))
                        else:
                            clean_str = str(v).replace("'", "''")
                            val_list.append(f"'{clean_str}'")
                    sf.write(f"INSERT OR REPLACE INTO {tbl} ({cols_str}) VALUES ({', '.join(val_list)});\n")

        return sql_path

    def _generate_source_manifest(
        self, seed: int, mode: str, table_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """Records data provenance, generator versions, and environment metadata."""
        manifest_path = self.export_root / "source_manifest.json"
        total_records = sum(table_counts.values())

        manifest = {
            "project_name": "YottaFlex AI Employee Onboarding & Offboarding Automation",
            "generator_version": "1.0.0",
            "provenance_statement": (
                "100% Synthetic relational dataset generated via deterministic pseudorandom simulation. "
                "No real, confidential, or proprietary third-party data was accessed or incorporated."
            ),
            "random_seed": seed,
            "dataset_scale_mode": mode.upper(),
            "python_runtime": sys.version.split()[0],
            "generation_timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "target_database": self.db_path.name,
            "total_relational_records": total_records,
            "table_record_counts": table_counts,
            "exports_provided": [
                "exports/csv/*.csv (12 entities)",
                "exports/json/*.json (12 entities)",
                "exports/sql/seed_data.sql",
                "exports/ground_truth.csv",
                "exports/ground_truth.json",
                "exports/validation_summary.json",
                "exports/acceptance_report.json",
                "exports/checksums.json",
                "exports/checksums.sha256",
            ],
        }

        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)

        return manifest

    def _generate_checksums(self) -> Dict[str, str]:
        """Calculates SHA-256 hashes for all exported files and yottaflex.db."""
        checksums_json = self.export_root / "checksums.json"
        checksums_txt = self.export_root / "checksums.sha256"

        files_to_hash: List[Path] = [self.db_path]

        # Collect all files inside exports/ recursively
        for path in self.export_root.rglob("*"):
            if path.is_file() and path.name not in ("checksums.json", "checksums.sha256"):
                files_to_hash.append(path)

        hash_ledger: Dict[str, str] = {}
        gnu_lines: List[str] = []

        for fpath in sorted(files_to_hash):
            h = hashlib.sha256()
            with open(fpath, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            sha = h.hexdigest()
            # Store relative path for portability
            rel = fpath.relative_to(self.db_path.parent).as_posix()
            hash_ledger[rel] = sha
            gnu_lines.append(f"{sha}  {rel}")

        with open(checksums_json, "w", encoding="utf-8") as jf:
            json.dump(hash_ledger, jf, indent=2)

        with open(checksums_txt, "w", encoding="utf-8") as tf:
            tf.write("\n".join(gnu_lines) + "\n")

        return hash_ledger