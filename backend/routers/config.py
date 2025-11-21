"""
Configuration router for database management
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import os

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

