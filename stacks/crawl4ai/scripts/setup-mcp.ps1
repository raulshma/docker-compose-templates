# Register the crawl4ai MCP server (SSE transport) with local AI clients.
# Reads CRAWL4AI_API_TOKEN from .env, registers with Claude Code if present,
# and writes a drop-in mcp.json snippet for Cursor / Windsurf / VS Code / ZCode.
param(
    [int]$Port = 11235,
    # claude mcp add scope: "local" (default), "user", or "project"
    [string]$Scope = "local"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$SseUrl = "http://localhost:$Port/mcp/sse"

$Token = $null
if (Test-Path .env) {
    foreach ($line in Get-Content .env) {
        if ($line -match '^\s*CRAWL4AI_API_TOKEN\s*=\s*(\S+)\s*$') {
            $Token = $Matches[1]
        }
    }
}

if (-not $Token) {
    Write-Error "CRAWL4AI_API_TOKEN is not set. Add it to .env first (generate one: openssl rand -hex 32)."
    exit 1
}

# Sanity check: server up?
try {
    Invoke-RestMethod "http://localhost:$Port/health" -TimeoutSec 5 | Out-Null
} catch {
    Write-Warning "crawl4ai is not reachable on port $Port. Run: docker compose up -d"
}

# Drop-in snippet for any client that reads an mcp.json (Cursor, Windsurf, VS Code, ZCode)
New-Item -ItemType Directory -Force -Path mcp | Out-Null
@{
    mcpServers = @{
        crawl4ai = @{
            url     = $SseUrl
            headers = @{ Authorization = "Bearer $Token" }
        }
    }
} | ConvertTo-Json -Depth 5 | Set-Content mcp\crawl4ai.mcp.json
Write-Host "Wrote mcp\crawl4ai.mcp.json (url: $SseUrl)"

# Claude Code CLI registration
if (Get-Command claude -ErrorAction SilentlyContinue) {
    claude mcp remove crawl4ai 2>$null
    claude mcp add --transport sse --scope $Scope crawl4ai $SseUrl --header "Authorization: Bearer $Token"
    Write-Host "Registered 'crawl4ai' with Claude Code ($Scope scope)."
} else {
    Write-Host "claude CLI not found - skipped Claude Code registration."
}

Write-Host ""
Write-Host "MCP endpoints:"
Write-Host "  SSE:       $SseUrl"
Write-Host "  WebSocket: ws://localhost:$Port/mcp/ws"
Write-Host "  Schemas:   http://localhost:$Port/mcp/schema"
Write-Host "Tools: md, html, screenshot, pdf, execute_js, crawl, ask"
