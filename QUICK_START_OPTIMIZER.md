# Quick Start: Running the Optimizer

## Run Optimizer Over 3 Years of Data in Docker

### Basic Command

```bash
docker-compose -f docker-compose.test.yml run --rm test python scripts/run_optimizer.py
```

This will:
- Use 3 years of data (2021-2023)
- Run 50 optimization iterations (default)
- Optimize for MAR ratio
- Print results to console

### Custom Number of Iterations

```bash
OPTIMIZER_ITERATIONS=100 docker-compose -f docker-compose.test.yml run --rm test python scripts/run_optimizer.py
```

### Save Results to File

```bash
OPTIMIZER_OUTPUT=/app/results.json OPTIMIZER_ITERATIONS=100 \
  docker-compose -f docker-compose.test.yml run --rm test python scripts/run_optimizer.py
```

Then copy results out:
```bash
docker cp $(docker ps -lq):/app/results.json ./results.json
```

### What It Does

1. **Downloads historical data** for SPY and VIX (2021-2023)
2. **Splits data** into:
   - Training: 2021-01-01 to 2022-06-30 (1.5 years)
   - Validation: 2022-07-01 to 2023-06-30 (1 year)
   - Test: 2023-07-01 to 2023-12-31 (6 months)
3. **Runs optimization** by testing different parameter combinations
4. **Reports best parameters** and performance metrics

### Expected Runtime

- 50 iterations: ~10-30 minutes
- 100 iterations: ~20-60 minutes
- 200 iterations: ~1-2 hours

### Output Example

```
Best Parameters:
  target_dte: 7
  hedge_dte: 30
  target_daily_premium_pct: 0.0008
  ...

Training Metrics:
  CAGR: 15.23%
  Max Drawdown: 8.45%
  MAR Ratio: 1.80

Validation Metrics:
  CAGR: 14.12%
  Max Drawdown: 9.23%
  MAR Ratio: 1.53
```

### Troubleshooting

**No data available?**
- Check internet connection (needs to download from yfinance)
- Try different date ranges

**Too slow?**
- Reduce iterations: `OPTIMIZER_ITERATIONS=25`
- Use shorter time periods (edit `scripts/run_optimizer.py`)

**Out of memory?**
- Reduce iterations
- Increase Docker memory limit

For more details, see `OPTIMIZER_USAGE.md`

