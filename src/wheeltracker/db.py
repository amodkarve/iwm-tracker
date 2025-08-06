import sqlite3
import os
from typing import List
from .models import Trade, Cashflow
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "wheel.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database and create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    side TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    strategy TEXT
                )
            """)
            
            # Create cashflows table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cashflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL,
                    symbol TEXT,
                    timestamp TEXT NOT NULL,
                    description TEXT
                )
            """)
            
            conn.commit()
    
    def insert_trade(self, trade: Trade) -> Trade:
        """Insert a trade into the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (symbol, quantity, price, side, timestamp, strategy)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                trade.symbol,
                trade.quantity,
                trade.price,
                trade.side,
                trade.timestamp.isoformat(),
                trade.strategy
            ))
            conn.commit()
            
            # Get the inserted trade with ID
            trade.id = cursor.lastrowid
            return trade
    
    def list_trades(self) -> List[Trade]:
        """Retrieve all trades from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, symbol, quantity, price, side, timestamp, strategy
                FROM trades
                ORDER BY timestamp DESC
            """)
            
            trades = []
            for row in cursor.fetchall():
                trade = Trade(
                    id=row[0],
                    symbol=row[1],
                    quantity=row[2],
                    price=row[3],
                    side=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    strategy=row[6]
                )
                trades.append(trade)
            
            return trades


# Global database instance
db = Database() 