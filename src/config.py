"""
Central configuration. Reads everything from .env so no secrets
are ever typed directly into code (assignment requirement 4.1).
"""
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()  # loads variables from a .env file in the project root

# --- Database ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "labor_force_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# URL-encode user/password since they may contain special characters like '@'
_DB_USER_ENC = quote_plus(DB_USER)
_DB_PASSWORD_ENC = quote_plus(DB_PASSWORD)

DATABASE_URL = (
    f"postgresql+psycopg2://{_DB_USER_ENC}:{_DB_PASSWORD_ENC}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# --- World Bank API ---
WB_INDICATOR = os.getenv("WB_INDICATOR", "SL.TLF.CACT.ZS")
WB_BASE_URL = os.getenv(
    "WB_BASE_URL", "https://api.worldbank.org/v2/country/all/indicator"
)
WB_DATE_RANGE = os.getenv("WB_DATE_RANGE", "1990:2025")
WB_PER_PAGE = 20000  # large enough to get everything in one page

# --- AI Assistant ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
CLEAN_DATA_DIR = os.path.join(BASE_DIR, "data", "clean")
LOG_DIR = os.path.join(BASE_DIR, "logs")
