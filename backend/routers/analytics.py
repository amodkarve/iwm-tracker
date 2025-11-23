"""
Analytics router
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from wheeltracker.db import db, Database
from wheeltracker.analytics import (
    trades_to_dataframe,
    monthly_net_premium,
    cumulative_net_premium,
    get_open_option_positions_for_closing,
)
from wheeltracker.calculations import cost_basis
from wheeltracker.portfolio import calculate_nav
from analytics.performance import get_performance_summary
from strategy.position_manager import calculate_capital_usage, get_current_positions
from market_data import get_iwm_price
from backend.routers.auth import get_current_user

router = APIRouter()


class PerformanceSummary(BaseModel):
    annualized_return: float
    total_premium: float
    win_rate: float
    avg_win: float
    avg_loss: float
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    total_trades: int
    days_active: int
    on_track: bool


class CostBasisResponse(BaseModel):
    symbol: str
    shares: float
    basis_without_premium: float
    basis_with_premium: float
    net_premium: float
    total_pnl: float


class CapitalUsageResponse(BaseModel):
    total_deployed: float
    buying_power_usage_pct: float
    cash_secured_puts: float
    long_stock: float


@router.get("/performance", response_model=PerformanceSummary)
async def get_performance(
    account_value: float = 1000000.0,
    initial_value: float = 1000000.0,
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get performance summary"""
    try:
        if db_path:
            db_instance = Database(db_path)
        else:
            db_instance = db
        
        trades = db_instance.list_trades()
        
        # Handle empty trades case
        if not trades:
            return PerformanceSummary(
                annualized_return=0.0,
                total_premium=0.0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                sharpe_ratio=None,
                max_drawdown=None,
                total_trades=0,
                days_active=0,
                on_track=False
            )
        
        perf = get_performance_summary(trades, account_value, initial_value)
        
        # Handle error case
        if 'error' in perf:
            raise HTTPException(status_code=400, detail=perf['error'])
        
        # Map the returned dictionary to the PerformanceSummary model
        return PerformanceSummary(
            annualized_return=perf.get('annualized_return', 0.0),
            total_premium=perf.get('total_premium', 0.0),
            win_rate=perf.get('win_rate', 0.0),
            avg_win=perf.get('avg_win', 0.0),
            avg_loss=perf.get('avg_loss', 0.0),
            sharpe_ratio=perf.get('sharpe_ratio'),
            max_drawdown=perf.get('max_drawdown'),
            total_trades=perf.get('total_trades', 0),
            days_active=perf.get('days_active', 0),
            on_track=perf.get('on_track', False)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating performance: {str(e)}")


@router.get("/cost-basis", response_model=List[CostBasisResponse])
async def get_cost_basis(
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get cost basis analysis for all symbols"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    trades = db_instance.list_trades()
    symbols = set(trade.symbol for trade in trades)
    
    results = []
    for symbol in sorted(symbols):
        symbol_trades = [trade for trade in trades if trade.symbol == symbol]
        basis = cost_basis(symbol_trades, use_wheel_strategy=True)
        results.append(CostBasisResponse(symbol=symbol, **basis))
    
    return results


@router.get("/capital-usage", response_model=CapitalUsageResponse)
async def get_capital_usage(
    account_size: float = 1000000.0,
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get capital usage statistics"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    trades = db_instance.list_trades()
    current_iwm_price = get_iwm_price() or 0.0
    capital_stats = calculate_capital_usage(trades, account_size, {'IWM': current_iwm_price})
    
    return CapitalUsageResponse(**capital_stats)


@router.get("/monthly-premium")
async def get_monthly_premium(
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get monthly premium data"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    trades = db_instance.list_trades()
    df = trades_to_dataframe(trades)
    
    if df.empty:
        return []
    
    monthly_premium = monthly_net_premium(df)
    if monthly_premium.empty:
        return []
    
    monthly_df = monthly_premium.reset_index()
    monthly_df.columns = ["month", "premium"]
    monthly_df["month"] = monthly_df["month"].astype(str)
    
    return monthly_df.to_dict(orient="records")


@router.get("/cumulative-premium")
async def get_cumulative_premium(
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get cumulative premium data"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    trades = db_instance.list_trades()
    df = trades_to_dataframe(trades)
    
    if df.empty:
        return []
    
    cumulative_df = cumulative_net_premium(df)
    if cumulative_df.empty:
        return []
    
    cumulative_df["timestamp"] = cumulative_df["timestamp"].dt.strftime("%Y-%m-%d")
    
    return cumulative_df.to_dict(orient="records")


@router.get("/open-positions")
async def get_open_positions(
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get open option positions"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    trades = db_instance.list_trades()
    df = trades_to_dataframe(trades)
    
    if df.empty:
        return []
    
    obligations_df = get_open_option_positions_for_closing(df)
    if obligations_df.empty:
        return []
    
    obligations_df["expiration_date"] = obligations_df["expiration_date"].dt.strftime("%Y-%m-%d")
    
    return obligations_df.to_dict(orient="records")


class PortfolioNavResponse(BaseModel):
    nav: float
    starting_value: float
    open_pnl: float
    closed_pnl: float


@router.get("/portfolio-nav", response_model=PortfolioNavResponse)
async def get_portfolio_nav(
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get portfolio NAV (Net Asset Value)"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    # Get starting portfolio value from config
    default_value = 1000000.0
    value_str = db_instance.get_config('starting_portfolio_value', str(default_value))
    try:
        starting_value = float(value_str)
    except (ValueError, TypeError):
        starting_value = default_value
    
    # Get all trades
    trades = db_instance.list_trades()
    
    # Get current prices
    iwm_price = get_iwm_price() or 0.0
    current_prices = {'IWM': iwm_price}
    
    # Calculate NAV
    nav_data = calculate_nav(starting_value, trades, current_prices)
    
    return PortfolioNavResponse(**nav_data)

