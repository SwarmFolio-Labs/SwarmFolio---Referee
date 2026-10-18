#!/usr/bin/env bash
# One command for the demo: the API (:8000) + the web app (:5173), and with --agents the 5 Fetch agents.
# Ctrl+C (or `kill <pid>`) stops everything it started.
#
#   scripts/demo.sh             # API + web app
#   scripts/demo.sh --agents    # also the 5 agents (needs the seeds and an LLM key in .env)
#
# Ports can be changed with API_PORT=... WEB_PORT=... scripts/demo.sh
set -uo pipefail
cd "$(dirname "$0")/.."

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
WITH_AGENTS=false
for arg in "$@"; do
  case "$arg" in
    --agents) WITH_AGENTS=true ;;
    -h|--help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg (try --help)" >&2; exit 2 ;;
  esac
done

PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
if ! command -v npm >/dev/null 2>&1 && [ -s "$HOME/.nvm/nvm.sh" ]; then
  . "$HOME/.nvm/nvm.sh"
fi
command -v npm >/dev/null 2>&1 || { echo "npm not found: install Node.js 20+ first." >&2; exit 1; }

port_free() { "$PY" -c "import socket,sys; s=socket.socket(); sys.exit(s.connect_ex(('127.0.0.1', int(sys.argv[1]))) == 0)" "$1"; }
for port in "$API_PORT" "$WEB_PORT"; do
  port_free "$port" || { echo "Port $port is already in use. Stop whatever runs there, or set API_PORT / WEB_PORT." >&2; exit 1; }
done
if [ "$WITH_AGENTS" = true ]; then
  for port in 8001 8002 8003 8004 8005; do
    port_free "$port" || { echo "Agent port $port is already in use (is run_all already running?)." >&2; exit 1; }
  done
fi

[ -d frontend/node_modules ] || (cd frontend && npm install)

NAMES=()
PIDS=()
# Each process gets its own process group (set -m), so stopping it also stops its children
# (npm -> vite, run_all -> 5 agents). Output is prefixed with the process name.
start() {
  local name="$1"; shift
  set -m
  "$@" > >(awk -v p="[$name] " '{ print p $0; fflush() }') 2>&1 &
  PIDS+=("$!")
  set +m
  NAMES+=("$name")
}

STOPPING=false
stop_all() {
  [ "$STOPPING" = true ] && return
  STOPPING=true
  # PIPE too: if our output is piped (demo.sh | tee log) and the reader died with the same Ctrl+C,
  # a failed echo must not kill us before the children are stopped.
  trap '' INT TERM HUP PIPE
  echo 2>/dev/null
  echo "Stopping ${NAMES[*]}..." 2>/dev/null
  for pid in "${PIDS[@]}"; do kill -TERM -- "-$pid" 2>/dev/null; done
  for _ in $(seq 1 50); do  # up to 10 s, then force
    alive=false
    for pid in "${PIDS[@]}"; do kill -0 -- "-$pid" 2>/dev/null && alive=true; done
    [ "$alive" = false ] && break
    sleep 0.2
  done
  for pid in "${PIDS[@]}"; do kill -KILL -- "-$pid" 2>/dev/null; done
  echo "Stopped." 2>/dev/null
}
trap 'stop_all; exit 0' INT TERM HUP
trap 'stop_all' EXIT

start api "$PY" -m uvicorn api:app --host 127.0.0.1 --port "$API_PORT"
start web env API_URL="http://127.0.0.1:$API_PORT" sh -c "cd frontend && exec npm run dev -- --port $WEB_PORT --strictPort"
[ "$WITH_AGENTS" = true ] && start agents "$PY" -m agents.run_all

# Wait for the API, so the URLs printed below work right away.
for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:$API_PORT/api/clients" >/dev/null 2>&1 && break
  sleep 0.5
done

echo
echo "  Web app:  http://localhost:$WEB_PORT"
echo "  API:      http://localhost:$API_PORT/api/clients   (docs: http://localhost:$API_PORT/docs)"
[ "$WITH_AGENTS" = true ] && echo "  Agents:   ports 8001-8005 (addresses and Inspector links are printed above)"
echo "  Ctrl+C to stop everything."
echo

# If any process dies, stop the rest instead of leaving half a demo running.
while true; do
  for i in "${!PIDS[@]}"; do
    if ! kill -0 "${PIDS[$i]}" 2>/dev/null; then
      echo "${NAMES[$i]} exited; stopping the rest." >&2
      exit 1
    fi
  done
  sleep 1
done
