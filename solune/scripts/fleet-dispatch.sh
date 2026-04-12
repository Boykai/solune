#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/fleet_dispatch_common.sh"

usage() {
  cat <<USAGE
Usage: bash $SCRIPT_DIR/fleet-dispatch.sh --owner OWNER --repo REPO --parent-issue NUMBER [options]

Options:
  --config PATH             Pipeline config JSON (default: solune/scripts/pipelines/fleet-dispatch.json)
  --base-ref REF            Override base branch
  --error-strategy MODE     fail-fast or continue
  --poll-interval SECONDS   Poll interval override
  --task-timeout SECONDS    Timeout override
  --agent SLUG              Re-dispatch one named agent
  --sub-issue NUMBER        Existing sub-issue number for --retry
  --retry                   Re-dispatch the selected --agent against --sub-issue
  --no-resume               Do not reuse existing labeled sub-issues
  --help                    Show this help text
USAGE
}

OWNER=""
REPO=""
PARENT_ISSUE=""
CONFIG_PATH="$REPO_ROOT/solune/scripts/pipelines/fleet-dispatch.json"
BASE_REF=""
ERROR_STRATEGY=""
POLL_INTERVAL=""
TASK_TIMEOUT=""
AGENT_SLUG=""
SUB_ISSUE=""
RETRY_MODE=0
RESUME_EXISTING=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner)
      OWNER="$2"
      shift 2
      ;;
    --repo)
      REPO="$2"
      shift 2
      ;;
    --parent-issue)
      PARENT_ISSUE="$2"
      shift 2
      ;;
    --config)
      CONFIG_PATH="$2"
      shift 2
      ;;
    --base-ref)
      BASE_REF="$2"
      shift 2
      ;;
    --error-strategy)
      ERROR_STRATEGY="$2"
      shift 2
      ;;
    --poll-interval)
      POLL_INTERVAL="$2"
      shift 2
      ;;
    --task-timeout)
      TASK_TIMEOUT="$2"
      shift 2
      ;;
    --agent)
      AGENT_SLUG="$2"
      shift 2
      ;;
    --sub-issue)
      SUB_ISSUE="$2"
      shift 2
      ;;
    --retry)
      RETRY_MODE=1
      shift
      ;;
    --no-resume)
      RESUME_EXISTING=0
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fd_die "Unknown argument: $1"
      ;;
  esac
done

[[ -n "$OWNER" ]] || fd_die '--owner is required'
[[ -n "$REPO" ]] || fd_die '--repo is required'
[[ -n "$PARENT_ISSUE" ]] || fd_die '--parent-issue is required'
if (( RETRY_MODE )); then
  [[ -n "$AGENT_SLUG" ]] || fd_die '--agent is required with --retry'
  [[ -n "$SUB_ISSUE" ]] || fd_die '--sub-issue is required with --retry'
fi

fd_require_cmd gh
fd_require_cmd jq
[[ -f "$CONFIG_PATH" ]] || fd_die "Config not found: $CONFIG_PATH"
fd_validate_pipeline_config "$CONFIG_PATH"

if [[ "${FLEET_DISPATCH_SKIP_AUTH:-0}" != '1' ]]; then
  gh auth status >/dev/null
fi

if [[ -z "$BASE_REF" ]]; then
  BASE_REF="$(jq -r '.defaults.baseRef' "$CONFIG_PATH")"
fi
if [[ -z "$ERROR_STRATEGY" ]]; then
  ERROR_STRATEGY="$(jq -r '.defaults.errorStrategy' "$CONFIG_PATH")"
fi
if [[ -z "$POLL_INTERVAL" ]]; then
  POLL_INTERVAL="$(jq -r '.defaults.pollIntervalSeconds' "$CONFIG_PATH")"
fi
if [[ -z "$TASK_TIMEOUT" ]]; then
  TASK_TIMEOUT="$(jq -r '.defaults.taskTimeoutSeconds' "$CONFIG_PATH")"
fi

STATE_DIR="${FLEET_DISPATCH_STATE_DIR:-$REPO_ROOT/.git/fleet-dispatch}"
mkdir -p "$STATE_DIR"
DISPATCH_ID="${PARENT_ISSUE}-$(date -u +%Y%m%d%H%M%S)"
STATE_FILE="$STATE_DIR/${DISPATCH_ID}.json"
LOCK_FILE="$STATE_DIR/parent-${PARENT_ISSUE}.lock"

