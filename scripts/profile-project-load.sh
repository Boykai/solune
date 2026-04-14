#!/usr/bin/env bash
# ─── Cold-Start Project Load Profiler ───────────────────────────────────
# Measures endpoint latencies for the project selection + board loading
# flow that runs when a user logs in and selects a GitHub project.
#
# Usage:
#   ./scripts/profile-project-load.sh <session_cookie>
#   ./scripts/profile-project-load.sh <session_cookie> <project_id>
#
# If project_id is omitted, the script lists projects and uses the first one.
# ────────────────────────────────────────────────────────────────────────

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000/api/v1}"
COOKIE_NAME="session_id"
SESSION_ID="${1:?Usage: $0 <session_cookie> [project_id]}"
PROJECT_ID="${2:-}"

# curl timing format: DNS | Connect | TLS | StartTransfer | Total
CURL_TIMING='\n  DNS:            %{time_namelookup}s\n  Connect:        %{time_connect}s\n  TLS:            %{time_appconnect}s\n  Start-Transfer: %{time_starttransfer}s\n  Total:          %{time_total}s\n  Size:           %{size_download} bytes\n  HTTP Status:    %{http_code}\n'

do_request() {
  local label="$1"
  local method="$2"
  local url="$3"

  echo ""
  echo "════════════════════════════════════════════════════════"
  echo "  $label"
  echo "  $method $url"
  echo "════════════════════════════════════════════════════════"

  local start
  start=$(date +%s%N)

  local http_code
  http_code=$(curl -s -o /tmp/solune_profile_response.json \
    -w "$CURL_TIMING" \
    -X "$method" \
    -b "${COOKIE_NAME}=${SESSION_ID}" \
    -H "Content-Type: application/json" \
    "$url" 2>&1)

  local end
  end=$(date +%s%N)
  local wall_ms=$(( (end - start) / 1000000 ))

  echo "$http_code"
  echo "  Wall clock:    ${wall_ms}ms"

  # Show truncated response body (first 500 chars)
  echo ""
  echo "  Response (truncated):"
  head -c 500 /tmp/solune_profile_response.json 2>/dev/null | python3 -m json.tool 2>/dev/null | head -30 || head -c 500 /tmp/solune_profile_response.json 2>/dev/null || echo "  (empty)"
  echo ""
}

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Solune Cold-Start Project Load Profiler               ║"
echo "║   $(date -Iseconds)                     ║"
echo "╚══════════════════════════════════════════════════════════╝"

# ── Step 0: Validate session ──
echo ""
echo "─── Step 0: Validate session (GET /auth/me) ───"
do_request "Validate Session" "GET" "${BASE_URL}/auth/me"

# Check if auth succeeded
if grep -q '"error"' /tmp/solune_profile_response.json 2>/dev/null; then
  echo "ERROR: Session cookie is invalid or expired. Please log in first."
  echo "Copy the '${COOKIE_NAME}' cookie value from your browser."
  exit 1
fi

# ── Step 1: List projects ──
echo ""
echo "─── Step 1: List projects (GET /projects) ───"
do_request "List Projects" "GET" "${BASE_URL}/projects"

if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(python3 -c "
import json, sys
try:
    data = json.load(open('/tmp/solune_profile_response.json'))
    projects = data.get('projects', [])
    if projects:
        print(projects[0]['project_id'])
    else:
        print('', file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
  if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: No projects found."
    exit 1
  fi
  echo "  Auto-selected project: $PROJECT_ID"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  COLD-START SEQUENCE (project: ${PROJECT_ID})"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TOTAL_START=$(date +%s%N)

# ── Step 2: Select project (POST /projects/{id}/select) ──
do_request "Select Project" "POST" "${BASE_URL}/projects/${PROJECT_ID}/select"

# ── Step 3: Fetch board data (GET /board/projects/{id}) ──
# This is the heaviest endpoint — fetches all items, sub-issues, reconciliation
do_request "Fetch Board Data" "GET" "${BASE_URL}/board/projects/${PROJECT_ID}"

# ── Step 4: Fetch workflow agents (GET /workflow/agents) ──
do_request "Fetch Workflow Agents" "GET" "${BASE_URL}/workflow/agents"

# ── Step 5: Fetch project settings (GET /settings/project/{id}) ──
do_request "Fetch Project Settings" "GET" "${BASE_URL}/settings/project/${PROJECT_ID}"

# ── Step 6: Fetch workflow config (GET /workflow/config) ──
do_request "Fetch Workflow Config" "GET" "${BASE_URL}/workflow/config"

# ── Step 7: Fetch board projects list (GET /board/projects) ──
do_request "Fetch Board Projects List" "GET" "${BASE_URL}/board/projects"

TOTAL_END=$(date +%s%N)
TOTAL_MS=$(( (TOTAL_END - TOTAL_START) / 1000000 ))

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TOTAL COLD-START WALL TIME: ${TOTAL_MS}ms"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "NOTE: In the browser, board data + agents + settings fire"
echo "      in parallel. The serialized total above is worst-case."
echo ""
echo "Backend logs (last 60s of container output) saved to:"
echo "  /tmp/solune_backend_logs.txt"
docker logs --since 60s solune-backend > /tmp/solune_backend_logs.txt 2>&1 || true
echo "Done."
