"""
Step 1 of the pipeline: EXTRACT.

Pulls the labor force participation rate indicator (SL.TLF.CACT.ZS)
from the World Bank API and saves the raw response to disk exactly
as received (data/raw/), before any cleaning happens.

Requirement mapping (Section 4.1):
- retries a few times before giving up if a request fails
- handles "no results returned" and network errors instead of crashing
- uses logging instead of print()
"""
import json
import os
from datetime import datetime

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
)

from src.config import WB_BASE_URL, WB_INDICATOR, WB_DATE_RANGE, WB_PER_PAGE, RAW_DATA_DIR
from src.logger import get_logger

logger = get_logger(__name__)

os.makedirs(RAW_DATA_DIR, exist_ok=True)


class EmptyResponseError(Exception):
    """Raised when the API responds successfully but with zero data rows."""
    pass


@retry(
    stop=stop_after_attempt(4),          # try up to 4 times total
    wait=wait_fixed(3),                  # wait 3 seconds between attempts
    retry=retry_if_exception_type((requests.exceptions.RequestException, EmptyResponseError)),
    reraise=True,
)
def fetch_indicator_data() -> list:
    """
    Calls the World Bank API and returns the list of data records
    (page 2 of the JSON response — page 1 is just metadata).
    Retries automatically on network errors or an empty result.
    """
    url = f"{WB_BASE_URL}/{WB_INDICATOR}"
    params = {
        "format": "json",
        "per_page": WB_PER_PAGE,
        "date": WB_DATE_RANGE,
    }

    logger.info(f"Requesting data for indicator {WB_INDICATOR} from World Bank API")
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()  # raises for HTTP error codes (4xx/5xx)

    payload = response.json()

    # World Bank API returns [metadata_dict, list_of_records]
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        logger.warning("API returned no data rows on this attempt — will retry")
        raise EmptyResponseError("World Bank API returned an empty data set")

    records = payload[1]
    logger.info(f"Request succeeded — {len(records)} rows received")
    return records


def save_raw(records: list) -> str:
    """Saves the raw API response to disk, untouched, timestamped."""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"labor_force_{timestamp}.json"
    filepath = os.path.join(RAW_DATA_DIR, filename)

    with open(filepath, "w") as f:
        json.dump(records, f, indent=2)

    logger.info(f"Saved raw response to {filepath}")
    return filepath


def run_extract() -> str:
    logger.info("Starting extract step")
    try:
        records = fetch_indicator_data()
    except requests.exceptions.RequestException as e:
        logger.error(f"Extract failed after all retry attempts: {e}")
        raise
    except EmptyResponseError as e:
        logger.error(f"Extract failed — API kept returning empty data: {e}")
        raise

    filepath = save_raw(records)
    logger.info("Extract step completed successfully")
    return filepath


if __name__ == "__main__":
    run_extract()
