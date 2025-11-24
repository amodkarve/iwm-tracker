"""
Historical market data fetcher for backtesting

Fetches SPX/SPY and VIX historical data using yfinance
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, date
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def get_spx_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period: str = "max"
) -> pd.DataFrame:
    """
    Get historical SPX (S&P 500 Index) data
    
    Args:
        start_date: Start date (if None, uses period)
        end_date: End date (if None, uses period)
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
    
    Returns:
        DataFrame with OHLCV data indexed by date
    """
    try:
        spx = yf.Ticker("^GSPC")  # SPX ticker
        if start_date and end_date:
            data = spx.history(start=start_date, end=end_date)
        else:
            data = spx.history(period=period)
        
        if data.empty:
            logger.warning(f"No SPX historical data available")
            return pd.DataFrame()
        
        return data
        
    except Exception as e:
        logger.error(f"Error fetching SPX history: {e}")
        return pd.DataFrame()


def get_spy_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period: str = "max"
) -> pd.DataFrame:
    """
    Get historical SPY (S&P 500 ETF) data
    
    Args:
        start_date: Start date (if None, uses period)
        end_date: End date (if None, uses period)
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
    
    Returns:
        DataFrame with OHLCV data indexed by date
    """
    try:
        spy = yf.Ticker("SPY")
        if start_date and end_date:
            data = spy.history(start=start_date, end=end_date)
        else:
            data = spy.history(period=period)
        
        if data.empty:
            logger.warning(f"No SPY historical data available")
            return pd.DataFrame()
        
        return data
        
    except Exception as e:
        logger.error(f"Error fetching SPY history: {e}")
        return pd.DataFrame()


def get_vix_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period: str = "max"
) -> pd.Series:
    """
    Get historical VIX data
    
    Args:
        start_date: Start date (if None, uses period)
        end_date: End date (if None, uses period)
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
    
    Returns:
        Series of VIX closing values indexed by date
    """
    try:
        vix = yf.Ticker("^VIX")
        if start_date and end_date:
            data = vix.history(start=start_date, end=end_date)
        else:
            data = vix.history(period=period)
        
        if data.empty:
            logger.warning(f"No VIX historical data available")
            return pd.Series(dtype=float)
        
        return data['Close']
        
    except Exception as e:
        logger.error(f"Error fetching VIX history: {e}")
        return pd.Series(dtype=float)


def get_combined_market_data(
    start_date: date,
    end_date: date,
    use_spy: bool = True
) -> pd.DataFrame:
    """
    Get combined market data (SPX/SPY + VIX) aligned by date
    
    Args:
        start_date: Start date
        end_date: End date
        use_spy: If True, use SPY; if False, use SPX
    
    Returns:
        DataFrame with columns: Close, High, Low, Open, Volume, VIX
    """
    if use_spy:
        price_data = get_spy_history(start_date, end_date)
    else:
        price_data = get_spx_history(start_date, end_date)
    
    vix_data = get_vix_history(start_date, end_date)
    
    if price_data.empty:
        return pd.DataFrame()
    
    # Align VIX data with price data
    result = price_data.copy()
    result['VIX'] = vix_data.reindex(result.index, method='ffill')
    
    return result

