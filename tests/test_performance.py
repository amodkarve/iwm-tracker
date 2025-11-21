"""
Tests for performance calculations
"""
import pytest
from datetime import datetime, timedelta
from src.wheeltracker.models import Trade
from src.analytics.performance import calculate_annual_return, get_performance_summary


class TestPerformanceCalculations:
    def test_annualized_return_same_day_trades(self):
        """Test that annualized return works correctly for same-day trades"""
        # Create trades on the same day
        today = datetime.now()
        trades = [
            Trade(
                symbol="IWM",
                quantity=1,
                price=0.80,
                side="sell",
                timestamp=today,
                strategy="wheel",
                expiration_date=today + timedelta(days=30),
                strike_price=200.0,
                option_type="put",
            )
        ]
        
        # Calculate annual return for same-day trades
        result = calculate_annual_return(
            trades=trades,
            start_date=today,
            end_date=today,
            initial_account_value=100000.0
        )
        
        # Should not return 0.0 due to division by zero
        # Should use at least 1 day for calculation
        assert result['days'] >= 1
        assert result['total_premium'] == 80.0  # 1 contract * $0.80 * 100
        assert result['total_return'] == 80.0 / 100000.0
        # Annualized return should be calculated (not 0.0)
        assert result['annualized_return'] != 0.0
        assert result['annualized_return'] > 0  # Should be positive for premium received

    def test_annualized_return_multiple_days(self):
        """Test annualized return calculation over multiple days"""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        trades = [
            Trade(
                symbol="IWM",
                quantity=1,
                price=0.80,
                side="sell",
                timestamp=start_date,
                strategy="wheel",
                expiration_date=start_date + timedelta(days=30),
                strike_price=200.0,
                option_type="put",
            )
        ]
        
        result = calculate_annual_return(
            trades=trades,
            start_date=start_date,
            end_date=end_date,
            initial_account_value=100000.0
        )
        
        assert result['days'] == 30
        assert result['total_premium'] == 80.0
        assert result['total_return'] == 80.0 / 100000.0
        # Annualized return should be calculated
        assert result['annualized_return'] != 0.0

    def test_annualized_return_no_option_trades(self):
        """Test that stock-only trades return 0 annualized return"""
        today = datetime.now()
        trades = [
            Trade(
                symbol="IWM",
                quantity=100,
                price=200.0,
                side="buy",
                timestamp=today,
                strategy="wheel",
                expiration_date=None,
                strike_price=None,
                option_type=None,  # Stock trade
            )
        ]
        
        result = calculate_annual_return(
            trades=trades,
            start_date=today,
            end_date=today,
            initial_account_value=100000.0
        )
        
        # Stock trades don't contribute to premium, so annualized return should be 0
        assert result['total_premium'] == 0.0
        assert result['total_return'] == 0.0
        assert result['annualized_return'] == 0.0

    def test_get_performance_summary_with_trades(self):
        """Test get_performance_summary returns correct structure"""
        today = datetime.now()
        trades = [
            Trade(
                symbol="IWM",
                quantity=1,
                price=0.80,
                side="sell",
                timestamp=today,
                strategy="wheel",
                expiration_date=today + timedelta(days=30),
                strike_price=200.0,
                option_type="put",
            )
        ]
        
        result = get_performance_summary(
            trades=trades,
            account_value=100000.0,
            initial_account_value=100000.0
        )
        
        # Should not have error key
        assert 'error' not in result
        # Should have annualized_return
        assert 'annualized_return' in result
        assert result['annualized_return'] >= 0  # Should be non-negative for premium received
        # Should have other required fields
        assert 'total_premium' in result
        assert 'days_active' in result
        assert 'on_track' in result

    def test_get_performance_summary_no_trades(self):
        """Test get_performance_summary with no trades"""
        result = get_performance_summary(
            trades=[],
            account_value=100000.0,
            initial_account_value=100000.0
        )
        
        # Should return error for no trades
        assert 'error' in result
        assert result['error'] == 'No trades available'

