import sqlite3
import os
from typing import List
from .models import Trade, Cashflow
from datetime import datetime


class Database:
    def __init__(self, db_path: str = None):
        # Support environment variable for database path
        # This allows separate test and production databases
        if db_path is None:
            db_path = os.getenv('WHEEL_DB_PATH', 'wheel.db')
        
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
                strategy TEXT,
                expiration_date TEXT,
                strike_price REAL,
                option_type TEXT
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
        
        # Create config table for portfolio settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
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
            INSERT INTO trades (symbol, quantity, price, side, timestamp, strategy, expiration_date, strike_price, option_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.symbol,
            trade.quantity,
            trade.price,
            trade.side,
            trade.timestamp.isoformat(),
            trade.strategy,
            trade.expiration_date.isoformat() if trade.expiration_date else None,
            trade.strike_price,
            trade.option_type
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
            SELECT id, symbol, quantity, price, side, timestamp, strategy, expiration_date, strike_price, option_type
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
                strategy=row[6],
                expiration_date=datetime.fromisoformat(row[7]) if row[7] else None,
                strike_price=row[8],
                option_type=row[9]
            )
            trades.append(trade)
        
        # Close connection for file-based databases
        if self.db_path != ":memory:":
            conn.close()
        
        return trades
    
    def get_config(self, key: str, default: str = None) -> str:
        """Get a configuration value."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        # Close connection for file-based databases
        if self.db_path != ":memory:":
            conn.close()
        
        return row[0] if row else default
    
    def set_config(self, key: str, value: str) -> None:
        """Set a configuration value."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        from datetime import datetime
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO config (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, now))
        
        conn.commit()
        
        # Close connection for file-based databases
        if self.db_path != ":memory:":
            conn.close()
    
    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None


# Global database instance
db = Database() 