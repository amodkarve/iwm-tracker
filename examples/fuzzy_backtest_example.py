"""
Example: Running Fuzzy Logic Strategy Backtest and Optimization

This example demonstrates how to:
1. Run a simple backtest
2. Optimize parameters using random search
3. Perform walk-forward optimization
"""
from datetime import date
from src.strategy.fuzzy_backtest import FuzzyBacktestEngine, FuzzyBacktestParams
from src.strategy.fuzzy_optimizer import FuzzyOptimizer


def example_simple_backtest():
    """Example: Run a simple backtest with default parameters"""
    print("=" * 60)
    print("Example 1: Simple Backtest")
    print("=" * 60)
    
    # Create backtest engine
    engine = FuzzyBacktestEngine(
        initial_capital=1_000_000.0,
        params=FuzzyBacktestParams(),  # Use defaults
        use_spy=True  # Use SPY instead of SPX
    )
    
    # Run backtest
    start_date = date(2020, 1, 1)
    end_date = date(2023, 12, 31)
    
    print(f"Running backtest from {start_date} to {end_date}...")
    metrics = engine.run(start_date, end_date)
    
    # Print results
    print(f"\nResults:")
    print(f"  Total Return: {metrics.total_return*100:.2f}%")
    print(f"  CAGR: {metrics.cagr*100:.2f}%")
    print(f"  Max Drawdown: {metrics.max_drawdown*100:.2f}%")
    print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"  MAR Ratio: {metrics.mar_ratio:.2f}")
    print(f"  Days Target Met: {metrics.days_target_met_pct:.1f}%")
    print(f"  Total Trades: {metrics.total_trades}")


def example_parameter_optimization():
    """Example: Optimize parameters using random search"""
    print("\n" + "=" * 60)
    print("Example 2: Parameter Optimization")
    print("=" * 60)
    
    # Create optimizer
    optimizer = FuzzyOptimizer(
        initial_capital=1_000_000.0,
        use_spy=True,
        objective='mar'  # Optimize for MAR ratio
    )
    
    # Define train/validation/test periods
    train_start = date(2005, 1, 1)
    train_end = date(2016, 12, 31)
    validation_start = date(2017, 1, 1)
    validation_end = date(2020, 12, 31)
    test_start = date(2021, 1, 1)
    test_end = date(2023, 12, 31)
    
    print(f"Training: {train_start} to {train_end}")
    print(f"Validation: {validation_start} to {validation_end}")
    print(f"Test: {test_start} to {test_end}")
    print(f"\nRunning optimization (this may take a while)...")
    
    # Run optimization
    result = optimizer.random_search(
        train_start=train_start,
        train_end=train_end,
        validation_start=validation_start,
        validation_end=validation_end,
        n_iterations=50,  # Use fewer iterations for example
        test_start=test_start,
        test_end=test_end
    )
    
    # Print results
    print(f"\nBest Parameters:")
    for key, value in result.best_params.to_dict().items():
        print(f"  {key}: {value}")
    
    print(f"\nTraining Metrics:")
    print(f"  CAGR: {result.train_metrics.cagr*100:.2f}%")
    print(f"  Max DD: {result.train_metrics.max_drawdown*100:.2f}%")
    print(f"  MAR: {result.train_metrics.mar_ratio:.2f}")
    
    print(f"\nValidation Metrics:")
    print(f"  CAGR: {result.validation_metrics.cagr*100:.2f}%")
    print(f"  Max DD: {result.validation_metrics.max_drawdown*100:.2f}%")
    print(f"  MAR: {result.validation_metrics.mar_ratio:.2f}")
    
    if result.test_metrics:
        print(f"\nTest Metrics:")
        print(f"  CAGR: {result.test_metrics.cagr*100:.2f}%")
        print(f"  Max DD: {result.test_metrics.max_drawdown*100:.2f}%")
        print(f"  MAR: {result.test_metrics.mar_ratio:.2f}")


def example_walk_forward():
    """Example: Walk-forward optimization"""
    print("\n" + "=" * 60)
    print("Example 3: Walk-Forward Optimization")
    print("=" * 60)
    
    optimizer = FuzzyOptimizer(
        initial_capital=1_000_000.0,
        use_spy=True,
        objective='mar'
    )
    
    start_date = date(2010, 1, 1)
    end_date = date(2023, 12, 31)
    
    print(f"Running walk-forward optimization from {start_date} to {end_date}...")
    print("(This will take a long time - using small iteration count for example)")
    
    results = optimizer.walk_forward_optimization(
        start_date=start_date,
        end_date=end_date,
        train_window_years=3,
        test_window_years=1,
        step_years=1,
        n_iterations=20  # Small for example
    )
    
    print(f"\nWalk-Forward Results ({len(results)} periods):")
    for i, result in enumerate(results):
        print(f"\nPeriod {i+1}:")
        print(f"  Test CAGR: {result.test_metrics.cagr*100:.2f}%" if result.test_metrics else "  No test metrics")
        print(f"  Test MAR: {result.test_metrics.mar_ratio:.2f}" if result.test_metrics else "  No test metrics")


def example_custom_objective():
    """Example: Custom objective function"""
    print("\n" + "=" * 60)
    print("Example 4: Custom Objective Function")
    print("=" * 60)
    
    def custom_objective(metrics):
        """Custom objective: maximize CAGR subject to max DD < 15%"""
        if metrics.max_drawdown > 0.15:
            return -1.0  # Penalty
        return metrics.cagr * (1 - metrics.max_drawdown)  # Reward low drawdown
    
    optimizer = FuzzyOptimizer(
        initial_capital=1_000_000.0,
        use_spy=True,
        objective=custom_objective
    )
    
    print("Using custom objective: maximize CAGR * (1 - DD) with DD < 15%")
    print("(Implementation would run optimization here)")


if __name__ == "__main__":
    print("Fuzzy Logic Strategy Backtest Examples")
    print("=" * 60)
    
    # Run examples (comment out ones that take too long)
    example_simple_backtest()
    # example_parameter_optimization()  # Uncomment to run (takes time)
    # example_walk_forward()  # Uncomment to run (takes a long time)
    example_custom_objective()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)

