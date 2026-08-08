-- Schema for the labor force participation project.
-- Run once to set up tables (safe to re-run — uses IF NOT EXISTS).

-- RAW TABLE: holds the data exactly as it came from the World Bank API.
-- Nothing is filtered or fixed here — this is our audit trail.
CREATE TABLE IF NOT EXISTS raw_labor_force (
    id SERIAL PRIMARY KEY,
    indicator_id TEXT,
    indicator_name TEXT,
    country_id TEXT,
    country_name TEXT,
    country_iso3 TEXT,
    year TEXT,
    value TEXT,          -- kept as TEXT here on purpose: raw layer should not assume clean types
    unit TEXT,
    obs_status TEXT,
    decimal_places TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (country_iso3, year)   -- prevents duplicate rows on re-run
);

-- CLEAN TABLE: fixed types, aggregates removed, nulls handled.
-- This is what EDA, ML, Tableau, and the AI assistant will query.
CREATE TABLE IF NOT EXISTS clean_labor_force (
    id SERIAL PRIMARY KEY,
    country_name TEXT NOT NULL,
    country_iso3 TEXT NOT NULL,
    year INTEGER NOT NULL,
    labor_force_participation_rate NUMERIC(6,3) NOT NULL,
    loaded_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (country_iso3, year)   -- prevents duplicate rows on re-run
);

CREATE INDEX IF NOT EXISTS idx_clean_country ON clean_labor_force (country_iso3);
CREATE INDEX IF NOT EXISTS idx_clean_year ON clean_labor_force (year);
