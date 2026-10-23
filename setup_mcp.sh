#!/usr/bin/env bash
# setup_mcp.sh — Register the Job-Apply Gmail MCP server with Antigravity
#
# This script:
#   1. Writes ~/.gemini/config/mcp_config.json (creates/merges the entry)
#   2. Prints instructions to reload Antigravity
#
# Run once:  bash setup_mcp.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
SERVER_SCRIPT="$PROJECT_DIR/mcp_gmail_server.py"
MCP_CONFIG_DIR="$HOME/.gemini/config"
MCP_CONFIG_FILE="$MCP_CONFIG_DIR/mcp_config.json"

# ── Checks ──────────────────────────────────────────────────────────────────
if [ ! -f "$PYTHON_BIN" ]; then
  echo "❌  venv not found at $PYTHON_BIN"
  echo "    Run:  python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [ ! -f "$SERVER_SCRIPT" ]; then
  echo "❌  Server script not found: $SERVER_SCRIPT"
  exit 1
fi

# Verify mcp package is importable using venv python
if ! "$PYTHON_BIN" -c "import mcp; print('mcp ok')" 2>/dev/null | grep -q "mcp ok"; then
  echo "❌  mcp package not installed in venv."
  echo "    Run:  $PYTHON_BIN -m pip install 'mcp>=1.0.0'"
  exit 1
fi

# ── Create config dir if needed ──────────────────────────────────────────────
mkdir -p "$MCP_CONFIG_DIR"

# ── Build or merge mcp_config.json ──────────────────────────────────────────
NEW_ENTRY=$(cat <<JSON
{
  "mcpServers": {
    "job-apply-gmail": {
      "command": "$PYTHON_BIN",
      "args": ["$SERVER_SCRIPT"],
      "env": {
        "PYTHONPATH": "$PROJECT_DIR"
      }
    }
  }
}
JSON
)

if [ -f "$MCP_CONFIG_FILE" ]; then
  # Merge: add/overwrite the "job-apply-gmail" key, preserve others
  python3 - <<PYEOF
import json, sys

config_path = "$MCP_CONFIG_FILE"
new_entry   = json.loads('''$NEW_ENTRY''')

with open(config_path) as f:
    existing = json.load(f)

servers = existing.get("mcpServers", {})
servers.update(new_entry["mcpServers"])
existing["mcpServers"] = servers

with open(config_path, "w") as f:
    json.dump(existing, f, indent=2)
    f.write("\\n")

print(f"✅  Updated existing config: $MCP_CONFIG_FILE")
PYEOF
else
  # Write fresh
  echo "$NEW_ENTRY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d, indent=2))" > "$MCP_CONFIG_FILE"
  echo "✅  Created new config: $MCP_CONFIG_FILE"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MCP Server registered: job-apply-gmail"
echo "  Python:  $PYTHON_BIN"
echo "  Script:  $SERVER_SCRIPT"
echo "  Config:  $MCP_CONFIG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "👉 Next steps:"
echo "   1. Restart Antigravity (reload the window or run 'agy reload')"
echo "   2. In chat, type:  list_available_jobs"
echo "      or:  draft_job_application  job_id=<ID from the list>"
echo ""
