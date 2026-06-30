"""
src/ui/streamlit_app.py
========================
Streamlit web dashboard for FYJC Cutoff Analyzer.

Run with:
    streamlit run src/ui/streamlit_app.py

Features:
  - Sidebar filters (stream, district, area, medium, round)
  - Color-coded results table
  - Cutoff distribution charts
  - Round-over-round trend charts
  - Excel export button
  - College search
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np

try:
    import streamlit as st
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    print("Install streamlit and plotly: pip install streamlit plotly")
    sys.exit(1)

from config.settings import DEFAULT_CSV_PATH, PARQUET_CACHE_PATH
from src.utils.constants import (
    CATEGORY_MAP, STREAM_DISPLAY, MEDIUMS, ALL_AREAS, ROUNDS
)

# ─── Page Configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="FYJC Cutoff Analyzer",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title { color: #1F4E79; font-size: 2rem; font-weight: bold; }
    .safe-badge   { background-color: #C6EFCE; color: #276221; padding: 2px 8px;
                    border-radius: 4px; font-weight: bold; }
    .moderate-badge { background-color: #FFEB9C; color: #9C6500; padding: 2px 8px;
                      border-radius: 4px; font-weight: bold; }
    .dream-badge  { background-color: #FFC7CE; color: #9C0006; padding: 2px 8px;
                    border-radius: 4px; font-weight: bold; }
    .metric-card  { background: #f0f4ff; border-radius: 8px; padding: 12px; }
</style>
""", unsafe_allow_html=True)


# ─── Data Loading (Cached) ────────────────────────────────────────────────────

@st.cache_data(show_spinner="Loading FYJC data...")
def load_data_v2(csv_path: str) -> pd.DataFrame:
    """Load and preprocess data (cached across Streamlit reruns)."""
    from src.core.loader import FYJCDataLoader
    from src.core.preprocessor import FYJCPreprocessor

    loader = FYJCDataLoader(csv_path=Path(csv_path), use_cache=True)
    raw_df = loader.load()
    return FYJCPreprocessor.quick_clean(raw_df)


# ─── Main App ─────────────────────────────────────────────────────────────────

