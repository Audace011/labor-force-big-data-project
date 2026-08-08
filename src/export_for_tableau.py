"""
One-off export: pulls clean_labor_force from PostgreSQL into a CSV
file that Tableau Public can use as a data source (Tableau Public
cannot connect directly to a live PostgreSQL database).
"""
import os
import pandas as pd
from sqlalchemy import create_engine

from src.config import DATABASE_URL, BASE_DIR
from src.logger import get_logger

logger = get_logger(__name__)


def run_export():
    engine = create_engine(DATABASE_URL)
    df = pd.read_sql("SELECT * FROM clean_labor_force ORDER BY country_iso3, year", engine)

    output_path = os.path.join(BASE_DIR, "data", "clean", "clean_labor_force.csv")
    df.to_csv(output_path, index=False)

    logger.info(f"Exported {len(df)} rows to {output_path}")
    return output_path


if __name__ == "__main__":
    run_export()
