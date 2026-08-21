# AMFI NAV Data Pipeline & Report Generator

Production-grade data pipeline built for Opus Wealth. Parses AMFI plain-text NAV files and metadata, performs defensive data cleaning & auditing, loads records idempotently into PostgreSQL, and generates `report.json` conforming strictly to `output_schema.json`.

---

## 🚀 Quick Start (Under 2 Minutes)

### 1. Start PostgreSQL (Docker)
```bash
docker compose up -d
```

### 2. Run Pipeline & Generate Report
```bash
# Create virtual environment and install requirements
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run pipeline (creates schema, loads DB, writes report.json)
python run.py
```

`report.json` will be generated in the project root directory.

---

## 🧪 Run Automated Tests

```bash
# Run pytest suite
pytest -o pythonpath=. tests/ -v
```

---

## 📁 Repository Structure

```
.
├── db/
│   └── schema.sql        # Scripted DDL for PostgreSQL schema
├── data/
│   ├── nav_2026-06-29.txt # AMFI NAV File Day 1
│   ├── nav_2026-06-30.txt # AMFI NAV File Day 2
│   └── scheme_meta.csv   # Scheme Metadata CSV
├── src/
│   ├── parser.py         # Stateful AMFI text & CSV parser
│   ├── db.py             # PostgreSQL connection & idempotent upserts
│   └── report.py         # Exclusions auditor & report builder
├── tests/
│   ├── test_parser.py    # Unit tests for text parsing & N.A. handling
│   ├── test_report.py    # Unit tests for 1d median change & schema validation
│   └── test_db.py        # Integration & idempotency database tests
├── run.py                # Single-command CLI entrypoint
├── output_schema.json    # JSON Schema specification
├── report.json           # Generated report output
├── NOTES.md              # Detailed engineering notes & failure modes
├── docker-compose.yml    # Postgres 16 container definition
└── requirements.txt      # Python dependencies
```

---

## 🔄 Idempotency Guarantee

Running `python run.py` multiple times will not duplicate database records or fail. The database uses `UNIQUE(amfi_code, nav_date)` constraints with `ON CONFLICT DO UPDATE` (upsert) semantics.
