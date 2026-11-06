#!/usr/bin/env bash
# Weekly, read-only knowledge checks. This script never downloads, ingests or
# edits the register; it writes a dated report under the run root.
set -euo pipefail

: "${SCS_FKB_DATA_ROOT:?set SCS_FKB_DATA_ROOT}"
: "${SCS_FKB_RUN_ROOT:?set SCS_FKB_RUN_ROOT}"
PYTHON="${PYTHON:-python3}"
TODAY="$(date +%F)"
DIR="$SCS_FKB_RUN_ROOT/P10-KB-141"
REPORT="$DIR/weekly-$TODAY.md"
mkdir -p "$DIR"
export PYTHONPATH="${PYTHONPATH:-src}"

{
  echo "# Weekly knowledge checks — $TODAY"
  echo
  echo "- Data root: \`$SCS_FKB_DATA_ROOT\`"
  echo "- This run is read-only: no download, ingest, register edit or index rebuild."
  echo
  echo "## Source currency"
  "$PYTHON" -m scs_fkb sources check --today "$TODAY"
  echo
  echo "## Watch (offline baseline)"
  "$PYTHON" -m scs_fkb watch --offline
  echo
  echo "## Facts"
  "$PYTHON" -m scs_fkb facts check --data-root "$SCS_FKB_DATA_ROOT"
  echo
  echo "## Terms"
  "$PYTHON" -m scs_fkb terms check --data-root "$SCS_FKB_DATA_ROOT"
  echo
  echo "## Playbooks"
  "$PYTHON" scripts/check_playbooks.py
  echo
  echo "## Knowledge gaps"
  "$PYTHON" -m scs_fkb knowledge gaps || true
  echo
  echo "## Review queue"
  echo "- Generated provision facts are drafts and need human review."
  echo "- New terms marked draft need a corpus check before approval."
  echo "- New source candidates remain in the candidate queue; nothing is promoted here."
} > "$REPORT"

echo "weekly report: $REPORT"
