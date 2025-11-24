"""
Parameter Optimization Framework for Fuzzy Logic Strategy

Uses the backtest engine to optimize fuzzy logic parameters using
train/validation/test splits and various optimization methods.
"""
import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Callable
import logging
from dataclasses import asdict

from src.strategy.fuzzy_backtest import FuzzyBacktestEngine, FuzzyBacktestParams, BacktestMetrics

logger = logging.getLogger(__name__)


class OptimizationResult:
    """Result from parameter optimization"""
    
    def __init__(
        self,
        best_params: FuzzyBacktestParams,
        train_metrics: BacktestMetrics,
        validation_metrics: BacktestMetrics,
        test_metrics: Optional[BacktestMetrics] = None,
        optimization_history: List[Dict] = None
    ):
        self.best_params = best_params
        self.train_metrics = train_metrics
        self.validation_metrics = validation_metrics
        self.test_metrics = test_metrics
        self.optimization_history = optimization_history or []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'best_params': self.best_params.to_dict(),
            'train_metrics': self.train_metrics.to_dict(),
            'validation_metrics': self.validation_metrics.to_dict(),
            'test_metrics': self.test_metrics.to_dict() if self.test_metrics else None,
            'optimization_history': self.optimization_history
        }


class FuzzyOptimizer:
    """
    Optimizer for fuzzy logic strategy parameters
    """
    
    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        use_spy: bool = True,
        objective: str = 'mar'  # 'mar', 'cagr', 'sharpe', or custom function
    ):
        """
        Initialize optimizer
        
        Args:
            initial_capital: Starting capital for backtests
            use_spy: If True, use SPY; if False, use SPX
            objective: Optimization objective ('mar', 'cagr', 'sharpe', or callable)
        """
        self.initial_capital = initial_capital
        self.use_spy = use_spy
        self.objective = objective
        self.optimization_history: List[Dict] = []
    
    def _calculate_objective(
        self,
        metrics: BacktestMetrics,
        custom_objective: Optional[Callable] = None
    ) -> float:
        """
        Calculate objective function value from metrics
        
        Args:
            metrics: Backtest metrics
            custom_objective: Custom objective function (takes metrics, returns float)
        
        Returns:
            Objective value (higher is better)
        """
        if custom_objective:
            return custom_objective(metrics)
        
        # Check if objective is a callable function
        if callable(self.objective):
            return self.objective(metrics)
        
        if self.objective == 'mar':
            return metrics.mar_ratio
        elif self.objective == 'cagr':
            return metrics.cagr
        elif self.objective == 'sharpe':
            return metrics.sharpe_ratio
        elif self.objective == 'cagr_constrained':
            # Maximize CAGR subject to max DD < 20%
            if metrics.max_drawdown > 0.20:
                return -1.0  # Penalty for exceeding drawdown limit
            return metrics.cagr
        else:
            return metrics.mar_ratio  # Default
    
    def _generate_random_params(self) -> FuzzyBacktestParams:
        """Generate random parameters within reasonable bounds"""
        return FuzzyBacktestParams(
            cycle_oversold_threshold=np.random.uniform(-0.6, -0.2),
            cycle_overbought_threshold=np.random.uniform(0.2, 0.6),
            trend_down_threshold=np.random.uniform(-0.5, -0.1),
            trend_up_threshold=np.random.uniform(0.1, 0.5),
            put_moneyness_weight=np.random.uniform(0.5, 1.5),
            put_size_weight=np.random.uniform(0.5, 1.5),
            call_sell_threshold=np.random.uniform(0.4, 0.8),
            hedge_score_threshold=np.random.uniform(0.3, 0.6),
            target_dte=1,  # Fixed at 1 DTE (3 DTE for Friday)
            hedge_dte=int(np.random.choice([21, 30, 45])),
            max_hedge_notional_pct=np.random.uniform(0.3, 0.6),
            target_daily_premium_pct=np.random.uniform(0.0005, 0.0012),
            min_contract_premium=np.random.uniform(30.0, 80.0),
            hedge_otm_pct_low_vix=np.random.uniform(8.0, 15.0),
            hedge_otm_pct_high_vix=np.random.uniform(3.0, 8.0),
        )
    
    def random_search(
        self,
        train_start: date,
        train_end: date,
        validation_start: date,
        validation_end: date,
        n_iterations: int = 100,
        test_start: Optional[date] = None,
        test_end: Optional[date] = None
    ) -> OptimizationResult:
        """
        Random search optimization
        
        Args:
            train_start: Training period start
            train_end: Training period end
            validation_start: Validation period start
            validation_end: Validation period end
            n_iterations: Number of random parameter sets to try
            test_start: Optional test period start
            test_end: Optional test period end
        
        Returns:
            OptimizationResult with best parameters
        """
        logger.info(f"Starting random search with {n_iterations} iterations")
        
        best_objective = float('-inf')
        best_params = None
        best_train_metrics = None
        best_validation_metrics = None
        
        for i in range(n_iterations):
            if i % 10 == 0:
                logger.info(f"Iteration {i}/{n_iterations}")
            
            # Generate random parameters
            params = self._generate_random_params()
            
            # Run backtest on training set
            engine = FuzzyBacktestEngine(
                initial_capital=self.initial_capital,
                params=params,
                use_spy=self.use_spy
            )
            
            try:
                train_metrics = engine.run(train_start, train_end)
                validation_metrics = engine.run(validation_start, validation_end)
                
                # Calculate objective (use validation set)
                objective = self._calculate_objective(validation_metrics)
                
                # Record history
                self.optimization_history.append({
                    'iteration': i,
                    'params': params.to_dict(),
                    'train_objective': self._calculate_objective(train_metrics),
                    'validation_objective': objective,
                    'train_metrics': train_metrics.to_dict(),
                    'validation_metrics': validation_metrics.to_dict()
                })
                
                # Update best
                if objective > best_objective:
                    best_objective = objective
                    best_params = params
                    best_train_metrics = train_metrics
                    best_validation_metrics = validation_metrics
                    logger.info(f"New best objective: {objective:.4f} (iteration {i})")
            
            except Exception as e:
                logger.warning(f"Error in iteration {i}: {e}")
                # Still record the error in history
                self.optimization_history.append({
                    'iteration': i,
                    'params': params.to_dict(),
                    'error': str(e)
                })
                continue
        
        # Run test set if provided
        test_metrics = None
        if test_start and test_end and best_params:
            engine = FuzzyBacktestEngine(
                initial_capital=self.initial_capital,
                params=best_params,
                use_spy=self.use_spy
            )
            try:
                test_metrics = engine.run(test_start, test_end)
            except Exception as e:
                logger.warning(f"Error running test set: {e}")
        
        return OptimizationResult(
            best_params=best_params or FuzzyBacktestParams(),
            train_metrics=best_train_metrics or BacktestMetrics(
                total_return=0.0, cagr=0.0, max_drawdown=0.0,
                sharpe_ratio=0.0, mar_ratio=0.0,
                days_target_met=0, days_target_met_pct=0.0,
                total_trades=0, winning_trades=0, losing_trades=0,
                avg_trade_return=0.0
            ),
            validation_metrics=best_validation_metrics or BacktestMetrics(
                total_return=0.0, cagr=0.0, max_drawdown=0.0,
                sharpe_ratio=0.0, mar_ratio=0.0,
                days_target_met=0, days_target_met_pct=0.0,
                total_trades=0, winning_trades=0, losing_trades=0,
                avg_trade_return=0.0
            ),
            test_metrics=test_metrics,
            optimization_history=self.optimization_history
        )
    
    def latin_hypercube_search(
        self,
        train_start: date,
        train_end: date,
        validation_start: date,
        validation_end: date,
        n_samples: int = 100,
        test_start: Optional[date] = None,
        test_end: Optional[date] = None
    ) -> OptimizationResult:
        """
        Latin Hypercube Sampling for more efficient parameter space exploration
        
        Args:
            train_start: Training period start
            train_end: Training period end
            validation_start: Validation period start
            validation_end: Validation period end
            n_samples: Number of samples
            test_start: Optional test period start
            test_end: Optional test period end
        
        Returns:
            OptimizationResult with best parameters
        """
        logger.info(f"Starting Latin Hypercube search with {n_samples} samples")
        
        # Define parameter bounds
        param_bounds = {
            'cycle_oversold_threshold': (-0.6, -0.2),
            'cycle_overbought_threshold': (0.2, 0.6),
            'trend_down_threshold': (-0.5, -0.1),
            'trend_up_threshold': (0.1, 0.5),
            'put_moneyness_weight': (0.5, 1.5),
            'put_size_weight': (0.5, 1.5),
            'call_sell_threshold': (0.4, 0.8),
            'hedge_score_threshold': (0.3, 0.6),
            # target_dte is fixed at 1 (3 DTE for Friday) - not optimized
            'hedge_dte': (21, 45),
            'max_hedge_notional_pct': (0.3, 0.6),
            'target_daily_premium_pct': (0.0005, 0.0012),
            'min_contract_premium': (30.0, 80.0),
            'hedge_otm_pct_low_vix': (8.0, 15.0),
            'hedge_otm_pct_high_vix': (3.0, 8.0),
        }
        
        # Generate Latin Hypercube samples
        # Exclude target_dte from optimization (it's fixed at 1)
        param_names = [p for p in param_bounds.keys() if p != 'target_dte']
        n_params = len(param_names)
        
        # Simple LHS implementation
        samples = np.random.uniform(0, 1, (n_samples, n_params))
        for i in range(n_params):
            # Stratify each dimension
            samples[:, i] = (np.arange(n_samples) + np.random.uniform(0, 1, n_samples)) / n_samples
        
        # Shuffle to break correlation
        np.random.shuffle(samples)
        
        # Scale to parameter bounds
        best_objective = float('-inf')
        best_params = None
        best_train_metrics = None
        best_validation_metrics = None
        
        for i, sample in enumerate(samples):
            if i % 10 == 0:
                logger.info(f"Sample {i}/{n_samples}")
            
            # Create params from sample
            param_dict = {}
            for j, param_name in enumerate(param_names):
                # Skip target_dte - it's fixed at 1 (3 DTE for Friday)
                if param_name == 'target_dte':
                    param_dict[param_name] = 1
                    continue
                
                low, high = param_bounds[param_name]
                value = sample[j] * (high - low) + low
                
                # Round integer parameters
                if param_name == 'hedge_dte':
                    value = int(round(value))
                
                param_dict[param_name] = value
            
            # Always set target_dte to 1 (3 DTE for Friday is handled in backtest)
            param_dict['target_dte'] = 1
            params = FuzzyBacktestParams(**param_dict)
            
            # Run backtest
            engine = FuzzyBacktestEngine(
                initial_capital=self.initial_capital,
                params=params,
                use_spy=self.use_spy
            )
            
            try:
                train_metrics = engine.run(train_start, train_end)
                validation_metrics = engine.run(validation_start, validation_end)
                
                objective = self._calculate_objective(validation_metrics)
                
                self.optimization_history.append({
                    'iteration': i,
                    'params': params.to_dict(),
                    'train_objective': self._calculate_objective(train_metrics),
                    'validation_objective': objective,
                    'train_metrics': train_metrics.to_dict(),
                    'validation_metrics': validation_metrics.to_dict()
                })
                
                if objective > best_objective:
                    best_objective = objective
                    best_params = params
                    best_train_metrics = train_metrics
                    best_validation_metrics = validation_metrics
                    logger.info(f"New best objective: {objective:.4f} (sample {i})")
            
            except Exception as e:
                logger.warning(f"Error in sample {i}: {e}")
                # Still record the error in history
                self.optimization_history.append({
                    'iteration': i,
                    'params': params.to_dict(),
                    'error': str(e)
                })
                continue
        
        # Run test set if provided
        test_metrics = None
        if test_start and test_end and best_params:
            engine = FuzzyBacktestEngine(
                initial_capital=self.initial_capital,
                params=best_params,
                use_spy=self.use_spy
            )
            try:
                test_metrics = engine.run(test_start, test_end)
            except Exception as e:
                logger.warning(f"Error running test set: {e}")
        
        return OptimizationResult(
            best_params=best_params or FuzzyBacktestParams(),
            train_metrics=best_train_metrics or BacktestMetrics(
                total_return=0.0, cagr=0.0, max_drawdown=0.0,
                sharpe_ratio=0.0, mar_ratio=0.0,
                days_target_met=0, days_target_met_pct=0.0,
                total_trades=0, winning_trades=0, losing_trades=0,
                avg_trade_return=0.0
            ),
            validation_metrics=best_validation_metrics or BacktestMetrics(
                total_return=0.0, cagr=0.0, max_drawdown=0.0,
                sharpe_ratio=0.0, mar_ratio=0.0,
                days_target_met=0, days_target_met_pct=0.0,
                total_trades=0, winning_trades=0, losing_trades=0,
                avg_trade_return=0.0
            ),
            test_metrics=test_metrics,
            optimization_history=self.optimization_history
        )
    
    def walk_forward_optimization(
        self,
        start_date: date,
        end_date: date,
        train_window_years: int = 3,
        test_window_years: int = 1,
        step_years: int = 1,
        n_iterations: int = 50
    ) -> List[OptimizationResult]:
        """
        Walk-forward optimization: re-optimize every step_years and test on next period
        
        Args:
            start_date: Start date
            end_date: End date
            train_window_years: Years of data for training
            test_window_years: Years of data for testing
            step_years: Years to step forward each iteration
            n_iterations: Number of parameter sets to try per window
        
        Returns:
            List of OptimizationResult for each walk-forward period
        """
        logger.info("Starting walk-forward optimization")
        
        results = []
        current_date = start_date
        
        while current_date < end_date:
            train_start = current_date
            train_end = current_date + timedelta(days=train_window_years * 365)
            test_start = train_end
            test_end = test_start + timedelta(days=test_window_years * 365)
            
            if test_end > end_date:
                test_end = end_date
            
            if test_start >= end_date:
                break
            
            logger.info(f"Walk-forward: Training {train_start} to {train_end}, Testing {test_start} to {test_end}")
            
            # Use validation = last year of training
            validation_start = train_end - timedelta(days=365)
            validation_end = train_end
            
            # Optimize on training set
            result = self.random_search(
                train_start=train_start,
                train_end=validation_start,
                validation_start=validation_start,
                validation_end=validation_end,
                n_iterations=n_iterations,
                test_start=test_start,
                test_end=test_end
            )
            
            results.append(result)
            
            # Step forward
            current_date += timedelta(days=step_years * 365)
        
        return results

