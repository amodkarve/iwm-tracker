import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_app_syntax():
    """
    Test that the app file can be compiled/imported without syntax errors.
    """
    try:
        # We don't want to actually run the app, just check syntax
        # compile() will raise SyntaxError if the file is invalid
        with open('app_enhanced.py', 'r') as f:
            source = f.read()
        compile(source, 'app_enhanced.py', 'exec')
    except SyntaxError as e:
        pytest.fail(f"Syntax Error in app_enhanced.py: {e}")
    except Exception as e:
        pytest.fail(f"Error checking syntax: {e}")
