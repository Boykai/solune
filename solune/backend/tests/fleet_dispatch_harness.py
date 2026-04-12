from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "fleet-dispatch.sh"

FAKE_GH_SCRIPT = textwrap.dedent(
    r"""#!/usr/bin/env python3
import json
import fcntl
import os
import sys
import time
from pathlib import Path

state_path = Path(os.environ["FAKE_GH_STATE"])
log_path = Path(os.environ["FAKE_GH_LOG"])
lock_path = state_path.with_suffix(".lock")
fail_agent = os.environ.get("FAKE_GH_FAIL_AGENT", "")
omit_task_agent = os.environ.get("FAKE_GH_OMIT_TASK_FOR_AGENT", "")
pending_agent = os.environ.get("FAKE_GH_PENDING_AGENT", "")
pending_views = int(os.environ.get("FAKE_GH_PENDING_VIEWS", "0"))
pending_final_state = os.environ.get("FAKE_GH_PENDING_FINAL_STATE", "COMPLETED")
dispatch_delay_agent = os.environ.get("FAKE_GH_DISPATCH_DELAY_AGENT", "")
dispatch_delay_seconds = float(os.environ.get("FAKE_GH_DISPATCH_DELAY_SECONDS", "0"))
args = sys.argv[1:]
lock_handle = lock_path.open("w", encoding="utf-8")
fcntl.flock(lock_handle, fcntl.LOCK_EX)
state = json.loads(state_path.read_text())


def save():
    state_path.write_text(json.dumps(state))


def log(message: str):
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(message + "\n")


def issue_for_number(number: int):
    if number == state["parent"]["number"]:
        return state["parent"]
    for issue in state["issues"]:
        if issue["number"] == number:
            return issue
    raise KeyError(number)


if args[:2] == ["auth", "status"]:
    sys.exit(0)
elif args[:2] == ["label", "create"]:
    sys.exit(0)
elif args[:2] == ["issue", "create"]:
    title = args[args.index("--title") + 1]
    body_file = Path(args[args.index("--body-file") + 1])
    labels = [args[i + 1] for i, value in enumerate(args) if value == "--label"]
    number = state["next_issue"]
    state["next_issue"] += 1
    issue = {
        "number": number,
        "node_id": f"ISSUE_NODE_{number}",
        "html_url": f"https://github.com/Boykai/solune/issues/{number}",
        "title": title,
        "body": body_file.read_text(),
        "labels": labels,
    }
    state["issues"].append(issue)
    save()
    log(f"issue_create:{title}")
    print(issue["html_url"])
elif args[:2] == ["issue", "edit"]:
    log(f"issue_edit:{args[2]}")
    sys.exit(0)
elif args[:2] == ["agent-task", "list"]:
    print(json.dumps(state["tasks"]))
elif args[:2] == ["agent-task", "view"]:
    task_id = args[2]
    task = next(task for task in state["tasks"] if task["id"] == task_id)
    if task.get("remaining_views", 0) > 0:
        task["remaining_views"] -= 1
    else:
        task["state"] = task.get("final_state", task["state"])
        if task["state"] == "COMPLETED":
            task["completedAt"] = task.get("completedAt") or "2026-04-12T16:00:05Z"
    save()
    log(f"task_view:{task_id}")
    print(json.dumps(task))
elif args[:2] == ["api", "graphql"]:
    stdin = sys.stdin.read()
    joined = " ".join(args)
    if "suggestedActors" in joined or "suggestedActors" in stdin:
        print(json.dumps({"data": {"repository": {"id": "REPO_NODE", "suggestedActors": {"nodes": [{"login": "copilot-swe-agent", "__typename": "Bot", "id": "BOT_NODE"}]}}}}))
    else:
        payload = json.loads(stdin or "{}")
        issue_id = payload.get("variables", {}).get("issueId")
        issue = next(item for item in state["issues"] if item["node_id"] == issue_id)
        agent = payload.get("variables", {}).get("customAgent", "")
        if fail_agent and agent == fail_agent:
            print("dispatch failed", file=sys.stderr)
            sys.exit(1)
        if omit_task_agent and agent == omit_task_agent:
            log(f"dispatch:{issue['title']}")
            print(json.dumps({"data": {"addAssigneesToAssignable": {"assignable": {"id": issue_id, "assignees": {"nodes": [{"login": "copilot-swe-agent"}]}}}}}))
            sys.exit(0)
        task_id = f"task-{state['next_task']}"
        state["next_task"] += 1
        task = {
            "id": task_id,
            "name": issue["title"],
            "state": "COMPLETED",
            "createdAt": "2026-04-12T16:00:00Z",
            "updatedAt": "2026-04-12T16:00:05Z",
            "completedAt": "2026-04-12T16:00:05Z",
            "pullRequestNumber": None,
            "pullRequestUrl": None,
        }
        if pending_agent and agent == pending_agent:
            task["state"] = "QUEUED"
            task["remaining_views"] = pending_views
            task["final_state"] = pending_final_state
        state["tasks"].append(task)
        save()
        if dispatch_delay_agent and agent == dispatch_delay_agent and dispatch_delay_seconds:
            time.sleep(dispatch_delay_seconds)
        log(f"dispatch:{issue['title']}")
        print(json.dumps({"data": {"addAssigneesToAssignable": {"assignable": {"id": issue_id, "assignees": {"nodes": [{"login": "copilot-swe-agent"}]}}}}}))
elif args[:1] == ["api"]:
    endpoint = args[1]
    if endpoint.endswith("/comments?per_page=100"):
        print(json.dumps(state["comments"]))
    elif endpoint.startswith("repos/") and "/issues?" in endpoint:
        query = endpoint.split("labels=", 1)[1]
        labels = query.replace("%3A", ":").replace("%2C", ",").split(",")
        matches = [issue for issue in state["issues"] if all(label in issue.get("labels", []) for label in labels)]
        print(json.dumps(matches))
    elif endpoint.startswith("repos/") and "/issues/" in endpoint:
        issue_number = int(endpoint.rsplit("/", 1)[1])
        print(json.dumps(issue_for_number(issue_number)))
    else:
        raise SystemExit(f"Unhandled endpoint: {endpoint}")
else:
    raise SystemExit(f"Unhandled gh call: {args}")
"""
)


