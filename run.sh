#!/bin/bash
# Convenience script to run the scanner UI
# Automatically handles virtual environment activation

# Ensure we're in the project root
cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Running setup first..."
    ./setup.sh
fi

# Run the UI using the venv python directly (no need to 'activate' the shell)
echo "🚀 Launching Momentum Scanner..."
./venv/bin/python scripts/run_ui.py
