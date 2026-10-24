#!/usr/bin/env bash
# Run from anywhere; .env and production compose are resolved beside this script.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
docker compose -f compose.production.yml pull app
docker compose -f compose.production.yml up -d --no-deps --wait app
docker compose -f compose.production.yml ps
