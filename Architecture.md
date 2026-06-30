# Architecture

How the FYJC Cutoff Analyzer is put together, and why.

## Design goals that shaped everything

Three constraints drove every decision in this codebase:

1. **900k+ rows has to feel instant.** Not "eventually loads" — instant after the first run, fast even on the first run.
2. **The CLI and a future web UI need to share 100% of the logic.** No business logic allowed to leak into `cli.py` or `streamlit_app.py`. If you can't unit-test a behavior without importing a UI module, it's misplaced.
3. **Someone other than me has to be able to add a feature without reading the whole codebase.** Hence strict layering — you should be able to guess which file a feature belongs in from its name alone.

That third constraint is why this isn't one big `analyzer.py` script. It's a deliberate trade of "more files" for "any single file fits in your head."

---

## Layered architecture

```
┌─────────────────────────────────────────────────────────────┐
│  UI LAYER            src/ui/                                │
│  cli.py · streamlit_app.py · prompts.py · display.py        │
│  Owns: user interaction, formatting, menus                  │
│  Knows nothing about: pandas internals, SQL, file formats    │
└───────────────────────────┬───────────────────────────────────┘
                            │ calls
┌───────────────────────────▼───────────────────────────────────┐
│  ANALYSIS LAYER      src/analysis/                            │
│  filter_engine.py · cutoff_analyzer.py · trend_analyzer.py    │
│  Owns: business logic — filtering rules, Safe/Moderate/Dream  │
│  classification, probability scoring, trend math              │
│  Knows nothing about: where data came from, how it'll be shown │
└───────────────────────────┬───────────────────────────────────┘
                            │ operates on
┌───────────────────────────▼───────────────────────────────────┐
│  CORE LAYER          src/core/                                │
│  loader.py · preprocessor.py · database.py                    │
│  Owns: getting raw data into a clean, optimized DataFrame      │
│  Knows nothing about: classification rules, UI                 │
└───────────────────────────┬───────────────────────────────────┘
                            │ produces
                  pandas.DataFrame (the contract)
```

`src/utils/` sits to the side of this stack — `exporter.py`, `fuzzy_search.py`, `helpers.py`, `constants.py` are used by any layer but depend on none of them. `config/settings.py` is the single source of truth for paths, thresholds, and column names; nothing hardcodes a path or a magic number outside that file.

**The rule that keeps this honest:** a clean `pandas.DataFrame` is the only thing that crosses a layer boundary. The UI layer never imports DuckDB. The core layer never imports Rich or Streamlit. This is what makes `cli.py` and `streamlit_app.py` both ~150 lines of orchestration calling the exact same analysis functions — they're two thin shells around one shared core.

---

## Data flow, end to end

```
CSV file (900k+ rows, 169 MB)
       │
       ▼
┌──────────────────┐   first run: chunked pd.read_csv, 100k rows/chunk
│  loader.py        │   later runs: Parquet cache (~9x faster, see below)
└──────┬────────────┘
       │ raw DataFrame, dtypes still loose
       ▼
┌──────────────────┐   drop dead rows, normalize text casing,
│ preprocessor.py   │   clamp 0–100, derive min/max cutoff,
└──────┬────────────┘   cast to category/float32/int8
       │ clean, optimized DataFrame  ◄── this is the shared contract
       ▼
┌──────────────────┐   registers the DataFrame as a DuckDB table
│  database.py       │   (zero-copy — no data duplication)
└──────┬────────────┘
       │
       ▼
┌──────────────────┐   district/region/area/stream/medium/round/category
│ filter_engine.py  │   SQL via DuckDB if available, pandas .isin() fallback
└──────┬────────────┘
       │ filtered DataFrame
       ▼
┌──────────────────┐   pick the user's reservation column as "cutoff",
│cutoff_analyzer.py │   compute difference, classify, score, dedup, sort
└──────┬────────────┘
       │ results DataFrame (collegename, cutoff, difference,
       │                     classification, chance_pct, ...)
       ▼
   ┌────────┴────────┐
   ▼                 ▼
display.py      exporter.py
(terminal table)  (Excel workbook)
```

Every arrow in that diagram is a `DataFrame -> DataFrame` function call. That's intentional — it means `trend_analyzer.py` can consume the output of `preprocessor.py` directly without going through `filter_engine.py` at all, and a future module can splice in anywhere without touching the others.

---

## Why DuckDB *and* pandas, not just one

`database.py` wraps an optional DuckDB connection. `filter_engine.py` checks `db.available` and picks a backend per call — DuckDB when present, plain pandas boolean masking when not. Two reasons this isn't over-engineering:

- **DuckDB registration is zero-copy.** `conn.register("fyjc", df)` doesn't duplicate 900k rows in memory; it lets DuckDB's vectorized engine read the same pandas buffers directly. You get SQL-speed filtering without a second copy of the data sitting around.
- **The fallback isn't theoretical.** DuckDB occasionally fails to install on locked-down or ARM environments. Rather than make it a hard dependency, every DuckDB-path function has a pandas equivalent that produces *identical results*, just slower. The stress test (920k rows) measured DuckDB at 0.64s and pandas at 0.71s for the same district+stream filter — close enough that the fallback is genuinely usable, not just a crash guard.

