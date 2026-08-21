-- PostgreSQL Schema for AMFI NAV Pipeline
-- Scripted & Idempotent DDL

CREATE TABLE IF NOT EXISTS schemes (
    amfi_code INT PRIMARY KEY,
    amc_name VARCHAR(255),
    sebi_category VARCHAR(255),
    plan VARCHAR(50),
    scheme_option VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS nav_history (
    id SERIAL PRIMARY KEY,
    amfi_code INT NOT NULL REFERENCES schemes(amfi_code) ON DELETE CASCADE,
    nav_date DATE NOT NULL,
    nav NUMERIC(14, 4),
    raw_nav VARCHAR(64),
    scheme_name VARCHAR(512),
    isin_payout_growth VARCHAR(64),
    isin_reinvestment VARCHAR(64),
    amc_name VARCHAR(255),
    is_valid BOOLEAN DEFAULT TRUE,
    error_reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_scheme_date UNIQUE (amfi_code, nav_date)
);

CREATE TABLE IF NOT EXISTS exclusions (
    amfi_code INT PRIMARY KEY,
    reason VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_nav_history_amfi_date ON nav_history(amfi_code, nav_date);
CREATE INDEX IF NOT EXISTS idx_nav_history_amc ON nav_history(amc_name);
