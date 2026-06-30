"""
src/analysis/filter_engine.py
==============================
Multi-criteria filtering engine for FYJC cutoff data.

Supports filtering by:
  - District, Region, Area (fuzzy match on college name)
  - Stream, Medium
  - Admission round
  - Reservation category (which cutoff column to use)
  - Cutoff range

Two backends:
  1. DuckDB (fast, SQL-based) — preferred for large datasets
  2. Pandas (fallback)

Usage:
    engine = FilterEngine(df, db)
    filtered = engine.filter(
        streams=["Science"],
        districts=["Mumbai"],
        category="OBC",
        round_ids=[1, 2]
    )
"""

import logging
from typing import Optional, List
import pandas as pd

from src.core.database import FYJCDatabase
from src.utils.helpers import normalize_str

logger = logging.getLogger("fyjc.filter_engine")


class FilterEngine:
    """
    Applies multi-criteria filters to FYJC data using DuckDB or pandas.
    """

    def __init__(self, df: pd.DataFrame, db: Optional[FYJCDatabase] = None):
        """
        Args:
            df:  Clean FYJC DataFrame
            db:  Optional DuckDB instance (faster for large datasets)
        """
        self.df  = df
        self.db  = db
        self._use_duckdb = db is not None and db.available

    # ── Main Filter Method ────────────────────────────────────────────────────

    def filter(
        self,
        streams:             Optional[List[str]] = None,
        districts:           Optional[List[str]] = None,
        regions:             Optional[List[str]] = None,
        mediums:             Optional[List[str]] = None,
        round_ids:           Optional[List[int]] = None,
        category:            str = "General",
        areas:               Optional[List[str]] = None,
        college_name:        Optional[str] = None,
        min_cutoff:          Optional[float] = None,
        max_cutoff:          Optional[float] = None,
        reservation_details: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Apply filters and return matching rows.

        Args:
            streams:             List of stream names (e.g., ['Science'])
            districts:           List of district IDs/names
            regions:             List of region IDs
            mediums:             List of instruction mediums
            round_ids:           Admission round numbers
            category:            Reservation category column (e.g., 'General', 'OBC')
            areas:               Area/locality names — fuzzy matched against college names
            college_name:        Partial college name search
            min_cutoff:          Minimum cutoff % filter
            max_cutoff:          Maximum cutoff % filter
            reservation_details: List of reservation details types (e.g. 'Women (30%)')

        Returns:
            Filtered DataFrame
        """
        if self._use_duckdb:
            result = self._filter_duckdb(
                streams, districts, mediums, round_ids,
                college_name, category, min_cutoff, max_cutoff, reservation_details
            )
        else:
            result = self._filter_pandas(
                streams, districts, regions, mediums,
                round_ids, category, college_name, min_cutoff, max_cutoff, reservation_details
            )

        # Area filter is always done in pandas (requires fuzzy/substring match)
        if areas:
            result = self._apply_area_filter(result, areas)

        logger.info(f"Filter returned {len(result):,} rows")
        return result

    # ── DuckDB Backend ────────────────────────────────────────────────────────

    def _filter_duckdb(
        self, streams, districts, mediums, round_ids,
        college_name, category, min_cutoff, max_cutoff, reservation_details
    ) -> pd.DataFrame:
        """Use SQL for filtering — fastest for 1M+ rows."""
        sql = self.db.build_filter_query(
            streams=streams,
            districts=districts,
            mediums=mediums,
            rounds=round_ids,
            college_name=college_name,
            category_col=category,
            min_cutoff=min_cutoff,
            max_cutoff=max_cutoff,
            reservation_details=reservation_details,
        )
        return self.db.query(sql)

    # ── Pandas Backend ────────────────────────────────────────────────────────

    def _filter_pandas(
        self, streams, districts, regions, mediums,
        round_ids, category, college_name, min_cutoff, max_cutoff, reservation_details
    ) -> pd.DataFrame:
        """Pure pandas filtering — fallback when DuckDB unavailable."""
        df = self.df.copy()

        if streams:
            df = df[df["stream"].isin(streams)]

        if districts:
            df = df[df["districtid"].isin(districts)]

        if regions:
            df = df[df["regionid"].isin(regions)]

        if mediums:
            df = df[df["medium"].isin(mediums)]

        if round_ids:
            df = df[df["round_id"].isin(round_ids)]

        if reservation_details:
            df = df[df["ReservationDetails"].isin(reservation_details)]

        if college_name:
            mask = df["collegename"].str.contains(
                college_name, case=False, na=False
            )
            df = df[mask]

        if category and category in df.columns:
            if min_cutoff is not None:
                df = df[df[category] >= min_cutoff]
            if max_cutoff is not None:
                df = df[df[category] <= max_cutoff]

        return df

    # ── Area Filter ───────────────────────────────────────────────────────────

    def _apply_area_filter(self, df: pd.DataFrame,
                           areas: List[str]) -> pd.DataFrame:
        """
        Filter colleges by area/locality using substring matching
        on college name. Returns rows where any area keyword is found.

        Args:
            df:    DataFrame to filter
            areas: List of area names (e.g., ['Mulund', 'Thane'])

        Returns:
            Filtered DataFrame
        """
        if not areas or df.empty:
            return df

        # Build a regex pattern: "Mulund|Thane|Bhandup"
        pattern = "|".join(
            normalize_str(a).replace(" ", r"\s+")
            for a in areas if a.strip()
        )

        if not pattern:
            return df

        mask = df["collegename"].str.contains(
            pattern, case=False, na=False, regex=True
        )
        filtered = df[mask]

        if filtered.empty:
            logger.info(
                f"Area filter '{areas}' found no colleges in 'collegename'. "
                "Returning unfiltered results."
            )
            return df  # Graceful fallback — don't return empty set

        return filtered

    # ── Deduplication ─────────────────────────────────────────────────────────

    @staticmethod
    def deduplicate(df: pd.DataFrame,
                    subset: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Remove duplicate college entries.
        Default: dedup by college name + stream + medium
        (keeps row with lowest cutoff for the user's category).

        Args:
            df:     DataFrame to deduplicate
            subset: Columns to consider for deduplication

        Returns:
            Deduplicated DataFrame
        """
        if subset is None:
            subset = ["collegename", "stream", "medium"]

        subset = [c for c in subset if c in df.columns]
        if not subset:
            return df

        # Sort so lowest round (most recent final cutoff) is first
        sort_cols = [c for c in ["round_id", "min_cutoff"] if c in df.columns]
        if sort_cols:
            df = df.sort_values(sort_cols, ascending=[True, True])

        return df.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)

    # ── Utility Getters ───────────────────────────────────────────────────────

    def unique_streams(self) -> List[str]:
        return sorted(self.df["stream"].dropna().unique().tolist())

    def unique_districts(self) -> List[str]:
        return sorted(self.df["districtid"].dropna().unique().tolist())

    def unique_mediums(self) -> List[str]:
        return sorted(self.df["medium"].dropna().unique().tolist())

    def unique_rounds(self) -> List[int]:
        return sorted(self.df["round_id"].dropna().unique().tolist())