def write_fake_gh(
    tmp_path: Path, *, extra_issues: list[dict] | None = None
) -> tuple[Path, Path, Path]:
    state_path = tmp_path / "state.json"
    log_path = tmp_path / "gh.log"
    log_path.touch()
    state_path.write_text(
        json.dumps(
            {
                "next_issue": 2000,
                "next_task": 1,
                "issues": extra_issues or [],
                "tasks": [],
                "parent": {
                    "number": 1555,
                    "node_id": "PARENT_NODE",
                    "html_url": "https://github.com/Boykai/solune/issues/1555",
                    "title": "Fleet Dispatch Parent",
                    "body": "Parent issue body",
                    "labels": [],
                },
                "comments": [
                    {
                        "user": {"login": "alice"},
                        "body": "Looks good",
                        "created_at": "2026-04-12T16:00:00Z",
                    }
                ],
            }
        )
    )
    gh_path = tmp_path / "gh"
    gh_path.write_text(FAKE_GH_SCRIPT)
    gh_path.chmod(0o755)
    return gh_path, state_path, log_path


def run_script(
    tmp_path: Path,
    config: dict,
    *,
    fail_agent: str | None = None,
    omit_task_for_agent: str | None = None,
    extra_issues: list[dict] | None = None,
    extra_args: list[str] | None = None,
    extra_env: dict[str, str] | None = None,
    prelock: bool = False,
) -> subprocess.CompletedProcess[str]:
    config_path = tmp_path / "fleet.json"
    config_path.write_text(json.dumps(config))
    _, state_path, log_path = write_fake_gh(tmp_path, extra_issues=extra_issues)
    state_dir = tmp_path / "dispatch-state"
    state_dir.mkdir(exist_ok=True)
    if prelock:
        (state_dir / "parent-1555.lock").write_text("123")
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "FAKE_GH_STATE": str(state_path),
        "FAKE_GH_LOG": str(log_path),
        "FLEET_DISPATCH_SKIP_AUTH": "1",
        "FLEET_DISPATCH_STATE_DIR": str(state_dir),
    }
    if fail_agent:
        env["FAKE_GH_FAIL_AGENT"] = fail_agent
    if omit_task_for_agent:
        env["FAKE_GH_OMIT_TASK_FOR_AGENT"] = omit_task_for_agent
    if extra_env:
        env.update(extra_env)
    args = [
        "bash",
        str(SCRIPT_PATH),
        "--owner",
        "Boykai",
        "--repo",
        "solune",
        "--parent-issue",
        "1555",
        "--config",
        str(config_path),
        "--base-ref",
        "copilot/test-branch",
        "--poll-interval",
        "1",
        "--task-timeout",
        "5",
    ]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(args, capture_output=True, text=True, env=env)


def read_log(tmp_path: Path) -> list[str]:
    return (tmp_path / "gh.log").read_text().splitlines()
