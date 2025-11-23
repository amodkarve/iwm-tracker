"""
Tests for portfolio NAV and config API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import Depends
from datetime import datetime, timedelta
import sys
import os
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wheeltracker.db import Database
from wheeltracker.models import Trade

# Mock authentication dependency
def override_get_current_user():
    return "test_user"


class TestConfigAPI:
    """Test config API endpoints"""
    
    @pytest.fixture
    def client_with_auth(self):
        """Create test client with mocked auth"""
        from backend.main import app
        from backend.routers import auth, config, analytics
        
        # Override auth dependency
        app.dependency_overrides[auth.get_current_user] = override_get_current_user
        app.dependency_overrides[config.get_current_user] = override_get_current_user
        app.dependency_overrides[analytics.get_current_user] = override_get_current_user
        
        with TestClient(app) as test_client:
            yield test_client
        
        # Clean up
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def test_db(self):
        """Create a test database"""
        return Database(":memory:")
    
    def test_get_starting_portfolio_value_default(self, client_with_auth, test_db):
        """Test getting default starting portfolio value"""
        with patch('backend.routers.config.db', test_db):
            response = client_with_auth.get("/api/config/starting-portfolio-value")
            
            assert response.status_code == 200
            data = response.json()
            assert "value" in data
            assert data["value"] == 1000000.0  # Default value
    
    def test_set_and_get_starting_portfolio_value(self, client_with_auth, test_db):
        """Test setting and getting starting portfolio value"""
        with patch('backend.routers.config.db', test_db):
            # Set value
            response = client_with_auth.post(
                "/api/config/starting-portfolio-value",
                json={"value": 1500000.0}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["value"] == 1500000.0
            
            # Get value
            response = client_with_auth.get("/api/config/starting-portfolio-value")
            assert response.status_code == 200
            data = response.json()
            assert data["value"] == 1500000.0
    
    def test_set_invalid_starting_portfolio_value(self, client_with_auth, test_db):
        """Test setting invalid starting portfolio value"""
        with patch('backend.routers.config.db', test_db):
            # Negative value
            response = client_with_auth.post(
                "/api/config/starting-portfolio-value",
                json={"value": -1000.0}
            )
            assert response.status_code == 400
            
            # Zero value
            response = client_with_auth.post(
                "/api/config/starting-portfolio-value",
                json={"value": 0.0}
            )
            assert response.status_code == 400


class TestPortfolioNavAPI:
    """Test portfolio NAV API endpoint"""
    
    @pytest.fixture
    def client_with_auth(self):
        """Create test client with mocked auth"""
        from backend.main import app
        from backend.routers import auth, config, analytics
        
        # Override auth dependency
        app.dependency_overrides[auth.get_current_user] = override_get_current_user
        app.dependency_overrides[config.get_current_user] = override_get_current_user
        app.dependency_overrides[analytics.get_current_user] = override_get_current_user
        
        with TestClient(app) as test_client:
            yield test_client
        
        # Clean up
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def test_db(self):
        """Create a test database"""
        return Database(":memory:")
    
    def test_get_portfolio_nav_no_trades(self, client_with_auth, test_db):
        """Test getting NAV with no trades"""
        # Set starting value
        test_db.set_config("starting_portfolio_value", "1000000.0")
        
        with patch('backend.routers.analytics.db', test_db):
            response = client_with_auth.get("/api/analytics/portfolio-nav")
            
            assert response.status_code == 200
            data = response.json()
            assert data["nav"] == 1000000.0
            assert data["starting_value"] == 1000000.0
            assert data["open_pnl"] == 0.0
            assert data["closed_pnl"] == 0.0
    
    def test_get_portfolio_nav_with_closed_profit(self, client_with_auth, test_db):
        """Test getting NAV with closed profit"""
        # Set starting value
        test_db.set_config("starting_portfolio_value", "1000000.0")
        
        # Add closed option trade
        trade1 = Trade(
            symbol="IWM",
            quantity=1,
            price=5.0,
            side="sell",
            timestamp=datetime.now(),
            option_type="put",
            strike_price=200.0,
            expiration_date=datetime.now() + timedelta(days=30)
        )
        trade2 = Trade(
            symbol="IWM",
            quantity=1,
            price=2.0,
            side="buy",
            timestamp=datetime.now() + timedelta(days=1),
            option_type="put",
            strike_price=200.0,
            expiration_date=datetime.now() + timedelta(days=30)
        )
        test_db.insert_trade(trade1)
        test_db.insert_trade(trade2)
        
        with patch('backend.routers.analytics.db', test_db):
            response = client_with_auth.get("/api/analytics/portfolio-nav")
            
            assert response.status_code == 200
            data = response.json()
            assert data["starting_value"] == 1000000.0
            assert data["closed_pnl"] == 300.0  # ($5 - $2) * 100
            assert data["open_pnl"] == 0.0
            assert data["nav"] == 1000300.0
    
    def test_get_portfolio_nav_with_open_position(self, client_with_auth, test_db):
        """Test getting NAV with open position"""
        # Mock get_iwm_price to return a specific value
        with patch('market_data.price_fetcher.get_iwm_price', return_value=210.0):
            # Set starting value
            test_db.set_config("starting_portfolio_value", "1000000.0")
            
            # Add open stock position
            trade = Trade(
                symbol="IWM",
                quantity=100,
                price=200.0,
                side="buy",
                timestamp=datetime.now(),
            )
            test_db.insert_trade(trade)
            
            with patch('backend.routers.analytics.db', test_db):
                response = client_with_auth.get("/api/analytics/portfolio-nav")
                
                assert response.status_code == 200
                data = response.json()
                assert data["starting_value"] == 1000000.0
                assert data["closed_pnl"] == 0.0
                # Open PnL: (210 - 200) * 100 = 1000
                assert abs(data["open_pnl"] - 1000.0) < 0.01
                assert abs(data["nav"] - 1001000.0) < 0.01
    
    def test_get_portfolio_nav_with_custom_starting_value(self, client_with_auth, test_db):
        """Test getting NAV with custom starting value"""
        # Set custom starting value
        test_db.set_config("starting_portfolio_value", "2000000.0")
        
        with patch('backend.routers.analytics.db', test_db):
            response = client_with_auth.get("/api/analytics/portfolio-nav")
            
            assert response.status_code == 200
            data = response.json()
            assert data["starting_value"] == 2000000.0
            assert data["nav"] == 2000000.0

