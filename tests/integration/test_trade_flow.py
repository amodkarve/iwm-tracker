"""
Integration tests for trade recommendations and entry
"""
import pytest
import sys
import os
from datetime import datetime, date, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from wheeltracker.db import Database
from wheeltracker.models import Trade
from strategy.trade_recommendations import get_trade_recommendations, TradeRecommendation


class TestTradeRecommendations:
    """Test trade recommendation engine"""
    
    def test_get_recommendations_returns_list(self):
        """Test that get_trade_recommendations returns a list"""
        recs = get_trade_recommendations(account_value=1_000_000, max_recommendations=3)
        assert isinstance(recs, list)
        assert len(recs) <= 3
    
    def test_recommendation_has_required_fields(self):
        """Test that recommendations have all required fields"""
        recs = get_trade_recommendations(account_value=1_000_000, max_recommendations=1)
        
        if recs:
            rec = recs[0]
            assert hasattr(rec, 'symbol')
            assert hasattr(rec, 'strike')
            assert hasattr(rec, 'expiration')
            assert hasattr(rec, 'option_type')
            assert hasattr(rec, 'bid')
            assert hasattr(rec, 'ask')
            assert hasattr(rec, 'mid')
            assert hasattr(rec, 'recommended_contracts')
            assert hasattr(rec, 'expected_premium')
            assert hasattr(rec, 'confidence')
            assert hasattr(rec, 'reason')
    
    def test_recommendation_confidence_levels(self):
        """Test that confidence levels are valid"""
        recs = get_trade_recommendations(account_value=1_000_000, max_recommendations=3)
        
        valid_confidence = ['high', 'medium', 'low']
        for rec in recs:
            assert rec.confidence in valid_confidence
    
    def test_recommendation_contracts_positive(self):
        """Test that recommended contracts are positive"""
        recs = get_trade_recommendations(account_value=1_000_000, max_recommendations=3)
        
        for rec in recs:
            assert rec.recommended_contracts > 0
            assert rec.expected_premium > 0


class TestTradeEntry:
    """Test trade entry functionality"""
    
    @pytest.fixture
    def db(self):
        """Create a test database"""
        test_db = Database(":memory:")
        yield test_db
    
    def test_insert_put_trade(self, db):
        """Test inserting a put option trade"""
        expiration = datetime.now() + timedelta(days=1)
        
        trade = Trade(
            symbol="IWM",
            quantity=5,
            price=0.80,
            side="sell",
            timestamp=datetime.now(),
            strategy="wheel",
            expiration_date=expiration,
            strike_price=200.0,
            option_type="put"
        )
        
        inserted = db.insert_trade(trade)
        
        assert inserted.id is not None
        assert inserted.symbol == "IWM"
        assert inserted.quantity == 5
        assert inserted.price == 0.80
        assert inserted.side == "sell"
        assert inserted.option_type == "put"
        assert inserted.strike_price == 200.0
        
        # Check expiration date is preserved correctly
        assert inserted.expiration_date.date() == expiration.date()
    
    def test_list_trades(self, db):
        """Test listing trades"""
        # Insert multiple trades
        for i in range(3):
            trade = Trade(
                symbol="IWM",
                quantity=5 + i,
                price=0.80 + (i * 0.1),
                side="sell",
                timestamp=datetime.now(),
                strategy="wheel",
                expiration_date=datetime.now() + timedelta(days=1),
                strike_price=200.0 + i,
                option_type="put"
            )
            db.insert_trade(trade)
        
        trades = db.list_trades()
        assert len(trades) == 3
        
        # Check all trades are present (order may vary)
        quantities = {trade.quantity for trade in trades}
        assert quantities == {5, 6, 7}
    
    def test_expiration_date_format(self, db):
        """Test that expiration dates are stored and retrieved correctly"""
        # Test with a specific date
        exp_date = datetime(2025, 12, 20, 0, 0, 0)
        
        trade = Trade(
            symbol="IWM",
            quantity=5,
            price=0.80,
            side="sell",
            timestamp=datetime.now(),
            strategy="wheel",
            expiration_date=exp_date,
            strike_price=200.0,
            option_type="put"
        )
        
        inserted = db.insert_trade(trade)
        
        # Retrieve and check
        trades = db.list_trades()
        assert len(trades) == 1
        
        retrieved_trade = trades[0]
        assert retrieved_trade.expiration_date.year == 2025
        assert retrieved_trade.expiration_date.month == 12
        assert retrieved_trade.expiration_date.day == 20


class TestTradeRecommendationObject:
    """Test TradeRecommendation class"""
    
    def test_create_recommendation(self):
        """Test creating a TradeRecommendation object"""
        rec = TradeRecommendation(
            symbol="IWM",
            option_symbol="IWM251220P00200000",
            strike=200.0,
            expiration=date(2025, 12, 20),
            option_type="put",
            bid=0.75,
            ask=0.85,
            mid=0.80,
            recommended_price=0.80,
            recommended_contracts=5,
            expected_premium=400.0,
            premium_pct=0.0004,
            delta=-0.25,
            iv=0.20,
            volume=1000,
            open_interest=5000,
            reason="Test reason",
            confidence="high"
        )
        
        assert rec.symbol == "IWM"
        assert rec.strike == 200.0
        assert rec.expiration == date(2025, 12, 20)
        assert rec.confidence == "high"
    
    def test_recommendation_to_dict(self):
        """Test converting recommendation to dictionary"""
        rec = TradeRecommendation(
            symbol="IWM",
            option_symbol="IWM251220P00200000",
            strike=200.0,
            expiration=date(2025, 12, 20),
            option_type="put",
            bid=0.75,
            ask=0.85,
            mid=0.80,
            recommended_price=0.80,
            recommended_contracts=5,
            expected_premium=400.0,
            premium_pct=0.0004,
            confidence="high"
        )
        
        rec_dict = rec.to_dict()
        
        assert isinstance(rec_dict, dict)
        assert rec_dict['symbol'] == "IWM"
        assert rec_dict['strike'] == 200.0
        assert rec_dict['confidence'] == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
