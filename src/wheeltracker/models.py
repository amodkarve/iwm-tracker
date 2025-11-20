from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class Trade(BaseModel):
    id: Optional[int] = None
    symbol: str
    quantity: int
    price: float
    side: str  # "buy" or "sell"
    timestamp: datetime
    strategy: Optional[str] = None
    # Option contract details
    expiration_date: Optional[datetime] = None  # For options: expiration date
    strike_price: Optional[float] = None  # For options: strike price
    option_type: Optional[str] = None  # "put" or "call" for options


class Cashflow(BaseModel):
    id: Optional[int] = None
    amount: float
    type: str  # "dividend", "interest", "fee", etc.
    symbol: Optional[str] = None
    timestamp: datetime
    description: Optional[str] = None 