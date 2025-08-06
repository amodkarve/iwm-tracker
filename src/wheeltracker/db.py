import sqlite3
import os
from typing import List
from .models import Trade, Cashflow
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "wheel.db"):
        self.db_path = db_path
        self._conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database and create tables if they don't exist."""
        # For in-memory databases, we need to ensure the schema is created
        # before any other operations
        if self.db_path == ":memory:":
            self._conn = sqlite3.connect(self.db_path)
            cursor = self._conn.cursor()
            
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
            
            self._conn.commit()
        else:
            # For file-based databases, use the original approach
            conn = sqlite3.connect(self.db_path)
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
            conn.close()
    
    def _ensure_tables_exist(self, cursor):
        """Ensure tables exist (for in-memory databases)."""
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
    
    def insert_trade(self, trade: Trade) -> Trade:
        """Insert a trade into the database."""
        if self.db_path == ":memory:":
            cursor = self._conn.cursor()
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
            self._conn.commit()
            
            # Get the inserted trade with ID
            trade.id = cursor.lastrowid
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Ensure tables exist (for in-memory databases)
            self._ensure_tables_exist(cursor)
            
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
            conn.close()
        
        return trade
    
    def list_trades(self) -> List[Trade]:
        """Retrieve all trades from the database."""
        if self.db_path == ":memory:":
            cursor = self._conn.cursor()
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
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Ensure tables exist (for in-memory databases)
            self._ensure_tables_exist(cursor)
            
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
            
            conn.close()
        
        return trades


# Global database instance
db = Database() 