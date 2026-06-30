"""
src/ui/prompts.py
=================
Interactive prompts for collecting user input.

Uses `questionary` for beautiful, keyboard-navigable prompts.
Falls back to standard input() if questionary is not available.

Functions return validated, cleaned values ready for analysis.
"""

import logging
from typing import List, Optional, Tuple
import sys

logger = logging.getLogger("fyjc.prompts")

try:
    import questionary
    from questionary import Style as QStyle
    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False
    logger.warning("questionary not installed. Using plain input() prompts.")

from src.utils.constants import (
    STREAM_DISPLAY, CATEGORY_MAP, ALL_CATEGORIES,
    MEDIUMS, GENDER_OPTIONS, ALL_AREAS, ROUNDS
)
from src.utils.helpers import validate_marks

# ─── Custom Style ─────────────────────────────────────────────────────────────
PROMPT_STYLE = None
if QUESTIONARY_AVAILABLE:
    PROMPT_STYLE = QStyle([
        ("qmark",        "fg:#ff9d00 bold"),
        ("question",     "bold"),
        ("answer",       "fg:#ff9d00 bold"),
        ("pointer",      "fg:#ff9d00 bold"),
        ("highlighted",  "fg:#ff9d00 bold"),
        ("selected",     "fg:#cc5454"),
        ("separator",    "fg:#cc5454"),
        ("instruction",  ""),
        ("text",         ""),
    ])


# ─── Marks Input ──────────────────────────────────────────────────────────────

def ask_marks() -> float:
    """
    Prompt user for SSC marks.

    Returns:
        Validated float between 0 and 100
    """
    while True:
        if QUESTIONARY_AVAILABLE:
            raw = questionary.text(
                "Enter your SSC marks (in %):",
                default="85.00",
                style=PROMPT_STYLE,
                validate=lambda x: (
                    "Please enter a number between 0 and 100"
                    if validate_marks(x) is None
                    else True
                )
            ).ask()
        else:
            raw = input("Enter your SSC marks (%): ").strip()

        if raw is None:  # User pressed Ctrl+C
            sys.exit(0)

        marks = validate_marks(raw)
        if marks is not None:
            return marks

        print("❌ Invalid marks. Please enter a number between 0 and 100.")


# ─── Category Selection ───────────────────────────────────────────────────────

def ask_category() -> str:
    """
    Prompt user to select their reservation category.

    Returns:
        Column name (e.g., 'General', 'OBC', 'SC')
    """
    choices = list(CATEGORY_MAP.keys())

    if QUESTIONARY_AVAILABLE:
        selected = questionary.select(
            "Select your reservation category:",
            choices=choices,
            style=PROMPT_STYLE,
            default="General (Open)",
        ).ask()
    else:
        print("\nReservation Categories:")
        for i, c in enumerate(choices, 1):
            print(f"  {i}. {c}")
        while True:
            raw = input("Enter number: ").strip()
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(choices):
                    selected = choices[idx]
                    break
            except ValueError:
                pass
            print("Invalid choice. Try again.")

    if selected is None:
        sys.exit(0)

    return CATEGORY_MAP[selected]   # Return column name, not display name


# ─── Stream Selection ─────────────────────────────────────────────────────────

def ask_streams(available_streams: Optional[List[str]] = None) -> List[str]:
    """
    Prompt user to select preferred streams (multi-select).

    Args:
        available_streams: Streams actually present in the dataset

    Returns:
        List of selected stream names
    """
    choices = available_streams or STREAM_DISPLAY

    if QUESTIONARY_AVAILABLE:
        selected = questionary.checkbox(
            "Select preferred streams (Space to select, Enter to confirm):",
            choices=choices,
            style=PROMPT_STYLE,
        ).ask()
    else:
        print("\nStreams (leave blank for all):")
        for i, s in enumerate(choices, 1):
            print(f"  {i}. {s}")
        raw = input("Enter numbers separated by comma (e.g. 1,2): ").strip()
        if not raw:
            return []
        selected = []
        for part in raw.split(","):
            try:
                idx = int(part.strip()) - 1
                if 0 <= idx < len(choices):
                    selected.append(choices[idx])
            except ValueError:
                pass

    if selected is None:
        sys.exit(0)

    return selected if selected else []


# ─── Area Selection ───────────────────────────────────────────────────────────

