
cd /home/sungche/stac
source .venv/bin/activate
uv run src/server.py
pkill -f "src/server.py