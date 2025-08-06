import pytest
from datetime import datetime
from src.wheeltracker.models import Trade
from src.wheeltracker.db import Database


class TestDatabase:
    def test_insert_and_list_trades(self):
        """Test inserting a trade and retrieving it from the database."""
        # Create in-memory database
        db = Database(":memory:")
        
        # Create a sample trade
        sample_trade = Trade(
            symbol="AAPL",
            quantity=100,
            price=150.50,
            side="buy",
            timestamp=datetime.now(),
            strategy="wheel"
        )
        
        # Insert the trade
        inserted_trade = db.insert_trade(sample_trade)
        
        # Verify the trade was inserted with an ID
        assert inserted_trade.id is not None
        assert inserted_trade.symbol == "AAPL"
        assert inserted_trade.quantity == 100
        assert inserted_trade.price == 150.50
        assert inserted_trade.side == "buy"
        assert inserted_trade.strategy == "wheel"
        
        # Retrieve all trades
        trades = db.list_trades()
        
        # Verify we got the trade back
        assert len(trades) == 1
        retrieved_trade = trades[0]
        assert retrieved_trade.id == inserted_trade.id
        assert retrieved_trade.symbol == "AAPL"
        assert retrieved_trade.quantity == 100
        assert retrieved_trade.price == 150.50
        assert retrieved_trade.side == "buy"
        assert retrieved_trade.strategy == "wheel"
    
    def test_multiple_trades(self):
        """Test inserting multiple trades and retrieving them."""
        # Create in-memory database
        db = Database(":memory:")
        
        # Create multiple trades
        trade1 = Trade(
            symbol="AAPL",
            quantity=100,
            price=150.50,
            side="buy",
            timestamp=datetime.now(),
            strategy="wheel"
        )
        
        trade2 = Trade(
            symbol="TSLA",
            quantity=50,
            price=250.00,
            side="sell",
            timestamp=datetime.now(),
            strategy="covered_call"
        )
        
        # Insert trades
        db.insert_trade(trade1)
        db.insert_trade(trade2)
        
        # Retrieve all trades
        trades = db.list_trades()
        
        # Verify we got both trades back
        assert len(trades) == 2
        
        # Verify the trades are ordered by timestamp DESC (most recent first)
        assert trades[0].symbol == "TSLA"  # Most recent
        assert trades[1].symbol == "AAPL"  # Less recent 