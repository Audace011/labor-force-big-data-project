"""
Tests for the data cleaning logic in src/load.py.

These test the pure clean_row() function directly, so they run instantly
and don't need a database connection or the World Bank API — satisfies
the assignment's requirement (4.6) for automated tests of the cleaning
and checking functions.

Run with: pytest tests/test_data_cleaning.py -v
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.load import clean_row

REAL_CODES = {"RWA", "USA", "CHN"}


def test_valid_row_is_kept():
    row = {"country_name": "Rwanda", "country_iso3": "RWA", "year": "2020", "value": "84.5"}
    result = clean_row(row, REAL_CODES)
    assert result is not None
    assert result["country_name"] == "Rwanda"
    assert result["year"] == 2020
    assert result["value"] == 84.5


def test_missing_value_is_dropped():
    row = {"country_name": "Rwanda", "country_iso3": "RWA", "year": "2020", "value": None}
    assert clean_row(row, REAL_CODES) is None


def test_empty_string_value_is_dropped():
    row = {"country_name": "Rwanda", "country_iso3": "RWA", "year": "2020", "value": ""}
    assert clean_row(row, REAL_CODES) is None


def test_aggregate_country_is_dropped():
    # AFE ("Africa Eastern and Southern") is a regional aggregate, not a real country
    row = {"country_name": "Africa Eastern and Southern", "country_iso3": "AFE", "year": "2020", "value": "65.0"}
    assert clean_row(row, REAL_CODES) is None


def test_negative_value_is_dropped():
    row = {"country_name": "Rwanda", "country_iso3": "RWA", "year": "2020", "value": "-5.0"}
    assert clean_row(row, REAL_CODES) is None


def test_value_over_100_is_dropped():
    row = {"country_name": "Rwanda", "country_iso3": "RWA", "year": "2020", "value": "150.0"}
    assert clean_row(row, REAL_CODES) is None


def test_non_numeric_value_is_dropped():
    row = {"country_name": "Rwanda", "country_iso3": "RWA", "year": "2020", "value": "not_a_number"}
    assert clean_row(row, REAL_CODES) is None


def test_non_numeric_year_is_dropped():
    row = {"country_name": "Rwanda", "country_iso3": "RWA", "year": "not_a_year", "value": "65.0"}
    assert clean_row(row, REAL_CODES) is None


def test_when_real_codes_unknown_nothing_filtered_by_country():
    # If the World Bank country-list API call failed, real_codes is None,
    # and we should NOT drop rows just because of that (graceful degradation)
    row = {"country_name": "Some Aggregate", "country_iso3": "ZZZ", "year": "2020", "value": "65.0"}
    result = clean_row(row, None)
    assert result is not None
