# Madrid Air Quality — Advanced Coding for Data Analytics 2025/2026

A reproducible analytics pipeline for the **METRAQ Air Quality Dataset** (Madrid, 2001–2024), covering data cleaning, imputation comparison, temporal analysis, spatial and correlation networks, parallelised correlation computation, a forecasting model for NO₂, and final visualisation.

---

## Project structure

```
.
├── main.ipynb                 # the full notebook — runs all tasks end-to-end
├── worker.py                  # standalone correlation-matrix worker for Task 8
├── metraq_air_quality.csv     # input data (download separately, see below)
├── requirements.txt           # pinned dependencies
├── README.md                  # this file
├── imputation_results/        # auto-created by Task 3 (per-magnitude parquets)
├── data_by_year/              # auto-created by Task 8 (per-year parquets)
├── correlation_matrices/      # auto-created by Task 8 (per-(year,sensor) matrices)
└── outputs/                   # auto-created by Task 10 (final figures)
```

The `*_results/`, `*_by_year/`, `*_matrices/` and `outputs/` folders are intermediate caches and final figure outputs written by the notebook itself. They will be created on first run; you do not need to set them up manually.

---

## Setup

### 1. Python environment

The pipeline targets Python 3.10 or newer. We recommend a dedicated virtual environment:

```bash
python -m venv venv
source venv/bin/activate           # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Download the dataset

The full dataset (~64 M rows, ~3 GB CSV) is not included in the submission. Download it from Hugging Face:

- <https://huggingface.co/datasets/dmariaa70/METRAQ-Air-Quality>

Place the resulting CSV in the project root and rename it to `metraq_air_quality.csv` if necessary. The notebook expects exactly this filename in the working directory (cell 2 of `main.ipynb`).

To do a quick smoke-test on a smaller file before processing the full 3 GB CSV, you can use the project's `sample_madrid_air_quality.csv` (~100K rows), distributed alongside the spec — just point the `pd.read_csv` call at it.

### 3. Verify

A 30-second smoke test:

```bash
jupyter nbconvert --to notebook --execute main.ipynb \
    --ExecutePreprocessor.timeout=60 \
    --output smoke_test.ipynb