if (( ! RETRY_MODE )); then
  if [[ -f "$LOCK_FILE" ]]; then
    fd_die "Parent issue #$PARENT_ISSUE is already locked by another fleet dispatch"
  fi
  printf '%s\n' "$$" > "$LOCK_FILE"
  trap 'rm -f "$LOCK_FILE"' EXIT
fi

PARENT_ISSUE_JSON="$(fd_load_issue "$OWNER" "$REPO" "$PARENT_ISSUE")"
PARENT_COMMENTS_JSON="$(fd_load_issue_comments "$OWNER" "$REPO" "$PARENT_ISSUE")"
PARENT_TITLE="$(jq -r '.title' <<<"$PARENT_ISSUE_JSON")"
PARENT_BODY="$(jq -r '.body // ""' <<<"$PARENT_ISSUE_JSON")"
PARENT_URL="$(jq -r '.html_url' <<<"$PARENT_ISSUE_JSON")"
COMMENTS_MARKDOWN="$(fd_read_comments_markdown "$PARENT_COMMENTS_JSON")"
COPILOT_INFO="$(fd_get_copilot_and_repo_ids "$OWNER" "$REPO")"
COPILOT_ID="$(jq -r '.copilotId' <<<"$COPILOT_INFO")"
REPO_ID="$(jq -r '.repoId' <<<"$COPILOT_INFO")"
[[ -n "$COPILOT_ID" && "$COPILOT_ID" != 'null' ]] || fd_die 'Unable to resolve Copilot bot id for repository'
[[ -n "$REPO_ID" && "$REPO_ID" != 'null' ]] || fd_die 'Unable to resolve repository node id'

jq -n \
  --arg dispatchId "$DISPATCH_ID" \
  --argjson parentIssueNumber "$PARENT_ISSUE" \
  --arg startedAt "$(fd_timestamp)" \
  '{dispatchId: $dispatchId, parentIssueNumber: $parentIssueNumber, startedAt: $startedAt, records: []}' > "$STATE_FILE"

state_upsert_record() {
  local record_json="$1"
  local tmp_file
  tmp_file="$(mktemp)"
  jq \
    --argjson record "$record_json" '
      .records |= (
        if any(.[]; .agentSlug == $record.agentSlug and .attempt == $record.attempt) then
          map(if .agentSlug == $record.agentSlug and .attempt == $record.attempt then $record else . end)
        else
          . + [$record]
        end
      )
    ' "$STATE_FILE" > "$tmp_file"
  mv "$tmp_file" "$STATE_FILE"
}

build_record() {
  local group_id="$1"
  local agent_slug="$2"
  local sub_issue_number="$3"
  local status="$4"
  local attempt="$5"
  local task_id="${6:-}"
  local started_at="${7:-$(fd_timestamp)}"
  local completed_at="${8:-}"
  local error_message="${9:-}"
  jq -n \
    --arg dispatchId "$DISPATCH_ID" \
    --arg groupId "$group_id" \
    --arg agentSlug "$agent_slug" \
    --argjson subIssueNumber "$sub_issue_number" \
    --arg status "$status" \
    --argjson attempt "$attempt" \
    --arg taskId "$task_id" \
    --arg startedAt "$started_at" \
    --arg completedAt "$completed_at" \
    --arg errorMessage "$error_message" '
      {
        dispatchId: $dispatchId,
        groupId: $groupId,
        agentSlug: $agentSlug,
        subIssueNumber: $subIssueNumber,
        status: $status,
        attempt: $attempt,
        taskId: (if ($taskId | length) > 0 then $taskId else null end),
        startedAt: (if ($startedAt | length) > 0 then $startedAt else null end),
        completedAt: (if ($completedAt | length) > 0 then $completedAt else null end),
        errorMessage: (if ($errorMessage | length) > 0 then $errorMessage else null end)
      }
    '
}

