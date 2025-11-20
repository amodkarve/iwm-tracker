import pytest
from datetime import datetime
from wheeltracker.models import Trade
from wheeltracker.db import Database
from wheeltracker.calculations import cost_basis


class TestOptionContracts:
    def test_option_contract_details(self):
        """Test that option contract details are properly captured."""
        # Create in-memory database
        db = Database(":memory:")
        
        # Create a put option trade with contract details
        put_trade = Trade(
            symbol="AAPL",
            quantity=1,
            price=5.0,  # $5 premium per share
            side="sell",
            timestamp=datetime.now(),
            strategy="wheel",
            expiration_date=datetime(2025, 8, 5),  # Aug 5 2025
            strike_price=219.0,  # $219 strike
            option_type="put"
        )
        
        # Insert the trade
        inserted_trade = db.insert_trade(put_trade)
        
        # Verify the trade was inserted with option details
        assert inserted_trade.id is not None
        assert inserted_trade.symbol == "AAPL"
        assert inserted_trade.quantity == 1
        assert inserted_trade.price == 5.0
        assert inserted_trade.side == "sell"
        assert inserted_trade.strategy == "wheel"
        assert inserted_trade.expiration_date == datetime(2025, 8, 5)
        assert inserted_trade.strike_price == 219.0
        assert inserted_trade.option_type == "put"
        
        # Retrieve all trades
        trades = db.list_trades()
        
        # Verify we got the trade back with option details
        assert len(trades) == 1
        retrieved_trade = trades[0]
        assert retrieved_trade.id == inserted_trade.id
        assert retrieved_trade.symbol == "AAPL"
        assert retrieved_trade.quantity == 1
        assert retrieved_trade.price == 5.0
        assert retrieved_trade.side == "sell"
        assert retrieved_trade.strategy == "wheel"
        assert retrieved_trade.expiration_date == datetime(2025, 8, 5)
        assert retrieved_trade.strike_price == 219.0
        assert retrieved_trade.option_type == "put"
    
    def test_stock_trade_no_option_details(self):
        """Test that stock trades don't have option details."""
        db = Database(":memory:")
        
        # Create a stock trade
        stock_trade = Trade(
            symbol="AAPL",
            quantity=100,
            price=150.0,
            side="buy",
            timestamp=datetime.now(),
            strategy="stock"
            # No option details
        )
        
        # Insert the trade
        inserted_trade = db.insert_trade(stock_trade)
        
        # Verify no option details
        assert inserted_trade.expiration_date is None
        assert inserted_trade.strike_price is None
        assert inserted_trade.option_type is None
        
        # Retrieve and verify
        trades = db.list_trades()
        retrieved_trade = trades[0]
        assert retrieved_trade.expiration_date is None
        assert retrieved_trade.strike_price is None
        assert retrieved_trade.option_type is None
    
    def test_cost_basis_with_option_details(self):
        """Test that cost basis calculation works with option contract details."""
        trades = [
            Trade(
                symbol="AAPL",
                quantity=1,
                price=5.0,
                side="sell",
                timestamp=datetime.now(),
                strategy="wheel",
                expiration_date=datetime(2025, 8, 5),
                strike_price=219.0,
                option_type="put"
            ),
            Trade(
                symbol="AAPL",
                quantity=1,
                price=2.0,
                side="buy",
                timestamp=datetime.now(),
                strategy="wheel",
                expiration_date=datetime(2025, 8, 5),
                strike_price=219.0,
                option_type="put"
            )
        ]
        
        result = cost_basis(trades)
        
        # Should work the same as before
        assert result['shares'] == 0
        assert result['basis_without_premium'] == 0
        assert result['net_premium'] == 300.0  # ($5 - $2) * 100
        assert result['basis_with_premium'] == -300.0 