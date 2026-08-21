#!/usr/bin/env python3
import os
import sys
import json
from src.parser import parse_scheme_meta, parse_nav_file
from src.db import DatabaseManager
from src.report import generate_report

DEFAULT_DB_URL = "postgresql://ws:ws@localhost:5432/worksample"


def main():
    print("=" * 60)
    print("AMFI NAV Data Pipeline & Report Generator")
    print("=" * 60)

    db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or DEFAULT_DB_URL
    meta_path = os.getenv("META_PATH", "data/scheme_meta.csv")
    nav_file_1 = os.getenv("NAV_FILE_1", "data/nav_2026-06-29.txt")
    nav_file_2 = os.getenv("NAV_FILE_2", "data/nav_2026-06-30.txt")
    output_report_path = os.getenv("REPORT_PATH", "report.json")

    # 1. Parse metadata
    print(f"[*] Parsing scheme metadata from {meta_path}...")
    metadata = parse_scheme_meta(meta_path)
    print(f"[+] Loaded {len(metadata)} scheme metadata entries.")

    # 2. Parse NAV files
    print(f"[*] Parsing Day 1 NAV file: {nav_file_1}...")
    d1_records, file_exc_1 = parse_nav_file(nav_file_1)
    print(f"[+] Day 1 valid records: {len(d1_records)} | File exclusions: {len(file_exc_1)}")

    print(f"[*] Parsing Day 2 NAV file: {nav_file_2}...")
    d2_records, file_exc_2 = parse_nav_file(nav_file_2)
    print(f"[+] Day 2 valid records: {len(d2_records)} | File exclusions: {len(file_exc_2)}")

    combined_file_exclusions = dict(file_exc_1)
    combined_file_exclusions.update(file_exc_2)

    # 3. Database operations
    print(f"[*] Connecting to Database ({db_url.split('@')[-1] if '@' in db_url else db_url})...")
    db = DatabaseManager(db_url)
    print("[*] Initializing database schema...")
    db.init_schema("db/schema.sql")

    print("[*] Upserting records into database (Idempotent)...")
    loaded_count = db.upsert_schemes_and_nav(d1_records + d2_records, metadata)
    print(f"[+] Upserted {loaded_count} scheme/NAV records into database.")

    # 4. Generate report.json
    print("[*] Calculating AMC 1-day median changes & auditing exclusions...")
    report = generate_report(
        d1_records=d1_records,
        d2_records=d2_records,
        file_exclusions=combined_file_exclusions,
        schema_path="output_schema.json"
    )

    # Save exclusions to database for audit history
    db.save_exclusions(report["exclusions"])

    # Write report.json to disk
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[SUCCESS] Generated '{output_report_path}' successfully!")
    print(f"  - Generated At:      {report['generated_at']}")
    print(f"  - Source Dates:      {report['source_dates']}")
    print(f"  - Schemes Loaded:    {report['schemes_loaded']}")
    print(f"  - Schemes Excluded:  {report['schemes_excluded']}")
    print(f"  - AMCs Processed:    {len(report['by_amc'])}")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()
