# Global Labor Force Participation Rate — Data Pipeline, ML & AI Assistant

**Course**: Introduction to Big Data — Final Project
**Indicator**: World Bank `SL.TLF.CACT.ZS` — Labor force participation rate, total (% of total population ages 15+) (modeled ILO estimate)
**Author**: Karenzi Audace

A complete data pipeline: World Bank API → PostgreSQL → EDA → Machine Learning → Tableau Dashboard → AI Assistant (natural language Q&A over the data).

---

## 1. Project Structure

```
labor-force-project/
├── src/                    # All pipeline source code
│   ├── config.py            # Central config, reads from .env
│   ├── logger.py            # Shared logging setup
│   ├── extract.py           # Step 1: pull data from World Bank API
│   ├── load.py               # Step 2: raw table -> clean table in PostgreSQL
│   ├── schema.sql            # Database schema (raw + clean tables)
│   ├── export_for_tableau.py # Exports clean table to CSV for Tableau Public
│   └── ai_assistant.py       # Step 5: natural-language Q&A over the data
├── notebooks/
│   ├── 01_eda.ipynb          # Exploratory Data Analysis
│   └── 02_ml.ipynb           # Machine Learning: Linear Regression vs Random Forest
├── tests/
│   ├── test_data_cleaning.py # Unit tests for the cleaning logic
│   └── test_ai_assistant.py  # Tests for SQL safety + live AI assistant Q&A
├── data/
│   ├── raw/                  # Raw JSON snapshots from the World Bank API
│   └── clean/                # Exported CSVs (for Tableau) + ML predictions
├── docs/                     # Saved chart images for the PDF report
├── .env.example               # Template for environment variables
├── .env                        # Your real secrets (NEVER commit this)
└── requirements.txt
```

---

## 2. Setup Instructions

### Prerequisites
- Python 3.11+ (tested on 3.13)
- PostgreSQL installed and running locally
- A free Groq API key ([console.groq.com](https://console.groq.com)) for the AI assistant

### Steps

**1. Create and activate a virtual environment**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Set up your environment file**
```bash
copy .env.example .env       # Windows
# cp .env.example .env       # Mac/Linux
```
Edit `.env` and fill in:
- `DB_PASSWORD` — your PostgreSQL password
- `GROQ_API_KEY` — your free Groq API key

**4. Create the database**
```sql
-- In psql:
CREATE DATABASE labor_force_db;
```
(Tables are created automatically by `load.py` on first run — no manual schema step needed.)

---

## 3. Running the Pipeline

Run each step in order:

```bash
python -m src.extract                # Pulls data from World Bank API -> data/raw/
python -m src.load                   # Loads raw JSON -> PostgreSQL (raw + clean tables)
python -m src.export_for_tableau     # Exports clean table -> data/clean/ CSV for Tableau
```

**Re-running is always safe.** Both `extract.py` and `load.py` are idempotent — running them again will not create duplicate rows (verified: running `load.py` twice in a row produces the same row count both times).

### Running the notebooks
```bash
pip install jupyter
jupyter notebook
```
Open `notebooks/01_eda.ipynb` first, then `notebooks/02_ml.ipynb`. Run all cells (Cell → Run All). The ML notebook exports `data/clean/ml_predictions.csv`, which is used both by Tableau and referenced in the report.

### Running the AI Assistant
```bash
python -m src.ai_assistant
```
Then type plain-English questions, e.g.:
- "What was Rwanda's participation rate in 2020?"
- "Which country had the highest rate in 2025?"

Type `quit` to exit.

### Running the tests
```bash
python -m pytest tests/ -v
```

---

## 4. Tableau Dashboard

Public link: **https://public.tableau.com/app/profile/karenzi.audace/viz/GlobalLaborForceParticipationRateAnalysis/Dashboard1**

The dashboard contains 4 charts and 2 interactive filters:
1. **World map** — average participation rate by country, filterable by year
2. **Trend line chart** — 5 selected countries (Rwanda, USA, China, Nigeria, Germany) over time
3. **Top 10 bar chart** — highest-participation countries for a selected year
4. **ML predicted vs. actual scatter plot** — shows how close the Random Forest model's predictions were on the test set

Filters: **Year** (controls the map and top-10 chart) and **Country Name** (controls the trend chart).

---

## 5. How Data Flows Through This Project

```
World Bank API (SL.TLF.CACT.ZS)
        │
        ▼
  src/extract.py  ──────────► data/raw/labor_force_*.json  (raw snapshot, untouched)
        │
        ▼
  src/load.py
        │
        ├──► raw_labor_force table (PostgreSQL)   — data exactly as received
        │
        └──► clean_labor_force table (PostgreSQL) — aggregates removed,
                                                      nulls dropped, types fixed
                        │
        ┌───────────────┼────────────────────┬─────────────────────┐
        ▼               ▼                    ▼                     ▼
  notebooks/01_eda   notebooks/02_ml    export_for_tableau.py    src/ai_assistant.py
  (analysis, charts) (Linear Regression  (CSV export)             (natural-language
                       vs Random Forest,        │                  Q&A, queries
                       predictions.csv)          ▼                 clean_labor_force
                                          Tableau Public            directly via SQL
                                          Dashboard (4 charts,      generated by Groq)
                                          2 filters, published)
```

---

## 6. Notes & Limitations

- The indicator is a **modeled ILO estimate**, not raw survey data for every country/year — the World Bank fills gaps using statistical modeling. This is why coverage is high (few missing values) but individual-year figures for some countries are estimates rather than direct measurements.
- The World Bank API mixes real countries with regional/income-group aggregates (e.g. "Africa Eastern and Southern") in the same feed. These are filtered out during the load step using the World Bank's own country classification metadata (not a hardcoded guess list).
- The ML models use a time-based train/test split (train ≤2020, test 2021-2025) rather than a random split, since this is panel/time-series data — a random split would risk leaking future information into training.
