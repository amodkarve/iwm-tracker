import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from src.market_data.marketdata_client import MarketDataClient

@pytest.fixture
def mock_client():
    client = MarketDataClient(api_token="fake_token")
    return client

def test_get_1dte_puts_standard_weekday(mock_client):
    """Test standard case: 1 DTE available"""
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    
    # Mock chain with 1 DTE and 2 DTE
    mock_chain = pd.DataFrame({
        'option_symbol': ['OPT1', 'OPT2'],
        'expiration': [tomorrow, day_after],
        'strike': [200, 200],
        'mid': [1.0, 1.5]
    })
    
    with patch.object(mock_client, 'get_options_chain', return_value=mock_chain) as mock_get:
        result = mock_client.get_1dte_puts('IWM', 200.0)
        
        # Should call with dte_max=5
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['dte_min'] == 1
        assert call_kwargs['dte_max'] == 5
        
        # Should filter to closest (tomorrow)
        assert len(result) == 1
        assert pd.to_datetime(result.iloc[0]['expiration']).date() == tomorrow

def test_get_1dte_puts_weekend(mock_client):
    """Test weekend case: Only 3 DTE available (Friday -> Monday)"""
    today = datetime.now().date()
    monday = today + timedelta(days=3)
    tuesday = today + timedelta(days=4)
    
    # Mock chain with 3 DTE and 4 DTE
    mock_chain = pd.DataFrame({
        'option_symbol': ['OPT1', 'OPT2'],
        'expiration': [monday, tuesday],
        'strike': [200, 200],
        'mid': [1.0, 1.5]
    })
    
    with patch.object(mock_client, 'get_options_chain', return_value=mock_chain):
        result = mock_client.get_1dte_puts('IWM', 200.0)
        
        # Should filter to closest (Monday)
        assert len(result) == 1
        assert pd.to_datetime(result.iloc[0]['expiration']).date() == monday

def test_get_1dte_puts_empty(mock_client):
    """Test empty chain"""
    with patch.object(mock_client, 'get_options_chain', return_value=pd.DataFrame()):
        result = mock_client.get_1dte_puts('IWM', 200.0)
        assert result.empty