monitor_record() {
  local record_json="$1"
  local task_id status started_at started_epoch task_json completed_at error_message
  task_id="$(jq -r '.taskId // empty' <<<"$record_json")"
  if [[ -z "$task_id" ]]; then
    printf '%s\n' "$record_json"
    return 0
  fi
  started_at="$(jq -r '.startedAt // empty' <<<"$record_json")"
  started_epoch="$(date -u +%s)"
  if task_json="$(fd_monitor_task "$OWNER" "$REPO" "$task_id" "$POLL_INTERVAL" "$TASK_TIMEOUT" "$started_epoch")"; then
    status="$(jq -r '.normalizedState // "completed"' <<<"$task_json")"
    completed_at="$(jq -r '.completedAt // empty' <<<"$task_json")"
    build_record \
      "$(jq -r '.groupId' <<<"$record_json")" \
      "$(jq -r '.agentSlug' <<<"$record_json")" \
      "$(jq -r '.subIssueNumber' <<<"$record_json")" \
      "$status" \
      "$(jq -r '.attempt' <<<"$record_json")" \
      "$task_id" \
      "$started_at" \
      "${completed_at:-$(fd_timestamp)}"
  else
    status="$(jq -r '.normalizedState // "failed"' <<<"$task_json")"
    completed_at="$(jq -r '.completedAt // empty' <<<"$task_json")"
    error_message="Agent task ${task_id} ended in state ${status}"
    build_record \
      "$(jq -r '.groupId' <<<"$record_json")" \
      "$(jq -r '.agentSlug' <<<"$record_json")" \
      "$(jq -r '.subIssueNumber' <<<"$record_json")" \
      "$status" \
      "$(jq -r '.attempt' <<<"$record_json")" \
      "$task_id" \
      "$started_at" \
      "${completed_at:-$(fd_timestamp)}" \
      "$error_message"
    return 1
  fi
}

create_or_resume_sub_issue() {
  local agent_json="$1"
  local slug title_template display_name title parent_label agent_label pipeline_label existing issue_json body_file body_text
  slug="$(jq -r '.slug' <<<"$agent_json")"
  display_name="$(jq -r '.displayName // .slug' <<<"$agent_json")"
  title_template="$(jq -r '.subIssue.title' <<<"$agent_json")"
  title="$(fd_render_string_template "$title_template" "$PARENT_ISSUE" "$PARENT_TITLE" "$display_name" "$slug" "$BASE_REF")"
  parent_label="$(fd_parent_label "$PARENT_ISSUE")"
  agent_label="$(fd_agent_label "$slug")"
  pipeline_label="$(fd_pipeline_label)"
  if (( RESUME_EXISTING )); then
    existing="$(fd_find_existing_sub_issue "$OWNER" "$REPO" "$pipeline_label" "$parent_label" "$agent_label")"
    if [[ -n "$existing" && "$existing" != 'null' ]]; then
      printf '%s\n' "$existing"
      return 0
    fi
  fi
  body_text="$(fd_tailor_body_for_agent "$PARENT_BODY" "$slug" "$PARENT_ISSUE" "$PARENT_TITLE")"
  body_file="$(mktemp)"
  trap 'rm -f "$body_file"' RETURN
  printf '%s\n' "$body_text" > "$body_file"
  mapfile -t raw_labels < <(jq -r '.subIssue.labels[]' <<<"$agent_json")
  issue_json="$(fd_create_sub_issue "$OWNER" "$REPO" "$title" "$body_file" "$pipeline_label" "$parent_label" "$agent_label" "${raw_labels[@]}")"
  printf '%s\n' "$issue_json"
}

dispatch_one_agent() {
  local agent_json="$1"
  local attempt="${2:-1}"
  local slug custom_agent model template_path instructions sub_issue_json sub_issue_number issue_node_id issue_title task_json task_id dispatch_started_at
  slug="$(jq -r '.slug' <<<"$agent_json")"
  custom_agent="$(jq -r '.customAgent // ""' <<<"$agent_json")"
  model="$(jq -r '.model' <<<"$agent_json")"
  template_path="$(fd_template_path "$REPO_ROOT" "$(jq -r '.instructionTemplate' <<<"$agent_json")")"
  dispatch_started_at="$(fd_timestamp)"

  if (( RETRY_MODE )); then
    sub_issue_json="$(fd_load_issue "$OWNER" "$REPO" "$SUB_ISSUE")"
    fd_unassign_copilot "$OWNER" "$REPO" "$SUB_ISSUE"
  else
    sub_issue_json="$(create_or_resume_sub_issue "$agent_json")"
  fi

  sub_issue_number="$(jq -r '.number' <<<"$sub_issue_json")"
  issue_node_id="$(jq -r '.node_id' <<<"$sub_issue_json")"
  issue_title="$(jq -r '.title' <<<"$sub_issue_json")"
  instructions="$(fd_render_template "$template_path" "$PARENT_TITLE" "$PARENT_BODY" "$COMMENTS_MARKDOWN" "$PARENT_ISSUE" "$PARENT_URL" "$BASE_REF" "$BASE_REF")"

  if ! fd_dispatch_graphql "$issue_node_id" "$COPILOT_ID" "$REPO_ID" "$BASE_REF" "$custom_agent" "$instructions" "$model" >/dev/null; then
    build_record "$(jq -r '.groupId' <<<"$agent_json")" "$slug" "$sub_issue_number" 'failed' "$attempt" '' "$dispatch_started_at" "$(fd_timestamp)" "GraphQL assignment failed"
    return 1
  fi

  task_json="$(fd_resolve_task_for_agent "$OWNER" "$REPO" "$slug" "$issue_title")"
  task_id="$(gh agent-task list --repo "$OWNER/$REPO" --limit 100 --json id,createdAt | jq -r 'sort_by(.createdAt // "") | last.id // empty')"
  build_record "$(jq -r '.groupId' <<<"$agent_json")" "$slug" "$sub_issue_number" 'queued' "$attempt" "$task_id" "$dispatch_started_at"
}

