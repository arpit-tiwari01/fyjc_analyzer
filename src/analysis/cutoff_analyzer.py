"""
src/analysis/cutoff_analyzer.py
================================
Core analysis engine: compares user marks against cutoffs,
classifies colleges, and ranks results.

Classification:
  🟢 Safe     → User marks ≥ Cutoff + SAFE_THRESHOLD (default: +5)
  🟡 Moderate → Cutoff - 3 ≤ User marks < Cutoff + 5
  🔴 Dream    → User marks < Cutoff - 3

Output columns added:
  - cutoff       : Cutoff for user's reservation category
  - user_marks   : User's SSC marks (copied for reference)
  - difference   : user_marks - cutoff
  - classification: Safe / Moderate / Dream
  - chance_pct   : Estimated admission probability (heuristic)

Usage:
    analyzer = CutoffAnalyzer(user_profile)
    results  = analyzer.analyze(filtered_df)
    safe     = results[results['classification'] == 'safe']
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List
import pandas as pd
import numpy as np

from config.settings import SAFE_THRESHOLD, MODERATE_THRESHOLD

logger = logging.getLogger("fyjc.analyzer")


# ─── User Profile ─────────────────────────────────────────────────────────────

@dataclass
class UserProfile:
    """
    Encapsulates everything the user tells us about themselves.

    Fields:
        marks:      SSC percentage (0–100)
        category:   Reservation category column name (e.g., 'General', 'OBC')
        gender:     'Male', 'Female', or 'Other'
        streams:    Preferred streams (e.g., ['Science'])
        areas:      Preferred areas (e.g., ['Mulund', 'Thane'])
        mediums:    Preferred medium of instruction
        districts:  Preferred districts
        round_ids:  Which admission rounds to consider (None = all)
    """
    marks:     float
    category:  str        = "General"
    gender:    str        = "Male"
    streams:   List[str]  = field(default_factory=list)
    areas:     List[str]  = field(default_factory=list)
    mediums:   List[str]  = field(default_factory=list)
    districts: List[str]  = field(default_factory=list)
    round_ids: Optional[List[int]] = None

    def __post_init__(self):
        """Validate marks after initialization."""
        if not (0 <= self.marks <= 100):
            raise ValueError(f"Marks must be between 0 and 100, got {self.marks}")
        if not self.category:
            self.category = "General"


# ─── Cutoff Analyzer ──────────────────────────────────────────────────────────

class CutoffAnalyzer:
    """
    Compares user marks against college cutoffs and classifies colleges.
    """

    # Classification thresholds (from config, can be overridden)
    SAFE_THRESHOLD     = SAFE_THRESHOLD      # +5 above cutoff
    MODERATE_THRESHOLD = MODERATE_THRESHOLD  # -3 to +5

    def __init__(self, user_profile: UserProfile):
        """
        Args:
            user_profile: UserProfile with marks, category, preferences
        """
        self.profile = user_profile

    def analyze(self, df: pd.DataFrame,
                deduplicate: bool = True) -> pd.DataFrame:
        """
        Main analysis: add cutoff comparison columns to filtered DataFrame.

        Args:
            df:          Filtered FYJC DataFrame
            deduplicate: Remove duplicate college entries

        Returns:
            DataFrame with added analysis columns, sorted by best chance first
        """
        if df.empty:
            logger.warning("analyze() called with empty DataFrame")
            return df

        result = df.copy()
        cat_col = self.profile.category

        # 1. Extract the relevant cutoff column
        result = self._extract_cutoff(result, cat_col)

        # 2. Drop rows where this category has no cutoff data
        result = result.dropna(subset=["cutoff"])

        if result.empty:
            logger.warning(
                f"No cutoff data found for category '{cat_col}'. "
                "Try a different reservation category."
            )
            return result

        # 3. Add user marks for reference
        result["user_marks"] = self.profile.marks

        # 4. Calculate difference
        result["difference"] = (
            self.profile.marks - result["cutoff"]
        ).round(2)

        # 5. Classify colleges
        result["classification"] = result["difference"].apply(
            self._classify
        )

        # 6. Estimate admission probability
        result["chance_pct"] = result["difference"].apply(
            self._estimate_probability
        )

        # 7. Deduplicate
        if deduplicate:
            result = self._deduplicate(result)

        # 8. Sort: best chance first
        result = self._sort_results(result)

        # 9. Select and reorder columns for clean output
        result = self._select_output_columns(result)

        logger.info(
            f"Analysis complete | "
            f"Total: {len(result)} | "
            f"Safe: {(result['classification']=='safe').sum()} | "
            f"Moderate: {(result['classification']=='moderate').sum()} | "
            f"Dream: {(result['classification']=='dream').sum()}"
        )

        return result

    # ── Private Methods ───────────────────────────────────────────────────────

    def _extract_cutoff(self, df: pd.DataFrame, cat_col: str) -> pd.DataFrame:
        """
        Extract the relevant cutoff column for the user's category.
        Falls back to 'General' if category column missing.
        """
        if cat_col in df.columns:
            df["cutoff"] = df[cat_col].astype("float32")
        elif "General" in df.columns:
            logger.warning(
                f"Category '{cat_col}' not found, falling back to 'General'"
            )
            df["cutoff"] = df["General"].astype("float32")
        else:
            df["cutoff"] = np.nan

        return df

    def _classify(self, difference: float) -> str:
        """
        Classify a college based on mark difference.

        Args:
            difference: user_marks - cutoff

        Returns:
            'safe', 'moderate', or 'dream'
        """
        if pd.isna(difference):
            return "unknown"
        if difference >= self.SAFE_THRESHOLD:
            return "safe"
        elif difference >= self.MODERATE_THRESHOLD:
            return "moderate"
        else:
            return "dream"

    def _estimate_probability(self, difference: float) -> int:
        """
        Heuristic probability estimate for admission.

        Formula:
          - Safe (diff ≥ 5):      90–99%
          - Moderate (−3 to 5):   50–89%
          - Dream (diff < −3):     5–49%

        Returns:
            Integer percentage (5–99)
        """
        if pd.isna(difference):
            return 0

        if difference >= 10:
            return 99
        elif difference >= 5:
            return int(90 + (difference - 5))   # 90–99
        elif difference >= 0:
            return int(70 + difference * 4)      # 70–89
        elif difference >= -3:
            return int(50 + difference * 6.7)    # 50–69
        elif difference >= -10:
            return max(10, int(30 + difference * 2.9))  # 10–29
        else:
            return 5

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate colleges — keep the best (highest chance) entry.
        """
        if "collegename" not in df.columns:
            return df

        sort_by = ["difference"]
        if "stream" in df.columns:
            sort_by.append("stream")

        df = df.sort_values("difference", ascending=False)
        dedup_cols = ["collegename", "stream", "medium"]
        dedup_cols = [c for c in dedup_cols if c in df.columns]
        return df.drop_duplicates(subset=dedup_cols, keep="first")

    def _sort_results(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sort results: highest chance first.
        Within same classification, sort by how close the cutoff is.
        """
        # Define sort order: safe → moderate → dream
        class_order = {"safe": 0, "moderate": 1, "dream": 2, "unknown": 3}
        df["_sort_order"] = df["classification"].map(class_order)

        df = df.sort_values(
            ["_sort_order", "difference"],
            ascending=[True, False]
        )
        df = df.drop(columns=["_sort_order"])
        return df.reset_index(drop=True)

    def _select_output_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Select and reorder columns for clean output.
        Keeps essential info + analysis columns.
        """
        priority_cols = [
            "collegename", "stream", "medium", "districtid",
            "cutoff", "user_marks", "difference",
            "classification", "chance_pct",
            "round_id", "status", "choicecode"
        ]
        # Only keep columns that exist
        out_cols = [c for c in priority_cols if c in df.columns]
        # Add any remaining columns at the end
        extras = [c for c in df.columns if c not in out_cols]
        return df[out_cols + extras]

    # ── Summary Statistics ────────────────────────────────────────────────────

    @staticmethod
    def summary(df: pd.DataFrame) -> dict:
        """
        Generate a summary of analysis results.

        Returns:
            Dict with counts, averages, etc.
        """
        if df.empty or "classification" not in df.columns:
            return {}

        return {
            "total": len(df),
            "safe": int((df["classification"] == "safe").sum()),
            "moderate": int((df["classification"] == "moderate").sum()),
            "dream": int((df["classification"] == "dream").sum()),
            "avg_cutoff": round(df["cutoff"].mean(), 2) if "cutoff" in df.columns else None,
            "min_cutoff": round(df["cutoff"].min(), 2) if "cutoff" in df.columns else None,
            "max_cutoff": round(df["cutoff"].max(), 2) if "cutoff" in df.columns else None,
            "avg_difference": round(df["difference"].mean(), 2) if "difference" in df.columns else None,
        }
