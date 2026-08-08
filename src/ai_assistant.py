"""
Step 5 of the pipeline: AI ASSISTANT (Section 4.5).

Lets someone type a plain-English question about the labor force data
and get a plain-English answer back, powered by a free LLM (Groq).

Flow:
  1. User types a question (e.g. "What was Rwanda's rate in 2020?")
  2. The LLM turns that question into a SQL query against clean_labor_force
  3. We run that SQL query and get the result
  4. The LLM turns the result into a plain-English sentence

Handles at least one failure gracefully (required by 4.5):
  - a broken/unsafe SQL query from the LLM
  - a question that can't be answered from this data
"""
import re
import sys

from groq import Groq
from sqlalchemy import create_engine, text

from src.config import DATABASE_URL, GROQ_API_KEY, GROQ_MODEL
from src.logger import get_logger

logger = get_logger(__name__)

engine = create_engine(DATABASE_URL)
client = Groq(api_key=GROQ_API_KEY)

# The LLM only ever needs to know about this one table.
SCHEMA_DESCRIPTION = """
Table: clean_labor_force
Columns:
  - country_name (TEXT): full country name, e.g. 'Rwanda'
  - country_iso3 (TEXT): 3-letter country code, e.g. 'RWA'
  - year (INTEGER): year of the observation, from 1990 to 2025
  - labor_force_participation_rate (NUMERIC): percentage of the population
    aged 15+ that is in the labor force, for that country and year
"""

SQL_SYSTEM_PROMPT = f"""You are a SQL generator for a PostgreSQL database.
{SCHEMA_DESCRIPTION}

Rules:
- Only generate SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or ALTER.
- Only query the clean_labor_force table.
- Return ONLY the raw SQL query, nothing else — no explanation, no markdown code fences.
- If the question cannot be answered using this table, return exactly: NOT_ANSWERABLE
"""

ANSWER_SYSTEM_PROMPT = """You are a helpful data assistant. You will be given
a user's original question and the raw result of a SQL query that answered it.
Turn that result into a short, clear, plain-English sentence. Do not mention
SQL, databases, or tables. Just answer naturally, like a knowledgeable person would.
"""


class UnanswerableQuestionError(Exception):
    pass


class UnsafeQueryError(Exception):
    pass


def validate_sql(sql: str) -> None:
    """
    Raises UnsafeQueryError if the SQL is anything other than a safe
    SELECT against our one table. Pulled out as its own function so it
    can be unit tested directly without calling the LLM (see
    tests/test_ai_assistant.py).
    """
    lowered = sql.lower()
    if not lowered.startswith("select"):
        raise UnsafeQueryError(f"Refusing to run a non-SELECT query: {sql}")
    forbidden = ["drop", "delete", "update", "insert", "alter", ";--", "truncate"]
    if any(word in lowered for word in forbidden):
        raise UnsafeQueryError(f"Refusing to run a potentially unsafe query: {sql}")


def question_to_sql(question: str) -> str:
    """Asks the LLM to turn a plain-English question into SQL."""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SQL_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    sql = response.choices[0].message.content.strip()
    sql = re.sub(r"^```sql\s*|\s*```$", "", sql, flags=re.IGNORECASE).strip()

    if sql == "NOT_ANSWERABLE":
        raise UnanswerableQuestionError(
            "That question can't be answered from the labor force data I have."
        )

    validate_sql(sql)
    return sql


def run_sql(sql: str):
    """Runs the SQL query and returns the raw result rows."""
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchall()
        columns = result.keys()
    return columns, rows


def result_to_answer(question: str, columns, rows) -> str:
    """Asks the LLM to turn the raw SQL result into a plain-English answer."""
    if not rows:
        result_text = "No matching data was found."
    else:
        result_text = "\n".join(
            ", ".join(f"{col}={val}" for col, val in zip(columns, row)) for row in rows[:20]
        )

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Original question: {question}\n\nQuery result:\n{result_text}",
            },
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def ask(question: str) -> str:
    """
    Main entry point: takes a plain-English question, returns a
    plain-English answer. Handles failures gracefully instead of crashing.
    """
    logger.info(f"Question received: {question}")
    try:
        sql = question_to_sql(question)
        logger.info(f"Generated SQL: {sql}")
    except UnanswerableQuestionError as e:
        logger.warning(str(e))
        return str(e)
    except UnsafeQueryError as e:
        logger.error(str(e))
        return "Sorry, I couldn't safely process that question. Could you rephrase it?"

    try:
        columns, rows = run_sql(sql)
    except Exception as e:
        # e.g. the LLM produced SQL that references a column that doesn't exist
        logger.error(f"SQL execution failed: {e}")
        return "Sorry, I ran into a problem answering that question. Could you rephrase it?"

    answer = result_to_answer(question, columns, rows)
    logger.info(f"Answer: {answer}")
    return answer


def main():
    print("Labor Force AI Assistant — ask a question, or type 'quit' to exit.\n")
    print("Example: What was Rwanda's participation rate in 2020?\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in ("quit", "exit"):
            break
        if not question:
            continue
        answer = ask(question)
        print(f"Assistant: {answer}\n")


if __name__ == "__main__":
    main()
