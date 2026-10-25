#!/usr/bin/env bash
# Optional Unix npm launcher; Python remains the only application runtime.
set -euo pipefail
python_bin=python3
if [[ -x .venv/bin/python ]]; then python_bin=.venv/bin/python; fi
app_port="${PORT:-3000}"
app_host=0.0.0.0
while (($#)); do
  case "$1" in
    --port) app_port="$2"; shift 2 ;;
    --host) app_host="$2"; shift 2 ;;
    --strictPort) shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
npm run build
exec "$python_bin" -m uvicorn backend.app.main:app --host "$app_host" --port "$app_port" --workers 1 --ws-max-size 65536
