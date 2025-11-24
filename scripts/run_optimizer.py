#!/usr/bin/env python3
"""
Run fuzzy logic optimizer over 3 years of historical data

This script runs parameter optimization using train/validation/test splits
over 3 years of SPY and VIX data.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date, timedelta
import logging
from src.strategy.fuzzy_optimizer import FuzzyOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run optimizer over 3 years of data"""
    
    # Define 3-year period (adjust dates as needed)
    # Using recent 3 years: 2021-2023
    train_start = date(2021, 1, 1)
    train_end = date(2022, 6, 30)  # 1.5 years for training
    
    validation_start = date(2022, 7, 1)
    validation_end = date(2023, 6, 30)  # 1 year for validation
    
    test_start = date(2023, 7, 1)
    test_end = date(2023, 12, 31)  # 6 months for testing
    
    logger.info("=" * 60)
    logger.info("Fuzzy Logic Strategy Optimizer")
    logger.info("=" * 60)
    logger.info(f"Training period: {train_start} to {train_end}")
    logger.info(f"Validation period: {validation_start} to {validation_end}")
    logger.info(f"Test period: {test_start} to {test_end}")
    logger.info("")
    
    # Create optimizer
    optimizer = FuzzyOptimizer(
        initial_capital=1_000_000.0,
        use_spy=True,  # Use SPY instead of SPX
        objective='mar'  # Optimize for MAR ratio (CAGR / Max Drawdown)
    )
    
    # Number of iterations (adjust based on available time)
    # More iterations = better results but longer runtime
    n_iterations = int(os.getenv('OPTIMIZER_ITERATIONS', '50'))
    
    logger.info(f"Running optimization with {n_iterations} iterations...")
    logger.info("This may take a while depending on data availability...")
    logger.info("")
    
    try:
        # Run optimization
        result = optimizer.random_search(
            train_start=train_start,
            train_end=train_end,
            validation_start=validation_start,
            validation_end=validation_end,
            n_iterations=n_iterations,
            test_start=test_start,
            test_end=test_end
        )
        
        # Print results
        logger.info("")
        logger.info("=" * 60)
        logger.info("OPTIMIZATION RESULTS")
        logger.info("=" * 60)
        
        logger.info("\nBest Parameters:")
        for key, value in result.best_params.to_dict().items():
            logger.info(f"  {key}: {value}")
        
        logger.info("\nTraining Metrics:")
        logger.info(f"  Total Return: {result.train_metrics.total_return*100:.2f}%")
        logger.info(f"  CAGR: {result.train_metrics.cagr*100:.2f}%")
        logger.info(f"  Max Drawdown: {result.train_metrics.max_drawdown*100:.2f}%")
        logger.info(f"  Sharpe Ratio: {result.train_metrics.sharpe_ratio:.2f}")
        logger.info(f"  MAR Ratio: {result.train_metrics.mar_ratio:.2f}")
        logger.info(f"  Days Target Met: {result.train_metrics.days_target_met_pct:.1f}%")
        logger.info(f"  Total Trades: {result.train_metrics.total_trades}")
        
        logger.info("\nValidation Metrics:")
        logger.info(f"  Total Return: {result.validation_metrics.total_return*100:.2f}%")
        logger.info(f"  CAGR: {result.validation_metrics.cagr*100:.2f}%")
        logger.info(f"  Max Drawdown: {result.validation_metrics.max_drawdown*100:.2f}%")
        logger.info(f"  Sharpe Ratio: {result.validation_metrics.sharpe_ratio:.2f}")
        logger.info(f"  MAR Ratio: {result.validation_metrics.mar_ratio:.2f}")
        logger.info(f"  Days Target Met: {result.validation_metrics.days_target_met_pct:.1f}%")
        logger.info(f"  Total Trades: {result.validation_metrics.total_trades}")
        
        if result.test_metrics:
            logger.info("\nTest Metrics:")
            logger.info(f"  Total Return: {result.test_metrics.total_return*100:.2f}%")
            logger.info(f"  CAGR: {result.test_metrics.cagr*100:.2f}%")
            logger.info(f"  Max Drawdown: {result.test_metrics.max_drawdown*100:.2f}%")
            logger.info(f"  Sharpe Ratio: {result.test_metrics.sharpe_ratio:.2f}")
            logger.info(f"  MAR Ratio: {result.test_metrics.mar_ratio:.2f}")
            logger.info(f"  Days Target Met: {result.test_metrics.days_target_met_pct:.1f}%")
            logger.info(f"  Total Trades: {result.test_metrics.total_trades}")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("Optimization complete!")
        logger.info("=" * 60)
        
        # Save results to file if requested
        output_file = os.getenv('OPTIMIZER_OUTPUT', None)
        if output_file:
            import json
            with open(output_file, 'w') as f:
                json.dump(result.to_dict(), f, indent=2, default=str)
            logger.info(f"\nResults saved to: {output_file}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during optimization: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

