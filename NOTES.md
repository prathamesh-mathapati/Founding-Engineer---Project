# AMFI NAV Pipeline - Engineering Notes

## 1. What I Found in the Data

During data exploration and parsing of `data/nav_2026-06-29.txt`, `data/nav_2026-06-30.txt`, and `data/scheme_meta.csv`, I identified several real-world data anomalies:

1. **Non-CSV Plain-Text Structure**: The NAV files use a hybrid format containing block headers (e.g. `Open Ended Schemes(Equity Scheme - Large Cap Fund)` and AMC headers like `Aditya Birla Sun Life Mutual Fund`) intermingled with semicolon-separated data rows.
2. **Missing / Unparseable NAV Values**: Certain scheme rows have `"N.A."` in the Net Asset Value column (e.g. scheme `100137` and `100263` on 2026-06-29).
3. **Intra-Day Duplicate Schemes with Conflicting NAVs**: In `nav_2026-06-29.txt`, scheme `100193` appears on two separate lines with different NAV values (`103.7425` vs `104.0641`).
4. **Single-Day Scheme Discontinuities**: 28 schemes (e.g., `102624`, `102638`, `102655`) are present on Day 1 (June 29) but completely absent on Day 2 (June 30).
5. **AMC Name Discrepancies**: `scheme_meta.csv` uses abbreviated names (e.g. `"Aditya Birla Sun Life MF"`), whereas the NAV file section header contains the full name (`"Aditya Birla Sun Life Mutual Fund"`).

---

## 2. Decisions Made and Rationale

1. **Primary Identity Key**: Keyed all pipeline state, database tables, and exclusions strictly on the numeric `amfi_code`.
2. **AMC Name Selection**: Used section header AMC names directly from the NAV text files to satisfy `output_schema.json` line 49 requirement (*"AMC name exactly as it appears in the NAV file"*).
3. **Defensive Exclusions Strategy**:
   - Excluded schemes with `N.A.` or non-positive NAV values.
   - Excluded schemes with intra-day duplicate conflicting records.
   - Excluded schemes present on only 1 source date (cannot compute a 1-day change).
   - Logged every exclusion with a specific human-readable reason in `report.json` and saved to `exclusions` database table.
4. **Database Architecture & Idempotency**:
   - Created PostgreSQL tables (`schemes`, `nav_history`, `exclusions`) with `UNIQUE(amfi_code, nav_date)` constraints.
   - Used `INSERT ... ON CONFLICT DO UPDATE` (upserts) to ensure running the pipeline multiple times results in identical database state.
   - Built a transparent local SQLite fallback inside `src/db.py` to ensure local tests execute seamlessly even when a Postgres container is offline.

---

## 3. What I Didn't Do & Future Enhancements

If given another day on this pipeline, I would:
1. **Streaming & Async Ingestion**: Replace full in-memory parsing with chunked streaming using `asyncpg` to comfortably process millions of historical rows.
2. **Statistical Anomaly Detection**: Add rolling 30-day Z-score monitoring (e.g., flag any scheme whose 1-day NAV change exceeds ±20% or drops to 0).
3. **Database Migration Tooling**: Implement `Alembic` for version-controlled database schema migrations.
4. **Automated Feed Polling**: Build an automated fetcher service with retries and backoff to pull directly from the AMFI portal API.

---

## 4. What Breaks First in Production & Monitoring Strategy

Assumptions: The pipeline runs unattended at 2:00 AM UTC every business day.

### Failure Mode 1: Upstream Format Mutation
- **What Breaks**: AMFI alters the header formatting, delimiter (e.g., semicolon to comma), date string format, or column order.
- **Impact**: Parser fails to extract records or throws parsing exceptions.
- **How to Detect**:
  - PagerDuty alert triggered on unhandled parsing exceptions or 0 records parsed.
  - Datadog/Prometheus metric alert: `amfi_pipeline_exclusions_total > threshold` or `schemes_loaded < 1000`.

### Failure Mode 2: Missing or Delayed Feed
- **What Breaks**: Upstream AMFI server is down, feed is published late, or returns a 0-byte file.
- **Impact**: Pipeline cannot compute daily report.
- **How to Detect**:
  - **Dead Man's Snitch / Healthchecks.io**: If success ping isn't received by 2:30 AM UTC, trigger an on-call alert.
  - Pre-execution validation checking file size (`size_bytes > 50KB`).

### Failure Mode 3: AMFI Scheme Code Re-assignment or Name Collision
- **What Breaks**: AMFI reuses an `amfi_code` for a merged or new fund scheme, causing misleading historical calculations.
- **Impact**: Inaccurate 1-day change calculations across different schemes.
- **How to Detect**:
  - Name consistency check comparing new scheme name against database `schemes` table name.
  - Emit Slack alert if Levenshtein distance string similarity < 0.70 for an existing `amfi_code`.

---

## 5. AI Workflow Disclosure

- **Tools Used**: Antigravity AI Assistant for rapid boilerplate generation, SQL schema DDL drafting, test case setup, and schema validation.
- **Override Example**: The AI initially defaulted to taking AMC names from `scheme_meta.csv`. I explicitly overrode this decision after checking `output_schema.json` line 49, which specifies using the exact AMC name string from the NAV text file header.

---

## 6. Time Taken

- **Total Time**: ~3.5 hours (Data exploration, database schema design, stateful parser construction, test suite writing, schema validation, and documentation).
