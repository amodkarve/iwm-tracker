#!/bin/bash
# Setup script for IWM Tracker

echo "🚀 Setting up IWM Tracker..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install streamlit pandas pydantic sqlite-utils numpy scipy yfinance python-dotenv altair

echo "✅ Setup complete!"
echo ""
echo "To run the enhanced app:"
echo "  source venv/bin/activate"
echo "  streamlit run app_enhanced.py"
echo ""
echo "Or run the original app:"
echo "  source venv/bin/activate"
echo "  streamlit run app.py"
