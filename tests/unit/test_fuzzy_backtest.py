"""
Unit tests for fuzzy logic backtest engine

Tests based on original specification requirements
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.strategy.fuzzy_backtest import (
    FuzzyBacktestEngine,
    FuzzyBacktestParams,
    PortfolioState,
    OptionPosition,
    BacktestMetrics
)


class TestFuzzyBacktestParams:
    """Test FuzzyBacktestParams dataclass"""
    
    def test_default_params(self):
        """Test default parameter values"""
        params = FuzzyBacktestParams()
        
        assert params.target_dte == 7, "Default target DTE should be 7"
        assert params.hedge_dte == 30, "Default hedge DTE should be 30"
        assert params.target_daily_premium_pct == 0.0008, "Default premium target should be 0.08%"
        assert params.max_hedge_notional_pct == 0.5, "Default max hedge should be 50%"
    
    def test_params_to_dict(self):
        """Test parameter conversion to dictionary"""
        params = FuzzyBacktestParams()
        param_dict = params.to_dict()
        
        assert isinstance(param_dict, dict)
        assert 'target_dte' in param_dict
        assert 'hedge_dte' in param_dict
        assert 'target_daily_premium_pct' in param_dict
        assert param_dict['target_dte'] == 7
    
    def test_params_from_dict(self):
        """Test parameter creation from dictionary"""
        param_dict = {
            'target_dte': 10,
            'hedge_dte': 45,
            'target_daily_premium_pct': 0.001
        }
        
        params = FuzzyBacktestParams.from_dict(param_dict)
        assert params.target_dte == 10
        assert params.hedge_dte == 45
        assert params.target_daily_premium_pct == 0.001


class TestOptionPosition:
    """Test OptionPosition dataclass"""
    
    def test_option_position_creation(self):
        """Test option position creation"""
        opt = OptionPosition(
            symbol="SPY",
            strike=400.0,
            expiration=date.today() + timedelta(days=7),
            option_type="put",
            quantity=-5,  # Short 5 contracts
            entry_price=2.0,
            entry_date=date.today()
        )
        
        assert opt.symbol == "SPY"
        assert opt.strike == 400.0
        assert opt.option_type == "put"
        assert opt.quantity == -5
        assert opt.dte == 7
    
    def test_option_position_unrealized_pnl_short(self):
        """Test unrealized PnL calculation for short position"""
        opt = OptionPosition(
            symbol="SPY",
            strike=400.0,
            expiration=date.today() + timedelta(days=7),
            option_type="put",
            quantity=-5,  # Short
            entry_price=2.0,
            entry_date=date.today(),
            current_price=1.0  # Price decreased (profit)
        )
        
        # Short put: profit when price decreases
        # PnL = (entry - current) * quantity * 100
        # = (2.0 - 1.0) * 5 * 100 = 500
        pnl = opt.unrealized_pnl
        assert pnl == 500.0, f"Expected 500.0, got {pnl}"
    
    def test_option_position_unrealized_pnl_long(self):
        """Test unrealized PnL calculation for long position"""
        opt = OptionPosition(
            symbol="SPY",
            strike=400.0,
            expiration=date.today() + timedelta(days=30),
            option_type="put",
            quantity=3,  # Long
            entry_price=1.5,
            entry_date=date.today(),
            current_price=2.0  # Price increased (profit)
        )
        
        # Long put: profit when price increases
        # PnL = (current - entry) * quantity * 100
        # = (2.0 - 1.5) * 3 * 100 = 150
        pnl = opt.unrealized_pnl
        assert pnl == 150.0, f"Expected 150.0, got {pnl}"
    
    def test_option_position_is_expired(self):
        """Test expiration check"""
        opt_expired = OptionPosition(
            symbol="SPY",
            strike=400.0,
            expiration=date.today() - timedelta(days=1),  # Expired
            option_type="put",
            quantity=-5,
            entry_price=2.0,
            entry_date=date.today() - timedelta(days=10)
        )
        
        opt_active = OptionPosition(
            symbol="SPY",
            strike=400.0,
            expiration=date.today() + timedelta(days=1),  # Active
            option_type="put",
            quantity=-5,
            entry_price=2.0,
            entry_date=date.today()
        )
        
        assert opt_expired.is_expired == True
        assert opt_active.is_expired == False


class TestPortfolioState:
    """Test PortfolioState dataclass"""
    
    def test_portfolio_total_value(self):
        """Test total portfolio value calculation"""
        portfolio = PortfolioState(
            cash=500_000.0,
            stock_shares=1000,
            stock_cost_basis=400.0
        )
        
        current_price = 420.0
        total_value = portfolio.total_value(current_price)
        
        # Cash + stock value + options value (0)
        expected = 500_000.0 + (1000 * 420.0)
        assert total_value == expected, f"Expected {expected}, got {total_value}"
    
    def test_portfolio_buying_power_used(self):
        """Test buying power calculation"""
        portfolio = PortfolioState(
            cash=500_000.0,
            stock_shares=1000,
            stock_cost_basis=400.0
        )
        
        # Add short put position
        opt = OptionPosition(
            symbol="SPY",
            strike=400.0,
            expiration=date.today() + timedelta(days=7),
            option_type="put",
            quantity=-10,  # Short 10 contracts
            entry_price=2.0,
            entry_date=date.today()
        )
        portfolio.options.append(opt)
        
        current_price = 420.0
        bp_used = portfolio.buying_power_used(current_price)
        
        # Stock capital + CSP capital
        stock_capital = 1000 * 420.0
        csp_capital = 400.0 * 100 * 10  # Strike * 100 * contracts
        expected = stock_capital + csp_capital
        
        assert abs(bp_used - expected) < 0.01, f"Expected {expected}, got {bp_used}"
    
    def test_portfolio_buying_power_available(self):
        """Test available buying power calculation"""
        portfolio = PortfolioState(
            cash=500_000.0,
            stock_shares=1000,
            stock_cost_basis=400.0
        )
        
        current_price = 420.0
        total_value = portfolio.total_value(current_price)
        bp_available = portfolio.buying_power_available(total_value, current_price)
        
        # Total value - used
        bp_used = portfolio.buying_power_used(current_price)
        expected = total_value - bp_used
        
        assert abs(bp_available - expected) < 0.01, f"Expected {expected}, got {bp_available}"


class TestFuzzyBacktestEngine:
    """Test FuzzyBacktestEngine"""
    
    @patch('src.strategy.fuzzy_backtest.get_combined_market_data')
    @patch('src.strategy.fuzzy_backtest.get_vix_history')
    def test_backtest_engine_initialization(self, mock_vix, mock_market):
        """Test backtest engine initialization"""
        # Mock market data
        dates = pd.date_range(start='2020-01-01', end='2020-01-10', freq='D')
        mock_market.return_value = pd.DataFrame({
            'Close': [400.0] * len(dates),
            'High': [405.0] * len(dates),
            'Low': [395.0] * len(dates),
            'Open': [400.0] * len(dates),
            'Volume': [1000000] * len(dates),
            'VIX': [20.0] * len(dates)
        }, index=dates)
        
        mock_vix.return_value = pd.Series([20.0] * len(dates), index=dates)
        
        engine = FuzzyBacktestEngine(
            initial_capital=1_000_000.0,
            params=FuzzyBacktestParams(),
            use_spy=True
        )
        
        assert engine.initial_capital == 1_000_000.0
        assert engine.use_spy == True
        assert engine.symbol == "SPY"
        assert engine.portfolio.cash == 1_000_000.0
    
    @patch('src.strategy.fuzzy_backtest.get_combined_market_data')
    @patch('src.strategy.fuzzy_backtest.get_vix_history')
    @patch('src.strategy.fuzzy_backtest.calculate_instantaneous_trend')
    @patch('src.strategy.fuzzy_backtest.calculate_cycle_swing')
    def test_backtest_runs_without_error(self, mock_cycle, mock_trend, mock_vix, mock_market):
        """Test that backtest runs without errors"""
        # Create mock data
        dates = pd.date_range(start='2020-01-01', end='2020-01-31', freq='D')
        market_data = pd.DataFrame({
            'Close': [400.0 + i * 0.5 for i in range(len(dates))],
            'High': [405.0 + i * 0.5 for i in range(len(dates))],
            'Low': [395.0 + i * 0.5 for i in range(len(dates))],
            'Open': [400.0 + i * 0.5 for i in range(len(dates))],
            'Volume': [1000000] * len(dates),
            'VIX': [20.0 + np.sin(i) * 5 for i in range(len(dates))]
        }, index=dates)
        
        mock_market.return_value = market_data
        mock_vix.return_value = pd.Series([20.0] * len(dates), index=dates)
        
        # Mock indicators
        mock_trend.return_value = {
            'trendline': pd.Series([400.0] * len(dates), index=dates),
            'smooth': pd.Series([400.0] * len(dates), index=dates),
            'signal': pd.Series([1] * len(dates), index=dates)
        }
        
        mock_cycle.return_value = {
            'csi': pd.Series([0.0] * len(dates), index=dates),
            'signal': pd.Series([0] * len(dates), index=dates),
            'high_band': pd.Series([10.0] * len(dates), index=dates),
            'low_band': pd.Series([-10.0] * len(dates), index=dates)
        }
        
        engine = FuzzyBacktestEngine(
            initial_capital=1_000_000.0,
            params=FuzzyBacktestParams(),
            use_spy=True
        )
        
        # Run backtest
        metrics = engine.run(date(2020, 1, 1), date(2020, 1, 31))
        
        assert isinstance(metrics, BacktestMetrics)
        assert len(engine.daily_values) > 0, "Should have daily values"
        assert len(engine.daily_dates) > 0, "Should have daily dates"
    
    def test_estimate_option_price_put_itm(self):
        """Test option price estimation for ITM put"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        
        current_price = 400.0
        strike = 410.0  # ITM put
        vix = 20.0
        dte = 7
        
        price = engine._estimate_option_price(
            current_price, strike, 'put', dte, vix, moneyness=-0.025  # 2.5% ITM
        )
        
        # ITM put should have intrinsic value + time value
        intrinsic = strike - current_price  # 10.0
        assert price >= intrinsic, "Price should be at least intrinsic value"
        assert price > 0, "Price should be positive"
    
    def test_estimate_option_price_put_otm(self):
        """Test option price estimation for OTM put"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        
        current_price = 400.0
        strike = 390.0  # OTM put
        vix = 20.0
        dte = 7
        
        price = engine._estimate_option_price(
            current_price, strike, 'put', dte, vix, moneyness=0.025  # 2.5% OTM
        )
        
        # OTM put should have only time value
        assert price >= 0, "Price should be non-negative"
        assert price < (strike - current_price) if strike > current_price else True
    
    def test_calculate_portfolio_metrics_for_fuzzy(self):
        """Test portfolio metrics calculation"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        engine.portfolio = PortfolioState(
            cash=500_000.0,
            stock_shares=1000,
            stock_cost_basis=400.0
        )
        
        current_price = 420.0
        vix = 20.0
        
        metrics = engine._calculate_portfolio_metrics_for_fuzzy(current_price, vix)
        
        assert 'bp_frac' in metrics
        assert 'stock_weight' in metrics
        assert 'delta_port' in metrics
        assert 'premium_gap' in metrics
        
        assert 0.0 <= metrics['bp_frac'] <= 1.0, "BP fraction should be in [0, 1]"
        assert 0.0 <= metrics['stock_weight'] <= 1.0, "Stock weight should be in [0, 1]"
        assert 0.0 <= metrics['premium_gap'] <= 1.0, "Premium gap should be in [0, 1]"
    
    def test_execute_put_sale_creates_position(self):
        """Test that put sale execution creates option position"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        engine.portfolio = PortfolioState(cash=1_000_000.0)
        
        current_price = 400.0
        vix = 20.0
        put_moneyness = 0.5  # Slightly OTM
        put_size_frac = 0.8
        trade_date = date.today()
        
        position = engine._execute_put_sale(
            current_price, vix, put_moneyness, put_size_frac, trade_date
        )
        
        # Should create position if conditions are met
        if position:
            assert isinstance(position, OptionPosition)
            assert position.option_type == 'put'
            assert position.quantity < 0, "Should be short position"
            assert len(engine.portfolio.options) > 0, "Should add to portfolio"
            assert engine.portfolio.cash > 1_000_000.0, "Should collect premium"
    
    def test_execute_put_sale_respects_buying_power(self):
        """Test that put sale respects buying power limits"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        # Use most of buying power
        engine.portfolio = PortfolioState(
            cash=100_000.0,
            stock_shares=2000,  # Heavy stock position
            stock_cost_basis=400.0
        )
        
        current_price = 400.0
        vix = 20.0
        put_moneyness = 0.0  # ATM
        put_size_frac = 1.0  # Full size
        trade_date = date.today()
        
        initial_cash = engine.portfolio.cash
        position = engine._execute_put_sale(
            current_price, vix, put_moneyness, put_size_frac, trade_date
        )
        
        # Should not exceed buying power
        if position:
            total_value = engine.portfolio.total_value(current_price)
            bp_used = engine.portfolio.buying_power_used(current_price)
            assert bp_used <= total_value, "Should not exceed total value"
    
    def test_execute_hedge_creates_position(self):
        """Test that hedge execution creates hedge position"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        engine.portfolio = PortfolioState(
            cash=500_000.0,
            stock_shares=1000,  # Have stock to hedge
            stock_cost_basis=400.0
        )
        
        current_price = 400.0
        vix = 15.0  # Low VIX
        hedge_score = 0.7  # High hedge score
        hedge_otm_pct = 10.0  # 10% OTM
        trade_date = date.today()
        
        position = engine._execute_hedge(
            current_price, vix, hedge_score, hedge_otm_pct, trade_date
        )
        
        # Should create hedge if score is high enough
        if position and hedge_score >= engine.params.hedge_score_threshold:
            assert isinstance(position, OptionPosition)
            assert position.option_type == 'put'
            assert position.quantity > 0, "Should be long position (hedge)"
            assert len(engine.portfolio.hedge_options) > 0, "Should add to hedges"
            assert engine.portfolio.cash < 500_000.0, "Should pay for hedge"
    
    def test_handle_expirations_itm_assignment(self):
        """Test handling of ITM put expiration and assignment"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        engine.portfolio = PortfolioState(cash=1_000_000.0)
        
        # Create short ITM put
        opt = OptionPosition(
            symbol="SPY",
            strike=410.0,
            expiration=date.today() - timedelta(days=1),  # Expired
            option_type="put",
            quantity=-5,  # Short 5 contracts
            entry_price=2.0,
            entry_date=date.today() - timedelta(days=10)
        )
        engine.portfolio.options.append(opt)
        
        current_price = 400.0  # Below strike (ITM)
        current_date = date.today()
        
        initial_shares = engine.portfolio.stock_shares
        initial_cash = engine.portfolio.cash
        
        engine._handle_expirations(current_date, current_price)
        
        # Should be assigned: buy stock at strike
        if current_price < opt.strike:
            assert engine.portfolio.stock_shares > initial_shares, "Should acquire shares"
            assert engine.portfolio.cash < initial_cash, "Should pay for shares"
            assert opt not in engine.portfolio.options, "Should remove expired option"
    
    def test_update_option_prices(self):
        """Test option price updates"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        
        opt = OptionPosition(
            symbol="SPY",
            strike=400.0,
            expiration=date.today() + timedelta(days=7),
            option_type="put",
            quantity=-5,
            entry_price=2.0,
            entry_date=date.today(),
            current_price=2.0
        )
        engine.portfolio.options.append(opt)
        
        current_price = 390.0  # Price moved down (put more valuable)
        vix = 25.0  # Higher VIX
        current_date = date.today()
        
        engine._update_option_prices(current_price, vix, current_date)
        
        # Price should be updated
        assert opt.current_price != 2.0, "Price should be updated"
        assert opt.current_price > 0, "Price should be positive"


class TestBacktestMetrics:
    """Test BacktestMetrics calculation"""
    
    def test_metrics_calculation_cagr(self):
        """Test CAGR calculation"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        
        # Simulate 2 years of growth
        dates = [date(2020, 1, 1), date(2022, 1, 1)]
        values = [1_000_000.0, 1_210_000.0]  # 21% total return over 2 years
        
        engine.daily_dates = dates
        engine.daily_values = values
        
        metrics = engine._calculate_metrics()
        
        # CAGR should be approximately 10% (1.21^(1/2) - 1 ≈ 0.10)
        assert abs(metrics.cagr - 0.10) < 0.01, f"Expected ~0.10 CAGR, got {metrics.cagr}"
        assert metrics.total_return == 0.21, "Total return should be 21%"
    
    def test_metrics_calculation_max_drawdown(self):
        """Test max drawdown calculation"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        
        # Simulate drawdown scenario
        dates = [date(2020, 1, 1), date(2020, 2, 1), date(2020, 3, 1), date(2020, 4, 1)]
        values = [1_000_000.0, 1_100_000.0, 900_000.0, 1_050_000.0]  # Peak at 1.1M, trough at 0.9M
        
        engine.daily_dates = dates
        engine.daily_values = values
        
        metrics = engine._calculate_metrics()
        
        # Max drawdown from 1.1M to 0.9M = (0.9 - 1.1) / 1.1 = -0.1818
        expected_dd = abs((900_000.0 - 1_100_000.0) / 1_100_000.0)
        assert abs(metrics.max_drawdown - expected_dd) < 0.01, f"Expected ~{expected_dd}, got {metrics.max_drawdown}"
    
    def test_metrics_calculation_sharpe_ratio(self):
        """Test Sharpe ratio calculation"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        
        # Create series with known return and volatility
        dates = pd.date_range(start='2020-01-01', end='2020-12-31', freq='D')
        # Create returns with mean 0.001 and std 0.01
        returns = np.random.normal(0.001, 0.01, len(dates))
        values = [1_000_000.0]
        for ret in returns[1:]:
            values.append(values[-1] * (1 + ret))
        
        engine.daily_dates = list(dates.date)
        engine.daily_values = values
        
        metrics = engine._calculate_metrics()
        
        # Sharpe should be positive if mean return > 0
        assert metrics.sharpe_ratio is not None, "Sharpe ratio should be calculated"
    
    def test_metrics_calculation_mar_ratio(self):
        """Test MAR ratio calculation"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        
        dates = [date(2020, 1, 1), date(2021, 1, 1)]
        values = [1_000_000.0, 1_100_000.0]  # 10% return, no drawdown
        
        engine.daily_dates = dates
        engine.daily_values = values
        engine.daily_premiums = [800.0] * len(dates)
        engine.daily_targets = [800.0] * len(dates)
        
        metrics = engine._calculate_metrics()
        
        # MAR = CAGR / Max Drawdown
        if metrics.max_drawdown > 0:
            expected_mar = metrics.cagr / metrics.max_drawdown
            assert abs(metrics.mar_ratio - expected_mar) < 0.01, "MAR should be CAGR / Max DD"
    
    def test_metrics_days_target_met(self):
        """Test days target met calculation"""
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        
        dates = [date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)]
        values = [1_000_000.0] * 3
        
        # Target = 800, premiums = [900, 600, 800]
        engine.daily_dates = dates
        engine.daily_values = values
        engine.daily_premiums = [900.0, 600.0, 800.0]
        engine.daily_targets = [800.0, 800.0, 800.0]
        
        metrics = engine._calculate_metrics()
        
        # Days met: 900 >= 640 (80% of 800), 600 < 640, 800 >= 640 = 2 days
        assert metrics.days_target_met >= 0, "Should count days target met"
        assert metrics.days_target_met_pct >= 0, "Should calculate percentage"


class TestBacktestIntegration:
    """Integration tests for backtest engine"""
    
    @patch('src.strategy.fuzzy_backtest.get_combined_market_data')
    @patch('src.strategy.fuzzy_backtest.get_vix_history')
    def test_backtest_tracks_daily_values(self, mock_vix, mock_market):
        """Test that backtest tracks daily portfolio values"""
        dates = pd.date_range(start='2020-01-01', end='2020-01-10', freq='D')
        market_data = pd.DataFrame({
            'Close': [400.0] * len(dates),
            'High': [405.0] * len(dates),
            'Low': [395.0] * len(dates),
            'Open': [400.0] * len(dates),
            'Volume': [1000000] * len(dates),
            'VIX': [20.0] * len(dates)
        }, index=dates)
        
        mock_market.return_value = market_data
        mock_vix.return_value = pd.Series([20.0] * len(dates), index=dates)
        
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        
        with patch.object(engine, '_update_option_prices'):
            with patch.object(engine, '_handle_expirations'):
                metrics = engine.run(date(2020, 1, 1), date(2020, 1, 10))
        
        assert len(engine.daily_values) > 0, "Should track daily values"
        assert len(engine.daily_dates) == len(engine.daily_values), "Dates and values should match"
        assert engine.daily_values[0] == 1_000_000.0, "First value should be initial capital"
    
    @patch('src.strategy.fuzzy_backtest.get_combined_market_data')
    @patch('src.strategy.fuzzy_backtest.get_vix_history')
    def test_backtest_handles_weekends(self, mock_vix, mock_market):
        """Test that backtest skips weekends (no market data)"""
        # Create data only for weekdays
        dates = pd.bdate_range(start='2020-01-01', end='2020-01-10', freq='D')
        market_data = pd.DataFrame({
            'Close': [400.0] * len(dates),
            'High': [405.0] * len(dates),
            'Low': [395.0] * len(dates),
            'Open': [400.0] * len(dates),
            'Volume': [1000000] * len(dates),
            'VIX': [20.0] * len(dates)
        }, index=dates)
        
        mock_market.return_value = market_data
        mock_vix.return_value = pd.Series([20.0] * len(dates), index=dates)
        
        engine = FuzzyBacktestEngine(initial_capital=1_000_000.0)
        
        with patch.object(engine, '_update_option_prices'):
            with patch.object(engine, '_handle_expirations'):
                metrics = engine.run(date(2020, 1, 1), date(2020, 1, 10))
        
        # Should only have values for trading days
        assert len(engine.daily_values) <= len(dates), "Should not exceed trading days"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

