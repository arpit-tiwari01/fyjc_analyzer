# 🎓 FYJC Cutoff Analyzer
### Maharashtra State Board | Class 10 → FYJC Admissions Tool

A **production-quality** Python application to analyze FYJC (First Year Junior College) cutoff data for Maharashtra admissions via **mahafyjc.org.in**.

---

## 📁 Project Structure

```
fyjc_analyzer/
├── data/
│   ├── raw/                    # Place your CSV files here
│   ├── processed/              # Parquet cache for fast re-loading
│   └── exports/                # Excel/CSV exports go here
├── src/
│   ├── core/
│   │   ├── loader.py           # Data loading with memory optimization
│   │   ├── preprocessor.py     # Cleaning, dtypes, normalization
│   │   └── database.py         # DuckDB / SQLite integration
│   ├── analysis/
│   │   ├── filter_engine.py    # Multi-criteria filtering
│   │   ├── cutoff_analyzer.py  # Core analysis: Safe/Moderate/Dream
│   │   ├── trend_analyzer.py   # Year-over-year trend analysis
│   │   └── probability.py      # Admission probability estimation
│   ├── ui/
│   │   ├── cli.py              # Rich terminal UI (main entry point)
│   │   ├── prompts.py          # User input prompts
│   │   └── display.py          # Tables, colors, formatting
│   └── utils/
│       ├── constants.py        # All constants: categories, streams, etc.
│       ├── exporter.py         # Excel / CSV export
│       ├── fuzzy_search.py     # Fuzzy college name search
│       └── helpers.py          # Utility functions
├── config/
│   └── settings.py             # App-wide configuration
├── tests/                      # Unit tests
├── logs/                       # Application logs
├── notebooks/                  # Jupyter notebooks for exploration
├── main.py                     # Entry point
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Place your CSV file in data/raw/
cp your_fyjc_data.csv data/raw/

# 3. Run the analyzer
python main.py

# 4. (Optional) Launch Streamlit web UI
streamlit run src/ui/streamlit_app.py
```

---

## ⚡ Performance Features

| Feature | Benefit |
|---|---|
| Categorical dtypes | ~70% memory reduction |
| Parquet cache | 10x faster reload after first run |
| DuckDB engine | SQL on 1M+ rows in milliseconds |
| Chunked reading | Handles files > available RAM |
| Polars option | Optional ultra-fast processing |

---

## 📊 Classification Logic

| Category | Condition |
|---|---|
| 🟢 **Safe** | User marks ≥ Cutoff + 5 |
| 🟡 **Moderate** | Cutoff - 3 ≤ User marks < Cutoff + 5 |
| 🔴 **Dream** | User marks < Cutoff - 3 |

---

## 🔮 Roadmap

- [x] Core CLI analyzer
- [x] Excel export
- [x] Fuzzy college search
- [x] DuckDB integration
- [ ] Streamlit web dashboard
- [ ] Cutoff trend graphs (Plotly)
- [ ] Nearby college suggestions (geolocation)
- [ ] Favorites list
- [ ] Mobile-friendly UI
