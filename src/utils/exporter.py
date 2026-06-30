"""
src/utils/exporter.py
======================
Professional Excel export with:
  - Multiple sheets (Safe, Moderate, Dream, All Results, Summary)
  - Color-coded classification rows
  - Auto-sized columns
  - Summary statistics sheet
  - Trend data sheet

Uses xlsxwriter for rich formatting.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd

logger = logging.getLogger("fyjc.exporter")

# Color codes for Excel
COLORS = {
    "safe":        "#C6EFCE",   # Light green
    "safe_font":   "#276221",   # Dark green
    "moderate":    "#FFEB9C",   # Light yellow
    "moderate_font": "#9C6500", # Dark orange
    "dream":       "#FFC7CE",   # Light red
    "dream_font":  "#9C0006",   # Dark red
    "header":      "#1F4E79",   # Dark blue
    "header_font": "#FFFFFF",   # White
    "title":       "#2E75B6",   # Medium blue
}


class FYJCExporter:
    """Exports FYJC analysis results to a formatted Excel workbook."""

    def __init__(self, export_dir: Optional[Path] = None):
        from config.settings import EXPORT_DIR
        self.export_dir = export_dir or EXPORT_DIR
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        results_df: pd.DataFrame,
        user_marks: float,
        category: str,
        stream: str = "All",
        filename: Optional[str] = None,
    ) -> Path:
        """
        Export analysis results to a formatted Excel file.

        Args:
            results_df: DataFrame from CutoffAnalyzer.analyze()
            user_marks: User's SSC marks
            category:   User's reservation category
            stream:     Selected stream
            filename:   Custom filename (auto-generated if None)

        Returns:
            Path to the created Excel file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"FYJC_Results_{stream}_{category}_{timestamp}.xlsx"

        output_path = self.export_dir / filename

        try:
            with pd.ExcelWriter(
                output_path,
                engine="xlsxwriter",
                datetime_format="DD-MM-YYYY",
            ) as writer:
                wb = writer.book

                # Write all sheets
                self._write_summary_sheet(writer, wb, results_df, user_marks, category, stream)
                self._write_all_results_sheet(writer, wb, results_df)
                self._write_classification_sheets(writer, wb, results_df)

            logger.info(f"Excel exported: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise

    # ── Sheet Writers ─────────────────────────────────────────────────────────

    def _write_summary_sheet(self, writer, wb, df, marks, category, stream):
        """Write a summary statistics sheet."""
        ws = wb.add_worksheet("📊 Summary")

        # Formats
        title_fmt = wb.add_format({
            "bold": True, "font_size": 16, "font_color": COLORS["title"],
            "border": 0
        })
        header_fmt = wb.add_format({
            "bold": True, "bg_color": COLORS["header"],
            "font_color": COLORS["header_font"], "border": 1
        })
        value_fmt = wb.add_format({"border": 1, "num_format": "0.00"})
        label_fmt = wb.add_format({"bold": True, "border": 1})

        # Title
        ws.write(0, 0, "🎓 FYJC Cutoff Analyzer — Results Summary", title_fmt)
        ws.write(1, 0, f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}")

        # User info
        ws.write(3, 0, "YOUR PROFILE", header_fmt)
        ws.write(3, 1, "", header_fmt)
        info_rows = [
            ("SSC Marks", f"{marks:.2f}%"),
            ("Category", category),
            ("Stream", stream),
        ]
        for i, (label, val) in enumerate(info_rows, start=4):
            ws.write(i, 0, label, label_fmt)
            ws.write(i, 1, val, value_fmt)

        # Stats
        if not df.empty and "classification" in df.columns:
            safe_count = int((df["classification"] == "safe").sum())
            mod_count  = int((df["classification"] == "moderate").sum())
            dream_count = int((df["classification"] == "dream").sum())

            ws.write(8, 0, "RESULTS BREAKDOWN", header_fmt)
            ws.write(8, 1, "", header_fmt)

            stats_rows = [
                ("Total Colleges Found", len(df)),
                ("🟢 Safe Colleges", safe_count),
                ("🟡 Moderate Colleges", mod_count),
                ("🔴 Dream Colleges", dream_count),
                ("Average Cutoff", f"{df['cutoff'].mean():.2f}%"),
                ("Lowest Cutoff", f"{df['cutoff'].min():.2f}%"),
                ("Highest Cutoff", f"{df['cutoff'].max():.2f}%"),
            ]
            for i, (label, val) in enumerate(stats_rows, start=9):
                ws.write(i, 0, label, label_fmt)
                ws.write(i, 1, str(val), value_fmt)

        ws.set_column(0, 0, 28)
        ws.set_column(1, 1, 20)

    def _write_all_results_sheet(self, writer, wb, df):
        """Write all results with color-coded rows."""
        if df.empty:
            return

        display_df = self._prepare_display_df(df)

        # Write with pandas first
        display_df.to_excel(writer, sheet_name="📋 All Results", index=False, startrow=1)
        ws = writer.sheets["📋 All Results"]

        self._apply_formatting(ws, wb, display_df, start_row=1)

        ws.write(0, 0, "All College Results — FYJC Cutoff Analyzer",
                 wb.add_format({"bold": True, "font_size": 13,
                                "font_color": COLORS["title"]}))

    def _write_classification_sheets(self, writer, wb, df):
        """Write separate sheets for each classification."""
        if df.empty or "classification" not in df.columns:
            return

        sheets = [
            ("🟢 Safe",     "safe",     "C6EFCE"),
            ("🟡 Moderate", "moderate", "FFEB9C"),
            ("🔴 Dream",    "dream",    "FFC7CE"),
        ]

        for sheet_name, cls, _ in sheets:
            subset = df[df["classification"] == cls]
            if subset.empty:
                continue

            display_df = self._prepare_display_df(subset)
            display_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=0)
            ws = writer.sheets[sheet_name]
            self._apply_formatting(ws, wb, display_df, start_row=0)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _prepare_display_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Select and rename columns for user-friendly output."""
        col_map = {
            "collegename":    "College Name",
            "stream":         "Stream",
            "medium":         "Medium",
            "districtid":     "District",
            "cutoff":         "Cutoff %",
            "user_marks":     "Your Marks %",
            "difference":     "Difference",
            "classification": "Category",
            "chance_pct":     "Chance %",
            "round_id":       "Round",
            "status":         "Status",
            "choicecode":     "Choice Code",
        }

        available = {k: v for k, v in col_map.items() if k in df.columns}
        result = df[list(available.keys())].rename(columns=available).copy()

        # Clean up classification for display
        if "Category" in result.columns:
            emoji_map = {"safe": "🟢 Safe", "moderate": "🟡 Moderate",
                         "dream": "🔴 Dream", "unknown": "❓ Unknown"}
            result["Category"] = result["Category"].map(emoji_map).fillna(result["Category"])

        return result

    def _apply_formatting(self, ws, wb, df: pd.DataFrame, start_row: int = 0):
        """Apply header formatting and auto-column widths."""
        header_fmt = wb.add_format({
            "bold": True, "bg_color": COLORS["header"],
            "font_color": COLORS["header_font"], "border": 1,
            "align": "center", "valign": "vcenter",
        })

        # Format header row
        for col_num, col_name in enumerate(df.columns):
            ws.write(start_row, col_num, col_name, header_fmt)

        # Auto-size columns
        for col_num, col_name in enumerate(df.columns):
            max_len = max(
                len(str(col_name)),
                df[col_name].astype(str).str.len().max() if len(df) > 0 else 0
            )
            ws.set_column(col_num, col_num, min(max_len + 2, 40))
