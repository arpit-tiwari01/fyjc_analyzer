"""
src/ui/display.py
=================
Rich terminal display module.
Handles all output formatting: tables, banners, progress, colors.

All display functions use the `rich` library for beautiful terminal output.
"""

from typing import Optional
import pandas as pd

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from rich.columns import Columns
    from rich import box
    from rich.style import Style
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console()

# ─── Color mapping for classifications ────────────────────────────────────────
CLASS_STYLES = {
    "safe":     "bold green",
    "moderate": "bold yellow",
    "dream":    "bold red",
    "unknown":  "dim",
}

CLASS_EMOJI = {
    "safe":     "🟢 Safe",
    "moderate": "🟡 Moderate",
    "dream":    "🔴 Dream",
    "unknown":  "❓",
}


# ─── Banner ───────────────────────────────────────────────────────────────────

def print_banner():
    """Print the application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║          🎓  FYJC CUTOFF ANALYZER  v1.0.0                   ║
║       Maharashtra State Board | Class 10 → FYJC             ║
║             Powered by mahafyjc.org.in Data                  ║
╚══════════════════════════════════════════════════════════════╝"""
    if RICH_AVAILABLE:
        console.print(Panel(banner, style="bold blue", expand=False))
    else:
        print(banner)


# ─── Section Headers ──────────────────────────────────────────────────────────

def print_section(title: str, emoji: str = "📌"):
    """Print a styled section header."""
    if RICH_AVAILABLE:
        console.rule(f"[bold cyan]{emoji} {title}[/bold cyan]")
    else:
        print(f"\n{'='*60}\n{emoji} {title}\n{'='*60}")


def print_success(message: str):
    """Print a success message."""
    if RICH_AVAILABLE:
        console.print(f"[bold green]✅ {message}[/bold green]")
    else:
        print(f"✅ {message}")


def print_warning(message: str):
    """Print a warning message."""
    if RICH_AVAILABLE:
        console.print(f"[bold yellow]⚠️  {message}[/bold yellow]")
    else:
        print(f"⚠️  {message}")


def print_error(message: str):
    """Print an error message."""
    if RICH_AVAILABLE:
        console.print(f"[bold red]❌ {message}[/bold red]")
    else:
        print(f"❌ {message}")


def print_info(message: str):
    """Print an info message."""
    if RICH_AVAILABLE:
        console.print(f"[cyan]ℹ️  {message}[/cyan]")
    else:
        print(f"ℹ️  {message}")


# ─── Results Table ────────────────────────────────────────────────────────────

def print_results_table(df: pd.DataFrame, max_rows: int = 50,
                        user_marks: Optional[float] = None):
    """
    Print a beautiful Rich table of FYJC analysis results.

    Args:
        df:         Results DataFrame from CutoffAnalyzer
        max_rows:   Maximum rows to display
        user_marks: User's marks (for header reference)
    """
    if df.empty:
        print_warning("No colleges found matching your criteria.")
        return

    display_df = df.head(max_rows)

    if RICH_AVAILABLE:
        _print_rich_table(display_df, user_marks)
    else:
        _print_plain_table(display_df)

    if len(df) > max_rows:
        print_info(f"Showing {max_rows} of {len(df)} total colleges. Export to Excel to see all.")


