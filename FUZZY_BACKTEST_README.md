# Fuzzy Logic Strategy Backtest and Optimization

This document describes the backtest engine and optimization framework for the fuzzy logic trading strategy.

## Overview

The backtest system allows you to:
1. Test the fuzzy logic strategy on historical SPX/SPY and VIX data
2. Optimize strategy parameters using train/validation/test splits
3. Perform walk-forward optimization to avoid overfitting
4. Analyze performance metrics (CAGR, Sharpe, MAR, drawdown, etc.)

## Components

### 1. Historical Data (`src/market_data/historical_data.py`)

Functions to fetch historical market data:
- `get_spx_history()` - SPX index data
- `get_spy_history()` - SPY ETF data  
- `get_vix_history()` - VIX volatility index
- `get_combined_market_data()` - Combined price + VIX data

### 2. Backtest Engine (`src/strategy/fuzzy_backtest.py`)

**FuzzyBacktestEngine**: Main backtest engine that:
- Tracks portfolio state (cash, stock, options, hedges)
- Updates indicators daily (Ehlers trend, Cycle Swing)
- Applies fuzzy logic rules to generate trading signals
- Executes trades (put sales, hedges)
- Handles option expirations and assignments
- Calculates performance metrics

**FuzzyBacktestParams**: Tunable parameters including:
- Membership function boundaries
- Rule weights
- Trading parameters (DTE, hedge settings)
- Position sizing parameters

**Key Features**:
- Daily simulation loop
- Option price estimation (simplified Black-Scholes)
- Buying power tracking
- Premium target tracking
- Performance metrics calculation

### 3. Optimization Framework (`src/strategy/fuzzy_optimizer.py`)

**FuzzyOptimizer**: Parameter optimization with:
- Random search
- Latin Hypercube Sampling
- Walk-forward optimization
- Custom objective functions

**Optimization Methods**:
- `random_search()` - Random parameter sampling
- `latin_hypercube_search()` - More efficient parameter space exploration
- `walk_forward_optimization()` - Re-optimize periodically to avoid overfitting

## Usage Examples

### Simple Backtest

```python
from datetime import date
from src.strategy.fuzzy_backtest import FuzzyBacktestEngine, FuzzyBacktestParams

# Create engine with default parameters
engine = FuzzyBacktestEngine(
    initial_capital=1_000_000.0,
    params=FuzzyBacktestParams(),
    use_spy=True
)

# Run backtest
metrics = engine.run(
    start_date=date(2020, 1, 1),
    end_date=date(2023, 12, 31)
)

print(f"CAGR: {metrics.cagr*100:.2f}%")
print(f"Max Drawdown: {metrics.max_drawdown*100:.2f}%")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
print(f"MAR Ratio: {metrics.mar_ratio:.2f}")
```

### Parameter Optimization

```python
from src.strategy.fuzzy_optimizer import FuzzyOptimizer

optimizer = FuzzyOptimizer(
    initial_capital=1_000_000.0,
    use_spy=True,
    objective='mar'  # Optimize for MAR ratio
)

result = optimizer.random_search(
    train_start=date(2005, 1, 1),
    train_end=date(2016, 12, 31),
    validation_start=date(2017, 1, 1),
    validation_end=date(2020, 12, 31),
    n_iterations=100
)

print("Best Parameters:", result.best_params.to_dict())
print("Validation MAR:", result.validation_metrics.mar_ratio)
```

### Walk-Forward Optimization

```python
results = optimizer.walk_forward_optimization(
    start_date=date(2010, 1, 1),
    end_date=date(2023, 12, 31),
    train_window_years=3,
    test_window_years=1,
    step_years=1,
    n_iterations=50
)

# Results contains one OptimizationResult per walk-forward period
for i, result in enumerate(results):
    print(f"Period {i+1} Test MAR: {result.test_metrics.mar_ratio:.2f}")
```

## Performance Metrics

The backtest calculates:

- **Total Return**: (Final Value - Initial Value) / Initial Value
- **CAGR**: Compound Annual Growth Rate
- **Max Drawdown**: Maximum peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted return (annualized)
- **MAR Ratio**: CAGR / Max Drawdown
- **Days Target Met**: % of days where premium target was achieved
- **Trade Statistics**: Total trades, win rate, average return

## Parameter Optimization

### Tunable Parameters

1. **Membership Boundaries**:
   - `cycle_oversold_threshold`: When cycle is considered oversold
   - `cycle_overbought_threshold`: When cycle is considered overbought
   - `trend_down_threshold`: When trend is considered down
   - `trend_up_threshold`: When trend is considered up

2. **Rule Weights**:
   - `put_moneyness_weight`: Weight for put moneyness calculation
   - `put_size_weight`: Weight for position sizing
   - `call_sell_threshold`: Minimum score to sell calls
   - `hedge_score_threshold`: Minimum score to hedge

3. **Trading Parameters**:
   - `target_dte`: Target days to expiration for puts
   - `hedge_dte`: Days to expiration for hedge puts
   - `max_hedge_notional_pct`: Max hedge as % of stock exposure
   - `target_daily_premium_pct`: Daily premium target (default 0.08%)
   - `min_contract_premium`: Minimum premium to trade
   - `hedge_otm_pct_low_vix`: OTM % for hedges when VIX is low
   - `hedge_otm_pct_high_vix`: OTM % for hedges when VIX is high

### Optimization Objectives

- `'mar'`: Maximize MAR ratio (CAGR / Max Drawdown)
- `'cagr'`: Maximize CAGR
- `'sharpe'`: Maximize Sharpe ratio
- `'cagr_constrained'`: Maximize CAGR with max DD < 20%
- Custom function: Provide your own objective function

## Trade Execution Mapping

The backtest engine maps fuzzy outputs to actual trades:

### Put Selling

```python
# Calculate target strike from moneyness
strike_offset = put_moneyness * current_price * 0.02
target_strike = current_price - strike_offset

# Calculate position size
target_premium = portfolio_value * target_daily_premium_pct
remaining_target = target_premium - premium_collected_today
target_notional = remaining_target * put_size_frac
contracts = target_notional / (option_price * 100)
```

### Hedging

```python
# Calculate hedge notional
stock_exposure = stock_shares * current_price
max_hedge_notional = stock_exposure * max_hedge_notional_pct
target_hedge_notional = hedge_score * max_hedge_notional

# Calculate strike
target_strike = current_price * (1 - hedge_otm_pct / 100)
```

## Data Requirements

The backtest requires:
- Historical SPX/SPY OHLCV data (via yfinance)
- Historical VIX data (via yfinance)
- At least 50 days of history for indicator calculation

## Limitations

1. **Option Pricing**: Uses simplified Black-Scholes approximation. For production, use real option prices.

2. **Execution**: Assumes fills at close price. No slippage or bid-ask spread modeling.

3. **Assignment**: Simplified assignment logic. Real assignment can be more complex.

4. **Greeks**: Simplified delta calculations. Full Greeks would require option pricing model.

5. **Margin**: Simplified buying power calculation. Real margin requirements vary by broker.

## Future Enhancements

- Real option pricing (Black-Scholes with proper IV)
- Bid-ask spread modeling
- Slippage and transaction costs
- More sophisticated assignment logic
- Full Greeks calculation
- Broker-specific margin requirements
- Multi-underlying support
- Parallel optimization (multiprocessing)

## Running Backtests

See `examples/fuzzy_backtest_example.py` for complete examples.

To run a quick backtest:
```bash
python examples/fuzzy_backtest_example.py
```

For optimization (takes longer):
```python
# Uncomment optimization examples in the script
```

