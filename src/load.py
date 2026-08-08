"""
Step 2 of the pipeline: LOAD.

Reads the most recent raw JSON file, loads it untouched into
raw_labor_force, then builds clean_labor_force by:
  - removing regional/income-group aggregates (using the World Bank's
    own country classification, not a hardcoded guess)
  - dropping rows with missing/invalid values
  - casting year -> INTEGER and value -> NUMERIC
  - upserting so re-running the script never creates duplicates

Requirement mapping (Section 4.1):
- raw table first, then cleaned table/view
- checks for missing values, bad types
- idempotent re-run (ON CONFLICT DO UPDATE)
- handles DB-unavailable and empty-file errors instead of crashing
- logging instead of print()
"""
import glob
import json
import os

import requests
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from src.config import DATABASE_URL, RAW_DATA_DIR
from src.logger import get_logger

logger = get_logger(__name__)

WB_COUNTRY_LIST_URL = "https://api.worldbank.org/v2/country"


def get_latest_raw_file() -> str:
    """Finds the most recently saved raw JSON file."""
    files = glob.glob(os.path.join(RAW_DATA_DIR, "labor_force_*.json"))
    if not files:
        raise FileNotFoundError(
            "No raw data files found. Run 'python -m src.extract' first."
        )
    latest = max(files, key=os.path.getctime)
    logger.info(f"Using raw file: {latest}")
    return latest


def load_raw_json(filepath: str) -> list:
    with open(filepath, "r") as f:
        records = json.load(f)
    if not records:
        raise ValueError(f"Raw file {filepath} is empty — nothing to load")
    return records


def get_real_country_codes() -> set:
    """
    Calls the World Bank country metadata endpoint and returns the set of
    ISO3 codes that are REAL countries (region != 'Aggregates').
    This avoids hardcoding a guessed list of aggregate codes.
    """
    try:
        resp = requests.get(
            WB_COUNTRY_LIST_URL, params={"format": "json", "per_page": 400}, timeout=30
        )
        resp.raise_for_status()
        payload = resp.json()
        countries = payload[1]
    except (requests.exceptions.RequestException, IndexError, KeyError) as e:
        logger.warning(f"Could not fetch country metadata ({e}) — proceeding without aggregate filtering")
        return None  # signal: skip this filter, don't crash the pipeline

    real_codes = {
        c["id"] for c in countries
        if c.get("region", {}).get("value") != "Aggregates" and c.get("id")
    }
    logger.info(f"Fetched {len(real_codes)} real (non-aggregate) country codes")
    return real_codes


def insert_raw(engine, records: list) -> int:
    inserted = 0
    with engine.begin() as conn:
        for r in records:
            conn.execute(
                text("""
                    INSERT INTO raw_labor_force
                        (indicator_id, indicator_name, country_id, country_name,
                         country_iso3, year, value, unit, obs_status, decimal_places)
                    VALUES
                        (:indicator_id, :indicator_name, :country_id, :country_name,
                         :country_iso3, :year, :value, :unit, :obs_status, :decimal_places)
                    ON CONFLICT (country_iso3, year) DO UPDATE SET
                        value = EXCLUDED.value,
                        loaded_at = NOW()
                """),
                {
                    "indicator_id": r["indicator"]["id"],
                    "indicator_name": r["indicator"]["value"],
                    "country_id": r["country"]["id"],
                    "country_name": r["country"]["value"],
                    "country_iso3": r.get("countryiso3code"),
                    "year": r.get("date"),
                    "value": str(r.get("value")) if r.get("value") is not None else None,
                    "unit": r.get("unit"),
                    "obs_status": r.get("obs_status"),
                    "decimal_places": str(r.get("decimal")),
                },
            )
            inserted += 1
    logger.info(f"Upserted {inserted} rows into raw_labor_force")
    return inserted


def clean_row(row: dict, real_codes: set | None) -> dict | None:
    """
    Applies the cleaning rules to a single raw row. Returns a cleaned dict
    ready for insertion, or None if the row should be dropped.

    Pulled out as its own function (rather than staying inline in a loop)
    so it can be unit tested directly without needing a database or the
    World Bank API (see tests/test_data_cleaning.py).
    """
    # 1. drop missing values
    if row.get("value") is None or row.get("value") in ("None", ""):
        return None

    # 2. drop aggregates (regions/income groups), if we know the real list
    if real_codes is not None and row.get("country_iso3") not in real_codes:
        return None

    # 3. cast types, skip row if it doesn't make sense (e.g. negative rate)
    try:
        year = int(row["year"])
        value = float(row["value"])
        if value < 0 or value > 100:  # participation rate is a percentage
            return None
    except (ValueError, TypeError, KeyError):
        return None

    return {
        "country_name": row["country_name"],
        "country_iso3": row["country_iso3"],
        "year": year,
        "value": value,
    }


def build_clean_table(engine, real_codes: set | None) -> int:
    """
    Reads from raw_labor_force, filters/cleans, and upserts into
    clean_labor_force. Returns number of rows loaded.
    """
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT * FROM raw_labor_force")).mappings().all()

    total = len(rows)
    dropped = 0
    clean_rows = []

    for r in rows:
        cleaned = clean_row(dict(r), real_codes)
        if cleaned is None:
            dropped += 1
        else:
            clean_rows.append(cleaned)

    logger.warning(f"{dropped} rows dropped during cleaning (missing/aggregate/bad type)")

    with engine.begin() as conn:
        for row in clean_rows:
            conn.execute(
                text("""
                    INSERT INTO clean_labor_force
                        (country_name, country_iso3, year, labor_force_participation_rate)
                    VALUES
                        (:country_name, :country_iso3, :year, :value)
                    ON CONFLICT (country_iso3, year) DO UPDATE SET
                        labor_force_participation_rate = EXCLUDED.labor_force_participation_rate,
                        loaded_at = NOW()
                """),
                row,
            )

    logger.info(f"{len(clean_rows)} clean rows loaded into clean_labor_force (out of {total} raw rows)")
    return len(clean_rows)


def run_load():
    logger.info("Starting load step")

    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect():
            pass  # just testing the connection works
    except OperationalError as e:
        logger.error(f"Could not connect to the database: {e}")
        raise

    # create tables if they don't exist yet
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    with engine.begin() as conn:
        for statement in schema_sql.split(";"):
            if statement.strip():
                conn.execute(text(statement))
    logger.info("Schema verified/created")

    filepath = get_latest_raw_file()
    records = load_raw_json(filepath)

    insert_raw(engine, records)

    real_codes = get_real_country_codes()
    build_clean_table(engine, real_codes)

    logger.info("Load step completed successfully")


if __name__ == "__main__":
    run_load()
