#!/bin/bash
# Generate (do not install) a macOS launchd user agent for the weekly cycle.
# Install explicitly with: launchctl bootstrap gui/$(id -u) <plist>
set -euo pipefail
REPO="${SCS_FKB_REPO:-$(cd "$(dirname "$0")/.." && pwd)}"
: "${SCS_FKB_DATA_ROOT:?set SCS_FKB_DATA_ROOT}"
: "${SCS_FKB_RUN_ROOT:?set SCS_FKB_RUN_ROOT}"
OUT="${1:-$SCS_FKB_RUN_ROOT/scheduler/com.scs-fkb.weekly.plist}"
mkdir -p "$(dirname "$OUT")"
cat > "$OUT" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.scs-fkb.weekly</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REPO/scripts/run_weekly.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Weekday</key><integer>0</integer><key>Hour</key><integer>2</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$SCS_FKB_RUN_ROOT/scheduler/weekly.out.log</string>
  <key>StandardErrorPath</key><string>$SCS_FKB_RUN_ROOT/scheduler/weekly.err.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>SCS_FKB_DATA_ROOT</key><string>$SCS_FKB_DATA_ROOT</string>
    <key>SCS_FKB_RUN_ROOT</key><string>$SCS_FKB_RUN_ROOT</string>
    <key>SCS_FKB_REPO</key><string>$REPO</string>
  </dict>
</dict>
</plist>
PLIST
echo "wrote $OUT"
echo "install with: launchctl bootstrap gui/$(id -u) $OUT"
