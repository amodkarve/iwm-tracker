"""
Trade recommendations router
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from wheeltracker.db import db, Database
from strategy import get_all_recommendations, get_position_sizing_recommendation, RecommendationType
from strategy.trade_recommendations import get_hedging_recommendation, get_stock_replacement_recommendation
from strategy.position_manager import calculate_capital_usage, get_current_positions
from market_data import get_iwm_price, get_data_source
from indicators import calculate_instantaneous_trend, calculate_cycle_swing
from market_data import get_hl2_series, get_price_series
from backend.routers.auth import get_current_user

router = APIRouter()


class RecommendationResponse(BaseModel):
    action_type: str
    symbol: str
    strike: float
    expiration: date
    option_type: str
    recommended_contracts: int
    recommended_price: float
    bid: float
    ask: float
    mid: float
    expected_premium: float
    premium_pct: float
    reason: str
    confidence: str
    delta: Optional[float] = None
    iv: Optional[float] = None
    volume: Optional[int] = None


class PositionSizingResponse(BaseModel):
    target_premium: float
    contracts: int
    expected_premium: float
    premium_pct: float


@router.get("/all", response_model=List[RecommendationResponse])
async def get_all_recommendations_endpoint(
    account_value: float = 1000000.0,
    max_recommendations: int = 10,
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get all trade recommendations"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    trades = db_instance.list_trades()
    recommendations = get_all_recommendations(
        trades=trades,
        account_value=account_value,
        max_recommendations=max_recommendations
    )
    
    results = []
    for rec in recommendations:
        results.append(RecommendationResponse(
            action_type=rec.action_type.value if hasattr(rec.action_type, 'value') else str(rec.action_type),
            symbol=rec.symbol,
            strike=rec.strike,
            expiration=rec.expiration if isinstance(rec.expiration, date) else rec.expiration.date(),
            option_type=rec.option_type,
            recommended_contracts=rec.recommended_contracts,
            recommended_price=float(rec.recommended_price),
            bid=rec.bid,
            ask=rec.ask,
            mid=rec.mid,
            expected_premium=rec.expected_premium,
            premium_pct=rec.premium_pct,
            reason=rec.reason,
            confidence=rec.confidence,
            delta=rec.delta,
            iv=rec.iv,
            volume=rec.volume
        ))
    
    return results


@router.get("/position-sizing", response_model=PositionSizingResponse)
async def get_position_sizing(
    option_price: float,
    account_value: float = 1000000.0,
    current_user: str = Depends(get_current_user)
):
    """Get position sizing recommendation"""
    sizing = get_position_sizing_recommendation(option_price, account_value)
    return PositionSizingResponse(**sizing)


@router.get("/hedging")
async def get_hedging_recommendation_endpoint(
    account_value: float = 100000.0,
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get hedging recommendation"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    trades = db_instance.list_trades()
    current_iwm_price = get_iwm_price() or 0.0
    
    # Get indicators
    hl2_series = get_hl2_series(period="3mo")
    trend_signal = 0
    if not hl2_series.empty:
        trend_result = calculate_instantaneous_trend(hl2_series)
        trend_signal = int(trend_result['signal'].iloc[-1]) if not trend_result['signal'].empty else 0
    
    price_series = get_price_series(period="3mo")
    csi_signal = 0
    if not price_series.empty:
        csi_result = calculate_cycle_swing(price_series)
        csi_signal = int(csi_result['signal'].iloc[-1]) if not csi_result['signal'].empty else 0
    
    rec = get_hedging_recommendation(
        account_value,
        get_current_positions(trades),
        trend_signal,
        csi_signal,
        current_iwm_price
    )
    
    if rec:
        return {
            "reason": rec.reason,
            "option_symbol": rec.option_symbol,
            "recommended_contracts": rec.recommended_contracts,
            "recommended_price": rec.recommended_price
        }
    
    return None

