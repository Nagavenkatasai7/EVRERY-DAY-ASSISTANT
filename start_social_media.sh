#!/bin/bash
# Quick start script for Social Media Automation UI

echo "🚀 Starting Social Media Automation UI..."
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✓ Activating virtual environment..."
    source venv/bin/activate
fi

# Check for required API keys
if [ -f ".env" ]; then
    echo "✓ Loading environment variables..."
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠️  Warning: .env file not found"
    echo "   Create one with your API keys:"
    echo "   cp .env.example .env"
    echo ""
fi

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  Warning: ANTHROPIC_API_KEY not set"
    echo "   Add it to your .env file"
fi

# Check if TAVILY_API_KEY is set
if [ -z "$TAVILY_API_KEY" ]; then
    echo "⚠️  Warning: TAVILY_API_KEY not set"
    echo "   Add it to your .env file for trend discovery"
fi

echo ""
echo "🌐 Opening browser at http://localhost:8501"
echo "📝 Press Ctrl+C to stop the server"
echo ""

# Start Streamlit
streamlit run social_media_app.py --server.port 8501 --server.address localhost
