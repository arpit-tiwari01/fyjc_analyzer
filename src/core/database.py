"""
src/core/database.py
====================
DuckDB integration for lightning-fast SQL queries on 1M+ rows.

Why DuckDB?
  - Columnar storage → reads only needed columns
  - Vectorized execution → 10-100x faster than pandas .query()
  - Zero-copy from pandas DataFrames
  - Full SQL support including window functions

Usage:
    db = FYJCDatabase(df)
    results = db.query("SELECT * FROM fyjc WHERE stream = 'Science' LIMIT 10")
"""

import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger("fyjc.database")

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    logger.warning("DuckDB not installed. Falling back to pandas filtering.")


class FYJCDatabase:
    """
    Wraps a pandas DataFrame in a DuckDB in-process database
    for high-performance SQL queries.

    The DataFrame is registered as a virtual table — no data is copied.
    """

    TABLE_NAME = "fyjc"

    def __init__(self, df: Optional[pd.DataFrame] = None):
        """
        Args:
            df: Pre-loaded FYJC DataFrame (optional; can load later)
        """
        self._df   = df
        self._conn = None
        self._initialized = False

        if DUCKDB_AVAILABLE and df is not None:
            self._init_connection(df)

    def _init_connection(self, df: pd.DataFrame):
        """Register the DataFrame as a DuckDB virtual table."""
        try:
            self._conn = duckdb.connect(database=":memory:")
            # Register pandas DataFrame as a SQL table (zero-copy)
            self._conn.register(self.TABLE_NAME, df)
            self._initialized = True
            logger.info(
                f"DuckDB initialized with {len(df):,} rows "
                f"as table '{self.TABLE_NAME}'"
            )
        except Exception as e:
            logger.error(f"DuckDB initialization failed: {e}")
            self._initialized = False

    def load(self, df: pd.DataFrame):
        """(Re-)load a DataFrame into DuckDB."""
        self._df = df
        if DUCKDB_AVAILABLE:
            self._init_connection(df)

    def query(self, sql: str) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a DataFrame.

        Args:
            sql: SQL query string (use table name 'fyjc')

        Returns:
            pandas DataFrame with query results
        """
        if not self._initialized or not DUCKDB_AVAILABLE:
            logger.debug("DuckDB unavailable, using pandas fallback")
            return self._df.copy() if self._df is not None else pd.DataFrame()

        try:
            result = self._conn.execute(sql).df()
            logger.debug(f"DuckDB query returned {len(result):,} rows")
            return result
        except Exception as e:
            logger.error(f"DuckDB query failed: {e}\nSQL: {sql}")
            return pd.DataFrame()

    def build_filter_query(
        self,
        streams: Optional[list] = None,
        districts: Optional[list] = None,
        mediums: Optional[list] = None,
        rounds: Optional[list] = None,
        college_name: Optional[str] = None,
        category_col: str = "General",
        min_cutoff: Optional[float] = None,
        max_cutoff: Optional[float] = None,
        reservation_details: Optional[list] = None,
    ) -> str:
        """
        Build a parameterized SQL WHERE clause from filter criteria.

        Args:
            streams:             List of stream names (e.g., ['Science', 'Commerce'])
            districts:           List of district IDs
            mediums:             List of medium names
            rounds:              List of round IDs
            college_name:        Partial college name (ILIKE match)
            category_col:        Which cutoff column to filter on
            min_cutoff:          Minimum cutoff value
            max_cutoff:          Maximum cutoff value
            reservation_details: List of reservation details types

        Returns:
            Full SQL query string
        """
        conditions = []

        if streams:
            quoted = ", ".join(f"'{s}'" for s in streams)
            conditions.append(f"stream IN ({quoted})")

        if districts:
            quoted = ", ".join(f"'{d}'" for d in districts)
            conditions.append(f"districtid IN ({quoted})")

        if mediums:
            quoted = ", ".join(f"'{m}'" for m in mediums)
            conditions.append(f"medium IN ({quoted})")

        if rounds:
            quoted = ", ".join(str(r) for r in rounds)
            conditions.append(f"round_id IN ({quoted})")

        if reservation_details:
            # Escape single quotes in details strings for safety
            quoted = ", ".join("'" + r.replace("'", "''") + "'" for r in reservation_details)
            conditions.append(f"ReservationDetails IN ({quoted})")

        if college_name:
            # Case-insensitive partial match
            safe_name = college_name.replace("'", "''")
            conditions.append(f"collegename ILIKE '%{safe_name}%'")

        if min_cutoff is not None:
            conditions.append(f'"{category_col}" >= {min_cutoff}')

        if max_cutoff is not None:
            conditions.append(f'"{category_col}" <= {max_cutoff}')

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f'SELECT * FROM {self.TABLE_NAME} WHERE {where}'

        logger.debug(f"Generated SQL: {sql}")
        return sql

    def get_unique(self, column: str) -> list:
        """Get unique values for a column using DuckDB."""
        if not self._initialized:
            return []
        try:
            result = self._conn.execute(
                f'SELECT DISTINCT "{column}" FROM {self.TABLE_NAME} '
                f'WHERE "{column}" IS NOT NULL ORDER BY "{column}"'
            ).fetchall()
            return [row[0] for row in result]
        except Exception:
            return []

    def count(self) -> int:
        """Return total row count."""
        if not self._initialized:
            return 0
        try:
            return self._conn.execute(
                f"SELECT COUNT(*) FROM {self.TABLE_NAME}"
            ).fetchone()[0]
        except Exception:
            return 0

    @property
    def available(self) -> bool:
        """Returns True if DuckDB is ready for queries."""
        return self._initialized and DUCKDB_AVAILABLE

    def close(self):
        """Close the DuckDB connection."""
        if self._conn:
            self._conn.close()
            self._initialized = False
