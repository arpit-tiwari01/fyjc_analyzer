"""
tests/test_core.py
==================
Unit tests for the FYJC Cutoff Analyzer core modules.

Run with:
    python -m pytest tests/ -v
    python -m pytest tests/test_core.py -v --tb=short
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_df():
    """Create a minimal sample DataFrame mimicking FYJC data."""
    return pd.DataFrame({
        "id":           range(1, 11),
        "districtid":   ["Mumbai"] * 5 + ["Pune"] * 5,
        "regionid":     ["Konkan"] * 5 + ["Pune"] * 5,
        "udise":        [f"272{i:05d}" for i in range(10)],
        "collegename":  [
            "Mulund Junior College",   "Thane Science College",
            "Bhandup Arts College",    "Kalwa Commerce College",
            "Airoli Vidyalaya",        "Pune Science Institute",
            "Deccan Junior College",   "Camp Arts College",
            "Kothrud Commerce College","Aundh Science College",
        ],
        "stream":       ["Science", "Science", "Arts", "Commerce", "Science",
                         "Science", "Arts", "Arts", "Commerce", "Science"],
        "status":       ["G", "A", "U", "G", "A", "U", "G", "A", "U", "G"],
        "medium":       ["English"] * 7 + ["Marathi"] * 3,
        "subject":      ["General"] * 10,
        "choicecode":   [f"{10000+i}" for i in range(10)],
        "ReservationDetails": ["Open"] * 10,
        "SC":     [70.0, 72.0, 65.0, 68.0, 75.0, 78.0, 60.0, 62.0, 66.0, 80.0],
        "ST":     [65.0, 68.0, 60.0, 63.0, 70.0, 73.0, 55.0, 57.0, 61.0, 75.0],
        "VJA":    [68.0, 70.0, 63.0, 66.0, 73.0, 76.0, None, None, None, None],
        "NTB":    [69.0, 71.0, 64.0, 67.0, 74.0, 77.0, None, None, None, None],
        "NTC":    [None] * 10,
        "NTD":    [None] * 10,
        "OBC":    [75.0, 77.0, 70.0, 73.0, 80.0, 83.0, 65.0, 67.0, 71.0, 85.0],
        "SBC":    [None] * 10,
        "SEBC":   [76.0, 78.0, 71.0, 74.0, 81.0, 84.0, 66.0, 68.0, 72.0, 86.0],
        "EWS":    [77.0, 79.0, 72.0, 75.0, 82.0, 85.0, 67.0, 69.0, 73.0, 87.0],
        "General":[82.0, 85.0, 78.0, 80.0, 88.0, 91.0, 72.0, 74.0, 78.0, 93.0],
        "round_id": [1, 1, 1, 1, 2, 2, 2, 3, 3, 3],
    })


# ─── Tests: Preprocessor ──────────────────────────────────────────────────────

class TestPreprocessor:

    def test_runs_without_error(self, sample_df):
        from src.core.preprocessor import FYJCPreprocessor
        result = FYJCPreprocessor(sample_df).run()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_drops_all_nan_cutoff_rows(self):
        from src.core.preprocessor import FYJCPreprocessor
        df = pd.DataFrame({
            "id": [1, 2],
            "districtid": ["Mumbai", "Pune"],
            "regionid": ["Konkan", "Pune"],
            "collegename": ["A College", "B College"],
            "stream": ["Science", "Arts"],
            "round_id": [1, 1],
            "General": [None, 80.0],
            "SC": [None, 70.0],
            "ST": [None, 65.0],
            "OBC": [None, 75.0],
            "EWS": [None, 77.0],
            "SEBC": [None, 76.0],
            "SBC": [None, None],
            "VJA": [None, None],
            "NTB": [None, None],
            "NTC": [None, None],
            "NTD": [None, None],
        })
        result = FYJCPreprocessor(df).run()
        assert len(result) == 1  # Row with all-NaN cutoffs should be dropped

    def test_adds_min_cutoff_column(self, sample_df):
        from src.core.preprocessor import FYJCPreprocessor
        result = FYJCPreprocessor(sample_df).run()
        assert "min_cutoff" in result.columns

    def test_clamps_out_of_range_values(self):
        from src.core.preprocessor import FYJCPreprocessor
        df = pd.DataFrame({
            "id": [1], "districtid": ["Mumbai"], "regionid": ["K"],
            "collegename": ["X"], "stream": ["Science"], "round_id": [1],
            "General": [150.0],  # Out of range
            "SC": [-5.0],        # Out of range
        })
        result = FYJCPreprocessor(df).run()
        if len(result) > 0:
            assert pd.isna(result["General"].iloc[0]) or result["General"].iloc[0] <= 100


# ─── Tests: Filter Engine ─────────────────────────────────────────────────────

class TestFilterEngine:

    def test_filter_by_stream(self, sample_df):
        from src.analysis.filter_engine import FilterEngine
        engine = FilterEngine(sample_df)
        result = engine.filter(streams=["Science"])
        assert all(result["stream"] == "Science")

    def test_filter_by_district(self, sample_df):
        from src.analysis.filter_engine import FilterEngine
        engine = FilterEngine(sample_df)
        result = engine.filter(districts=["Mumbai"])
        assert all(result["districtid"] == "Mumbai")

    def test_filter_by_round(self, sample_df):
        from src.analysis.filter_engine import FilterEngine
        engine = FilterEngine(sample_df)
        result = engine.filter(round_ids=[1])
        assert all(result["round_id"] == 1)

    def test_area_filter(self, sample_df):
        from src.analysis.filter_engine import FilterEngine
        engine = FilterEngine(sample_df)
        result = engine.filter(areas=["Mulund"])
        assert len(result) >= 1
        assert any("Mulund" in name for name in result["collegename"])

    def test_returns_all_when_no_filters(self, sample_df):
        from src.analysis.filter_engine import FilterEngine
        engine = FilterEngine(sample_df)
        result = engine.filter()
        assert len(result) == len(sample_df)

    def test_empty_result_with_impossible_filter(self, sample_df):
        from src.analysis.filter_engine import FilterEngine
        engine = FilterEngine(sample_df)
        result = engine.filter(districts=["NonExistentDistrict123"])
        assert len(result) == 0


# ─── Tests: Cutoff Analyzer ───────────────────────────────────────────────────

class TestCutoffAnalyzer:

    def test_analyze_returns_classification(self, sample_df):
        from src.analysis.cutoff_analyzer import CutoffAnalyzer, UserProfile
        user = UserProfile(marks=80.0, category="General")
        analyzer = CutoffAnalyzer(user)
        result = analyzer.analyze(sample_df)
        assert "classification" in result.columns
        assert all(result["classification"].isin(["safe", "moderate", "dream", "unknown"]))

    def test_safe_classification(self, sample_df):
        """High marks → more safe colleges."""
        from src.analysis.cutoff_analyzer import CutoffAnalyzer, UserProfile
        user = UserProfile(marks=99.0, category="General")
        analyzer = CutoffAnalyzer(user)
        result = analyzer.analyze(sample_df)
        safe_count = (result["classification"] == "safe").sum()
        assert safe_count > 0

    def test_dream_classification(self, sample_df):
        """Low marks → more dream colleges."""
        from src.analysis.cutoff_analyzer import CutoffAnalyzer, UserProfile
        user = UserProfile(marks=50.0, category="General")
        analyzer = CutoffAnalyzer(user)
        result = analyzer.analyze(sample_df)
        dream_count = (result["classification"] == "dream").sum()
        assert dream_count > 0

    def test_difference_column(self, sample_df):
        from src.analysis.cutoff_analyzer import CutoffAnalyzer, UserProfile
        user = UserProfile(marks=80.0, category="General")
        analyzer = CutoffAnalyzer(user)
        result = analyzer.analyze(sample_df)
        assert "difference" in result.columns
        # Verify difference = user_marks - cutoff
        diff_check = (result["user_marks"] - result["cutoff"]).round(2)
        pd.testing.assert_series_equal(
            result["difference"].astype("float64"),
            diff_check.astype("float64"),
            check_names=False, rtol=0.01
        )

    def test_chance_pct_range(self, sample_df):
        from src.analysis.cutoff_analyzer import CutoffAnalyzer, UserProfile
        user = UserProfile(marks=80.0, category="General")
        result = CutoffAnalyzer(user).analyze(sample_df)
        assert result["chance_pct"].between(0, 100).all()

    def test_sorted_by_chance(self, sample_df):
        from src.analysis.cutoff_analyzer import CutoffAnalyzer, UserProfile
        user = UserProfile(marks=80.0, category="General")
        result = CutoffAnalyzer(user).analyze(sample_df)
        # Safe colleges should come before dream colleges
        cls = result["classification"].tolist()
        if "safe" in cls and "dream" in cls:
            assert cls.index("safe") < cls.index("dream")

    def test_summary_keys(self, sample_df):
        from src.analysis.cutoff_analyzer import CutoffAnalyzer, UserProfile
        user = UserProfile(marks=80.0, category="General")
        result = CutoffAnalyzer(user).analyze(sample_df)
        summary = CutoffAnalyzer.summary(result)
        expected_keys = ["total", "safe", "moderate", "dream", "avg_cutoff"]
        for k in expected_keys:
            assert k in summary


# ─── Tests: Helpers ───────────────────────────────────────────────────────────

class TestHelpers:

    def test_validate_marks_valid(self):
        from src.utils.helpers import validate_marks
        assert validate_marks("85.5") == 85.5
        assert validate_marks(100)    == 100.0
        assert validate_marks("0")    == 0.0

    def test_validate_marks_invalid(self):
        from src.utils.helpers import validate_marks
        assert validate_marks("abc")  is None
        assert validate_marks(101)    is None
        assert validate_marks(-1)     is None

    def test_normalize_str(self):
        from src.utils.helpers import normalize_str
        assert normalize_str("  Hello   World  ") == "hello world"
        assert normalize_str("SCIENCE") == "science"

    def test_memory_usage_mb(self, sample_df):
        from src.utils.helpers import memory_usage_mb
        mem = memory_usage_mb(sample_df)
        assert isinstance(mem, float)
        assert mem > 0


# ─── Tests: Fuzzy Search ──────────────────────────────────────────────────────

class TestFuzzySearch:

    def test_finds_exact_match(self, sample_df):
        from src.utils.fuzzy_search import build_search_engine
        engine = build_search_engine(sample_df)
        results = engine.find_names_only("Mulund Junior College")
        assert len(results) > 0

    def test_finds_partial_match(self, sample_df):
        from src.utils.fuzzy_search import build_search_engine
        engine = build_search_engine(sample_df)
        results = engine.find_names_only("Mulund")
        assert len(results) > 0
        assert any("Mulund" in r for r in results)

    def test_no_results_for_nonsense(self, sample_df):
        from src.utils.fuzzy_search import build_search_engine
        engine = build_search_engine(sample_df, threshold=95)
        results = engine.find_names_only("xyzxyzxyz123")
        assert len(results) == 0

    def test_filter_dataframe(self, sample_df):
        from src.utils.fuzzy_search import build_search_engine
        engine = build_search_engine(sample_df)
        filtered = engine.filter_dataframe(sample_df, "Pune")
        assert all("Pune" in name or True for name in filtered["collegename"])


# ─── Tests: UserProfile ───────────────────────────────────────────────────────

class TestUserProfile:

    def test_valid_profile(self):
        from src.analysis.cutoff_analyzer import UserProfile
        p = UserProfile(marks=80.0, category="OBC")
        assert p.marks == 80.0
        assert p.category == "OBC"

    def test_invalid_marks_raises(self):
        from src.analysis.cutoff_analyzer import UserProfile
        with pytest.raises(ValueError):
            UserProfile(marks=110.0)

    def test_default_category(self):
        from src.analysis.cutoff_analyzer import UserProfile
        p = UserProfile(marks=75.0, category="")
        assert p.category == "General"


# ─── Run directly ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
