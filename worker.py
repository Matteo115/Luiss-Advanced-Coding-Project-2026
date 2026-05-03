import pandas as pd
import os


def compute_correlation_matrix(args):
    """
    Worker function for parallel execution.

    For one (year, sensor) pair:
      1. Read only that year's parquet file from disk (workers do not share
         the global df — each one loads its own slice to keep memory low).
      2. Filter to the requested sensor.
      3. Pivot to wide format (one column per variable, one row per timestamp).
      4. Compute the Pearson correlation matrix between variables, requiring
         at least 24 overlapping non-null hours per pair.
      5. Save the resulting matrix to disk.

    Returns (year, sensor_id, n_variables_in_matrix). A return of 0 means the
    pair was skipped (no data, or fewer than 2 variables recorded).
    """
    year, sensor_id = args

    os.makedirs("correlation_matrices", exist_ok=True)

    df_local = pd.read_parquet(f"data_by_year/year_{year}.parquet")
    sub = df_local[df_local["sensor_id"] == sensor_id]

    if len(sub) == 0:
        return (year, sensor_id, 0)

    wide = sub.pivot_table(
        index="entry_date",
        columns="magnitude_name",
        values="value",
    )

    # Need at least 2 variables to compute a correlation
    if wide.shape[1] < 2:
        return (year, sensor_id, 0)

    corr = wide.corr(min_periods=24)
    corr.to_parquet(f"correlation_matrices/year{year}_sensor{sensor_id}.parquet")
    return (year, sensor_id, corr.shape[0])
