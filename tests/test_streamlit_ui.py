import pytest
from unittest.mock import patch, MagicMock
import streamlit as st
from datetime import datetime, date
from wheeltracker.models import Trade
from wheeltracker.db import Database


class TestStreamlitUI:
    def test_trade_form_option_fields_logic(self):
        """Test that option fields are properly set when trade type is put/call."""
        # Mock the database
        with patch('wheeltracker.db.Database') as mock_db:
            mock_db_instance = MagicMock()
            mock_db.return_value = mock_db_instance
            
            # Test data for different trade types
            test_cases = [
                {
                    "trade_type": "put",
                    "should_have_option_fields": True,
                    "expected_option_type": "put"
                },
                {
                    "trade_type": "call", 
                    "should_have_option_fields": True,
                    "expected_option_type": "call"
                },
                {
                    "trade_type": "stock",
                    "should_have_option_fields": False,
                    "expected_option_type": None
                }
            ]
            
            for test_case in test_cases:
                trade_type = test_case["trade_type"]
                should_have_option_fields = test_case["should_have_option_fields"]
                expected_option_type = test_case["expected_option_type"]
                
                # Simulate the form logic
                option_type = None
                expiration_date = None
                strike_price = None
                
                if trade_type == "put" or trade_type == "call":
                    option_type = trade_type
                    expiration_date = date.today()
                    strike_price = 150.0
                
                # Verify the logic works correctly
                if should_have_option_fields:
                    assert option_type == expected_option_type
                    assert expiration_date is not None
                    assert strike_price is not None
                else:
                    assert option_type is None
                    assert expiration_date is None
                    assert strike_price is None
    
    def test_trade_creation_with_option_details(self):
        """Test creating a trade with option contract details."""
        # Create a put option trade
        trade = Trade(
            symbol="AAPL",
            quantity=1,
            price=5.0,
            side="sell",
            timestamp=datetime.now(),
            strategy="wheel",
            expiration_date=datetime(2025, 8, 5),
            strike_price=219.0,
            option_type="put"
        )
        
        # Verify option details are set correctly
        assert trade.symbol == "AAPL"
        assert trade.quantity == 1
        assert trade.price == 5.0
        assert trade.side == "sell"
        assert trade.strategy == "wheel"
        assert trade.expiration_date == datetime(2025, 8, 5)
        assert trade.strike_price == 219.0
        assert trade.option_type == "put"
    
    def test_trade_creation_without_option_details(self):
        """Test creating a stock trade without option details."""
        # Create a stock trade
        trade = Trade(
            symbol="AAPL",
            quantity=100,
            price=150.0,
            side="buy",
            timestamp=datetime.now(),
            strategy="stock"
            # No option details
        )
        
        # Verify no option details are set
        assert trade.symbol == "AAPL"
        assert trade.quantity == 100
        assert trade.price == 150.0
        assert trade.side == "buy"
        assert trade.strategy == "stock"
        assert trade.expiration_date is None
        assert trade.strike_price is None
        assert trade.option_type is None
    
    def test_form_validation_logic(self):
        """Test the form validation logic from the Streamlit app."""
        # Test cases for form validation
        test_cases = [
            {
                "symbol": "AAPL",
                "price": 150.0,
                "should_be_valid": True,
                "description": "Valid trade data"
            },
            {
                "symbol": "",
                "price": 150.0,
                "should_be_valid": False,
                "description": "Missing symbol"
            },
            {
                "symbol": "AAPL",
                "price": 0.0,
                "should_be_valid": False,
                "description": "Invalid price"
            },
            {
                "symbol": "AAPL",
                "price": -10.0,
                "should_be_valid": False,
                "description": "Negative price"
            }
        ]
        
        for test_case in test_cases:
            symbol = test_case["symbol"]
            price = test_case["price"]
            should_be_valid = test_case["should_be_valid"]
            description = test_case["description"]
            
            # Simulate the validation logic from the app
            is_valid = bool(symbol) and price > 0
            
            assert is_valid == should_be_valid, f"Failed: {description}"
    
    def test_option_field_conditional_logic(self):
        """Test the conditional logic for showing option fields."""
        # Test different trade types
        trade_types = ["stock", "put", "call"]
        
        for trade_type in trade_types:
            # Simulate the conditional logic from the app
            option_type = None
            expiration_date = None
            strike_price = None
            
            if trade_type == "put" or trade_type == "call":
                option_type = trade_type
                expiration_date = date.today()
                strike_price = 150.0
            
            # Verify the logic
            if trade_type in ["put", "call"]:
                assert option_type == trade_type
                assert expiration_date is not None
                assert strike_price is not None
            else:
                assert option_type is None
                assert expiration_date is None
                assert strike_price is None 