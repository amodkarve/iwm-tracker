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
    
    def _get_connection(self):
        """Get a database connection, creating it if necessary."""
        if self.db_path == ":memory:":
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path)
                self._create_tables(self._conn.cursor())
                self._conn.commit()
            return self._conn
        else:
            return sqlite3.connect(self.db_path)
    
    def _create_tables(self, cursor):
        """Create database tables if they don't exist."""
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
    
    def _init_db(self):
        """Initialize database and create tables if they don't exist."""
        if self.db_path != ":memory:":
            # For file-based databases, create tables immediately
            conn = self._get_connection()
            self._create_tables(conn.cursor())
            conn.commit()
            conn.close()
    
    def insert_trade(self, trade: Trade) -> Trade:
        """Insert a trade into the database."""
        conn = self._get_connection()
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
        
        # Close connection for file-based databases
        if self.db_path != ":memory:":
            conn.close()
        
        return trade
    
    def list_trades(self) -> List[Trade]:
        """Retrieve all trades from the database."""
        conn = self._get_connection()
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
        
        # Close connection for file-based databases
        if self.db_path != ":memory:":
            conn.close()
        
        return trades
    
    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None


# Global database instance
db = Database() 