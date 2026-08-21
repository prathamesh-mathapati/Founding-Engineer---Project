import os
import sqlite3
import psycopg2
from urllib.parse import urlparse
from typing import List, Dict, Any, Tuple, Optional


class DatabaseManager:
    """
    Handles database operations for PostgreSQL with a transparent SQLite fallback
    for local test/development environments without a running Postgres service.
    """

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.is_postgres = db_url.startswith("postgresql://") or db_url.startswith("postgres://")
        self._conn = None
        self._engine_type = "postgres" if self.is_postgres else "sqlite"

    def get_connection(self):
        if self._conn is not None:
            return self._conn

        if self.is_postgres:
            try:
                self._conn = psycopg2.connect(self.db_url)
                return self._conn
            except Exception as e:
                # If Postgres connection fails, fallback to sqlite in-memory / local db file
                print(f"[WARN] Unable to connect to Postgres ({e}). Falling back to SQLite database.")
                self.is_postgres = False
                self._engine_type = "sqlite"

        # SQLite connection setup
        if self.db_url.startswith("sqlite:///"):
            sqlite_path = self.db_url.replace("sqlite:///", "")
        else:
            sqlite_path = "worksample.db"
        self._conn = sqlite3.connect(sqlite_path)
        self._conn.row_factory = sqlite3.Row
        return self._conn

    def init_schema(self, schema_sql_path: str = "db/schema.sql"):
        conn = self.get_connection()
        cur = conn.cursor()
        
        with open(schema_sql_path, "r", encoding="utf-8") as f:
            sql_content = f.read()

        if self._engine_type == "sqlite":
            # Adjust PostgreSQL specific DDL types for SQLite compatibility
            sqlite_sql = sql_content.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
            sqlite_sql = sqlite_sql.replace("NUMERIC(14, 4)", "REAL")
            sqlite_sql = sqlite_sql.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "DATETIME DEFAULT CURRENT_TIMESTAMP")
            cur.executescript(sqlite_sql)
        else:
            cur.execute(sql_content)

        conn.commit()
        cur.close()

    def upsert_schemes_and_nav(
        self,
        records: List[Dict[str, Any]],
        metadata: Dict[int, Dict[str, str]]
    ) -> int:
        conn = self.get_connection()
        cur = conn.cursor()
        inserted_count = 0

        for r in records:
            amfi_code = r["amfi_code"]
            meta = metadata.get(amfi_code, {})
            
            amc_name = r.get("amc_name") or meta.get("amc_name", "Unknown AMC")
            sebi_category = r.get("sebi_category") or meta.get("sebi_category")
            plan = meta.get("plan")
            option = meta.get("option")

            if self._engine_type == "postgres":
                # Upsert into schemes
                cur.execute(
                    """
                    INSERT INTO schemes (amfi_code, amc_name, sebi_category, plan, scheme_option, updated_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (amfi_code) DO UPDATE SET
                        amc_name = EXCLUDED.amc_name,
                        sebi_category = EXCLUDED.sebi_category,
                        plan = EXCLUDED.plan,
                        scheme_option = EXCLUDED.scheme_option,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (amfi_code, amc_name, sebi_category, plan, option)
                )

                # Upsert into nav_history
                cur.execute(
                    """
                    INSERT INTO nav_history (
                        amfi_code, nav_date, nav, raw_nav, scheme_name,
                        isin_payout_growth, isin_reinvestment, amc_name,
                        is_valid, error_reason, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (amfi_code, nav_date) DO UPDATE SET
                        nav = EXCLUDED.nav,
                        raw_nav = EXCLUDED.raw_nav,
                        scheme_name = EXCLUDED.scheme_name,
                        amc_name = EXCLUDED.amc_name,
                        is_valid = EXCLUDED.is_valid,
                        error_reason = EXCLUDED.error_reason;
                    """,
                    (
                        amfi_code, r["nav_date"], r["nav"], r["raw_nav"], r["scheme_name"],
                        r["isin_payout_growth"], r["isin_reinvestment"], amc_name,
                        r["is_valid"], r["error_reason"]
                    )
                )
            else:
                # SQLite upsert
                cur.execute(
                    """
                    INSERT INTO schemes (amfi_code, amc_name, sebi_category, plan, scheme_option, updated_at)
                    VALUES (?, ?, ?, ?, ?, DATETIME('now'))
                    ON CONFLICT(amfi_code) DO UPDATE SET
                        amc_name = excluded.amc_name,
                        sebi_category = excluded.sebi_category,
                        plan = excluded.plan,
                        scheme_option = excluded.scheme_option,
                        updated_at = DATETIME('now');
                    """,
                    (amfi_code, amc_name, sebi_category, plan, option)
                )

                cur.execute(
                    """
                    INSERT INTO nav_history (
                        amfi_code, nav_date, nav, raw_nav, scheme_name,
                        isin_payout_growth, isin_reinvestment, amc_name,
                        is_valid, error_reason, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATETIME('now'))
                    ON CONFLICT(amfi_code, nav_date) DO UPDATE SET
                        nav = excluded.nav,
                        raw_nav = excluded.raw_nav,
                        scheme_name = excluded.scheme_name,
                        amc_name = excluded.amc_name,
                        is_valid = excluded.is_valid,
                        error_reason = excluded.error_reason;
                    """,
                    (
                        amfi_code, r["nav_date"], r["nav"], r["raw_nav"], r["scheme_name"],
                        r["isin_payout_growth"], r["isin_reinvestment"], amc_name,
                        1 if r["is_valid"] else 0, r["error_reason"]
                    )
                )
            inserted_count += 1

        conn.commit()
        cur.close()
        return inserted_count

    def save_exclusions(self, exclusions: List[Dict[str, Any]]):
        conn = self.get_connection()
        cur = conn.cursor()

        for exc in exclusions:
            code = exc["amfi_code"]
            reason = exc["reason"]
            if self._engine_type == "postgres":
                cur.execute(
                    """
                    INSERT INTO exclusions (amfi_code, reason, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (amfi_code) DO UPDATE SET reason = EXCLUDED.reason;
                    """,
                    (code, reason)
                )
            else:
                cur.execute(
                    """
                    INSERT INTO exclusions (amfi_code, reason, created_at)
                    VALUES (?, ?, DATETIME('now'))
                    ON CONFLICT(amfi_code) DO UPDATE SET reason = excluded.reason;
                    """,
                    (code, reason)
                )

        conn.commit()
        cur.close()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
