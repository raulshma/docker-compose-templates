#!/usr/bin/env bash
# Register the crawl4ai MCP server (SSE transport) with local AI clients.
# Reads CRAWL4AI_API_TOKEN from .env, registers with Claude Code if present,
# and writes a drop-in mcp.json snippet for Cursor / Windsurf / VS Code / ZCode.
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="${CRAWL4AI_PORT:-11235}"
SSE_URL="http://localhost:${PORT}/mcp/sse"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

TOKEN="${CRAWL4AI_API_TOKEN:-}"
if [[ -z "$TOKEN" ]]; then
  echo "ERROR: CRAWL4AI_API_TOKEN is not set." >&2
  echo "Add it to .env first (generate one: openssl rand -hex 32)." >&2
  exit 1
fi

# Sanity check: server up and MCP endpoint answering?
if ! curl -sf "http://localhost:${PORT}/health" >/dev/null 2>&1; then
  echo "WARN: crawl4ai is not reachable on port ${PORT}. Run: docker compose up -d" >&2
fi

# Drop-in snippet for any client that reads an mcp.json (Cursor, Windsurf, VS Code, ZCode)
mkdir -p mcp
cat > mcp/crawl4ai.mcp.json <<EOF
{
  "mcpServers": {
    "crawl4ai": {
      "url": "${SSE_URL}",
      "headers": {
        "Authorization": "Bearer ${TOKEN}"
      }
    }
  }
}
EOF
echo "Wrote mcp/crawl4ai.mcp.json (url: ${SSE_URL})"

# Claude Code CLI registration
if command -v claude >/dev/null 2>&1; then
  claude mcp remove crawl4ai >/dev/null 2>&1 || true
  claude mcp add --transport sse crawl4ai "$SSE_URL" \
    --header "Authorization: Bearer ${TOKEN}"
  echo "Registered 'crawl4ai' with Claude Code (local scope)."
else
  echo "claude CLI not found — skipped Claude Code registration."
fi

echo
echo "MCP endpoints:"
echo "  SSE:      ${SSE_URL}"
echo "  WebSocket: ws://localhost:${PORT}/mcp/ws"
echo "  Schemas:  http://localhost:${PORT}/mcp/schema"
echo "Tools: md, html, screenshot, pdf, execute_js, crawl, ask"
