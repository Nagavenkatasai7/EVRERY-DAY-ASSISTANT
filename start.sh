#!/bin/bash

# AI Research Assistant - Start Script
# Starts the Streamlit application with proper error handling

echo "🚀 Starting AI Research Assistant..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your ANTHROPIC_API_KEY"
    exit 1
fi

# Check if API key is set
if ! grep -q "ANTHROPIC_API_KEY=sk-" .env; then
    echo "❌ Error: ANTHROPIC_API_KEY not properly configured in .env"
    exit 1
fi

echo "✅ Configuration validated"
echo ""
echo "🌐 Starting Streamlit application..."
echo "📍 Application will be available at: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

# Start Streamlit
streamlit run app.py
