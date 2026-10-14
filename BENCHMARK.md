# Candidate selection record

All candidates use the same positive-order monthly target and the same eligible material-month rows. Validation is May–August 2024; audit is September–October 2024. Metrics are pooled over rows, not averaged over monthly metric values. WAPE is total absolute error divided by total actual quantity.

| Candidate | Definition |
| --- | --- |
| nearby_random_forest | 75 trees, one demand lag, previous-month revenue, calendar and history-length features, seed 42. |
| long_history_random_forest | 100 trees, 12 demand lags, previous-month revenue, calendar and history-length features, seed 42. |
| regularized_random_forest | 200 trees, 12 lags, rolling means and standard deviation, minimum leaf 5, maximum depth 12, seed 42. |
| log_random_forest | 200 trees, 12 lags and rolling features, minimum leaf 3, maximum depth 16, seed 42, log1p target. Selected. |
| online_bagged_trees | Per-material River BaggingRegressor with 100 HoeffdingTreeRegressor learners, mean leaf prediction, seed 42; one-lag feature family. |
| last_month | Previous observed monthly aggregate, including modeled zero months. |
| trailing_three_month_mean | Mean of up to three earlier covered months. |
| zero_demand | Always zero; included as a sparsity sanity check. |

Candidates are corrected prospective versions of the historical approaches, not byte-identical reproductions. The online candidate uses a mean leaf predictor rather than the legacy adaptive leaf/default scaler pipeline. Historical notebooks were also executed separately with minimal compatibility adaptations; their original target definitions and cohorts differ, so their printed RMSEs must not be ranked against one another.

The comparison evidence is retained in `results/candidate_predictions.csv` and `results/candidate_comparison.csv`. `test_forecast.py` independently recomputes every saved aggregate metric. Only the selected model's implementation is maintained; discarded experiment notebooks and training scripts are not duplicated in this repository. Benchmark online dependency: River 0.26.1.
