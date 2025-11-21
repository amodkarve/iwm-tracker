"""
Market Data App API Client

Provides real-time stock quotes and options data from marketdata.app
Trader plan ($75/month) includes:
- Real-time stock quotes
- Real-time options chains
- Greeks and IV
- Unlimited historical data
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
import os

logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "https://api.marketdata.app/v1"


class MarketDataClient:
    """Client for Market Data App API"""
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize Market Data App client
        
        Args:
            api_token: API token from marketdata.app dashboard
                      If None, will try to read from MARKETDATA_API_TOKEN env var
        """
        self.api_token = api_token or os.getenv('MARKETDATA_API_TOKEN')
        if not self.api_token:
            logger.warning("No Market Data API token provided. Set MARKETDATA_API_TOKEN environment variable.")
        
        self.headers = {
            'Authorization': f'Token {self.api_token}' if self.api_token else ''
        }
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make API request
        
        Args:
            endpoint: API endpoint (e.g., '/stocks/quotes/IWM')
            params: Query parameters
        
        Returns:
            JSON response as dictionary
        """
        url = f"{BASE_URL}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Market Data API request failed: {e}")
            return {}
    
    def get_stock_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time stock quote
        
        Args:
            symbol: Stock symbol (e.g., 'IWM')
        
        Returns:
            Dictionary with quote data:
            {
                'symbol': 'IWM',
                'last': 195.50,
                'bid': 195.48,
                'ask': 195.52,
                'volume': 1234567,
                'change': 1.25,
                'changepct': 0.64,
                'updated': 1234567890
            }
        """
        endpoint = f"/stocks/quotes/{symbol}/"
        data = self._make_request(endpoint)
        
        if data and 's' in data and data['s'] == 'ok':
            return {
                'symbol': symbol,
                'last': data.get('last', [0])[0] if isinstance(data.get('last'), list) else data.get('last', 0),
                'bid': data.get('bid', [0])[0] if isinstance(data.get('bid'), list) else data.get('bid', 0),
                'ask': data.get('ask', [0])[0] if isinstance(data.get('ask'), list) else data.get('ask', 0),
                'volume': data.get('volume', [0])[0] if isinstance(data.get('volume'), list) else data.get('volume', 0),
                'change': data.get('change', [0])[0] if isinstance(data.get('change'), list) else data.get('change', 0),
                'changepct': data.get('changepct', [0])[0] if isinstance(data.get('changepct'), list) else data.get('changepct', 0),
                'updated': data.get('updated', [0])[0] if isinstance(data.get('updated'), list) else data.get('updated', 0)
            }
        
        return None
    
    def get_options_chain(
        self,
        symbol: str,
        expiration: Optional[str] = None,
        strike_min: Optional[float] = None,
        strike_max: Optional[float] = None,
        dte_min: Optional[int] = None,
        dte_max: Optional[int] = None,
        option_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get options chain for a symbol
        
        Args:
            symbol: Underlying symbol (e.g., 'IWM')
            expiration: Specific expiration date (YYYY-MM-DD)
            strike_min: Minimum strike price
            strike_max: Maximum strike price
            dte_min: Minimum days to expiration
            dte_max: Maximum days to expiration
            option_type: 'call' or 'put' (None for both)
        
        Returns:
            DataFrame with options chain data including Greeks
        """
        endpoint = f"/options/chain/{symbol}/"
        
        params = {}
        if expiration:
            params['expiration'] = expiration
        if strike_min:
            params['strikemin'] = strike_min
        if strike_max:
            params['strikemax'] = strike_max
        if dte_min:
            params['dtemin'] = dte_min
        if dte_max:
            params['dtemax'] = dte_max
        if option_type:
            params['side'] = option_type
        
        data = self._make_request(endpoint, params)
        
        if not data or 's' not in data or data['s'] != 'ok':
            return pd.DataFrame()
        
        # Convert to DataFrame
        records = []
        for i in range(len(data.get('optionSymbol', []))):
            record = {
                'option_symbol': data['optionSymbol'][i],
                'underlying': data.get('underlying', [symbol] * len(data['optionSymbol']))[i],
                'expiration': data.get('expiration', [])[i] if 'expiration' in data else None,
                'strike': data.get('strike', [])[i] if 'strike' in data else None,
                'option_type': data.get('side', [])[i] if 'side' in data else None,
                'bid': data.get('bid', [])[i] if 'bid' in data else None,
                'ask': data.get('ask', [])[i] if 'ask' in data else None,
                'last': data.get('last', [])[i] if 'last' in data else None,
                'mid': data.get('mid', [])[i] if 'mid' in data else None,
                'volume': data.get('volume', [])[i] if 'volume' in data else None,
                'open_interest': data.get('openInterest', [])[i] if 'openInterest' in data else None,
                'iv': data.get('iv', [])[i] if 'iv' in data else None,
                'delta': data.get('delta', [])[i] if 'delta' in data else None,
                'gamma': data.get('gamma', [])[i] if 'gamma' in data else None,
                'theta': data.get('theta', [])[i] if 'theta' in data else None,
                'vega': data.get('vega', [])[i] if 'vega' in data else None,
                'rho': data.get('rho', [])[i] if 'rho' in data else None,
                'updated': data.get('updated', [])[i] if 'updated' in data else None
            }
            records.append(record)
        
        return pd.DataFrame(records)
    
    def get_1dte_puts(
        self,
        symbol: str,
        current_price: float,
        strike_range_pct: float = 0.05
    ) -> pd.DataFrame:
        """
        Get 1 DTE puts near the money (for your strategy)
        
        Args:
            symbol: Underlying symbol (e.g., 'IWM')
            current_price: Current stock price
            strike_range_pct: Strike range as percentage (default 5%)
        
        Returns:
            DataFrame with 1 DTE put options near the money
        """
        strike_min = current_price * (1 - strike_range_pct)
        strike_max = current_price * (1 + strike_range_pct)
        
        # Fetch options for next 1-5 days to handle weekends/holidays
        chain = self.get_options_chain(
            symbol=symbol,
            strike_min=strike_min,
            strike_max=strike_max,
            dte_min=1,
            dte_max=5,
            option_type='put'
        )
        
        if chain.empty:
            return chain
            
        # Find the closest expiration date
        # Ensure expiration column is datetime
        chain['expiration'] = pd.to_datetime(chain['expiration'])
        next_expiration = chain['expiration'].min()
        
        # Filter for only that expiration
        chain = chain[chain['expiration'] == next_expiration]
        
        # Sort by strike (descending for puts)
        chain = chain.sort_values('strike', ascending=False)
        
        return chain
    
    def get_hedge_puts(
        self,
        symbol: str,
        current_price: float,
        otm_pct: float = 0.05,
        dte: int = 30,
        max_price: float = 1.50
    ) -> pd.DataFrame:
        """
        Get hedge puts (30 DTE, 5% OTM, ~$1.50 target)
        
        Args:
            symbol: Underlying symbol
            current_price: Current stock price
            otm_pct: Out of the money percentage (default 5%)
            dte: Days to expiration (default 30)
            max_price: Maximum price per contract (default $1.50)
        
        Returns:
            DataFrame with hedge put options
        """
        strike_max = current_price * (1 - otm_pct)
        
        chain = self.get_options_chain(
            symbol=symbol,
            strike_max=strike_max,
            dte_min=dte - 5,
            dte_max=dte + 5,
            option_type='put'
        )
        
        if chain.empty:
            return chain
        
        # Filter by price
        chain = chain[chain['mid'] <= max_price]
        
        # Sort by strike (closest to target)
        target_strike = current_price * (1 - otm_pct)
        chain['strike_diff'] = abs(chain['strike'] - target_strike)
        chain = chain.sort_values('strike_diff')
        
        return chain.drop('strike_diff', axis=1)
