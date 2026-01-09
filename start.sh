#!/bin/bash

# ==============================================================================
# STAC Server Startup Script
# ==============================================================================
# Uses tmux to run the server in the background.
# Automatically cleans up previous sessions.

SESSION_NAME="stac-server"
WORK_DIR="/home/sungche/stac"
SERVER_CMD="python src/server.py"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 0. Check for build argument
if [ "$1" == "build" ]; then
    echo "Triggering STAC Catalog Regeneration..."
    # Run the build script synchronously so we see errors
    PYTHONPATH=. .venv/bin/python src/main.py build "${@:2}"
    
    if [ $? -ne 0 ]; then
        echo "Error: Build failed. Aborting server start."
        exit 1
    fi
    echo "Build complete."
elif [ "$1" == "help" ]; then
    echo "Usage: ./start.sh [mode]"
    echo "Modes:"
    echo "  (empty)   Start server only"
    echo "  build     Regenerate STAC catalogs then start server"
    exit 0
fi

# 1. Check for tmux
if ! command_exists tmux; then
    echo "Error: tmux is not installed. Please install it (e.g., sudo apt install tmux)."
    exit 1
fi

echo "Preparing to start STAC Server..."

# 2. Stop existing session and process
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "   Stopping existing tmux session '$SESSION_NAME'..."
    tmux kill-session -t $SESSION_NAME
fi

# Force kill any lingering server processes just in case
pkill -f "$SERVER_CMD" 2>/dev/null

# 3. Start new session
echo "   Starting new tmux session..."
cd "$WORK_DIR" || exit 1

# Create session in detached mode
tmux new-session -d -s $SESSION_NAME

# Send commands to the tmux session
# Activate virtual environment
tmux send-keys -t $SESSION_NAME "source .venv/bin/activate" C-m
# Run server
tmux send-keys -t $SESSION_NAME "$SERVER_CMD" C-m

echo "STAC Server is running in background (tmux session: $SESSION_NAME)."
echo ""
echo "To view logs/console:   tmux attach -t $SESSION_NAME"
echo "To detach (keep running):  Press 'Ctrl+b' then 'd'"
echo "To stop server:         ./stop.sh (or kill the session)"