run_parallel_group() {
  local group_json="$1"
  local temp_dir pid_files=() idx=0 agent_json output_file monitored failed=0 dispatch_failed=0
  temp_dir="$(mktemp -d)"
  trap 'rm -rf "$temp_dir"' RETURN
  while IFS= read -r agent_json; do
    output_file="$temp_dir/$idx.json"
    (
      dispatch_one_agent "$(jq -c '. + {groupId: $groupId}' --arg groupId "$(jq -r '.id' <<<"$group_json")" <<<"$agent_json")" > "$output_file"
    ) &
    pid_files+=("$!:$output_file")
    idx=$((idx + 1))
  done < <(jq -c '.agents[]' <<<"$group_json")

  local pair pid file record
  for pair in "${pid_files[@]}"; do
    pid="${pair%%:*}"
    file="${pair#*:}"
    wait "$pid" || dispatch_failed=1
    record="$(cat "$file")"
    state_upsert_record "$record"
  done

  for pair in "${pid_files[@]}"; do
    file="${pair#*:}"
    monitored="$(monitor_record "$(cat "$file")")" || failed=1
    state_upsert_record "$monitored"
  done

  [[ $dispatch_failed -eq 0 && $failed -eq 0 ]]
}

run_serial_group() {
  local group_json="$1"
  local failed=0 agent_json record monitored
  while IFS= read -r agent_json; do
    record="$(dispatch_one_agent "$(jq -c '. + {groupId: $groupId}' --arg groupId "$(jq -r '.id' <<<"$group_json")" <<<"$agent_json")")" || failed=1
    state_upsert_record "$record"
    monitored="$(monitor_record "$record")" || failed=1
    state_upsert_record "$monitored"
    if [[ $failed -ne 0 && "$ERROR_STRATEGY" == 'fail-fast' ]]; then
      return 1
    fi
  done < <(jq -c '.agents[]' <<<"$group_json")
  [[ $failed -eq 0 ]]
}

summarize_state() {
  jq -r '
    ["Status summary:" ]
    + ( .records
        | group_by(.status)
        | map("- \(.[0].status): \(length)")
      )
    + ["", "Records:"]
    + (.records | map("- \(.agentSlug) → #\(.subIssueNumber) [\(.status)]"))
    | join("\n")
  ' "$STATE_FILE"
}

overall_status='completed'
if (( RETRY_MODE )); then
  agent_json="$(fd_find_agent_in_config "$CONFIG_PATH" "$AGENT_SLUG")"
  [[ -n "$agent_json" ]] || fd_die "Agent not found in config: $AGENT_SLUG"
  record="$(dispatch_one_agent "$agent_json" 2)" || overall_status='failed'
  state_upsert_record "$record"
  monitored="$(monitor_record "$record")" || overall_status='failed'
  state_upsert_record "$monitored"
else
  while IFS= read -r group_json; do
    mode="$(jq -r '.executionMode' <<<"$group_json")"
    if [[ "$mode" == 'parallel' ]]; then
      run_parallel_group "$group_json" || overall_status='failed'
    else
      run_serial_group "$group_json" || overall_status='failed'
    fi
    if [[ "$overall_status" == 'failed' && "$ERROR_STRATEGY" == 'fail-fast' ]]; then
      break
    fi
  done < <(fd_group_ordered_json "$CONFIG_PATH")
fi

echo "Dispatch state written to: $STATE_FILE"
summarize_state
[[ "$overall_status" == 'completed' ]]
