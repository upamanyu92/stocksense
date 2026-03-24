# Agent Instructions (StockSense)

## Mission
Ship safe, reproducible finance-model improvements that are test-backed, leakage-resistant, and production-ready.

## Scope Map
- `app/agents/`: training/inference orchestration and evaluation flow.
- `app/services/`: data/provider integrations and feature pipelines.
- `app/api/`: prediction/backtest request surface and response contracts.
- `app/models/`, `app/model/`: model artifacts and persistence.
- `tests/`: `api/`, `agents/`, `integration/` validation.
- `scripts/`: scheduled jobs, schema/init, and ops tooling.

## Core Guardrails
- Make small, scoped changes; no broad refactors unless requested.
- Preserve API contracts (paths, keys, status codes) unless explicitly approved.
- Keep units, timezones, and precision explicit and unchanged by default.
- Never hardcode secrets or credentials.
- Log assumptions that affect financial interpretation.

## Experimentation Guardrails
- Define objective, hypothesis, and acceptance criteria before training.
- Use a fixed baseline and compare against it in every experiment.
- Track run metadata: code version, data snapshot/window, features, params, seed.
- Set hard stop criteria (overfit signals, unstable variance, degraded risk metrics).
- Promote only experiments that beat baseline on pre-agreed metrics.

## Reproducibility Requirements
- Use deterministic seeds where libraries allow.
- Pin data ranges and feature definitions per run.
- Version model artifacts with config + schema fingerprints.
- Save train/validation/test boundaries used for each result.
- Ensure one-command rerun can reproduce reported metrics.

## Leakage Prevention (Mandatory)
- Enforce time-aware splits; no random shuffle for time-series.
- Build features using only information available at prediction time.
- Fit scalers/encoders on train split only; apply to val/test.
- Purge overlapping windows when needed (embargo/purge for close horizons).
- Fail the run if future data or target-derived features are detected.

## Backtesting Expectations
- Use rolling or walk-forward validation aligned to trading cadence.
- Include realistic assumptions: latency, fees, slippage, and execution timing.
- Report per-window and aggregate performance, not only a single period.
- Compare against simple baselines (buy-and-hold, naive lag, sector benchmark).
- Stress test across regimes (bull/bear/high-volatility windows).

## Metrics Standard
- Forecast quality: MAE, RMSE, MAPE/sMAPE (as appropriate), directional accuracy.
- Strategy quality: Sharpe/Sortino, max drawdown, Calmar, hit rate, turnover.
- Calibration/uncertainty: prediction interval coverage when applicable.
- Stability: metric variance across folds/windows.
- Always report sample size and evaluation horizon with metrics.

## Feature/Label Consistency
- Keep feature definitions identical between training and inference.
- Validate schema/order/dtypes before scoring.
- Ensure label generation logic is versioned and unchanged across splits.
- Verify point-in-time joins for fundamentals/news features.
- Block inference if required features are missing or stale.

## Data Quality Gates
- Enforce checks for missingness, duplicates, stale timestamps, outliers, and corporate-action anomalies.
- Validate symbol mapping, timezone normalization, and market calendar alignment.
- Reject or quarantine bad batches; do not silently impute critical fields.
- Emit data quality summaries for each training and inference run.
- Treat provider outages as explicit, observable degraded mode.

## Drift Monitoring
- Monitor input drift (PSI/distribution shift), concept drift (error drift), and label drift.
- Define alert thresholds and escalation paths.
- Record rolling metric degradation vs baseline.
- Trigger retraining only when drift + performance criteria are met.
- Keep audit logs linking alerts to data/model versions.

## Safe Deployment Handoff
- Require go/no-go checklist: metrics met, leakage checks passed, backtest complete, data quality green.
- Package artifact + config + feature schema + dependency versions.
- Document rollout plan: canary/shadow strategy, rollback trigger, owner.
- Confirm monitoring dashboards/alerts exist before release.
- Provide clear risk notes: known blind spots, market-regime sensitivity, and operational dependencies.

## Validation Commands
```zsh
pytest tests/agents -q
pytest tests/api -q
pytest tests/integration -q
pytest -q
```

## Handoff Template
- Changed: `<files>`
- Objective/Hypothesis: `<what was tested and why>`
- Data Window + Split: `<dates, walk-forward setup>`
- Metrics vs Baseline: `<key numbers>`
- Leakage/Data Quality Checks: `<passed/failed + notes>`
- Deployment Plan: `<canary/shadow, rollback conditions>`
- Risks/Follow-ups: `<known limitations and next steps>`
