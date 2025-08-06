import pytest
from datetime import datetime
from wheeltracker.models import Trade
from wheeltracker.calculations import cost_basis


class TestCostBasis:
    def test_all_puts_closed(self):
        """Test scenario where all puts are closed (no assignment)."""
        trades = [
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,  # $5 premium
                side="sell",
                timestamp=datetime.now(),
                strategy="put"
            ),
            Trade(
                symbol="AAPL",
                quantity=1,
                price=2.0,  # $2 premium to close
                side="buy",
                timestamp=datetime.now(),
                strategy="put"
            )
        ]
        
        result = cost_basis(trades)
        
        # Net premium received: ($5 - $2) * 100 = $300
        assert result['shares'] == 0  # No shares owned
        assert result['basis_without_premium'] == 0  # No stock basis
        assert result['net_premium'] == 300.0  # $300 net premium received
        assert result['basis_with_premium'] == -300.0  # Negative basis (profit)
    
    def test_puts_assigned_then_covered_calls(self):
        """Test scenario where puts are assigned, then covered calls sold."""
        trades = [
            # Sell put
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,  # $5 premium
                side="sell",
                timestamp=datetime.now(),
                strategy="put"
            ),
            # Put gets assigned (buy shares at strike)
            Trade(
                symbol="AAPL",
                quantity=100,
                price=150.0,  # Strike price
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"  # Assignment
            ),
            # Sell covered call
            Trade(
                symbol="AAPL",
                quantity=1,
                price=3.0,  # $3 premium
                side="sell",
                timestamp=datetime.now(),
                strategy="call"
            )
        ]
        
        result = cost_basis(trades)
        
        # Own 100 shares, paid $15000, received $800 in premiums
        assert result['shares'] == 100
        assert result['basis_without_premium'] == 150.0  # $15000 / 100 shares
        assert result['net_premium'] == 800.0  # ($5 + $3) * 100 premiums received
        assert result['basis_with_premium'] == 142.0  # ($15000 - $800) / 100 shares
    
    def test_partial_exercises(self):
        """Test scenario with partial option exercises."""
        trades = [
            # Sell 2 puts
            Trade(
                symbol="AAPL",
                quantity=2,
                price=5.0,  # $5 premium each
                side="sell",
                timestamp=datetime.now(),
                strategy="put"
            ),
            # One put gets assigned
            Trade(
                symbol="AAPL",
                quantity=100,
                price=150.0,  # Strike price
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"  # Assignment
            ),
            # Close the other put
            Trade(
                symbol="AAPL",
                quantity=1,
                price=2.0,  # $2 premium to close
                side="buy",
                timestamp=datetime.now(),
                strategy="put"
            )
        ]
        
        result = cost_basis(trades)
        
        # Own 100 shares, paid $15000, received $800 in premiums ($10 - $2) * 100
        assert result['shares'] == 100
        assert result['basis_without_premium'] == 150.0  # $15000 / 100 shares
        assert result['net_premium'] == 800.0  # ($10 - $2) * 100 premiums
        assert result['basis_with_premium'] == 142.0  # ($15000 - $800) / 100 shares
    
    def test_stock_only_trades(self):
        """Test scenario with only stock trades (no options)."""
        trades = [
            # Buy 100 shares
            Trade(
                symbol="AAPL",
                quantity=100,
                price=150.0,
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"
            ),
            # Sell 50 shares
            Trade(
                symbol="AAPL",
                quantity=50,
                price=160.0,
                side="sell",
                timestamp=datetime.now(),
                strategy="stock"
            )
        ]
        
        result = cost_basis(trades)
        
        # Own 50 shares, basis reduced proportionally
        assert result['shares'] == 50
        assert result['basis_without_premium'] == 150.0  # $7500 / 50 shares
        assert result['net_premium'] == 0.0  # No options
        assert result['basis_with_premium'] == 150.0  # Same as without premium
    
    def test_complex_wheel_strategy(self):
        """Test a complex wheel strategy with multiple cycles."""
        trades = [
            # Sell put
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,
                side="sell",
                timestamp=datetime.now(),
                strategy="put"
            ),
            # Put assigned
            Trade(
                symbol="AAPL",
                quantity=100,
                price=150.0,
                side="buy",
                timestamp=datetime.now(),
                strategy="stock"
            ),
            # Sell covered call
            Trade(
                symbol="AAPL",
                quantity=1,
                price=3.0,
                side="sell",
                timestamp=datetime.now(),
                strategy="call"
            ),
            # Call assigned (shares called away)
            Trade(
                symbol="AAPL",
                quantity=100,
                price=160.0,
                side="sell",
                timestamp=datetime.now(),
                strategy="stock"
            ),
            # Sell another put
            Trade(
                symbol="AAPL",
                quantity=1,
                price=4.0,
                side="sell",
                timestamp=datetime.now(),
                strategy="put"
            )
        ]
        
        result = cost_basis(trades)
        
        # No shares owned, but received premiums and profit from stock sale
        assert result['shares'] == 0
        assert result['basis_without_premium'] == 0  # No shares
        assert result['net_premium'] == 1200.0  # ($5 + $3 + $4) * 100 premiums
        assert result['basis_with_premium'] == -1200.0  # Negative basis (profit)
    
    def test_empty_trades(self):
        """Test with empty trade list."""
        result = cost_basis([])
        
        assert result['shares'] == 0
        assert result['basis_without_premium'] == 0
        assert result['net_premium'] == 0
        assert result['basis_with_premium'] == 0 