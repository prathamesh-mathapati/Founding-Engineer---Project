import pytest
from src.db import DatabaseManager


def test_database_manager_idempotency(tmp_path):
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    
    db = DatabaseManager(db_url)
    db.init_schema("db/schema.sql")

    records = [
        {
            "amfi_code": 100001,
            "nav_date": "2026-06-29",
            "nav": 100.0,
            "raw_nav": "100.0000",
            "scheme_name": "Test Scheme 1",
            "isin_payout_growth": "INF001",
            "isin_reinvestment": None,
            "amc_name": "Test AMC",
            "sebi_category": "Large Cap Fund",
            "is_valid": True,
            "error_reason": None,
        }
    ]
    metadata = {100001: {"amc_name": "Test AMC", "sebi_category": "Large Cap Fund", "plan": "Regular", "option": "Growth"}}

    # First upsert
    db.upsert_schemes_and_nav(records, metadata)
    # Second upsert (Idempotency test)
    db.upsert_schemes_and_nav(records, metadata)

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM schemes")
    schemes_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM nav_history")
    nav_count = cur.fetchone()[0]

    assert schemes_count == 1
    assert nav_count == 1
    db.close()