Area filtering (matching "Mulund" against college names) is **always** done in pandas regardless of backend, because it needs regex/substring logic that's easier to express correctly in Python than to keep correct across two SQL dialects.

---

## Why the loader looks the way it does

`src/core/loader.py` does three things that aren't obvious from a glance and are easy to get wrong:

**Chunked reading.** `pd.read_csv(..., chunksize=100_000)` instead of one `read_csv` call. On a 900k-row file this means peak memory during load is bounded by one chunk, not the whole file — important if this ever runs on a constrained machine. Dtype optimization (see below) is applied *per chunk*, then chunks are concatenated, so the final `pd.concat` only ever holds already-shrunk data.

**Categorical dtypes for low-cardinality columns.** `stream`, `medium`, `districtid`, `regionid`, `status`, `ReservationDetails` become `pandas.Categorical`. These columns have maybe a few dozen distinct values across 900k rows — storing them as Python strings means 900k separate string objects; storing them as categories means 900k small integer codes pointing at one shared lookup table. This single change accounts for most of the ~70% memory reduction mentioned in the README. Cutoff columns (`SC`, `OBC`, `General`, etc.) go from `float64` to `float32` — sub-percentage precision in a 0–100 range doesn't need 64 bits, and that's another 50% on eleven columns.

**Parquet as a cache layer, not a format choice.** First load reads the CSV (slow, ~5s on the 920k-row stress test) and immediately writes a Parquet snapshot. Every subsequent load checks for that Parquet file first. Parquet preserves the categorical/float32 dtypes exactly — no re-inference, no re-optimization — so the second load is ~9x faster (0.59s vs 5.14s measured). This matters most for the Streamlit app, which reruns the load function on every interaction; without the cache check, every filter change would mean a multi-second CSV re-read.

---

## Why classification logic lives where it does

`cutoff_analyzer.py` is deliberately the only place that knows what "Safe" means. The thresholds (`SAFE_THRESHOLD = 5`, `MODERATE_THRESHOLD = -3`) live in `config/settings.py`, not hardcoded in the analyzer — change a number in one file, the CLI table, the Excel export, and the Streamlit charts all update consistently, because they're all reading the same `classification` column the analyzer produced.

`UserProfile` is a `@dataclass` rather than a loose dict of kwargs passed around. Two reasons: it validates marks are 0–100 at construction time (`__post_init__`), failing fast instead of producing silent `NaN` classifications three function calls later; and it gives every function in the analysis layer one typed object to accept instead of five or six separate parameters, which is what made it easy to keep `cli.py`'s `_run_analysis()` and `streamlit_app.py`'s `main()` calling the exact same `CutoffAnalyzer(user).analyze(filtered_df)` line.

The probability score (`chance_pct`) is a documented heuristic, not a model — it's a piecewise linear function of `difference` calibrated to feel right at the boundaries (90% right at the Safe threshold, 50% right at the Moderate threshold). It's isolated in `_estimate_probability()` specifically so it can be swapped for a real model later — e.g. one trained on actual round-to-round admission outcomes — without touching classification or sorting.

---

## What's genuinely missing vs. what's a deliberate non-goal

**Missing, worth adding if you extend this:**
- A `data/raw/` schema validator that runs before `loader.py` even starts, giving a friendlier error than a `KeyError` three modules deep if a column is renamed upstream.
- True year-over-year trends. `trend_analyzer.py` only has `round_id` to work with (1, 2, 3, special round) within a single admission cycle — there's no `year` column in the source data, so "previous year cutoff comparison" from the original feature list is not actually implemented, only round-over-round trending within one year.
- Persistent storage for favorites/saved searches — currently nothing survives a process restart; this would need SQLite (the file is even imported in `requirements.txt` implicitly via DuckDB, but no schema exists for it yet).

**Deliberate non-goals:**
- No ORM, no Alembic migrations — there's exactly one data shape, one read path, and DuckDB is queried directly with f-string-built SQL (see `build_filter_query()`) guarded by basic quote-escaping, not parameterized queries, because the inputs are constrained to values pulled from the dataset's own `unique()` lists, not raw user text reaching the DB layer unfiltered.
- No async/threading anywhere. At this scale (900k rows, sub-second operations once loaded) the complexity cost of async isn't worth it; the only genuinely slow step is the first CSV read, which is a one-time cost solved by caching, not concurrency.

---

## Where to add things

| You want to... | Touch this file | Don't touch |
|---|---|---|
| Change Safe/Moderate/Dream thresholds | `config/settings.py` | `cutoff_analyzer.py` |
| Add a new filter (e.g. by `status`) | `filter_engine.py` (both `_filter_duckdb` and `_filter_pandas`) | UI files |
| Change how probability is scored | `_estimate_probability()` in `cutoff_analyzer.py` | nothing else — it's isolated by design |
| Add a new export format (e.g. PDF) | new file in `src/utils/`, mirror `exporter.py`'s interface | `cutoff_analyzer.py` |
| Add a new CLI menu option | `_main_loop()` + `_ask_action()` in `cli.py` | analysis layer |
| Add the same feature to Streamlit | `streamlit_app.py`, call the same analysis function `cli.py` calls | — |
| Support a differently-named CSV column | `config/settings.py` (`COL_*` constants) | hardcoded strings elsewhere (there shouldn't be any) |