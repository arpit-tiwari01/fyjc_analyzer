"""
src/utils/helpers.py
====================
General-purpose utility functions used across modules.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Optional, Union
from functools import wraps

# ─── Logging Setup ────────────────────────────────────────────────────────────

def setup_logger(name: str = "fyjc", log_file: Optional[Path] = None,
                 level: str = "INFO") -> logging.Logger:
    """
    Create and configure a logger with both console and file handlers.

    Args:
        name:     Logger name
        log_file: Path to log file (optional)
        level:    Logging level string ('INFO', 'DEBUG', etc.)

    Returns:
        Configured logging.Logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger  # Already configured

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler (optional)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


# ─── Timing Decorator ─────────────────────────────────────────────────────────

def timer(func):
    """Decorator to measure and print execution time of any function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"  ⏱  {func.__name__} completed in {elapsed:.2f}s")
        return result
    return wrapper


# ─── Marks Validation ─────────────────────────────────────────────────────────

def validate_marks(marks: Union[str, float, int]) -> Optional[float]:
    """
    Validate and convert SSC marks input.

    Args:
        marks: Raw user input for marks (string or numeric)

    Returns:
        Float percentage (0–100) or None if invalid
    """
    try:
        val = float(str(marks).strip())
        if 0.0 <= val <= 100.0:
            return round(val, 2)
        return None
    except (ValueError, TypeError):
        return None


# ─── Safe Column Access ───────────────────────────────────────────────────────

def safe_get_column(df, col: str, default=None):
    """
    Safely get a DataFrame column, returning default if missing.

    Args:
        df:      pandas DataFrame
        col:     Column name
        default: Value to return if column not found

    Returns:
        pd.Series or default
    """
    return df[col] if col in df.columns else default


# ─── Memory Usage Reporter ────────────────────────────────────────────────────

def memory_usage_mb(df) -> float:
    """
    Return memory usage of a DataFrame in megabytes.

    Args:
        df: pandas DataFrame

    Returns:
        Memory in MB (float)
    """
    return df.memory_usage(deep=True).sum() / (1024 ** 2)


# ─── File Size Reporter ───────────────────────────────────────────────────────

def file_size_mb(path: Path) -> float:
    """Return file size in MB."""
    return path.stat().st_size / (1024 ** 2) if path.exists() else 0.0


# ─── Normalize Strings ────────────────────────────────────────────────────────

def normalize_str(s: str) -> str:
    """Lowercase, strip, and normalize whitespace."""
    return " ".join(str(s).lower().strip().split())


# ─── Pluralize ────────────────────────────────────────────────────────────────

def pluralize(count: int, singular: str, plural: str = None) -> str:
    """Return singular/plural based on count."""
    if plural is None:
        plural = singular + "s"
    return f"{count} {singular if count == 1 else plural}"


# ─── Format Percentage ────────────────────────────────────────────────────────

def fmt_pct(val) -> str:
    """Format a float as a percentage string."""
    try:
        return f"{float(val):.2f}%"
    except (TypeError, ValueError):
        return "N/A"


# ─── Difference Indicator ─────────────────────────────────────────────────────

def fmt_diff(diff: float) -> str:
    """Format the mark difference with a visual indicator."""
    if diff >= 5:
        return f"+{diff:.2f} ✅"
    elif diff >= -3:
        return f"{diff:+.2f} ⚠️"
    else:
        return f"{diff:.2f} ❌"
