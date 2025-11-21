"""
Market data router
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from market_data import get_iwm_price, get_price_series, get_hl2_series, get_data_source
from indicators import calculate_instantaneous_trend, calculate_cycle_swing
from backend.routers.auth import get_current_user

router = APIRouter()


class MarketDataResponse(BaseModel):
    price: Optional[float]
    data_source: str
    delay: str


class IndicatorResponse(BaseModel):
    signal: int
    signal_text: str
    signal_class: str


@router.get("/iwm-price", response_model=MarketDataResponse)
async def get_market_price(current_user: str = Depends(get_current_user)):
    """Get current IWM price"""
    price = get_iwm_price()
    data_source = get_data_source()
    delay = "15-20 min" if data_source != "marketdata" else "real-time"
    
    return MarketDataResponse(
        price=price,
        data_source=data_source,
        delay=delay
    )


@router.get("/indicators/trend", response_model=IndicatorResponse)
async def get_trend_indicator(current_user: str = Depends(get_current_user)):
    """Get Ehler's Instantaneous Trend indicator"""
    hl2_series = get_hl2_series(period="3mo")
    
    if hl2_series.empty:
        return IndicatorResponse(signal=0, signal_text="NEUTRAL →", signal_class="neutral")
    
    trend_result = calculate_instantaneous_trend(hl2_series)
    trend_signal = int(trend_result['signal'].iloc[-1]) if not trend_result['signal'].empty else 0
    
    signal_class = "bullish" if trend_signal > 0 else "bearish" if trend_signal < 0 else "neutral"
    signal_text = "BULLISH ↑" if trend_signal > 0 else "BEARISH ↓" if trend_signal < 0 else "NEUTRAL →"
    
    return IndicatorResponse(
        signal=trend_signal,
        signal_text=signal_text,
        signal_class=signal_class
    )


@router.get("/indicators/cycle-swing", response_model=IndicatorResponse)
async def get_cycle_swing_indicator(current_user: str = Depends(get_current_user)):
    """Get Cycle Swing Momentum indicator"""
    price_series = get_price_series(period="3mo")
    
    if price_series.empty:
        return IndicatorResponse(signal=0, signal_text="NEUTRAL", signal_class="neutral")
    
    csi_result = calculate_cycle_swing(price_series)
    csi_signal = int(csi_result['signal'].iloc[-1]) if not csi_result['signal'].empty else 0
    
    signal_class = "bullish" if csi_signal > 0 else "bearish" if csi_signal < 0 else "neutral"
    signal_text = "OVERBOUGHT" if csi_signal > 0 else "OVERSOLD" if csi_signal < 0 else "NEUTRAL"
    
    return IndicatorResponse(
        signal=csi_signal,
        signal_text=signal_text,
        signal_class=signal_class
    )

