"""
Tests for database config operations
"""
import pytest
from wheeltracker.db import Database


class TestConfigDatabase:
    """Test config database operations"""
    
    def test_get_config_default(self):
        """Test getting config value with default"""
        db = Database(":memory:")
        
        # Get non-existent config with default
        value = db.get_config("test_key", "default_value")
        assert value == "default_value"
    
    def test_set_and_get_config(self):
        """Test setting and getting config value"""
        db = Database(":memory:")
        
        # Set config
        db.set_config("test_key", "test_value")
        
        # Get config
        value = db.get_config("test_key")
        assert value == "test_value"
    
    def test_update_config(self):
        """Test updating existing config value"""
        db = Database(":memory:")
        
        # Set initial value
        db.set_config("test_key", "initial_value")
        assert db.get_config("test_key") == "initial_value"
        
        # Update value
        db.set_config("test_key", "updated_value")
        assert db.get_config("test_key") == "updated_value"
    
    def test_starting_portfolio_value(self):
        """Test starting portfolio value config"""
        db = Database(":memory:")
        
        # Set starting portfolio value
        db.set_config("starting_portfolio_value", "1000000.0")
        
        # Get starting portfolio value
        value = db.get_config("starting_portfolio_value")
        assert value == "1000000.0"
        
        # Update starting portfolio value
        db.set_config("starting_portfolio_value", "1500000.0")
        value = db.get_config("starting_portfolio_value")
        assert value == "1500000.0"
    
    def test_multiple_config_keys(self):
        """Test multiple config keys"""
        db = Database(":memory:")
        
        # Set multiple configs
        db.set_config("key1", "value1")
        db.set_config("key2", "value2")
        db.set_config("key3", "value3")
        
        # Get all configs
        assert db.get_config("key1") == "value1"
        assert db.get_config("key2") == "value2"
        assert db.get_config("key3") == "value3"
    
    def test_config_with_numeric_string(self):
        """Test config with numeric string value"""
        db = Database(":memory:")
        
        # Set numeric string
        db.set_config("numeric_key", "12345.67")
        value = db.get_config("numeric_key")
        assert value == "12345.67"
        
        # Verify it's stored as string
        assert isinstance(value, str)


