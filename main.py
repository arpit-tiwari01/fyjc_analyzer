"""
main.py
=======
Entry point for the FYJC Cutoff Analyzer.

Usage:
    python main.py                          # Use default CSV path
    python main.py --csv data/raw/my.csv   # Specify custom CSV path
    python main.py --demo                  # Run with generated demo data

For Streamlit web UI:
    streamlit run src/ui/streamlit_app.py
"""

import sys
import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="🎓 FYJC Cutoff Analyzer — Maharashtra State Board",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --csv /path/to/fyjc_data.csv
  python main.py --demo
        """
    )
    parser.add_argument(
        "--csv", type=Path, default=None,
        help="Path to FYJC cutoff CSV file"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Generate and use demo data (for testing without real CSV)"
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Show version and exit"
    )
    return parser.parse_args()


def generate_demo_data() -> Path:
    """
    Generate a synthetic demo CSV with ~10,000 rows for testing.
    Mimics the structure of the real FYJC dataset.

    Returns:
        Path to the generated CSV file
    """
    import pandas as pd
    import numpy as np
    import random
    from config.settings import RAW_DATA_DIR

    print("🔧 Generating demo data...")

    random.seed(42)
    np.random.seed(42)

    n = 10_000  # Demo: 10k rows (real data: ~900k)

    # Sample college names (Mumbai + Pune focus)
    college_prefixes = [
        "Shree", "Smt.", "Dr.", "Pt.", "R.D.", "K.C.",
        "S.M.", "N.S.", "Vivekanand", "Gokhale", "Tilak",
        "Chhatrapati", "Rajmata", "Elphinstone", "Wilson",
    ]
    college_suffixes = [
        "Junior College", "College of Arts & Science",
        "College of Commerce", "Vidyalaya", "Institute",
    ]
    areas = ["Mulund", "Thane", "Bhandup", "Airoli", "Kalwa",
             "Ghatkopar", "Dadar", "Andheri", "Borivali", "Pune"]

    def rand_college():
        return (
            f"{random.choice(college_prefixes)} "
            f"{random.choice(areas)} "
            f"{random.choice(college_suffixes)}"
        )

    unique_colleges = [rand_college() for _ in range(500)]
    college_names   = [random.choice(unique_colleges) for _ in range(n)]

    streams     = np.random.choice(["Science", "Commerce", "Arts"], n, p=[0.4, 0.35, 0.25])
    mediums     = np.random.choice(["English", "Marathi", "Semi-English"], n, p=[0.5, 0.3, 0.2])
    districts   = np.random.choice(["Mumbai", "Thane", "Pune", "Nashik", "Nagpur"], n)
    regions     = np.random.choice(["Konkan", "Nashik", "Pune", "Aurangabad", "Amravati", "Nagpur"], n)
    rounds      = np.random.choice([1, 2, 3], n, p=[0.4, 0.35, 0.25])
    statuses    = np.random.choice(["G", "A", "U"], n, p=[0.3, 0.4, 0.3])

    def base_cutoff():
        return round(random.uniform(55.0, 95.0), 2)

    base = [base_cutoff() for _ in range(n)]
    noise = lambda: round(random.uniform(-5.0, 5.0), 2)

    df = pd.DataFrame({
        "id":               range(1, n + 1),
        "districtid":       districts,
        "regionid":         regions,
        "udise":            [f"2720{random.randint(10000, 99999)}" for _ in range(n)],
        "collegename":      college_names,
        "stream":           streams,
        "status":           statuses,
        "medium":           mediums,
        "subject":          np.random.choice(["General", "Science", "Commerce", "Arts"], n),
        "choicecode":       [f"{random.randint(10000, 99999)}" for _ in range(n)],
        "ReservationDetails": np.random.choice(["Open", "Reserved"], n),
        "SC":               [max(0, b + noise()) for b in base],
        "ST":               [max(0, b + noise() - 2) for b in base],
        "VJA":              [max(0, b + noise()) for b in base],
        "NTB":              [max(0, b + noise()) for b in base],
        "NTC":              [max(0, b + noise()) for b in base],
        "NTD":              [max(0, b + noise()) for b in base],
        "OBC":              [max(0, b + noise()) for b in base],
        "SBC":              [max(0, b + noise()) for b in base],
        "SEBC":             [max(0, b + noise()) for b in base],
        "EWS":              [max(0, b + noise()) for b in base],
        "General":          [min(100, b + abs(noise())) for b in base],
        "round_id":         rounds,
    })

    # Introduce realistic NaN values (not all categories available everywhere)
    for col in ["VJA", "NTB", "NTC", "NTD", "SBC"]:
        mask = np.random.random(n) < 0.3
        df.loc[mask, col] = None

    demo_path = RAW_DATA_DIR / "fyjc_demo.csv"
    df.to_csv(demo_path, index=False)
    print(f"✅ Demo data generated: {demo_path} ({n:,} rows)")
    return demo_path


def main():
    args = parse_args()

    if args.version:
        from config.settings import APP_VERSION
        print(f"FYJC Cutoff Analyzer v{APP_VERSION}")
        sys.exit(0)

    csv_path = None

    if args.demo:
        csv_path = generate_demo_data()
    elif args.csv:
        csv_path = args.csv

    # Add project root to path
    sys.path.insert(0, str(Path(__file__).parent))

    from src.ui.cli import run
    run(csv_path=csv_path)


if __name__ == "__main__":
    main()