def ask_areas() -> List[str]:
    """
    Prompt user to select preferred areas/localities.

    Returns:
        List of area name strings
    """
    if QUESTIONARY_AVAILABLE:
        # First ask if they want area filter at all
        want_area = questionary.confirm(
            "Do you want to filter by specific area/locality?",
            default=False,
            style=PROMPT_STYLE,
        ).ask()

        if not want_area:
            return []

        selected = questionary.checkbox(
            "Select preferred areas:",
            choices=ALL_AREAS,
            style=PROMPT_STYLE,
        ).ask()
    else:
        raw = input("Enter areas (comma-separated, or blank for all): ").strip()
        if not raw:
            return []
        selected = [a.strip() for a in raw.split(",") if a.strip()]

    return selected if selected else []


# ─── Medium Selection ─────────────────────────────────────────────────────────

def ask_medium(available_mediums: Optional[List[str]] = None) -> List[str]:
    """
    Prompt user to select preferred medium of instruction.

    Returns:
        List of selected medium names (empty = all mediums)
    """
    choices = available_mediums or MEDIUMS

    if QUESTIONARY_AVAILABLE:
        want = questionary.confirm(
            "Filter by medium of instruction?",
            default=False,
            style=PROMPT_STYLE,
        ).ask()

        if not want:
            return []

        selected = questionary.checkbox(
            "Select preferred mediums:",
            choices=choices,
            style=PROMPT_STYLE,
        ).ask()
    else:
        raw = input("Mediums (comma-separated, or blank for all): ").strip()
        selected = [m.strip() for m in raw.split(",") if m.strip()] if raw else []

    return selected if selected else []


# ─── Round Selection ──────────────────────────────────────────────────────────

def ask_rounds(available_rounds: Optional[List[int]] = None) -> List[int]:
    """
    Prompt user to select admission round(s).

    Returns:
        List of round IDs (empty = all rounds)
    """
    round_choices = [
        f"Round {r}" + (f" — {ROUNDS.get(r, '')}" if r in ROUNDS else "")
        for r in (available_rounds or list(ROUNDS.keys()))
    ]

    if QUESTIONARY_AVAILABLE:
        want = questionary.confirm(
            "Filter by specific admission round?",
            default=False,
            style=PROMPT_STYLE,
        ).ask()

        if not want:
            return []

        selected = questionary.checkbox(
            "Select rounds:",
            choices=round_choices,
            style=PROMPT_STYLE,
        ).ask()
    else:
        raw = input("Rounds (comma-separated numbers, or blank for all): ").strip()
        if not raw:
            return []
        selected = [f"Round {r.strip()}" for r in raw.split(",") if r.strip().isdigit()]

    if not selected:
        return []

    # Extract round numbers
    rounds = []
    for s in selected:
        try:
            num = int(s.split("Round ")[-1].split(" ")[0])
            rounds.append(num)
        except (ValueError, IndexError):
            pass
    return rounds


# ─── District Selection ───────────────────────────────────────────────────────

def ask_districts(available_districts: List[str]) -> List[str]:
    """
    Prompt user to select districts.

    Returns:
        List of selected district names (empty = all)
    """
    if not available_districts:
        return []

    if QUESTIONARY_AVAILABLE:
        want = questionary.confirm(
            "Filter by specific district?",
            default=False,
            style=PROMPT_STYLE,
        ).ask()

        if not want:
            return []

        selected = questionary.checkbox(
            "Select districts:",
            choices=sorted(available_districts)[:30],  # Limit for readability
            style=PROMPT_STYLE,
        ).ask()
    else:
        raw = input("Districts (comma-separated, or blank for all): ").strip()
        selected = [d.strip() for d in raw.split(",") if d.strip()] if raw else []

    return selected if selected else []


# ─── Collect Full Profile ─────────────────────────────────────────────────────

def collect_user_profile(
    available_streams: Optional[List[str]] = None,
    available_districts: Optional[List[str]] = None,
    available_mediums: Optional[List[str]] = None,
    available_rounds: Optional[List[int]] = None,
) -> dict:
    """
    Run the full interactive prompt sequence to collect all user preferences.

    Returns:
        dict with keys: marks, category, streams, areas, mediums,
                        districts, round_ids
    """
    from src.ui.display import print_section

    print_section("Your Profile", "👤")

    marks    = ask_marks()
    category = ask_category()
    streams  = ask_streams(available_streams)
    areas    = ask_areas()
    mediums  = ask_medium(available_mediums)
    districts = ask_districts(available_districts or [])
    rounds   = ask_rounds(available_rounds)

    return {
        "marks":      marks,
        "category":   category,
        "streams":    streams,
        "areas":      areas,
        "mediums":    mediums,
        "districts":  districts,
        "round_ids":  rounds if rounds else None,
    }
