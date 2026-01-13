#!/usr/bin/env bash

# ==============================================================================
# STAC Server Shutdown Script (v2.1.0)
# ==============================================================================
# Description: Safely terminates the STAC Server tmux session and cleanup 
#              associated background processes.
# ==============================================================================

# Strict mode
set -euo pipefail

# --- Configuration ---
SESSION_NAME="stac-server"

# ANSI Color Codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Helper Functions ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }

# --- Main Shutdown Logic ---

log_info "Initiating STAC Server shutdown..."

# 1. Terminate Tmux Session
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
    log_success "Tmux session '$SESSION_NAME' terminated."
else
    log_warn "No active tmux session '$SESSION_NAME' was found."
fi

# 2. Force Cleanup of Background Processes
# We target both the CLI wrapper and the underlying Uvicorn server
log_info "Performing process cleanup..."

# Function to kill processes and check status
cleanup_process() {
    local pattern=$1
    if pgrep -f "$pattern" > /dev/null; then
        pkill -f "$pattern"
        log_info "Sent termination signal to: $pattern"
    fi
}

cleanup_process "src/cli.py serve"
cleanup_process "uvicorn src.server.app"

# 3. Final Verification
sleep 1 # Brief pause to allow processes to exit
if ! pgrep -f "src/cli.py serve" > /dev/null; then
    log_success "Shutdown complete. All processes cleared."
else
    log_warn "Some processes are still lingering. You might need to check 'top' or 'ps'."
fi

echo "--------------------------------------------------"
