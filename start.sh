#!/bin/bash

# EmbedScape Start Script
# Creates uv environment on first run, then starts both backend and frontend

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_msg() {
    echo -e "${2}${1}${NC}"
}

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    print_msg "❌ uv is not installed. Installing uv..." "$RED"
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Source the shell config to get uv in PATH
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
    fi

    if ! command -v uv &> /dev/null; then
        print_msg "❌ Failed to install uv. Please install manually: https://github.com/astral-sh/uv" "$RED"
        exit 1
    fi
    print_msg "✓ uv installed successfully" "$GREEN"
fi

# Backend setup
print_msg "🔧 Setting up backend..." "$BLUE"
cd backend

if [ ! -d ".venv" ]; then
    print_msg "📦 First run detected - creating uv environment..." "$YELLOW"
    uv venv
fi

# Always install/update dependencies
print_msg "📦 Installing/Updating Python dependencies..." "$YELLOW"
uv pip install -r requirements.txt
print_msg "✓ Backend dependencies installed" "$GREEN"

cd ..

# Frontend setup
print_msg "🔧 Setting up frontend..." "$BLUE"
cd frontend

# Always install/update dependencies
print_msg "📦 Installing/Updating frontend dependencies..." "$YELLOW"
npm install
print_msg "✓ Frontend dependencies installed" "$GREEN"

cd ..

# Start both servers
print_msg "\n🚀 Starting EmbedScape..." "$GREEN"
print_msg "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "$BLUE"

# Function to cleanup on exit
cleanup() {
    print_msg "\n\n🛑 Shutting down EmbedScape..." "$YELLOW"
    kill $(jobs -p) 2>/dev/null
    wait 2>/dev/null
    print_msg "✓ Shutdown complete" "$GREEN"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Start backend
print_msg "🐍 Starting Python backend on http://localhost:8000" "$BLUE"
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start frontend
print_msg "⚡ Starting Svelte frontend on http://localhost:5173" "$BLUE"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

print_msg "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "$GREEN"
print_msg "\n✨ EmbedScape is running!" "$GREEN"
print_msg "   Frontend: http://localhost:5173" "$GREEN"
print_msg "   Backend:  http://localhost:8000" "$GREEN"
print_msg "   API Docs: http://localhost:8000/docs" "$GREEN"
print_msg "\n📊 Press Ctrl+C to stop both servers\n" "$YELLOW"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
