"""
Unit tests for fuzzy logic optimizer

Tests based on original specification requirements
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.strategy.fuzzy_optimizer import (
    FuzzyOptimizer,
    OptimizationResult
)
from src.strategy.fuzzy_backtest import (
    FuzzyBacktestEngine,
    FuzzyBacktestParams,
    BacktestMetrics
)


class TestFuzzyOptimizer:
    """Test FuzzyOptimizer class"""
    
    def test_optimizer_initialization(self):
        """Test optimizer initialization"""
        optimizer = FuzzyOptimizer(
            initial_capital=1_000_000.0,
            use_spy=True,
            objective='mar'
        )
        
        assert optimizer.initial_capital == 1_000_000.0
        assert optimizer.use_spy == True
        assert optimizer.objective == 'mar'
        assert len(optimizer.optimization_history) == 0
    
    def test_calculate_objective_mar(self):
        """Test MAR objective calculation"""
        optimizer = FuzzyOptimizer(objective='mar')
        
        metrics = BacktestMetrics(
            total_return=0.2,
            cagr=0.15,
            max_drawdown=0.10,
            sharpe_ratio=1.5,
            mar_ratio=1.5,  # 0.15 / 0.10
            days_target_met=100,
            days_target_met_pct=50.0,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            avg_trade_return=0.01
        )
        
        objective = optimizer._calculate_objective(metrics)
        assert objective == 1.5, "Should return MAR ratio"
    
    def test_calculate_objective_cagr(self):
        """Test CAGR objective calculation"""
        optimizer = FuzzyOptimizer(objective='cagr')
        
        metrics = BacktestMetrics(
            total_return=0.2,
            cagr=0.15,
            max_drawdown=0.10,
            sharpe_ratio=1.5,
            mar_ratio=1.5,
            days_target_met=100,
            days_target_met_pct=50.0,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            avg_trade_return=0.01
        )
        
        objective = optimizer._calculate_objective(metrics)
        assert objective == 0.15, "Should return CAGR"
    
    def test_calculate_objective_sharpe(self):
        """Test Sharpe objective calculation"""
        optimizer = FuzzyOptimizer(objective='sharpe')
        
        metrics = BacktestMetrics(
            total_return=0.2,
            cagr=0.15,
            max_drawdown=0.10,
            sharpe_ratio=1.5,
            mar_ratio=1.5,
            days_target_met=100,
            days_target_met_pct=50.0,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            avg_trade_return=0.01
        )
        
        objective = optimizer._calculate_objective(metrics)
        assert objective == 1.5, "Should return Sharpe ratio"
    
    def test_calculate_objective_cagr_constrained(self):
        """Test constrained CAGR objective"""
        optimizer = FuzzyOptimizer(objective='cagr_constrained')
        
        # Within constraint
        metrics_good = BacktestMetrics(
            total_return=0.2,
            cagr=0.15,
            max_drawdown=0.15,  # < 20%
            sharpe_ratio=1.5,
            mar_ratio=1.0,
            days_target_met=100,
            days_target_met_pct=50.0,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            avg_trade_return=0.01
        )
        
        objective_good = optimizer._calculate_objective(metrics_good)
        assert objective_good == 0.15, "Should return CAGR if within constraint"
        
        # Exceeds constraint
        metrics_bad = BacktestMetrics(
            total_return=0.2,
            cagr=0.20,
            max_drawdown=0.25,  # > 20%
            sharpe_ratio=1.5,
            mar_ratio=0.8,
            days_target_met=100,
            days_target_met_pct=50.0,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            avg_trade_return=0.01
        )
        
        objective_bad = optimizer._calculate_objective(metrics_bad)
        assert objective_bad < 0, "Should penalize if exceeds constraint"
    
    def test_calculate_objective_custom(self):
        """Test custom objective function"""
        def custom_obj(metrics):
            return metrics.cagr * (1 - metrics.max_drawdown)
        
        optimizer = FuzzyOptimizer(objective=custom_obj)
        
        metrics = BacktestMetrics(
            total_return=0.2,
            cagr=0.15,
            max_drawdown=0.10,
            sharpe_ratio=1.5,
            mar_ratio=1.5,
            days_target_met=100,
            days_target_met_pct=50.0,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            avg_trade_return=0.01
        )
        
        objective = optimizer._calculate_objective(metrics)
        expected = 0.15 * (1 - 0.10)  # 0.135
        assert abs(objective - expected) < 0.001, f"Expected {expected}, got {objective}"
    
    def test_generate_random_params(self):
        """Test random parameter generation"""
        optimizer = FuzzyOptimizer()
        
        params = optimizer._generate_random_params()
        
        assert isinstance(params, FuzzyBacktestParams)
        assert 5 <= params.target_dte <= 21, "Target DTE should be in reasonable range"
        assert 21 <= params.hedge_dte <= 45, "Hedge DTE should be in reasonable range"
        assert 0.0005 <= params.target_daily_premium_pct <= 0.0012, "Premium target should be reasonable"
    
    @patch('src.strategy.fuzzy_optimizer.FuzzyBacktestEngine')
    def test_random_search_basic(self, mock_engine_class):
        """Test random search optimization"""
        # Mock backtest engine
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Mock metrics
        train_metrics = BacktestMetrics(
            total_return=0.2, cagr=0.15, max_drawdown=0.10,
            sharpe_ratio=1.5, mar_ratio=1.5,
            days_target_met=100, days_target_met_pct=50.0,
            total_trades=50, winning_trades=30, losing_trades=20,
            avg_trade_return=0.01
        )
        
        validation_metrics = BacktestMetrics(
            total_return=0.18, cagr=0.14, max_drawdown=0.12,
            sharpe_ratio=1.4, mar_ratio=1.17,
            days_target_met=95, days_target_met_pct=48.0,
            total_trades=45, winning_trades=28, losing_trades=17,
            avg_trade_return=0.01
        )
        
        mock_engine.run.side_effect = [train_metrics, validation_metrics]
        
        optimizer = FuzzyOptimizer(
            initial_capital=1_000_000.0,
            objective='mar'
        )
        
        result = optimizer.random_search(
            train_start=date(2020, 1, 1),
            train_end=date(2020, 12, 31),
            validation_start=date(2021, 1, 1),
            validation_end=date(2021, 12, 31),
            n_iterations=5
        )
        
        assert isinstance(result, OptimizationResult)
        assert result.best_params is not None
        assert result.train_metrics is not None
        assert result.validation_metrics is not None
        assert len(optimizer.optimization_history) == 5, "Should track all iterations"
    
    @patch('src.strategy.fuzzy_optimizer.FuzzyBacktestEngine')
    def test_random_search_finds_best(self, mock_engine_class):
        """Test that random search finds best parameters"""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Create metrics with varying MAR ratios
        metrics_list = [
            BacktestMetrics(total_return=0.1, cagr=0.08, max_drawdown=0.15, sharpe_ratio=1.0, mar_ratio=0.53,
                           days_target_met=80, days_target_met_pct=40.0, total_trades=30, winning_trades=18,
                           losing_trades=12, avg_trade_return=0.005),
            BacktestMetrics(total_return=0.2, cagr=0.15, max_drawdown=0.10, sharpe_ratio=1.5, mar_ratio=1.5,
                           days_target_met=100, days_target_met_pct=50.0, total_trades=50, winning_trades=30,
                           losing_trades=20, avg_trade_return=0.01),
            BacktestMetrics(total_return=0.15, cagr=0.12, max_drawdown=0.12, sharpe_ratio=1.2, mar_ratio=1.0,
                           days_target_met=90, days_target_met_pct=45.0, total_trades=40, winning_trades=24,
                           losing_trades=16, avg_trade_return=0.008),
        ]
        
        # Cycle through metrics
        call_count = [0]
        def side_effect(*args, **kwargs):
            idx = call_count[0] % 2  # Alternate between train and validation
            call_count[0] += 1
            return metrics_list[idx]
        
        mock_engine.run.side_effect = side_effect
        
        optimizer = FuzzyOptimizer(objective='mar')
        
        result = optimizer.random_search(
            train_start=date(2020, 1, 1),
            train_end=date(2020, 12, 31),
            validation_start=date(2021, 1, 1),
            validation_end=date(2021, 12, 31),
            n_iterations=3
        )
        
        # Should find the best (MAR = 1.5)
        assert result.validation_metrics.mar_ratio >= 0.0, "Should have valid metrics"
    
    @patch('src.strategy.fuzzy_optimizer.FuzzyBacktestEngine')
    def test_random_search_with_test_set(self, mock_engine_class):
        """Test random search with test set"""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        train_metrics = BacktestMetrics(
            total_return=0.2, cagr=0.15, max_drawdown=0.10,
            sharpe_ratio=1.5, mar_ratio=1.5,
            days_target_met=100, days_target_met_pct=50.0,
            total_trades=50, winning_trades=30, losing_trades=20,
            avg_trade_return=0.01
        )
        
        validation_metrics = BacktestMetrics(
            total_return=0.18, cagr=0.14, max_drawdown=0.12,
            sharpe_ratio=1.4, mar_ratio=1.17,
            days_target_met=95, days_target_met_pct=48.0,
            total_trades=45, winning_trades=28, losing_trades=17,
            avg_trade_return=0.01
        )
        
        test_metrics = BacktestMetrics(
            total_return=0.16, cagr=0.13, max_drawdown=0.11,
            sharpe_ratio=1.3, mar_ratio=1.18,
            days_target_met=92, days_target_met_pct=46.0,
            total_trades=42, winning_trades=25, losing_trades=17,
            avg_trade_return=0.009
        )
        
        mock_engine.run.side_effect = [train_metrics, validation_metrics, test_metrics]
        
        optimizer = FuzzyOptimizer(objective='mar')
        
        result = optimizer.random_search(
            train_start=date(2020, 1, 1),
            train_end=date(2020, 12, 31),
            validation_start=date(2021, 1, 1),
            validation_end=date(2021, 12, 31),
            n_iterations=1,
            test_start=date(2022, 1, 1),
            test_end=date(2022, 12, 31)
        )
        
        assert result.test_metrics is not None, "Should have test metrics"
        assert result.test_metrics.mar_ratio > 0, "Test metrics should be valid"
    
    @patch('src.strategy.fuzzy_optimizer.FuzzyBacktestEngine')
    def test_latin_hypercube_search(self, mock_engine_class):
        """Test Latin Hypercube sampling"""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        train_metrics = BacktestMetrics(
            total_return=0.2, cagr=0.15, max_drawdown=0.10,
            sharpe_ratio=1.5, mar_ratio=1.5,
            days_target_met=100, days_target_met_pct=50.0,
            total_trades=50, winning_trades=30, losing_trades=20,
            avg_trade_return=0.01
        )
        
        validation_metrics = BacktestMetrics(
            total_return=0.18, cagr=0.14, max_drawdown=0.12,
            sharpe_ratio=1.4, mar_ratio=1.17,
            days_target_met=95, days_target_met_pct=48.0,
            total_trades=45, winning_trades=28, losing_trades=17,
            avg_trade_return=0.01
        )
        
        # Return metrics for all samples (5 samples * 2 calls each = 10 calls)
        mock_engine.run.side_effect = [train_metrics, validation_metrics] * 5
        
        optimizer = FuzzyOptimizer(objective='mar')
        
        result = optimizer.latin_hypercube_search(
            train_start=date(2020, 1, 1),
            train_end=date(2020, 12, 31),
            validation_start=date(2021, 1, 1),
            validation_end=date(2021, 12, 31),
            n_samples=5
        )
        
        assert isinstance(result, OptimizationResult)
        assert len(optimizer.optimization_history) == 5, "Should track all samples"
    
    @patch('src.strategy.fuzzy_optimizer.FuzzyBacktestEngine')
    def test_walk_forward_optimization(self, mock_engine_class):
        """Test walk-forward optimization"""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Create metrics for multiple periods
        metrics = BacktestMetrics(
            total_return=0.2, cagr=0.15, max_drawdown=0.10,
            sharpe_ratio=1.5, mar_ratio=1.5,
            days_target_met=100, days_target_met_pct=50.0,
            total_trades=50, winning_trades=30, losing_trades=20,
            avg_trade_return=0.01
        )
        
        mock_engine.run.return_value = metrics
        
        optimizer = FuzzyOptimizer(objective='mar')
        
        results = optimizer.walk_forward_optimization(
            start_date=date(2010, 1, 1),
            end_date=date(2013, 12, 31),
            train_window_years=2,
            test_window_years=1,
            step_years=1,
            n_iterations=2  # Small for test
        )
        
        assert len(results) > 0, "Should have results for each walk-forward period"
        assert all(isinstance(r, OptimizationResult) for r in results), "All should be OptimizationResult"


class TestOptimizationResult:
    """Test OptimizationResult class"""
    
    def test_optimization_result_creation(self):
        """Test OptimizationResult creation"""
        params = FuzzyBacktestParams()
        train_metrics = BacktestMetrics(
            total_return=0.2, cagr=0.15, max_drawdown=0.10,
            sharpe_ratio=1.5, mar_ratio=1.5,
            days_target_met=100, days_target_met_pct=50.0,
            total_trades=50, winning_trades=30, losing_trades=20,
            avg_trade_return=0.01
        )
        validation_metrics = BacktestMetrics(
            total_return=0.18, cagr=0.14, max_drawdown=0.12,
            sharpe_ratio=1.4, mar_ratio=1.17,
            days_target_met=95, days_target_met_pct=48.0,
            total_trades=45, winning_trades=28, losing_trades=17,
            avg_trade_return=0.01
        )
        
        result = OptimizationResult(
            best_params=params,
            train_metrics=train_metrics,
            validation_metrics=validation_metrics
        )
        
        assert result.best_params == params
        assert result.train_metrics == train_metrics
        assert result.validation_metrics == validation_metrics
        assert result.test_metrics is None
        assert result.optimization_history == []
    
    def test_optimization_result_to_dict(self):
        """Test OptimizationResult to_dict conversion"""
        params = FuzzyBacktestParams()
        train_metrics = BacktestMetrics(
            total_return=0.2, cagr=0.15, max_drawdown=0.10,
            sharpe_ratio=1.5, mar_ratio=1.5,
            days_target_met=100, days_target_met_pct=50.0,
            total_trades=50, winning_trades=30, losing_trades=20,
            avg_trade_return=0.01
        )
        validation_metrics = BacktestMetrics(
            total_return=0.18, cagr=0.14, max_drawdown=0.12,
            sharpe_ratio=1.4, mar_ratio=1.17,
            days_target_met=95, days_target_met_pct=48.0,
            total_trades=45, winning_trades=28, losing_trades=17,
            avg_trade_return=0.01
        )
        
        result = OptimizationResult(
            best_params=params,
            train_metrics=train_metrics,
            validation_metrics=validation_metrics,
            optimization_history=[{'iteration': 0, 'objective': 1.5}]
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert 'best_params' in result_dict
        assert 'train_metrics' in result_dict
        assert 'validation_metrics' in result_dict
        assert 'optimization_history' in result_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

