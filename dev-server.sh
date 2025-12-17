#!/bin/bash
# Quick start script for local development with test database

echo "🎬 Starting FlickStream in development mode..."
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if dev.db exists
if [ ! -f "dev.db" ]; then
    echo "📦 dev.db not found. Initializing test database..."
    python3 init_dev_db.py
    echo ""
fi

# Set environment variables for local dev
export DB_PATH=./dev.db
export TMDB_ACCOUNT_ID=dev_account

echo "✓ Using test database with 5 classic movies"
echo "✓ Starting Flask development server..."
echo ""
echo "🌐 Open http://localhost:5000 in your browser"
echo ""

# Run the app
uv run python app.py
