#!/usr/bin/env bash

# ==============================================================================
# STAC Server Startup Script (v2.1.0)
# ==============================================================================
# Entry point for building and serving the STAC Catalog.

set -euo pipefail

# --- Configuration ---
SESSION_NAME="stac-server"
WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_CMD="uv run src/cli.py"

# ANSI Color Codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper Functions
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# Ensure dependencies
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

check_deps() {
    if ! command -v uv &> /dev/null; then
        log_error "'uv' is not installed."
        exit 1
    fi
    if ! command -v tmux &> /dev/null; then
        log_error "'tmux' is not installed."
        exit 1
    fi
}

# Main Logic
check_deps

MODE="${1:-serve}" # Default to serve
if [ "$#" -ge 1 ]; then
    shift # Shift args so $@ contains the rest
fi

case "$MODE" in
    "clean-build")
        log_info "Starting Clean Build..."
        log_info "Command: $CLI_CMD build --clean --parallel --validate $*"
        $CLI_CMD build --clean --parallel --validate "$@"
        ;;
    "serve")
        log_info "Preparing STAC Server..."
        ./stop.sh # Use the robust stop script

        cd "$WORK_DIR"
        tmux new-session -d -s "$SESSION_NAME"
        
        # Run server
        # We pass remaining args to the serve command (e.g. --port)
        tmux send-keys -t "$SESSION_NAME" "$CLI_CMD serve $*" C-m
        
        log_success "Server started in background (tmux: $SESSION_NAME)."
        log_info "View logs:   tmux attach -t $SESSION_NAME"
        log_info "Stop server: ./stop.sh"
        ;;
    "build-serve")
        log_info "Running Clean Build & Serve..."
        $0 clean-build "$@"
        if [ $? -eq 0 ]; then
            $0 serve
        else
            log_error "Build failed. Server not started."
            exit 1
        fi
        ;;
    "help"|*)
        echo -e "${BLUE}STAC Server Manager CLI${NC}"
        echo -e "Usage: ./start.sh [COMMAND] [ARGS]"
        echo ""
        echo "Commands:"
        echo -e "  ${GREEN}serve${NC}        Start the server in background (tmux)"
        echo -e "  ${GREEN}clean-build${NC}  Clean output directory and rebuild all in parallel"
        echo -e "  ${GREEN}build-serve${NC}  Run clean-build followed by serve (Args passed to build)"
        echo -e "  ${GREEN}help${NC}         Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./start.sh serve"
        echo "  ./start.sh clean-build"
        echo "  ./start.sh build-serve"
        ;;
esac
