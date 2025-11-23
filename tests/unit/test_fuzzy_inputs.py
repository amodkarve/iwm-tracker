"""
Unit tests for fuzzy input calculations

Tests functions that calculate fuzzy logic inputs from portfolio and market data
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.wheeltracker.models import Trade
from src.strategy.fuzzy_inputs import (
    normalize_vix,
    calculate_trend_normalized,
    calculate_cycle_normalized,
    calculate_portfolio_metrics,
    calculate_assigned_share_metrics,
    get_fuzzy_inputs
)


class TestNormalizeVIX:
    """Test VIX normalization"""
    
    def test_normalize_vix_with_history(self):
        """Test VIX normalization using historical percentile"""
        vix_history = pd.Series([10, 12, 15, 18, 20, 25, 30, 35, 40])
        vix_value = 20.0
        
        result = normalize_vix(vix_value, vix_history)
        # VIX 20 in range [10, 40] should normalize to approximately (20-10)/(40-10) = 0.33
        assert 0.0 <= result <= 1.0, "Normalized VIX should be in [0, 1]"
        assert abs(result - 0.33) < 0.1, "Should normalize correctly"
    
    def test_normalize_vix_min(self):
        """Test VIX normalization at minimum"""
        vix_history = pd.Series([10, 15, 20, 25, 30])
        vix_value = 10.0
        
        result = normalize_vix(vix_value, vix_history)
        assert result == 0.0, "Minimum VIX should normalize to 0.0"
    
    def test_normalize_vix_max(self):
        """Test VIX normalization at maximum"""
        vix_history = pd.Series([10, 15, 20, 25, 30])
        vix_value = 30.0
        
        result = normalize_vix(vix_value, vix_history)
        assert result == 1.0, "Maximum VIX should normalize to 1.0"
    
    def test_normalize_vix_fallback(self):
        """Test VIX normalization with fallback range (10-40)"""
        vix_value = 20.0
        
        result = normalize_vix(vix_value, None)
        # Using fallback range [10, 40], 20 should be (20-10)/(40-10) = 0.33
        assert 0.0 <= result <= 1.0, "Normalized VIX should be in [0, 1]"
        assert abs(result - 0.33) < 0.1, "Should use fallback range"
    
    def test_normalize_vix_clamping(self):
        """Test VIX normalization clamps to [0, 1]"""
        vix_value = 5.0  # Below minimum
        
        result = normalize_vix(vix_value, None)
        assert result == 0.0, "Below minimum should clamp to 0.0"
        
        vix_value = 50.0  # Above maximum
        
        result = normalize_vix(vix_value, None)
        assert result == 1.0, "Above maximum should clamp to 1.0"


class TestCalculateTrendNormalized:
    """Test trend normalization"""
    
    @patch('src.strategy.fuzzy_inputs.get_trend_signal')
    @patch('src.indicators.ehlers_trend.calculate_instantaneous_trend')
    def test_trend_normalized_from_signal(self, mock_calc, mock_signal):
        """Test trend normalization from signal"""
        mock_signal.return_value = 1  # Bullish
        mock_calc.return_value = {
            'trendline': pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109]),
            'smooth': pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        }
        
        hl2_series = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109] * 10)
        
        result = calculate_trend_normalized(hl2_series)
        assert -1.0 <= result <= 1.0, "Trend should be in [-1, 1]"
    
    def test_trend_normalized_empty_series(self):
        """Test trend normalization with empty series"""
        hl2_series = pd.Series([])
        
        result = calculate_trend_normalized(hl2_series)
        assert result == 0.0, "Empty series should return 0.0"
    
    def test_trend_normalized_insufficient_data(self):
        """Test trend normalization with insufficient data"""
        hl2_series = pd.Series([100, 101, 102])  # Less than 50 bars
        
        result = calculate_trend_normalized(hl2_series)
        assert result == 0.0, "Insufficient data should return 0.0"


class TestCalculateCycleNormalized:
    """Test cycle normalization"""
    
    @patch('src.indicators.cycle_swing.calculate_cycle_swing')
    def test_cycle_normalized_from_csi(self, mock_calc):
        """Test cycle normalization from CSI"""
        mock_calc.return_value = {
            'csi': pd.Series([-10, -5, 0, 5, 10]),
            'high_band': pd.Series([np.nan, np.nan, np.nan, 8.0, 8.0]),
            'low_band': pd.Series([np.nan, np.nan, np.nan, -8.0, -8.0])
        }
        
        price_series = pd.Series([100, 101, 102, 103, 104] * 20)
        
        result = calculate_cycle_normalized(price_series)
        assert -1.0 <= result <= 1.0, "Cycle should be in [-1, 1]"
    
    def test_cycle_normalized_empty_series(self):
        """Test cycle normalization with empty series"""
        price_series = pd.Series([])
        
        result = calculate_cycle_normalized(price_series)
        assert result == 0.0, "Empty series should return 0.0"
    
    def test_cycle_normalized_insufficient_data(self):
        """Test cycle normalization with insufficient data"""
        price_series = pd.Series([100, 101, 102])  # Less than 50 bars
        
        result = calculate_cycle_normalized(price_series)
        assert result == 0.0, "Insufficient data should return 0.0"


class TestCalculatePortfolioMetrics:
    """Test portfolio metrics calculation"""
    
    def test_portfolio_metrics_basic(self):
        """Test basic portfolio metrics calculation"""
        trades = [
            Trade(
                symbol="IWM",
                quantity=100,
                price=200.0,
                side="buy",
                timestamp=datetime.now(),
                option_type="stock"
            )
        ]
        account_value = 100000.0
        current_prices = {'IWM': 205.0}
        
        metrics = calculate_portfolio_metrics(trades, account_value, current_prices)
        
        assert 'bp_frac' in metrics
        assert 'stock_weight' in metrics
        assert 'delta_port' in metrics
        assert 'premium_gap' in metrics
        
        assert 0.0 <= metrics['bp_frac'] <= 1.0, "BP fraction should be in [0, 1]"
        assert 0.0 <= metrics['stock_weight'] <= 1.0, "Stock weight should be in [0, 1]"
        assert 0.0 <= metrics['premium_gap'] <= 1.0, "Premium gap should be in [0, 1]"
    
    def test_portfolio_metrics_no_trades(self):
        """Test portfolio metrics with no trades"""
        trades = []
        account_value = 100000.0
        current_prices = {'IWM': 200.0}
        
        metrics = calculate_portfolio_metrics(trades, account_value, current_prices)
        
        assert metrics['stock_weight'] == 0.0, "No trades should result in 0 stock weight"
        assert metrics['bp_frac'] > 0.0, "No trades should have available buying power"
    
    def test_portfolio_metrics_bp_frac_calculation(self):
        """Test buying power fraction calculation"""
        trades = [
            Trade(
                symbol="IWM",
                quantity=100,
                price=200.0,
                side="buy",
                timestamp=datetime.now(),
                option_type="stock"
            )
        ]
        account_value = 100000.0
        current_prices = {'IWM': 200.0}
        
        metrics = calculate_portfolio_metrics(trades, account_value, current_prices)
        
        # Stock capital = 100 * 200 = 20,000
        # BP usage = 20,000 / 100,000 = 0.2
        # BP frac = 1.0 - 0.2 = 0.8
        assert abs(metrics['bp_frac'] - 0.8) < 0.1, "BP fraction should be approximately 0.8"
    
    def test_portfolio_metrics_stock_weight(self):
        """Test stock weight calculation"""
        trades = [
            Trade(
                symbol="IWM",
                quantity=100,
                price=200.0,
                side="buy",
                timestamp=datetime.now(),
                option_type="stock"
            )
        ]
        account_value = 100000.0
        current_prices = {'IWM': 200.0}
        
        metrics = calculate_portfolio_metrics(trades, account_value, current_prices)
        
        # Stock weight = (100 * 200) / 100,000 = 0.2
        assert abs(metrics['stock_weight'] - 0.2) < 0.01, "Stock weight should be 0.2"


class TestCalculateAssignedShareMetrics:
    """Test assigned share metrics calculation"""
    
    def test_assigned_share_metrics_profit(self):
        """Test metrics for shares in profit"""
        trades = [
            Trade(
                symbol="IWM",
                quantity=100,
                price=190.0,  # Cost basis
                side="buy",
                timestamp=datetime.now() - timedelta(days=10),
                option_type="stock"
            )
        ]
        current_price = 200.0
        
        metrics = calculate_assigned_share_metrics(trades, "IWM", current_price)
        
        assert 'unreal_pnl_pct' in metrics
        assert 'iv_rank' in metrics
        assert 'days_since_assignment' in metrics
        assert 'cost_basis' in metrics
        
        # Unrealized PnL = (200 - 190) / 190 = 0.0526 (5.26%)
        assert metrics['unreal_pnl_pct'] > 0, "Should be in profit"
        assert abs(metrics['unreal_pnl_pct'] - 0.0526) < 0.01, "Should calculate PnL correctly"
        assert metrics['days_since_assignment'] == 10, "Should calculate days since assignment"
        assert metrics['cost_basis'] == 190.0, "Should return cost basis"
    
    def test_assigned_share_metrics_loss(self):
        """Test metrics for shares at a loss"""
        trades = [
            Trade(
                symbol="IWM",
                quantity=100,
                price=200.0,  # Cost basis
                side="buy",
                timestamp=datetime.now() - timedelta(days=5),
                option_type="stock"
            )
        ]
        current_price = 190.0
        
        metrics = calculate_assigned_share_metrics(trades, "IWM", current_price)
        
        # Unrealized PnL = (190 - 200) / 200 = -0.05 (-5%)
        assert metrics['unreal_pnl_pct'] < 0, "Should be at a loss"
        assert abs(metrics['unreal_pnl_pct'] - (-0.05)) < 0.01, "Should calculate loss correctly"
    
    def test_assigned_share_metrics_no_shares(self):
        """Test metrics when no shares owned"""
        trades = []
        current_price = 200.0
        
        metrics = calculate_assigned_share_metrics(trades, "IWM", current_price)
        
        assert metrics['unreal_pnl_pct'] == 0.0, "No shares should have 0 PnL"
        assert metrics['days_since_assignment'] == 0, "No shares should have 0 days"
        assert metrics['cost_basis'] == current_price, "Should use current price as default"


class TestGetFuzzyInputs:
    """Test get_fuzzy_inputs aggregation"""
    
    @patch('src.strategy.fuzzy_inputs.get_hl2_series')
    @patch('src.strategy.fuzzy_inputs.get_price_series')
    @patch('src.strategy.fuzzy_inputs.calculate_trend_normalized')
    @patch('src.strategy.fuzzy_inputs.calculate_cycle_normalized')
    @patch('src.strategy.fuzzy_inputs.calculate_portfolio_metrics')
    def test_get_fuzzy_inputs_complete(self, mock_portfolio, mock_cycle, mock_trend, 
                                        mock_price, mock_hl2):
        """Test complete fuzzy inputs aggregation"""
        mock_hl2.return_value = pd.Series([100, 101, 102] * 20)
        mock_price.return_value = pd.Series([100, 101, 102] * 20)
        mock_trend.return_value = 0.5
        mock_cycle.return_value = -0.3
        mock_portfolio.return_value = {
            'bp_frac': 0.6,
            'stock_weight': 0.4,
            'delta_port': 0.3,
            'premium_gap': 0.5
        }
        
        trades = []
        account_value = 100000.0
        
        inputs = get_fuzzy_inputs(trades, account_value, vix_value=20.0)
        
        assert 'trend' in inputs
        assert 'cycle' in inputs
        assert 'vix_norm' in inputs
        assert 'bp_frac' in inputs
        assert 'stock_weight' in inputs
        assert 'delta_port' in inputs
        assert 'premium_gap' in inputs
        
        assert -1.0 <= inputs['trend'] <= 1.0
        assert -1.0 <= inputs['cycle'] <= 1.0
        assert 0.0 <= inputs['vix_norm'] <= 1.0
        assert 0.0 <= inputs['bp_frac'] <= 1.0
        assert 0.0 <= inputs['stock_weight'] <= 1.0
        assert 0.0 <= inputs['premium_gap'] <= 1.0
    
    def test_get_fuzzy_inputs_defaults(self):
        """Test fuzzy inputs with defaults when data unavailable"""
        trades = []
        account_value = 100000.0
        
        with patch('src.strategy.fuzzy_inputs.get_hl2_series', return_value=pd.Series([])):
            with patch('src.strategy.fuzzy_inputs.get_price_series', return_value=pd.Series([])):
                inputs = get_fuzzy_inputs(trades, account_value)
                
                assert inputs['trend'] == 0.0, "Should default to 0.0"
                assert inputs['cycle'] == 0.0, "Should default to 0.0"
                assert inputs['vix_norm'] == 0.5, "Should default to 0.5"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

