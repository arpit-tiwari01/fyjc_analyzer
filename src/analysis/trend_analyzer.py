"""
src/analysis/trend_analyzer.py
===============================
Year-over-year and round-over-round cutoff trend analysis.

Features:
  - Compare cutoffs across admission rounds (1, 2, 3...)
  - Detect rising/falling/stable trends
  - Find colleges where cutoff dropped (easier to get in)
  - Pivot table: college × round → cutoff

Usage:
    trend = TrendAnalyzer(df)
    pivot = trend.round_pivot(category="General", stream="Science")
    changes = trend.cutoff_changes(category="OBC")
"""

import logging
from typing import Optional, List
import pandas as pd
import numpy as np

logger = logging.getLogger("fyjc.trend")


class TrendAnalyzer:
    """Analyzes cutoff trends across rounds and college profiles."""

    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: Clean FYJC DataFrame
        """
        self.df = df

    def round_pivot(
        self,
        category:   str = "General",
        stream:     Optional[str] = None,
        district:   Optional[str] = None,
        top_n:      int = 50,
    ) -> pd.DataFrame:
        """
        Create a pivot table: College × Round → Cutoff

        Args:
            category: Reservation category column
            stream:   Filter by stream (optional)
            district: Filter by district (optional)
            top_n:    Limit to top N colleges by average cutoff

        Returns:
            Pivot DataFrame with colleges as rows, rounds as columns
        """
        if category not in self.df.columns:
            logger.warning(f"Category '{category}' not found in dataset")
            return pd.DataFrame()

        df = self.df.copy()

        if stream:
            df = df[df["stream"].str.lower() == stream.lower()]
        if district:
            df = df[df["districtid"].astype(str).str.lower() == district.lower()]

        # Aggregate: average cutoff per college per round
        pivot = df.pivot_table(
            values=category,
            index="collegename",
            columns="round_id",
            aggfunc="mean"
        ).round(2)

        # Rename columns to "Round 1", "Round 2", etc.
        pivot.columns = [f"Round {int(c)}" for c in pivot.columns]

        # Sort by highest average cutoff (most competitive first)
        pivot["avg"] = pivot.mean(axis=1)
        pivot = pivot.sort_values("avg", ascending=False).drop(columns="avg")

        return pivot.head(top_n)

    def cutoff_changes(
        self,
        category: str = "General",
        stream:   Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Identify colleges where cutoff changed significantly between rounds.

        Args:
            category: Reservation category
            stream:   Filter by stream

        Returns:
            DataFrame with college, round_from, round_to, change, direction
        """
        pivot = self.round_pivot(category=category, stream=stream, top_n=500)

        if pivot.empty or pivot.shape[1] < 2:
            return pd.DataFrame()

        round_cols = pivot.columns.tolist()
        results = []

        for college in pivot.index:
            row = pivot.loc[college]
            for i in range(len(round_cols) - 1):
                r_from = round_cols[i]
                r_to   = round_cols[i + 1]
                val_from = row[r_from]
                val_to   = row[r_to]

                if pd.notna(val_from) and pd.notna(val_to):
                    change = round(val_to - val_from, 2)
                    if abs(change) >= 0.5:  # Only report meaningful changes
                        results.append({
                            "collegename": college,
                            "from_round": r_from,
                            "to_round":   r_to,
                            "cutoff_from": val_from,
                            "cutoff_to":   val_to,
                            "change": change,
                            "direction": "⬆️ Rising" if change > 0 else "⬇️ Falling",
                        })

        if not results:
            return pd.DataFrame()

        return (
            pd.DataFrame(results)
            .sort_values("change", ascending=True)
            .reset_index(drop=True)
        )

    def colleges_with_falling_cutoff(
        self,
        category: str = "General",
        stream: Optional[str] = None,
        min_drop: float = 2.0,
    ) -> pd.DataFrame:
        """
        Find colleges where cutoff dropped (easier to get in over rounds).

        Args:
            category: Reservation category
            stream:   Filter by stream
            min_drop: Minimum drop in percentage points

        Returns:
            DataFrame of colleges with falling cutoffs
        """
        changes = self.cutoff_changes(category, stream)
        if changes.empty:
            return pd.DataFrame()

        falling = changes[changes["change"] <= -min_drop].copy()
        falling = falling.sort_values("change")  # Biggest drops first
        return falling

    def average_cutoff_by_stream(self, category: str = "General") -> pd.DataFrame:
        """
        Average cutoff per stream per round.
        Useful for high-level trend overview.
        """
        if category not in self.df.columns or "stream" not in self.df.columns:
            return pd.DataFrame()

        return (
            self.df.groupby(["stream", "round_id"])[category]
            .mean()
            .round(2)
            .reset_index()
            .rename(columns={category: "avg_cutoff", "round_id": "round"})
            .sort_values(["stream", "round"])
        )