def main():
    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown('<p class="main-title">🎓 FYJC Cutoff Analyzer</p>', unsafe_allow_html=True)
    st.markdown("**Maharashtra State Board | Class 10 → FYJC Admissions**")
    st.divider()

    # ── CSV Path ──────────────────────────────────────────────────────────────
    csv_path = str(DEFAULT_CSV_PATH)
    default_exists = Path(csv_path).exists()
    round_files = list(Path(csv_path).parent.glob("[Rr]ound_*.csv"))
    if not default_exists and not round_files:
        st.error(
            f"⚠️ CSV file not found: `{csv_path}`\n\n"
            "Place your consolidated CSV at `data/raw/fyjc_cutoff.csv` "
            "or place round-specific CSV files like `Round_1_cutoff_2026-27.csv` in `data/raw/`."
        )
        st.stop()

    # ── Load Data ─────────────────────────────────────────────────────────────
    with st.spinner("Loading dataset..."):
        df = load_data_v2(csv_path)

    st.success(f"✅ Dataset loaded: **{len(df):,} records**")

    # ── Sidebar: User Profile + Filters ───────────────────────────────────────
    with st.sidebar:
        st.header("👤 Your Profile")

        user_marks = st.slider(
            "SSC Marks (%)", min_value=0.0, max_value=100.0,
            value=80.0, step=0.5, format="%.1f%%"
        )

        cat_display = st.selectbox(
            "Reservation Category",
            options=list(CATEGORY_MAP.keys()),
            index=0
        )
        category = CATEGORY_MAP[cat_display]

        st.header("🔍 Filters")

        streams_avail = sorted(df["stream"].dropna().unique().tolist())
        selected_streams = st.multiselect(
            "Stream", options=streams_avail, default=streams_avail[:1]
            if streams_avail else []
        )

        districts_avail = sorted(df["districtid"].dropna().unique().tolist())
        selected_districts = st.multiselect("District", options=districts_avail)

        mediums_avail = sorted(df["medium"].dropna().unique().tolist())
        selected_mediums = st.multiselect("Medium", options=mediums_avail)

        rounds_avail = sorted(df["round_id"].dropna().unique().tolist())
        selected_rounds = st.multiselect(
            "Admission Round", options=rounds_avail,
            format_func=lambda r: f"Round {r}"
        )

        res_details_avail = sorted([str(x) for x in df["ReservationDetails"].dropna().unique().tolist()])
        selected_res_details = st.multiselect(
            "Reservation Details", options=res_details_avail
        )

        area_search = st.text_input("🔎 Area / Locality (type to search)")
        college_name_search = st.text_input("🏫 College Name (type to search)")

        st.subheader("📈 Projection Simulator")
        projected_change = st.slider(
            "Projected Cutoff Inflation/Change",
            min_value=-10.0, max_value=10.0,
            value=0.0, step=0.1,
            format="%+.1f%%",
            help="Simulate an increase/decrease in cutoffs (inflation/deflation) for future rounds."
        )

        st.divider()
        st.caption(f"v1.0.0 | mahafyjc.org.in data")

    # ── Apply Filters ─────────────────────────────────────────────────────────
    from src.analysis.filter_engine import FilterEngine
    from src.analysis.cutoff_analyzer import UserProfile, CutoffAnalyzer

    engine = FilterEngine(df)
    filtered = engine.filter(
        streams             = selected_streams or None,
        districts           = selected_districts or None,
        mediums             = selected_mediums or None,
        round_ids           = selected_rounds or None,
        areas               = [area_search] if area_search else None,
        college_name        = college_name_search or None,
        category            = category,
        reservation_details = selected_res_details or None,
    )

    if filtered.empty:
        st.warning("⚠️ No colleges found with these filters. Try relaxing some criteria.")
        st.stop()

    # ── Analyze ───────────────────────────────────────────────────────────────
    user    = UserProfile(marks=user_marks, category=category,
                          streams=selected_streams, projected_change=projected_change)
    analyzer = CutoffAnalyzer(user)
    results  = analyzer.analyze(filtered, deduplicate=True)

    if results.empty:
        st.warning(f"No cutoff data for category '{category}'. Try a different category.")
        st.stop()

    summary = CutoffAnalyzer.summary(results)

    # ── Summary Metrics ───────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Colleges", f"{summary['total']:,}")
    col2.metric("🟢 Safe", summary['safe'], delta=None)
    col3.metric("🟡 Moderate", summary['moderate'])
    col4.metric("🔴 Dream", summary['dream'])
    col5.metric("Avg Cutoff", f"{summary.get('avg_cutoff', 0):.2f}%")

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏫 College List", "📊 Charts", "📈 Trends", "🔎 Search"
    ])

    with tab1:
        _render_college_table(results, user_marks, category)

    with tab2:
        _render_charts(results, user_marks)

    with tab3:
        _render_trends(df, category, selected_streams)

    with tab4:
        _render_search(df, category)


# ── Tab Renderers ─────────────────────────────────────────────────────────────

