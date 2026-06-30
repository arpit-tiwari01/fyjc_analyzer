"""
src/utils/fuzzy_search.py
=========================
Fuzzy string matching for college name search.
Uses fuzzywuzzy (Levenshtein distance) for typo-tolerant search.

Example:
    >>> search = FuzzySearchEngine(college_names)
    >>> results = search.find("joshi college")
    >>> # Returns ranked list of matches
"""

from typing import List, Tuple, Optional
import pandas as pd

try:
    from fuzzywuzzy import fuzz, process as fuzz_process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False


class FuzzySearchEngine:
    """
    Fuzzy search engine for college names.
    Falls back to substring search if fuzzywuzzy is not installed.
    """

    def __init__(self, college_names: List[str], threshold: int = 60):
        """
        Initialize the search engine.

        Args:
            college_names: List of all unique college names from dataset
            threshold:     Minimum similarity score (0–100) to include in results
        """
        self.college_names = [str(n) for n in college_names if pd.notna(n)]
        self.threshold = threshold

        # Pre-compute lowercase index for faster matching
        self._lower_map = {name.lower(): name for name in self.college_names}

    def find(self, query: str, top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Search for colleges matching the query.

        Args:
            query: Search string (college name or partial name)
            top_n: Maximum number of results to return

        Returns:
            List of (college_name, score) tuples, sorted by score desc
        """
        if not query or not query.strip():
            return []

        query_clean = query.strip().lower()

        if FUZZY_AVAILABLE:
            results = fuzz_process.extractBests(
                query_clean,
                self._lower_map.keys(),
                scorer=fuzz.partial_ratio,
                score_cutoff=self.threshold,
                limit=top_n,
            )
            # Map back to original case
            return [(self._lower_map[name], score) for name, score in results]
        else:
            # Fallback: simple substring search
            matches = [
                (original, 100)
                for lower, original in self._lower_map.items()
                if query_clean in lower
            ]
            return matches[:top_n]

    def find_names_only(self, query: str, top_n: int = 10) -> List[str]:
        """Return only the matched college names (no scores)."""
        return [name for name, _ in self.find(query, top_n)]

    def filter_dataframe(self, df: pd.DataFrame, query: str,
                         col: str = "collegename",
                         top_n: int = 20) -> pd.DataFrame:
        """
        Filter a DataFrame to rows where college name fuzzy-matches query.

        Args:
            df:    DataFrame to filter
            query: Search query
            col:   Column name containing college names
            top_n: Maximum matches

        Returns:
            Filtered DataFrame
        """
        matched_names = self.find_names_only(query, top_n)
        if not matched_names:
            return df.iloc[0:0]  # Empty DataFrame with same schema
        return df[df[col].isin(matched_names)]


def build_search_engine(df: pd.DataFrame,
                        col: str = "collegename",
                        threshold: int = 60) -> FuzzySearchEngine:
    """
    Convenience factory: build a FuzzySearchEngine from a DataFrame column.

    Args:
        df:        Source DataFrame
        col:       Column containing college names
        threshold: Fuzzy match threshold

    Returns:
        FuzzySearchEngine instance
    """
    unique_names = df[col].dropna().unique().tolist() if col in df.columns else []
    return FuzzySearchEngine(unique_names, threshold=threshold)
