#!/bin/bash
# One weekly update cycle + report. Intended for a macOS launchd user agent.
set -euo pipefail
REPO="${SCS_FKB_REPO:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$REPO"
export PYTHONPATH="${PYTHONPATH:-src}:src"
: "${SCS_FKB_DATA_ROOT:?set SCS_FKB_DATA_ROOT}"
: "${SCS_FKB_RUN_ROOT:?set SCS_FKB_RUN_ROOT}"
PYTHON="${PYTHON:-python3}"
"$PYTHON" scripts/update_cycle.py \
  --data-root "$SCS_FKB_DATA_ROOT" --run-root "$SCS_FKB_RUN_ROOT" --live
"$PYTHON" scripts/weekly_report.py --today "$(date +%F)" --task-id weekly
