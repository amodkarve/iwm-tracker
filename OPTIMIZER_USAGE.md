# Running the Fuzzy Logic Optimizer

This guide explains how to run the fuzzy logic strategy optimizer over 3 years of historical data inside a Docker container.

## Quick Start

### Basic Usage

Run the optimizer with default settings (50 iterations):

```bash
docker-compose -f docker-compose.test.yml run --rm test python scripts/run_optimizer.py
```

### Custom Number of Iterations

Set the number of optimization iterations:

```bash
OPTIMIZER_ITERATIONS=100 docker-compose -f docker-compose.test.yml run --rm test python scripts/run_optimizer.py
```

### Save Results to File

Save optimization results to a JSON file:

```bash
OPTIMIZER_OUTPUT=/app/results.json OPTIMIZER_ITERATIONS=100 \
  docker-compose -f docker-compose.test.yml run --rm test python scripts/run_optimizer.py
```

## Configuration

### Time Periods

The optimizer uses the following default periods (defined in `scripts/run_optimizer.py`):

- **Training**: 2021-01-01 to 2022-06-30 (1.5 years)
- **Validation**: 2022-07-01 to 2023-06-30 (1 year)
- **Test**: 2023-07-01 to 2023-12-31 (6 months)

To change these periods, edit `scripts/run_optimizer.py`:

```python
train_start = date(2021, 1, 1)
train_end = date(2022, 6, 30)
validation_start = date(2022, 7, 1)
validation_end = date(2023, 6, 30)
test_start = date(2023, 7, 1)
test_end = date(2023, 12, 31)
```

### Optimization Objective

The optimizer can optimize for different objectives:

- `'mar'` - MAR ratio (CAGR / Max Drawdown) - **Default**
- `'cagr'` - Compound Annual Growth Rate
- `'sharpe'` - Sharpe ratio
- `'cagr_constrained'` - CAGR with max drawdown < 20%

To change the objective, edit `scripts/run_optimizer.py`:

```python
optimizer = FuzzyOptimizer(
    initial_capital=1_000_000.0,
    use_spy=True,
    objective='mar'  # Change this
)
```

### Initial Capital

Default is $1,000,000. To change:

```python
optimizer = FuzzyOptimizer(
    initial_capital=500_000.0,  # Change this
    use_spy=True,
    objective='mar'
)
```

## Optimization Methods

### Random Search (Default)

The script uses random search by default. This is good for initial exploration:

```python
result = optimizer.random_search(
    train_start=train_start,
    train_end=train_end,
    validation_start=validation_start,
    validation_end=validation_end,
    n_iterations=100
)
```

### Latin Hypercube Sampling

For more efficient parameter space exploration:

```python
result = optimizer.latin_hypercube_search(
    train_start=train_start,
    train_end=train_end,
    validation_start=validation_start,
    validation_end=validation_end,
    n_samples=100
)
```

### Walk-Forward Optimization

For time-series cross-validation:

```python
results = optimizer.walk_forward_optimization(
    start_date=date(2021, 1, 1),
    end_date=date(2023, 12, 31),
    train_window_years=1,
    test_window_years=0.5,
    step_years=0.5,
    n_iterations=50
)
```

## Output

The optimizer prints:

1. **Best Parameters**: Optimized parameter values
2. **Training Metrics**: Performance on training set
3. **Validation Metrics**: Performance on validation set
4. **Test Metrics**: Performance on test set (if provided)

Example output:

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
  ...

Validation Metrics:
  CAGR: 14.12%
  Max Drawdown: 9.23%
  MAR Ratio: 1.53
  ...
```

## Performance Considerations

- **Iterations**: More iterations = better results but longer runtime
  - 50 iterations: ~10-30 minutes (depending on data)
  - 100 iterations: ~20-60 minutes
  - 500 iterations: ~2-5 hours

- **Data Fetching**: First run may be slower as it downloads historical data
  - Subsequent runs use cached data (if available)

- **Docker**: Running in Docker adds minimal overhead (~5-10%)

## Troubleshooting

### No Data Available

If you get "No market data available" errors:

1. Check your internet connection (needs to download from yfinance)
2. Verify the date ranges are valid (markets closed on weekends/holidays)
3. Try a different time period

### Out of Memory

If Docker runs out of memory:

1. Reduce number of iterations
2. Use shorter time periods
3. Increase Docker memory limit

### Slow Performance

To speed up optimization:

1. Reduce number of iterations
2. Use shorter time periods
3. Run on a machine with more CPU cores
4. Consider using Latin Hypercube instead of random search

## Advanced Usage

### Custom Objective Function

Create a custom objective function:

```python
def custom_objective(metrics):
    """Maximize CAGR while penalizing high drawdown"""
    if metrics.max_drawdown > 0.15:
        return -1.0  # Penalty
    return metrics.cagr * (1 - metrics.max_drawdown)

optimizer = FuzzyOptimizer(objective=custom_objective)
```

### Accessing Optimization History

The optimizer tracks all iterations:

```python
result = optimizer.random_search(...)

# Access history
for entry in optimizer.optimization_history:
    print(f"Iteration {entry['iteration']}: {entry['validation_objective']}")
```

### Saving Results

Results can be saved as JSON:

```python
import json

result_dict = result.to_dict()
with open('results.json', 'w') as f:
    json.dump(result_dict, f, indent=2, default=str)
```

## Example: Full Optimization Run

```bash
# Run with 200 iterations and save results
OPTIMIZER_ITERATIONS=200 \
OPTIMIZER_OUTPUT=/app/optimization_results.json \
docker-compose -f docker-compose.test.yml run --rm test python scripts/run_optimizer.py

# Copy results out of container
docker cp $(docker ps -lq):/app/optimization_results.json ./optimization_results.json
```

## Next Steps

After optimization:

1. Review the best parameters
2. Test on out-of-sample data
3. Adjust parameters manually if needed
4. Run backtests with optimized parameters
5. Deploy to production (with caution!)