def _print_rich_table(df: pd.DataFrame, user_marks: Optional[float]):
    """Render a Rich Table with color-coded rows."""
    table = Table(
        title=f"🎓 FYJC College Results" +
              (f" | Your Marks: [bold]{user_marks}%[/bold]" if user_marks else ""),
        box=box.ROUNDED,
        show_header=True,
        header_style="bold white on dark_blue",
        show_lines=True,
        expand=False,
    )

    # ── Column definitions ────────────────────────────────────────────────
    col_defs = [
        ("collegename",    "College Name",    "left",   30),
        ("stream",         "Stream",          "center", 10),
        ("medium",         "Medium",          "center", 10),
        ("cutoff",         "Cutoff %",        "right",  9),
        ("difference",     "Diff",            "right",  8),
        ("classification", "Category",        "center", 12),
        ("chance_pct",     "Chance",          "center", 8),
        ("round_id",       "Round",           "center", 6),
    ]

    for col, header, justify, width in col_defs:
        if col in df.columns:
            table.add_column(header, justify=justify, max_width=width, no_wrap=False)

    # ── Rows ──────────────────────────────────────────────────────────────
    for _, row in df.iterrows():
        cls = str(row.get("classification", "unknown")).lower()
        style = CLASS_STYLES.get(cls, "")

        cells = []
        for col, *_ in col_defs:
            if col not in df.columns:
                continue
            val = row[col]

            if col == "classification":
                cells.append(CLASS_EMOJI.get(cls, str(val)))
            elif col == "difference":
                diff = float(val) if pd.notna(val) else 0
                sign = "+" if diff >= 0 else ""
                cells.append(f"{sign}{diff:.2f}")
            elif col in ("cutoff", "user_marks"):
                cells.append(f"{float(val):.2f}%" if pd.notna(val) else "N/A")
            elif col == "chance_pct":
                cells.append(f"{int(val)}%" if pd.notna(val) else "N/A")
            else:
                cells.append(str(val) if pd.notna(val) else "—")

        table.add_row(*cells, style=style)

    console.print(table)


def _print_plain_table(df: pd.DataFrame):
    """Plain text fallback table (no Rich)."""
    cols = ["collegename", "stream", "cutoff", "difference", "classification"]
    cols = [c for c in cols if c in df.columns]
    print(df[cols].to_string(index=False))


# ─── Summary Panel ────────────────────────────────────────────────────────────

def print_summary(summary: dict, user_marks: float, category: str):
    """Print a summary statistics panel."""
    if not summary:
        return

    text = (
        f"📊 Total Colleges: [bold]{summary.get('total', 0)}[/bold]\n"
        f"🟢 Safe:          [bold green]{summary.get('safe', 0)}[/bold green]\n"
        f"🟡 Moderate:      [bold yellow]{summary.get('moderate', 0)}[/bold yellow]\n"
        f"🔴 Dream:         [bold red]{summary.get('dream', 0)}[/bold red]\n"
        f"──────────────────────────────\n"
        f"📈 Avg Cutoff:    [cyan]{summary.get('avg_cutoff', 'N/A')}%[/cyan]\n"
        f"⬇️  Min Cutoff:    [cyan]{summary.get('min_cutoff', 'N/A')}%[/cyan]\n"
        f"⬆️  Max Cutoff:    [cyan]{summary.get('max_cutoff', 'N/A')}%[/cyan]\n"
        f"──────────────────────────────\n"
        f"🎯 Your Marks:    [bold]{user_marks}%[/bold]  |  Category: [bold]{category}[/bold]"
    )

    if RICH_AVAILABLE:
        console.print(Panel(text, title="📋 Analysis Summary", border_style="cyan"))
    else:
        print("\n" + summary.__repr__())


# ─── Loading Spinner ──────────────────────────────────────────────────────────

def get_spinner(description: str = "Loading data..."):
    """Return a Rich Progress spinner context manager."""
    if RICH_AVAILABLE:
        return Progress(
            SpinnerColumn(),
            TextColumn("[cyan]{task.description}"),
            TimeElapsedColumn(),
            transient=True,
        )
    return None


# ─── Data Load Stats ──────────────────────────────────────────────────────────

def print_load_stats(row_count: int, col_count: int, memory_mb: float,
                     load_time: float):
    """Print data loading statistics."""
    if RICH_AVAILABLE:
        text = (
            f"📂 Rows:    [bold]{row_count:,}[/bold]\n"
            f"📊 Columns: [bold]{col_count}[/bold]\n"
            f"💾 Memory:  [bold]{memory_mb:.1f} MB[/bold]\n"
            f"⏱  Load time: [bold]{load_time:.2f}s[/bold]"
        )
        console.print(Panel(text, title="📦 Data Loaded", border_style="green"))
    else:
        print(f"Loaded {row_count:,} rows in {load_time:.2f}s ({memory_mb:.1f} MB)")
