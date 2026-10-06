# crawl4ai (Docker Compose + MCP)

Self-hosted [crawl4ai](https://crawl4ai.com) server: REST API for crawling plus a built-in
MCP server (tools: `md`, `html`, `screenshot`, `pdf`, `execute_js`, `crawl`, `ask`).

## Setup

```bash
cd stacks/crawl4ai
cp .env.example .env
# generate a token and put it in .env as CRAWL4AI_API_TOKEN
openssl rand -hex 32

docker compose up -d
curl http://localhost:11235/health   # no auth needed; ~10s startup
```

Requires ~4GB RAM. Without `CRAWL4AI_API_TOKEN` compose refuses to start (the server
would bind to loopback only and the published port would return connection resets).

## REST API

Base URL: `http://localhost:11235` — every endpoint except `GET /health` requires
`Authorization: Bearer $CRAWL4AI_API_TOKEN`.

```bash
curl -X POST http://localhost:11235/crawl \
  -H "Authorization: Bearer $CRAWL4AI_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com"], "browser_config": {"headless": true}}'
```

## MCP

Endpoints served by the same container:

| Transport  | URL                                    |
|------------|----------------------------------------|
| SSE        | `http://localhost:11235/mcp/sse`       |
| WebSocket  | `ws://localhost:11235/mcp/ws`          |
| Schemas    | `http://localhost:11235/mcp/schema`    |

### Register with clients

Run from this folder (`stacks/crawl4ai/`):

```bash
# bash (Linux / macOS / Git Bash)
./scripts/setup-mcp.sh

# PowerShell
./scripts/setup-mcp.ps1
```

The script reads the token from `.env`, registers `crawl4ai` with Claude Code if the
`claude` CLI is installed, and writes `mcp/crawl4ai.mcp.json` — a drop-in snippet for
Cursor (`.cursor/mcp.json`), Windsurf, VS Code (`.vscode/mcp.json`) and ZCode.

Claude Code manually:

```bash
claude mcp add --transport sse crawl4ai http://localhost:11235/mcp/sse \
  --header "Authorization: Bearer $CRAWL4AI_API_TOKEN"
```

## Optional: LLM keys

Uncomment `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` etc. in `.env` to enable the `ask`
tool and LLM extraction strategies.
