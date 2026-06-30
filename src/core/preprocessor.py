"""
src/core/preprocessor.py
========================
Cleans, validates, and normalizes the raw FYJC DataFrame.

Responsibilities:
  - Drop fully null rows
  - Normalize college name casing
  - Validate cutoff values (0–100 range)
  - Handle missing cutoff values
  - Add derived helper columns
  - Ensure correct dtypes after loading

Run ONCE after loading. Returns a clean DataFrame.
"""

import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("fyjc.preprocessor")


class FYJCPreprocessor:
    """
    Cleans and enriches the raw FYJC DataFrame.
    """

    # Columns that must exist in the dataset
    REQUIRED_COLUMNS = [
        "collegename", "stream", "districtid", "round_id"
    ]

    # Reservation columns to validate
    CUTOFF_COLUMNS = ["SC", "ST", "VJA", "NTB", "NTC", "NTD",
                      "OBC", "SBC", "SEBC", "EWS", "General"]

    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: Raw DataFrame from FYJCDataLoader
        """
        self.df = df.copy()
        self._report = {}  # Stores cleanup statistics

    def run(self) -> pd.DataFrame:
        """
        Execute all preprocessing steps in order.

        Returns:
            Clean, enriched DataFrame ready for analysis
        """
        logger.info("Starting preprocessing pipeline...")
        original_rows = len(self.df)

        self._validate_required_columns()
        self._drop_fully_empty_rows()
        self._normalize_text_columns()
        self._clamp_cutoff_values()
        self._add_derived_columns()
        self._convert_categoricals()

        final_rows = len(self.df)
        dropped = original_rows - final_rows

        logger.info(
            f"Preprocessing complete | "
            f"Original: {original_rows:,} | "
            f"Final: {final_rows:,} | "
            f"Dropped: {dropped:,}"
        )
        return self.df

    # ── Step 1: Validate Required Columns ─────────────────────────────────────

    def _validate_required_columns(self):
        """Raise early if essential columns are missing."""
        missing = [c for c in self.REQUIRED_COLUMNS if c not in self.df.columns]
        if missing:
            raise ValueError(
                f"Missing required columns in dataset: {missing}\n"
                f"Available columns: {list(self.df.columns)}"
            )
        logger.debug(f"Required columns present: {self.REQUIRED_COLUMNS}")

    # ── Step 2: Drop Empty Rows ───────────────────────────────────────────────

    def _drop_fully_empty_rows(self):
        """
        Drop rows where ALL cutoff values are NaN.
        (A row with no cutoff data is useless for analysis.)
        """
        cutoff_cols = [c for c in self.CUTOFF_COLUMNS if c in self.df.columns]
        if cutoff_cols:
            before = len(self.df)
            self.df.dropna(subset=cutoff_cols, how="all", inplace=True)
            dropped = before - len(self.df)
            if dropped > 0:
                logger.info(f"Dropped {dropped:,} rows with all-NaN cutoffs")

    # ── Step 3: Normalize Text Columns ────────────────────────────────────────

    def _normalize_text_columns(self):
        """
        Standardize casing and strip whitespace.
        College names → Title Case
        Stream → Title Case
        Medium → Title Case
        """
        str_title_cols = ["collegename", "stream", "medium", "status", "subject"]

        for col in str_title_cols:
            if col in self.df.columns:
                self.df[col] = (
                    self.df[col]
                    .astype(str)
                    .str.strip()
                    .str.title()
                    .replace("Nan", pd.NA)
                    .replace("None", pd.NA)
                )

        # District and region IDs — just strip
        for col in ["districtid", "regionid"]:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).str.strip()

        logger.debug("Text columns normalized")

    # ── Step 4: Clamp Cutoff Values ───────────────────────────────────────────

    def _clamp_cutoff_values(self):
        """
        Ensure all cutoff percentages are in [0, 100].
        Values outside this range are set to NaN (data errors).
        """
        cutoff_cols = [c for c in self.CUTOFF_COLUMNS if c in self.df.columns]
        invalid_count = 0

        for col in cutoff_cols:
            mask = (self.df[col] < 0) | (self.df[col] > 100)
            invalid_count += mask.sum()
            self.df.loc[mask, col] = np.nan

        if invalid_count > 0:
            logger.warning(
                f"Clamped {invalid_count} out-of-range cutoff values to NaN"
            )

    # ── Step 5: Add Derived Columns ───────────────────────────────────────────

    def _add_derived_columns(self):
        """
        Add computed columns useful for filtering and display.

        New columns:
          - min_cutoff: Minimum cutoff across all categories (useful for
                        quickly identifying the most accessible entry point)
          - available_categories: Comma-separated list of non-null categories
        """
        cutoff_cols = [c for c in self.CUTOFF_COLUMNS if c in self.df.columns]

        if cutoff_cols:
            # Minimum cutoff across all reservation categories
            self.df["min_cutoff"] = self.df[cutoff_cols].min(axis=1)

            # Maximum cutoff (usually General)
            self.df["max_cutoff"] = self.df[cutoff_cols].max(axis=1)

        logger.debug("Derived columns added: min_cutoff, max_cutoff")

    # ── Step 6: Convert to Categoricals ──────────────────────────────────────

    def _convert_categoricals(self):
        """
        Convert low-cardinality string columns to pandas Categorical dtype.
        This is the single biggest memory optimization step.

        Estimated savings: 60–70% memory reduction on these columns.
        """
        categorical_cols = ["stream", "medium", "status", "districtid",
                            "regionid", "subject", "ReservationDetails"]

        for col in categorical_cols:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype("category")

        # round_id as int8 if not already
        if "round_id" in self.df.columns:
            try:
                self.df["round_id"] = self.df["round_id"].astype("int8")
            except (ValueError, OverflowError):
                pass  # Keep as-is if conversion fails

        logger.debug("Categorical dtypes applied")

    # ── Public Utilities ──────────────────────────────────────────────────────

    def get_report(self) -> dict:
        """Return preprocessing statistics."""
        return self._report

    @staticmethod
    def quick_clean(df: pd.DataFrame) -> pd.DataFrame:
        """
        Static convenience method: run full preprocessing in one call.

        Usage:
            clean_df = FYJCPreprocessor.quick_clean(raw_df)
        """
        return FYJCPreprocessor(df).run()
