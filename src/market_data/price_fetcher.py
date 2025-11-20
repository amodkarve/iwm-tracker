"""
Price data fetcher with support for multiple data sources

Supports:
1. Market Data App (paid, real-time) - Primary if API token is set
2. yfinance (free, 15-20 min delay) - Fallback
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

# Try to import Market Data client
try:
    from .marketdata_client import MarketDataClient
    MARKETDATA_AVAILABLE = True
except ImportError:
    MARKETDATA_AVAILABLE = False
    logger.warning("Market Data App client not available")


def _get_marketdata_client() -> Optional['MarketDataClient']:
    """Get Market Data App client if available and configured"""
    if not MARKETDATA_AVAILABLE:
        return None
    
    api_token = os.getenv('MARKETDATA_API_TOKEN')
    if not api_token:
        return None
    
    return MarketDataClient(api_token)


def get_iwm_price() -> Optional[float]:
    """
    Get current IWM price
    
    Tries Market Data App first (if configured), falls back to yfinance
    
    Returns:
        Current IWM price or None if error
    """
    # Try Market Data App first
    md_client = _get_marketdata_client()
    if md_client:
        try:
            quote = md_client.get_stock_quote('IWM')
            if quote and quote.get('last'):
                logger.info("Using Market Data App for IWM price (real-time)")
                return float(quote['last'])
        except Exception as e:
            logger.warning(f"Market Data App failed, falling back to yfinance: {e}")
    
    # Fallback to yfinance
    try:
        iwm = yf.Ticker("IWM")
        data = yf.download('IWM', period='1d', progress=False)
        
        if data.empty:
            logger.warning("No IWM price data available from yfinance")
            return None
            
        # Get the most recent close price
        current_price = data['Close'].iloc[-1]
        logger.info("Using yfinance for IWM price (15-20 min delay)")
        return float(current_price)
        
    except Exception as e:
        logger.error(f"Error fetching IWM price: {e}")
        return None


def get_iwm_history(period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Get historical IWM price data
    
    Args:
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        iwm = yf.Ticker("IWM")
        data = iwm.history(period=period, interval=interval)
        
        if data.empty:
            logger.warning(f"No historical data for period={period}, interval={interval}")
            return pd.DataFrame()
        
        return data
        
    except Exception as e:
        logger.error(f"Error fetching IWM history: {e}")
        return pd.DataFrame()


def get_price_series(period: str = "1y") -> pd.Series:
    """
    Get IWM price series for indicator calculations
    
    Args:
        period: Time period for historical data
    
    Returns:
        Series of closing prices with datetime index
    """
    data = get_iwm_history(period=period, interval="1d")
    
    if data.empty:
        return pd.Series(dtype=float)
    
    # Return close prices as a series
    return data['Close']


def get_hl2_series(period: str = "1y") -> pd.Series:
    """
    Get (High + Low) / 2 price series (hl2) for Ehler's indicator
    
    Args:
        period: Time period for historical data
    
    Returns:
        Series of hl2 prices with datetime index
    """
    data = get_iwm_history(period=period, interval="1d")
    
    if data.empty:
        return pd.Series(dtype=float)
    
    # Calculate hl2 = (high + low) / 2
    hl2 = (data['High'] + data['Low']) / 2
    return hl2


def get_options_chain(
    symbol: str = 'IWM',
    dte_min: int = 1,
    dte_max: int = 1,
    option_type: str = 'put'
) -> pd.DataFrame:
    """
    Get options chain (only available with Market Data App)
    
    Args:
        symbol: Underlying symbol
        dte_min: Minimum days to expiration
        dte_max: Maximum days to expiration
        option_type: 'call' or 'put'
    
    Returns:
        DataFrame with options data including Greeks
    """
    md_client = _get_marketdata_client()
    if not md_client:
        logger.warning("Options chain requires Market Data App API token")
        return pd.DataFrame()
    
    try:
        chain = md_client.get_options_chain(
            symbol=symbol,
            dte_min=dte_min,
            dte_max=dte_max,
            option_type=option_type
        )
        return chain
    except Exception as e:
        logger.error(f"Error fetching options chain: {e}")
        return pd.DataFrame()


def get_1dte_puts_near_money(current_price: Optional[float] = None) -> pd.DataFrame:
    """
    Get 1 DTE puts near the money (for your strategy)
    
    Args:
        current_price: Current IWM price (will fetch if not provided)
    
    Returns:
        DataFrame with 1 DTE put options
    """
    if current_price is None:
        current_price = get_iwm_price()
        if current_price is None:
            return pd.DataFrame()
    
    md_client = _get_marketdata_client()
    if not md_client:
        logger.warning("1 DTE puts require Market Data App API token")
        return pd.DataFrame()
    
    try:
        puts = md_client.get_1dte_puts('IWM', current_price)
        return puts
    except Exception as e:
        logger.error(f"Error fetching 1 DTE puts: {e}")
        return pd.DataFrame()


def get_data_source() -> str:
    """
    Get current data source being used
    
    Returns:
        'marketdata' or 'yfinance'
    """
    md_client = _get_marketdata_client()
    return 'marketdata' if md_client else 'yfinance'
