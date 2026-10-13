#!/bin/sh
# DeerFlow Gateway start-up on Railway.
#   1. seed the writable extensions config on the volume (first boot only)
#   2. render config.yaml from Railway variables
#   3. wait until Postgres and Redis actually answer (services start in parallel)
#   4. create the first admin account in the background (idempotent)
#   5. exec uvicorn (single worker, as upstream recommends)
set -eu

log() { echo "[deerflow-railway] $*"; }

PY=/app/backend/.venv/bin/python
PORT="${PORT:-8001}"
DEER_FLOW_HOME="${DEER_FLOW_HOME:-/app/backend/.deer-flow}"
DEER_FLOW_EXTENSIONS_CONFIG_PATH="${DEER_FLOW_EXTENSIONS_CONFIG_PATH:-$DEER_FLOW_HOME/extensions_config.json}"
# The Gateway calls itself for IM channels; never route that through private
# DNS (a service cannot resolve its own *.railway.internal name at boot).
DEER_FLOW_CHANNELS_LANGGRAPH_URL="${DEER_FLOW_CHANNELS_LANGGRAPH_URL:-http://127.0.0.1:${PORT}/api}"
DEER_FLOW_CHANNELS_GATEWAY_URL="${DEER_FLOW_CHANNELS_GATEWAY_URL:-http://127.0.0.1:${PORT}}"
export PORT DEER_FLOW_HOME DEER_FLOW_EXTENSIONS_CONFIG_PATH \
       DEER_FLOW_CHANNELS_LANGGRAPH_URL DEER_FLOW_CHANNELS_GATEWAY_URL

mkdir -p "$DEER_FLOW_HOME" "$(dirname "$DEER_FLOW_EXTENSIONS_CONFIG_PATH")"
if [ ! -s "$DEER_FLOW_EXTENSIONS_CONFIG_PATH" ]; then
  cp /opt/railway/extensions_config.json "$DEER_FLOW_EXTENSIONS_CONFIG_PATH"
  log "seeded $DEER_FLOW_EXTENSIONS_CONFIG_PATH"
fi

"$PY" /opt/railway/render_config.py
"$PY" /opt/railway/wait_for_services.py

# Double fork: the helper is re-parented to the init process, which reaps it.
( "$PY" /opt/railway/bootstrap_admin.py & )

cd /app/backend
export PYTHONPATH=.

if [ "${GATEWAY_WORKERS:-1}" = "1" ]; then
  # One worker (upstream default): serve on a dual-stack socket so Railway's
  # IPv4 healthcheck and IPv6-only private networks can both reach it.
  exec uv run --no-sync python /opt/railway/serve.py
fi

log "WARNING: GATEWAY_WORKERS=${GATEWAY_WORKERS}; upstream supports >1 only with run_ownership heartbeats enabled. Listening on 0.0.0.0 (IPv4 only)."
exec uv run --no-sync uvicorn app.gateway.app:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --workers "${GATEWAY_WORKERS}" \
  --timeout-graceful-shutdown 10
