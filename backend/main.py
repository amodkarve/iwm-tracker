"""
FastAPI backend for IWM Tracker
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer
import os
import sys
import traceback

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from backend.routers import auth, trades, market_data, analytics, recommendations, config
from wheeltracker.db import db

app = FastAPI(
    title="IWM Tracker API",
    description="API for IWM Put Selling Strategy Tracker",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """
    Initialize database and run migrations on application startup.
    This ensures all tables (including new ones) are created automatically.
    
    The Database class automatically creates missing tables using CREATE TABLE IF NOT EXISTS,
    so this migration is safe and idempotent - it won't delete or modify existing data.
    """
    try:
        # The global db instance is created at module import time, which calls _init_db()
        # This ensures all tables (trades, cashflows, config) are created if they don't exist
        # Accessing db properties ensures initialization is complete
        db_path = db.db_path
        
        # Explicitly ensure tables are created (idempotent operation)
        # This is safe because CREATE TABLE IF NOT EXISTS won't modify existing tables
        conn = db._get_connection()
        db._create_tables(conn.cursor())
        conn.commit()
        conn.close()
        
        print(f"[INFO] Database initialized: {db_path}")
        print("[INFO] Database migrations completed (all tables verified/created)")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        # Don't raise - let the app start and handle errors at request time

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    error_detail = str(exc)
    error_traceback = traceback.format_exc()
    
    # Log the full traceback (in production, use proper logging)
    print(f"Unhandled exception: {error_traceback}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": error_detail,
            "type": type(exc).__name__,
        }
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(market_data.router, prefix="/api/market-data", tags=["market-data"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])
app.include_router(config.router, prefix="/api/config", tags=["config"])


@app.get("/")
async def root():
    return {"message": "IWM Tracker API", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    return {"status": "healthy"}

