"""
FastAPI backend for IWM Tracker
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from backend.routers import auth, trades, market_data, analytics, recommendations

app = FastAPI(
    title="IWM Tracker API",
    description="API for IWM Put Selling Strategy Tracker",
    version="1.0.0"
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


@app.get("/")
async def root():
    return {"message": "IWM Tracker API", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    return {"status": "healthy"}

