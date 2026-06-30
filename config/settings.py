"""
config/settings.py
==================
Central configuration for the FYJC Cutoff Analyzer.
Change these values to tune performance and behavior.
"""

import os
from pathlib import Path

# ─── Directory Paths ──────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent.parent
DATA_DIR        = BASE_DIR / "data"
RAW_DATA_DIR    = DATA_DIR / "raw"
PROCESSED_DIR   = DATA_DIR / "processed"
EXPORT_DIR      = DATA_DIR / "exports"
LOG_DIR         = BASE_DIR / "logs"

# Auto-create directories if they don't exist
for _dir in [RAW_DATA_DIR, PROCESSED_DIR, EXPORT_DIR, LOG_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# ─── Data File Settings ───────────────────────────────────────────────────────
# Default CSV filename (place in data/raw/)
DEFAULT_CSV_FILENAME   = "fyjc_cutoff.csv"
DEFAULT_CSV_PATH       = RAW_DATA_DIR / DEFAULT_CSV_FILENAME

# Parquet cache filename (auto-generated for fast re-loading)
PARQUET_CACHE_FILENAME = "fyjc_cutoff_cache.parquet"
PARQUET_CACHE_PATH     = PROCESSED_DIR / PARQUET_CACHE_FILENAME

# DuckDB database path
DUCKDB_PATH            = PROCESSED_DIR / "fyjc.duckdb"

# ─── Performance Settings ─────────────────────────────────────────────────────
# Chunk size for reading large CSV files (rows per chunk)
CSV_CHUNK_SIZE         = 100_000

# Use DuckDB for filtering (True = SQL-based, much faster for 1M+ rows)
USE_DUCKDB             = True

# Use Parquet cache on second run (True = 10x faster reload)
USE_PARQUET_CACHE      = True

# ─── Column Names ─────────────────────────────────────────────────────────────
# These must match your CSV exactly (case-sensitive)
COL_ID          = "id"
COL_DISTRICT    = "districtid"
COL_REGION      = "regionid"
COL_UDISE       = "udise"
COL_COLLEGE     = "collegename"
COL_STREAM      = "stream"
COL_STATUS      = "status"
COL_MEDIUM      = "medium"
COL_SUBJECT     = "subject"
COL_CHOICE_CODE = "choicecode"
COL_RESERVATION = "ReservationDetails"
COL_ROUND       = "round_id"

# All reservation category columns
RESERVATION_COLS = ["SC", "ST", "VJA", "NTB", "NTC", "NTD",
                    "OBC", "SBC", "SEBC", "EWS", "General"]

# ─── Classification Thresholds ────────────────────────────────────────────────
# College classification based on (UserMarks - Cutoff)
SAFE_THRESHOLD     = 5    # marks above cutoff → SAFE
MODERATE_THRESHOLD = -3   # marks within 3 below cutoff → MODERATE
# Below MODERATE_THRESHOLD → DREAM

# ─── Display Settings ─────────────────────────────────────────────────────────
MAX_DISPLAY_ROWS   = 50   # Max colleges shown in terminal
EXPORT_MAX_ROWS    = None # None = export all

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL          = "INFO"
LOG_FILE           = LOG_DIR / "fyjc_analyzer.log"

# ─── App Info ─────────────────────────────────────────────────────────────────
APP_NAME           = "FYJC Cutoff Analyzer"
APP_VERSION        = "1.0.0"
APP_AUTHOR         = "Maharashtra FYJC Tool"
