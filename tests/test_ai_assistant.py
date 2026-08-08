"""
Tests for src/ai_assistant.py (Section 4.6 requirement).

Two kinds of tests here:
  1. Unit tests for validate_sql() — fast, no network/API needed.
  2. Integration tests that call the real ask() function, which hits
     the Groq API and the database. These require GROQ_API_KEY to be
     set in .env and a working database connection. They are skipped
     automatically if no API key is found, so the test suite doesn't
     break in an environment without credentials.

Run with: pytest tests/test_ai_assistant.py -v
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.config import GROQ_API_KEY
from src.ai_assistant import validate_sql, UnsafeQueryError, ask


# ---------- Unit tests: SQL safety validation (no network needed) ----------

def test_valid_select_passes():
    validate_sql("SELECT * FROM clean_labor_force WHERE year = 2020")  # should not raise


def test_drop_statement_is_rejected():
    with pytest.raises(UnsafeQueryError):
        validate_sql("DROP TABLE clean_labor_force")


def test_delete_statement_is_rejected():
    with pytest.raises(UnsafeQueryError):
        validate_sql("DELETE FROM clean_labor_force WHERE year = 2020")


def test_update_statement_is_rejected():
    with pytest.raises(UnsafeQueryError):
        validate_sql("UPDATE clean_labor_force SET labor_force_participation_rate = 0")


def test_non_select_statement_is_rejected():
    with pytest.raises(UnsafeQueryError):
        validate_sql("INSERT INTO clean_labor_force VALUES (1, 'x', 'x', 2020, 50.0)")


def test_select_with_sneaky_drop_is_rejected():
    # A query that starts innocently but tries to sneak in a second statement
    with pytest.raises(UnsafeQueryError):
        validate_sql("SELECT * FROM clean_labor_force; DROP TABLE clean_labor_force;--")


# ---------- Integration tests: real questions through the full pipeline ----------

requires_groq_key = pytest.mark.skipif(
    not GROQ_API_KEY, reason="GROQ_API_KEY not set in .env — skipping live AI assistant tests"
)


@requires_groq_key
def test_normal_question_produces_an_answer():
    """A normal, answerable question should return a non-empty, sensible answer."""
    answer = ask("What was Rwanda's labor force participation rate in 2020?")
    assert isinstance(answer, str)
    assert len(answer) > 0
    # It should not have fallen back to the "can't answer" message
    assert "can't be answered" not in answer.lower()


@requires_groq_key
def test_confusing_question_does_not_crash():
    """
    A question that has nothing to do with our data should be handled
    gracefully — no exception, and a polite message instead of a crash
    or a made-up answer.
    """
    answer = ask("What is the capital city of France?")
    assert isinstance(answer, str)
    assert len(answer) > 0
    # Should not have somehow found a "France" match in the country data
    # and made up a labor force answer instead of admitting it can't help
    assert "capital" not in answer.lower() or "can't" in answer.lower()
