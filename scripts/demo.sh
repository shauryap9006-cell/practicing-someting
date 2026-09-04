#!/usr/bin/env bash
# RailTwin-X 1-Click Signature Hackathon Demo Launcher (SIH PS 26028)
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REPO_ROOT="$(dirname "$DIR")"

echo "================================================================="
echo "  RailTwin-X: Dynamic ETA Forecast & Station OS (SIH PS 26028)  "
echo "================================================================="

cd "$REPO_ROOT"
python3 -c "from data.db import get_db; db = get_db(); db.init_schema(); print(f'Database verified: {db.table_counts()}')"

echo "[1/3] Starting FastAPI backend on http://localhost:8000..."
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "[2/3] Starting Vite web dashboard on http://localhost:5173..."
cd "$REPO_ROOT/web"
npm run dev &
FRONTEND_PID=$!

sleep 4

echo "[3/3] Opening browser to Live Comparator..."
if command -v xdg-open > /dev/null; then
  xdg-open "http://localhost:5173/compare"
elif command -v open > /dev/null; then
  open "http://localhost:5173/compare"
fi

echo "================================================================="
echo "  DEMO READY! Press Ctrl+C to terminate services."
echo "  Foresight Console : http://localhost:5173/"
echo "  Live Comparator   : http://localhost:5173/compare"
echo "  The Time Machine  : http://localhost:5173/replay"
echo "  Ripple Board & DSS: http://localhost:5173/cascade"
echo "  Honest Model Card : http://localhost:5173/model-card"
echo "================================================================="

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