def _render_college_table(results: pd.DataFrame, user_marks: float, category: str):
    """Render the main results table with export."""
    st.subheader(f"Results for {category} category | Your marks: {user_marks}%")

    # Filter by classification
    cls_filter = st.radio(
        "Show", ["All", "🟢 Safe", "🟡 Moderate", "🔴 Dream"],
        horizontal=True
    )

    display = results.copy()
    if cls_filter == "🟢 Safe":
        display = display[display["classification"] == "safe"]
    elif cls_filter == "🟡 Moderate":
        display = display[display["classification"] == "moderate"]
    elif cls_filter == "🔴 Dream":
        display = display[display["classification"] == "dream"]

    # Color-code the table
    def color_row(val):
        colors = {"safe": "background-color: #C6EFCE",
                  "moderate": "background-color: #FFEB9C",
                  "dream": "background-color: #FFC7CE"}
        return colors.get(str(val).lower(), "")

    show_cols = ["collegename", "stream", "medium", "districtid",
                 "cutoff", "projected_cutoff", "difference", "classification", "chance_pct", "round_id"]
    show_cols = [c for c in show_cols if c in display.columns]

    styled = display[show_cols].style.map(
        color_row, subset=["classification"]
    ).format({
        "cutoff": "{:.2f}%",
        "projected_cutoff": "{:.2f}%",
        "difference": "{:+.2f}",
        "chance_pct": "{:.0f}%",
    })

    st.dataframe(styled, use_container_width=True, height=500)

    # Export
    if st.button("📥 Export to Excel"):
        from src.utils.exporter import FYJCExporter
        from io import BytesIO
        import io

        exporter = FYJCExporter()
        path = exporter.export(results, user_marks, category)

        with open(path, "rb") as f:
            st.download_button(
                "⬇️ Download Excel File",
                data=f.read(),
                file_name=path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


def _render_charts(results: pd.DataFrame, user_marks: float):
    """Render distribution and comparison charts."""
    st.subheader("📊 Cutoff Distribution")

    if "cutoff" not in results.columns:
        st.info("No cutoff data to chart.")
        return

    col1, col2 = st.columns(2)
    x_col = "projected_cutoff" if "projected_cutoff" in results.columns else "cutoff"

    with col1:
        # Histogram of cutoffs
        fig = px.histogram(
            results, x=x_col, nbins=30,
            title="Projected Cutoff Distribution" if x_col == "projected_cutoff" else "Cutoff Distribution",
            labels={x_col: "Cutoff %", "count": "Colleges"},
            color_discrete_sequence=["#2E75B6"]
        )
        fig.add_vline(x=user_marks, line_dash="dash", line_color="red",
                      annotation_text=f"Your marks: {user_marks}%")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Pie chart: Safe / Moderate / Dream
        cls_counts = results["classification"].value_counts()
        fig2 = px.pie(
            values=cls_counts.values,
            names=cls_counts.index,
            title="College Distribution",
            color=cls_counts.index,
            color_discrete_map={
                "safe": "#00B050",
                "moderate": "#FFC000",
                "dream": "#FF0000",
            }
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Box plot by stream
    if "stream" in results.columns and results["stream"].nunique() > 1:
        fig3 = px.box(
            results, x="stream", y=x_col,
            title="Projected Cutoff Range by Stream" if x_col == "projected_cutoff" else "Cutoff Range by Stream",
            color="stream",
        )
        fig3.add_hline(y=user_marks, line_dash="dash", line_color="red")
        st.plotly_chart(fig3, use_container_width=True)


def _render_trends(df: pd.DataFrame, category: str, streams: list):
    """Render round-by-round trend analysis."""
    from src.analysis.trend_analyzer import TrendAnalyzer

    st.subheader("📈 Cutoff Trends Across Rounds")

    trend = TrendAnalyzer(df)
    stream_arg = streams[0] if len(streams) == 1 else None

    avg_by_round = trend.average_cutoff_by_stream(category)
    if not avg_by_round.empty:
        fig = px.line(
            avg_by_round,
            x="round", y="avg_cutoff", color="stream",
            title=f"Average {category} Cutoff by Round",
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)

    falling = trend.colleges_with_falling_cutoff(category, stream_arg)
    if not falling.empty:
        st.subheader("⬇️ Colleges with Falling Cutoffs (Better Chances!)")
        st.dataframe(falling.head(20), use_container_width=True)


def _render_search(df: pd.DataFrame, category: str):
    """Render college name search."""
    from src.utils.fuzzy_search import build_search_engine
    from src.analysis.cutoff_analyzer import UserProfile, CutoffAnalyzer

    st.subheader("🔎 Search by College Name")
    query = st.text_input("Type college name (partial match supported):")

    if query:
        engine = build_search_engine(df)
        matches = engine.filter_dataframe(df, query, top_n=50)

        if matches.empty:
            st.warning(f"No colleges found matching '{query}'")
        else:
            st.success(f"Found {len(matches)} matching colleges")
            user = UserProfile(marks=75.0, category=category)
            analyzer = CutoffAnalyzer(user)
            analyzed = analyzer.analyze(matches, deduplicate=False)

            show_cols = ["collegename", "stream", "medium", "cutoff",
                         "round_id", "classification"]
            show_cols = [c for c in show_cols if c in analyzed.columns]
            st.dataframe(analyzed[show_cols], use_container_width=True)


if __name__ == "__main__":
    main()
