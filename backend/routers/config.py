"""
Configuration router for database management
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from wheeltracker.db import db, Database
from backend.routers.auth import get_current_user

router = APIRouter()

# Database paths
PROD_DB_PATH = os.getenv('WHEEL_DB_PATH', '/app/data/wheel.db')
TEST_DB_PATH = '/app/data/wheel_test.db'


class DatabaseConfig(BaseModel):
    mode: str  # 'prod' or 'test'
    db_path: str
    is_production: bool


@router.get("/database", response_model=DatabaseConfig)
async def get_database_config(
    current_user: str = Depends(get_current_user)
):
    """Get current database configuration"""
    # Default to production
    mode = 'prod'
    db_path = PROD_DB_PATH
    
    return DatabaseConfig(
        mode=mode,
        db_path=db_path,
        is_production=(mode == 'prod')
    )


@router.get("/database/paths")
async def get_database_paths(
    current_user: str = Depends(get_current_user)
):
    """Get available database paths"""
    return {
        'production': PROD_DB_PATH,
        'test': TEST_DB_PATH
    }


class StartingPortfolioValue(BaseModel):
    value: float


@router.get("/starting-portfolio-value", response_model=StartingPortfolioValue)
async def get_starting_portfolio_value(
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get starting portfolio value"""
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    # Default to 1M if not set
    default_value = 1000000.0
    value_str = db_instance.get_config('starting_portfolio_value', str(default_value))
    
    try:
        value = float(value_str)
    except (ValueError, TypeError):
        value = default_value
    
    return StartingPortfolioValue(value=value)


@router.post("/starting-portfolio-value", response_model=StartingPortfolioValue)
async def set_starting_portfolio_value(
    config: StartingPortfolioValue,
    db_path: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Set starting portfolio value"""
    if config.value <= 0:
        raise HTTPException(status_code=400, detail="Starting portfolio value must be positive")
    
    if db_path:
        db_instance = Database(db_path)
    else:
        db_instance = db
    
    db_instance.set_config('starting_portfolio_value', str(config.value))
    
    return StartingPortfolioValue(value=config.value)