```

If cell 2 (the data load) runs without `FileNotFoundError`, you're set. The full notebook takes roughly 30–60 minutes end-to-end depending on hardware (most of the time is in Task 3's imputation, Task 8's correlation matrices, and Task 9's random forest fit).

---

## Running the notebook

Open `main.ipynb` in Jupyter and run the cells **in order** from top to bottom. The notebook is structured by task, with a section header for each:

- **Task 1** — load and inspect schema, distributions, timeline.
- **Task 2** — quantify missingness and remove physically impossible values (including a wind-speed cap at 30 m/s, since legitimate Madrid wind never exceeds ~28 m/s but the dataset contains a handful of 160 m/s sensor-glitch spikes).
- **Task 3** — compare four imputation methods (METRAQ, Linear interpolation, Linear regression, KNN) via Kolmogorov–Smirnov distance to the real distribution.
- **Task 4** — restore the dataset using a best-of-breed strategy (KNN baseline, per-variable winner override) and analyse temporal patterns at monthly granularity.
- **Task 5** — build spatial graphs of the sensor network using two construction methods (distance threshold and k-nearest neighbours).
- **Task 6** — build correlation networks per pollutant, compare them against the distance-based network, and run a sensitivity sweep.
- **Task 8** — compute hourly correlation matrices for every (year, sensor) combination, sequentially and in parallel using `multiprocessing.Pool` with 1, 2, 4, 8 and 10 workers; report scaling and identify the variables most associated with NO₂.
- **Task 9** *(optional)* — forecast hourly city-wide NO₂ on a held-out 2023 test set using only weather, traffic and calendar features (deliberately no other pollutants and no autoregressive features). Compare a linear regression baseline against a Random Forest to quantify how much of NO₂'s variance is explainable from confounding variables alone.
- **Task 10** — final four-panel visualisation (WHERE / WHEN / HOW / WHY) summarising the headline findings.

Task 7 (propagation modelling) is marked optional in the project spec and is not implemented.

### Why cells must run in order

The pipeline carries state in memory across cells: the cleaned `df` from Task 2, the `missing_df` and `ks_df` produced by Task 3, the imputed `df` from Task 4 Step 1, the `monthly` aggregation built in Task 6 and reused in Task 10, and so on. Restarting the kernel mid-run requires re-executing from the top.

For Task 8 specifically, the parallel section (`from worker import compute_correlation_matrix`) requires `worker.py` to live in the same directory as `main.ipynb` so the worker processes can import it.

---

## Reproducibility notes

- **Random seeds** are set wherever sampling or stochastic fitting is done. The reference distribution for the KS test (Task 3) is sampled with `random_state=42`. The Random Forest in Task 9 is fit with `random_state=42`. All other methods (`LinearRegression`, `KNeighborsRegressor`, `linear` interpolation) are deterministic functions of their input data, so no further seeding is needed.
- **Data caching.** Intermediate parquet files are written to disk once and read back in subsequent steps. This keeps memory flat (~7 M imputed rows would otherwise sit in RAM) and lets you re-run downstream cells without redoing the heavy work. Delete the `imputation_results/`, `data_by_year/` or `correlation_matrices/` folders to force a recompute.
- **Hardware.** All cells run on a machine with ≥8 GB RAM. The Task 8 parallel run uses up to 10 worker processes; on machines with fewer cores, edit the `worker_counts` list in cell 91 to `[1, 2, 4]` or similar. The Task 9 random forest uses `n_jobs=-1` (all cores) with a memory footprint around 100 MB; if RAM is tight, change to `n_jobs=2` in the model-fit cell.

---

## Methodology summary

The full methodology is documented in the markdown cells inside the notebook. A short version:

- **Outlier handling (Task 2).** We NaN out only physically impossible values (negative humidity, sub-vacuum atmospheric pressure, wind speeds above any plausible meteorological value, etc.) and deliberately keep heavy-tailed distributions intact, since pollutants like benzene and CO are zero-inflated by design — sensors read zero most of the time and spike during episodes. Treating those tails as outliers would delete the actual pollution signal.
- **Imputation evaluation (Task 3).** Each method is evaluated *purely*, with no cross-method fallback: where a method cannot produce a value for a row (e.g. linear interpolation on a long gap), we leave the row NaN rather than substituting another method's output. The KS scores therefore measure each method as itself. A separate coverage report quantifies the trade-off between imputation quality (KS) and imputation completeness.
- **Final dataset construction (Task 4 Step 1).** A best-of-breed strategy: every missing row is initialised with its KNN imputation as a universal baseline (KNN has 100% coverage by construction), then overwritten with each variable's winning method (lowest KS in Task 3) wherever that winner produced a value. METRAQ wins ties within 0.01 KS units, since it uses real spatial neighbours that our purely-temporal methods do not access.
- **Parallelisation (Task 8).** Each (year, sensor) correlation matrix is computed by an independent worker process that reads only its own slice of pre-partitioned per-year parquet files and writes the resulting matrix to disk. Speedup, efficiency and scaling vs the sequential baseline are reported.
- **Forecasting (Task 9).** Hourly city-wide NO₂ is predicted from weather (`TEMP`, `HR`, `VV`, `RS`, `PRE`), traffic (`TI/SP/OC_KRIGING`) and calendar features (cyclical hour and month encodings, day-of-week, year). Other pollutants are deliberately excluded from the feature set — including `NOX` would inflate R² to a near-trivial number since `NOX = NO + NO₂` by definition. Train: 2019–2022, test: 2023, no shuffling. Linear regression is the interpretable baseline; Random Forest captures the threshold/interaction effects that linear cannot.

---

## Authors

LUISS — Management and Computer Science, Advanced Coding for Data Analytics 2025/2026.

## Dataset citation

David María-Arribas et al., *METRAQ Air Quality dataset*. <https://huggingface.co/datasets/dmariaa70/METRAQ-Air-Quality>
