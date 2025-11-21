"""
Trades router
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from wheeltracker.db import db, Database
from wheeltracker.models import Trade
from backend.routers.auth import get_current_user

router = APIRouter()


class TradeCreate(BaseModel):
    symbol: str
    quantity: int
    price: float
    side: str
    strategy: Optional[str] = None
    expiration_date: Optional[date] = None
    strike_price: Optional[float] = None
    option_type: Optional[str] = None


class TradeResponse(BaseModel):
    id: int
    symbol: str
    quantity: int
    price: float
    side: str
    timestamp: datetime
    strategy: Optional[str]
    expiration_date: Optional[datetime]
    strike_price: Optional[float]
    option_type: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[TradeResponse])
async def list_trades(
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """List all trades"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    trades = db_instance.list_trades()
    return trades


@router.post("/", response_model=TradeResponse)
async def create_trade(
    trade: TradeCreate,
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Create a new trade"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    # Convert date to datetime
    expiration_dt = None
    if trade.expiration_date:
        expiration_dt = datetime.combine(trade.expiration_date, datetime.min.time())
    
    trade_obj = Trade(
        symbol=trade.symbol.upper(),
        quantity=trade.quantity,
        price=trade.price,
        side=trade.side,
        timestamp=datetime.now(),
        strategy=trade.strategy,
        expiration_date=expiration_dt,
        strike_price=trade.strike_price,
        option_type=trade.option_type,
    )
    
    try:
        inserted_trade = db_instance.insert_trade(trade_obj)
        return inserted_trade
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: int,
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get a specific trade"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    trades = db_instance.list_trades()
    trade = next((t for t in trades if t.id == trade_id), None)
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    return trade

