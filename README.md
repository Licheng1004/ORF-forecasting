# Monthly Demand Forecasting

A single maintained forecasting implementation, selected by chronological validation on the supplied sales-order snapshot. Historical notebooks have been consolidated into `forecast.py` and one executed companion notebook, `analysis.ipynb`.

## Selected version and measured results

**Log-target random forest**: 200 trees, 12 demand lags, rolling demand summaries, previous-month revenue features, calendar features, maximum depth 16, minimum leaf size 3, and seed 42. Training uses `log1p(quantity)`; predictions use `expm1` and are clipped at zero. This reduces sensitivity to extreme order quantities; it also introduces aggregate underprediction.

- Selection period: May–August 2024, 1,546 eligible material-month observations.
- Audit period: September–October 2024, 783 observations, never used to fit the prediction for the same month.
- Audit MAE: **1,684.27 units per material-month**.
- Audit RMSE: **11,364.53 units**; WAPE: **56.66%**.
- Last-month baseline MAE: 3,230.70; selected-model MAE is **47.87% lower** on these two audit months.
- Audit actual total: 2,327,391; predicted total: 1,376,445. The model underpredicts aggregate demand; optimizing MAE does not guarantee an unbiased total.

The selected model had the lowest pooled validation MAE among eight tested candidates. See `results/candidate_comparison.csv` and the retained per-candidate predictions. These are historical snapshot results, not a claim of production readiness or universal optimality.

## Run

Tested with Python 3.12.14. From this repository directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe forecast.py
.\.venv\Scripts\python.exe -m unittest -v test_forecast.py
```

Open `analysis.ipynb` in VS Code with this environment to inspect the executed analysis. To re-execute from a terminal:

```powershell
.\.venv\Scripts\python.exe -m ipykernel install --prefix .venv --name demand-forecasting --display-name "Demand Forecasting"
.\.venv\Scripts\python.exe -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.kernel_name=demand-forecasting analysis.ipynb
```

`forecast.py --data PATH --output-dir PATH` accepts an alternative input and output directory. Each run retrains chronologically, recomputes the two audit-month predictions, and trains through October 2024 to produce the November 2024 forecast. Existing result files with the same names are overwritten.

## Required data

`data/SO.csv.gz` is a lossless gzip copy of the original `SO.csv`: all 153,679 rows and original columns remain available. The uncompressed bytes are unchanged; SHA-256 hashes and sizes are recorded in `data_manifest.json`. Pandas reads gzip directly. Public release of this original data was explicitly authorized by the owner.

The final pipeline uses `MATERIAL`, `MONTH_DAY`, `QTY`, `NET_VALUE`, and `NET_NET_VALUE_RMB`. It removes exact duplicate full rows, keeps positive valid quantities, and aggregates by material and order month. Missing covered months after a material's first observation are treated as zero demand. This is an explicit modeling assumption: missing data cannot be distinguished from zero sales using this snapshot alone.

`CSF_FCST.xlsx` and old forecast exports are omitted because the selected pipeline does not use them. Forecast-version labels do not establish when historical forecast values were actually available, so those values were excluded from model selection.

## Evaluation and leakage controls

For each target month, train on earlier months only; all demand and revenue predictors are lagged. Materials become eligible after at least one observed month, without requiring positive target-month demand. Calendar gaps are filled only after first observation. New materials without history are outside this model's coverage.

The earlier cross-section notebooks mapped the earliest month to suffix `_00`, then used later months as predictors of that earlier target. Their random-split RMSE values are therefore not valid prospective forecasting evidence. The current implementation fixes the time direction and compares the legacy model families under a common rolling-origin protocol. Original rerun status and compatibility adjustments are documented in `results/legacy_audit.json`.

Selection used May–August MAE. September–October results are reported separately, using expanding training histories; September actuals may legitimately be used to train the October prediction. Log-target stabilization was motivated by validation-period errors, rather than a search over audit results. The audit comprises only two months from one snapshot, and cannot establish generalization to a different business period.

## Contents

- `forecast.py`: the sole maintained training and forecasting implementation.
- `model_config.json`: frozen selected model and evaluation periods.
- `analysis.ipynb`: executed analysis with charts and retained outputs.
- `test_forecast.py`: temporal isolation and metric reconciliation checks.
- `data/`: required original input, losslessly compressed.
- `results/`: comparison evidence, audit predictions, next-month forecast, plots, and run metadata.

## Limitations

There is no confirmed source-extraction timestamp or independent completeness audit for each month. The results treat the supplied month labels as a consistent historical snapshot. Cold starts, prediction intervals, external economic drivers, and service-level costs are not modeled. Direct package versions are pinned in `requirements.txt`; this is not an operating-system-independent environment image. No new reuse license has been granted.
