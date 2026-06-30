"""
src/ui/cli.py
=============
Main CLI application controller.
Orchestrates all modules: loading → filtering → analyzing → displaying → exporting.

Entry point: run()
"""

import logging
import sys
import time
from pathlib import Path
from typing import Optional

from config.settings import (
    DEFAULT_CSV_PATH, USE_DUCKDB, USE_PARQUET_CACHE,
    CSV_CHUNK_SIZE, MAX_DISPLAY_ROWS, LOG_FILE, LOG_LEVEL, APP_VERSION
)
from src.utils.helpers import setup_logger, memory_usage_mb
from src.ui.display import (
    print_banner, print_section, print_success, print_warning,
    print_error, print_info, print_results_table, print_summary,
    print_load_stats, console
)

logger = logging.getLogger("fyjc.cli")


class FYJCApp:
    """
    Main application controller.
    Wires together all modules and manages the user interaction loop.
    """

    def __init__(self, csv_path: Optional[Path] = None):
        """
        Args:
            csv_path: Override default CSV path (useful for testing)
        """
        self.csv_path  = csv_path or DEFAULT_CSV_PATH
        self._df       = None
        self._db       = None
        self._filter   = None
        self._search   = None

    def run(self):
        """Main application loop."""
        setup_logger("fyjc", log_file=LOG_FILE, level=LOG_LEVEL)

        print_banner()
        print_info(f"FYJC Cutoff Analyzer v{APP_VERSION}")
        print()

        # ── Step 1: Load Data ─────────────────────────────────────────────
        self._df = self._load_data()
        if self._df is None:
            sys.exit(1)

        # ── Step 2: Initialize DuckDB ─────────────────────────────────────
        if USE_DUCKDB:
            self._init_database()

        # ── Step 3: Build filter engine ───────────────────────────────────
        self._init_filter_engine()

        # ── Step 4: Build fuzzy search engine ────────────────────────────
        self._init_search_engine()

        # ── Step 5: Main interaction loop ────────────────────────────────
        self._main_loop()

    # ── Data Loading ──────────────────────────────────────────────────────────

    def _load_data(self):
        """Load, preprocess, and cache FYJC data."""
        from src.core.loader import FYJCDataLoader
        from src.core.preprocessor import FYJCPreprocessor

        print_section("Loading Data", "📂")

        if not self.csv_path.exists():
            print_error(
                f"CSV file not found: {self.csv_path}\n\n"
                "  ➡️  Please place your FYJC cutoff CSV file at:\n"
                f"     {self.csv_path}\n\n"
                "  The file should have columns: collegename, stream, districtid,\n"
                "  medium, round_id, SC, ST, OBC, General, EWS, etc."
            )
            return None

        try:
            start = time.perf_counter()
            print_info(f"Source: {self.csv_path}")

            loader = FYJCDataLoader(
                csv_path=self.csv_path,
                chunk_size=CSV_CHUNK_SIZE,
                use_cache=USE_PARQUET_CACHE,
            )
            raw_df = loader.load()

            print_info("Preprocessing data...")
            preprocessor = FYJCPreprocessor(raw_df)
            df = preprocessor.run()

            elapsed = time.perf_counter() - start
            mem_mb  = memory_usage_mb(df)

            print_load_stats(len(df), len(df.columns), mem_mb, elapsed)
            print_success(f"Data ready: {len(df):,} records loaded")
            return df

        except Exception as e:
            print_error(f"Failed to load data: {e}")
            logger.exception("Data loading error")
            return None

    def _init_database(self):
        """Initialize DuckDB for fast SQL queries."""
        from src.core.database import FYJCDatabase
        try:
            print_info("Initializing DuckDB for fast queries...")
            self._db = FYJCDatabase(self._df)
            if self._db.available:
                print_success(f"DuckDB ready ({self._db.count():,} rows indexed)")
            else:
                print_warning("DuckDB unavailable, using pandas fallback")
        except Exception as e:
            logger.warning(f"DuckDB init failed: {e}")
            self._db = None

    def _init_filter_engine(self):
        """Initialize the filter engine."""
        from src.analysis.filter_engine import FilterEngine
        self._filter = FilterEngine(self._df, db=self._db)
        logger.debug("Filter engine initialized")

    def _init_search_engine(self):
        """Initialize fuzzy college name search."""
        from src.utils.fuzzy_search import build_search_engine
        self._search = build_search_engine(self._df)
        logger.debug("Fuzzy search engine initialized")

    # ── Main Interaction Loop ──────────────────────────────────────────────────

    def _main_loop(self):
        """Interactive menu loop."""
        while True:
            print_section("Main Menu", "🏠")
            action = self._ask_action()

            if action == "analyze":
                self._run_analysis()
            elif action == "search":
                self._run_college_search()
            elif action == "trends":
                self._run_trend_analysis()
            elif action == "exit":
                print_success("Thank you for using FYJC Cutoff Analyzer. Best of luck! 🎓")
                sys.exit(0)

    def _ask_action(self) -> str:
        """Show main menu and get user choice."""
        try:
            import questionary
            choice = questionary.select(
                "What would you like to do?",
                choices=[
                    "🔍 Analyze cutoffs (find colleges for my marks)",
                    "🔎 Search for a specific college",
                    "📈 View cutoff trends across rounds",
                    "🚪 Exit",
                ]
            ).ask()

            if choice is None:
                sys.exit(0)

            action_map = {
                "🔍 Analyze cutoffs (find colleges for my marks)": "analyze",
                "🔎 Search for a specific college":               "search",
                "📈 View cutoff trends across rounds":            "trends",
                "🚪 Exit":                                        "exit",
            }
            return action_map.get(choice, "exit")

        except ImportError:
            raw = input("\n[1] Analyze  [2] Search  [3] Trends  [4] Exit\nChoice: ").strip()
            return {"1": "analyze", "2": "search", "3": "trends", "4": "exit"}.get(raw, "exit")

    # ── Analysis Flow ──────────────────────────────────────────────────────────

    def _run_analysis(self):
        """Full analysis flow: prompts → filter → analyze → display → export."""
        from src.ui.prompts import collect_user_profile
        from src.analysis.cutoff_analyzer import UserProfile, CutoffAnalyzer
        from src.utils.exporter import FYJCExporter

        # Collect user profile
        profile_data = collect_user_profile(
            available_streams   = self._filter.unique_streams(),
            available_districts = self._filter.unique_districts(),
            available_mediums   = self._filter.unique_mediums(),
            available_rounds    = self._filter.unique_rounds(),
        )

        user = UserProfile(**profile_data)

        # Filter data
        print_section("Filtering Colleges", "🔍")
        print_info(
            f"Marks: {user.marks}% | Category: {user.category} | "
            f"Streams: {user.streams or 'All'}"
        )

        start = time.perf_counter()
        filtered_df = self._filter.filter(
            streams    = user.streams or None,
            districts  = user.districts or None,
            mediums    = user.mediums or None,
            round_ids  = user.round_ids,
            areas      = user.areas or None,
            category   = user.category,
        )
        filter_time = time.perf_counter() - start

        if filtered_df.empty:
            print_warning(
                "No colleges found with your filters.\n"
                "Try: removing area/district filters, or selecting more streams."
            )
            return

        print_success(
            f"Found {len(filtered_df):,} matching records "
            f"({filter_time:.2f}s)"
        )

        # Analyze
        print_section("Analyzing Cutoffs", "📊")
        analyzer = CutoffAnalyzer(user)
        results  = analyzer.analyze(filtered_df, deduplicate=True)

        if results.empty:
            print_warning(
                f"No cutoff data available for category '{user.category}'.\n"
                "Try a different reservation category."
            )
            return

        # Display summary
        summary = CutoffAnalyzer.summary(results)
        print_summary(summary, user.marks, user.category)

        # Display table
        print_section("College List", "🏫")
        print_results_table(results, max_rows=MAX_DISPLAY_ROWS, user_marks=user.marks)

        # Export to Excel
        self._ask_export(results, user)

    def _ask_export(self, results, user):
        """Ask if user wants to export results to Excel."""
        try:
            import questionary
            want_export = questionary.confirm(
                "Export results to Excel?",
                default=True
            ).ask()
        except ImportError:
            raw = input("Export to Excel? (y/n): ").strip().lower()
            want_export = raw == "y"

        if want_export:
            from src.utils.exporter import FYJCExporter
            try:
                exporter = FYJCExporter()
                stream_label = "_".join(user.streams) if user.streams else "All"
                path = exporter.export(
                    results_df = results,
                    user_marks = user.marks,
                    category   = user.category,
                    stream     = stream_label,
                )
                print_success(f"Excel exported: {path}")
            except Exception as e:
                print_error(f"Export failed: {e}")

    # ── College Search ────────────────────────────────────────────────────────

    def _run_college_search(self):
        """Search for a college by name using fuzzy matching."""
        from src.analysis.cutoff_analyzer import CutoffAnalyzer, UserProfile

        print_section("College Search", "🔎")

        try:
            import questionary
            query = questionary.text("Enter college name (partial is fine):").ask()
            category = questionary.select(
                "Which category to show cutoffs for?",
                choices=["General", "OBC", "SC", "ST", "EWS", "SEBC", "SBC"]
            ).ask()
        except ImportError:
            query    = input("College name: ").strip()
            category = input("Category (General/OBC/SC/...): ").strip() or "General"

        if not query:
            return

        results = self._search.filter_dataframe(self._df, query, top_n=30)

        if results.empty:
            print_warning(f"No colleges found matching '{query}'")
            return

        print_success(f"Found {len(results)} matching colleges")

        # Add dummy user profile to get analysis columns
        dummy_user = UserProfile(marks=85.0, category=category)
        analyzer   = CutoffAnalyzer(dummy_user)
        analyzed   = analyzer.analyze(results, deduplicate=False)

        print_results_table(analyzed, max_rows=30)

    # ── Trend Analysis ────────────────────────────────────────────────────────

    def _run_trend_analysis(self):
        """Show cutoff trends across rounds."""
        from src.analysis.trend_analyzer import TrendAnalyzer

        print_section("Cutoff Trends", "📈")

        try:
            import questionary
            category = questionary.select(
                "Show trends for which category?",
                choices=["General", "OBC", "SC", "ST", "EWS"]
            ).ask()
            stream = questionary.select(
                "Which stream?",
                choices=["All"] + self._filter.unique_streams()
            ).ask()
        except ImportError:
            category = input("Category: ").strip() or "General"
            stream   = input("Stream (or blank for all): ").strip() or None

        trend = TrendAnalyzer(self._df)

        stream_arg = None if stream == "All" else stream

        pivot = trend.round_pivot(category=category, stream=stream_arg, top_n=20)

        if pivot.empty:
            print_warning("No trend data available.")
            return

        print_section(f"Cutoff Trend — {category} | {stream}", "📊")

        # Display pivot table
        try:
            from rich.table import Table
            from rich import box

            table = Table(
                title=f"Cutoffs by Round — {category}",
                box=box.SIMPLE_HEAD, show_header=True,
                header_style="bold cyan"
            )
            table.add_column("College", max_width=35)
            for col in pivot.columns:
                table.add_column(col, justify="right")

            for college, row in pivot.iterrows():
                cells = [str(college)]
                for val in row:
                    cells.append(f"{val:.2f}" if not __import__('math').isnan(val) else "—")
                table.add_row(*cells)

            console.print(table)
        except Exception:
            print(pivot.to_string())

        # Show falling cutoff colleges
        falling = trend.colleges_with_falling_cutoff(category, stream_arg)
        if not falling.empty:
            print_section("Colleges with Falling Cutoffs (Easier Entry!)", "⬇️")
            print_results_table(
                falling.rename(columns={
                    "collegename": "collegename",
                    "change": "difference"
                }),
                max_rows=10
            )


def run(csv_path: Optional[Path] = None):
    """Entry point for the FYJC Analyzer CLI."""
    app = FYJCApp(csv_path=csv_path)
    app.run()
