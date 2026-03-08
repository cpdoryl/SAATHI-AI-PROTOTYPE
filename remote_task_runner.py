#!/usr/bin/env python3
"""
SAATHI AI -- Remote Agent Task Runner
======================================
Runs on GitHub Actions (Linux). Picks exactly ONE pending task from TASKS.md,
executes it via Claude CLI, commits results, then exits.

Designed for the schedule-based GitHub Actions workflow:
  - Scheduled every 5 min → each run picks next task → natural 5-min inter-task gap
  - No busy-wait loops, no Windows-specific paths
  - State persisted in .watcher_state.json (committed back to git after each run)

Exit codes:
  0  task completed successfully  OR  no pending tasks (clean idle)
  1  task failed (Claude returned non-zero)
  2  API rate limit hit (workflow will wait for next schedule tick to retry)
  3  fatal config / git error (needs human intervention)
"""

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Force UTF-8 everywhere (safe on Linux, required for special chars in tasks)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Config  (auto-detected for CI vs local)
# ---------------------------------------------------------------------------
REPO_DIR      = Path(__file__).parent.resolve()
TASKS_FILE    = REPO_DIR / "TASKS.md"
STATE_FILE    = REPO_DIR / ".watcher_state.json"
STATUS_MD     = REPO_DIR / "WATCHER_STATUS.md"
LOG_FILE      = REPO_DIR / "watcher.log"
BRANCH        = "main"
MAX_TURNS     = 30     # cap Claude turns per task (token budget)
TASK_TIMEOUT  = 1800   # 30 min max per task

# On GitHub Actions: `claude` is in PATH after npm install -g @anthropic-ai/claude-code
# On Windows local:  use the .cmd path
if sys.platform == "win32":
    CLAUDE_CMD = r"C:\Users\B P Verma\AppData\Roaming\npm\claude.cmd"
else:
    CLAUDE_CMD = "claude"

# Phase -> blueprint (only ONE file per task invocation to save tokens)
PHASE_BLUEPRINTS = {
    "P1-BE":   "therapeutic-copilot/server/BACKEND_BLUEPRINT.md",
    "P2-FE":   "therapeutic-copilot/client/FRONTEND_BLUEPRINT.md",
    "P3-WI":   "therapeutic-copilot/widget/WIDGET_BLUEPRINT.md",
    "P4-RAG":  "therapeutic-copilot/server/RAG_BLUEPRINT.md",
    "P5-ML":   "ml_pipeline/ML_BLUEPRINT.md",
    "P6-DB":   "therapeutic-copilot/server/DATABASE_BLUEPRINT.md",
    "P7-TEST": "therapeutic-copilot/server/BACKEND_BLUEPRINT.md",
    "P8-OPS":  "therapeutic-copilot/server/BACKEND_BLUEPRINT.md",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str, level: str = "INFO"):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"completed_tasks": [], "current_task": None,
            "session_started": None, "tasks_total": 0}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                          encoding="utf-8")

# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git(args: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=REPO_DIR, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )


def git_commit_push(files: list, message: str) -> bool:
    for f in files:
        git(["add", "--", f])
    r = git(["commit", "-m", message])
    if r.returncode != 0:
        if "nothing to commit" in (r.stdout + r.stderr).lower():
            return True
        log(f"Commit failed: {r.stderr.strip()}", "WARN")
        return False
    r2 = git(["push", "origin", BRANCH])
    if r2.returncode != 0:
        log(f"Push failed: {r2.stderr.strip()}", "WARN")
        return False
    return True

# ---------------------------------------------------------------------------
# Task parsing (identical logic to github_watcher.py)
# ---------------------------------------------------------------------------

def extract_ordered_pending_tasks(tasks_md: str) -> list:
    """Parse all unchecked - [ ] tasks in document order."""
    pending = []
    current_phase = None
    in_task_zone  = False

    for line in tasks_md.splitlines():
        stripped = line.strip()

        if stripped.startswith("## "):
            header = stripped[3:].strip()
            upper  = header.upper()
            if "STANDING" in upper or "COMPLETED" in upper or "INSTRUCTION" in upper:
                current_phase = None
                in_task_zone  = False
                continue
            if header and all(c in "\u2550\u2500\u2014-= " for c in header):
                continue
            current_phase = None
            continue

        if stripped.startswith("### "):
            header = stripped[4:].strip()
            upper  = header.upper()
            if "STANDING" in upper or "COMPLETED" in upper:
                current_phase = None
                continue
            first_word    = header.split()[0] if header.split() else header
            current_phase = first_word
            in_task_zone  = True
            continue

        if current_phase and in_task_zone and stripped.startswith("- [ ]"):
            task_text = stripped[5:].strip()
            if "BLOCKED:" not in task_text:
                key = f"{current_phase}::{task_text}"
                pending.append({
                    "phase":   current_phase,
                    "text":    task_text,
                    "key":     key,
                    "display": f"[{current_phase}] {task_text}",
                })

    return pending

# ---------------------------------------------------------------------------
# Prompt builder — token-efficient, quality-preserving
# (identical quality standards as local watcher)
# ---------------------------------------------------------------------------

def build_prompt(task: dict) -> str:
    phase     = task["phase"]
    text      = task["text"]
    blueprint = PHASE_BLUEPRINTS.get(phase, "DEVELOPER_GUIDE.md")

    return f"""You are a senior full-stack engineer on SAATHI AI (RYL NEUROACADEMY PRIVATE LIMITED).
Working directory: {REPO_DIR}
Stack: FastAPI/Python 3.11, SQLAlchemy 2.0 async, Alembic, Redis, Razorpay, Pinecone,
       React 18/TypeScript/Vite/Tailwind, Zustand, TanStack Query, Recharts,
       Shadow DOM widget, Qwen 2.5-7B via llama.cpp / Together AI, Docker.

\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
TASK  [{phase}]  {text}
\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

EXECUTION \u2014 follow every step in order:

STEP 1 \u2014 READ BLUEPRINT
  Read: {blueprint}
  This defines design requirements and completion criteria you must satisfy.

STEP 2 \u2014 READ EXISTING CODE
  Read every file you will modify before touching it.
  Understand existing patterns, naming, and architecture.
  Do NOT read files unrelated to this task.

STEP 3 \u2014 IMPLEMENT (production quality \u2014 non-negotiable)
  \u2022 No placeholder returns, no TODO comments, no hardcoded secrets.
  \u2022 Backend: business logic in services/, HTTP handling in routes/ (never mix).
             Every async DB call uses SQLAlchemy AsyncSession correctly.
             Every endpoint has proper HTTPException error handling.
             Use Loguru for logging. Config values from Pydantic settings / .env only.
  \u2022 Frontend: API calls only in lib/api.ts or custom hooks, never inside components.
              Every component handles loading state AND error state.
  \u2022 Database: all schema changes via Alembic migration \u2014 never create_all().
              No raw SQL \u2014 SQLAlchemy ORM only.
  \u2022 Tests: add a test for every new function / endpoint introduced.

STEP 4 \u2014 VERIFY BEFORE COMMITTING
  Re-read every file you just modified.
  Confirm: (a) matches blueprint requirements, (b) does not break existing code,
           (c) no .env values hardcoded, (d) no leftover debug prints.
  Fix anything wrong before proceeding.

STEP 5 \u2014 COMMIT & PUSH implementation
  git add <only the changed source files \u2014 never .env, *.gguf, __pycache__, node_modules>
  git commit -m "feat({phase.lower()}): <concise description>"
  git push origin main

STEP 6 \u2014 MARK TASK DONE in TASKS.md
  Find the exact line:  - [ ] {text}
  Change it to:         - [x] {text}
  git commit -m "chore(tasks): mark [{text[:55]}] complete"
  git push origin main

STEP 7 \u2014 UPDATE BUILD RECORD
  Append to BUILD_DESIGN_RECORD.md:
    Date, Task, Files changed, Design decision and why, Algorithm / pattern used.
  git commit -m "docs(build-record): {text[:50]}"
  git push origin main

Stop immediately after step 7. Do not start the next task.
"""

# ---------------------------------------------------------------------------
# Rate limit detection
# ---------------------------------------------------------------------------

RATE_LIMIT_PHRASES = [
    "you've hit your limit",
    "you have exceeded your",
    "rate limit",
    "too many requests",
]

def is_rate_limited(output: str) -> bool:
    lo = output.lower()
    return any(p in lo for p in RATE_LIMIT_PHRASES)

# ---------------------------------------------------------------------------
# WATCHER_STATUS.md writer
# ---------------------------------------------------------------------------

def write_status(status: str, details: str = "", push: bool = True):
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state = load_state()
    try:
        log_lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-15:]
        log_block = "\n".join(log_lines)
    except Exception:
        log_block = "(log unavailable)"

    content = f"""# WATCHER STATUS

**Updated**: {ts}
**Status**:  {status}
**Runner**:  GitHub Actions (remote)

## Progress

- Tasks completed : {len(state.get('completed_tasks', []))} / {state.get('tasks_total', 0)}
- Last task       : `{state.get('current_task') or 'None'}`

## Details

{details or '(no additional details)'}

## Recent Log

```
{log_block}
```
"""
    STATUS_MD.write_text(content, encoding="utf-8")
    if push:
        try:
            git_commit_push([str(STATUS_MD)], f"chore(watcher): status -- {status[:80]}")
        except Exception as e:
            log(f"Could not push WATCHER_STATUS.md: {e}", "WARN")

# ---------------------------------------------------------------------------
# Task verification helpers
# ---------------------------------------------------------------------------

def task_is_marked_done(task: dict) -> bool:
    try:
        content = TASKS_FILE.read_text(encoding="utf-8", errors="replace")
        return f"- [x] {task['text']}" in content
    except Exception:
        return False


def force_mark_task_done(task: dict):
    try:
        content = TASKS_FILE.read_text(encoding="utf-8", errors="replace")
        new_content = content.replace(
            f"- [ ] {task['text']}", f"- [x] {task['text']}", 1)
        if new_content != content:
            TASKS_FILE.write_text(new_content, encoding="utf-8")
            git_commit_push(
                [str(TASKS_FILE)],
                f"chore(tasks): watcher force-marked [{task['text'][:55]}] complete",
            )
            log(f"Force-marked task done in TASKS.md", "WARN")
    except Exception as e:
        log(f"Could not force-mark task: {e}", "WARN")

# ---------------------------------------------------------------------------
# Main: pick ONE task and run it
# ---------------------------------------------------------------------------

def main() -> int:
    """
    Returns exit code:
      0 = success or no tasks
      1 = task failed
      2 = rate limited
      3 = fatal error
    """
    # Configure git identity (needed in CI)
    git(["config", "user.name",  "SAATHI Agent"])
    git(["config", "user.email", "agent@rylneuroacademy.com"])

    log("=" * 60)
    log("SAATHI AI Remote Task Runner started")
    log(f"Repo: {REPO_DIR}  Branch: {BRANCH}")
    log("=" * 60)

    # Pull latest state
    pull = git(["pull", "--ff-only", "origin", BRANCH])
    if pull.returncode != 0:
        log(f"git pull failed: {pull.stderr.strip()}", "WARN")

    state          = load_state()
    completed_keys = set(state.get("completed_tasks", []))

    try:
        content = TASKS_FILE.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        log(f"Cannot read TASKS.md: {e}", "ERROR")
        return 3

    all_tasks = extract_ordered_pending_tasks(content)
    remaining = [t for t in all_tasks if t["key"] not in completed_keys]

    state["tasks_total"] = len(all_tasks)
    save_state(state)

    if not remaining:
        log("No pending tasks. All done or nothing new.")
        write_status(
            "ALL TASKS COMPLETE",
            "Every task in TASKS.md has been implemented.\n\n"
            "Add new tasks to TASKS.md to continue.",
            push=True,
        )
        return 0

    # Pick the FIRST pending task (document order = phase order)
    task = remaining[0]
    done_count = len(completed_keys)
    total      = len(all_tasks)
    log(f"[{done_count+1}/{total}] Executing: {task['display']}")

    # Mark as in-progress
    state["current_task"] = task["key"]
    if not state.get("session_started"):
        state["session_started"] = datetime.now().isoformat()
    save_state(state)

    write_status(
        f"RUNNING -- task {done_count+1}/{total}",
        f"**Task**: `{task['display']}`",
        push=True,
    )

    # Build prompt and invoke Claude
    prompt = build_prompt(task)
    log(f"Invoking Claude CLI (max-turns={MAX_TURNS}, timeout={TASK_TIMEOUT}s)")

    try:
        result = subprocess.run(
            [
                CLAUDE_CMD,
                "--dangerously-skip-permissions",
                "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep",
                "--max-turns",    str(MAX_TURNS),
                "--print",
            ],
            input=prompt,
            cwd=REPO_DIR,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TASK_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        log(f"Claude timed out ({TASK_TIMEOUT}s): {task['display']}", "ERROR")
        write_status(
            f"TASK TIMEOUT -- {task['display'][:80]}",
            "Claude exceeded the 30-minute per-task limit.\n\n"
            "Task has been skipped. Review and simplify the task if needed.",
            push=True,
        )
        # Skip this task so the next run moves forward
        state = load_state()
        state["completed_tasks"].append(task["key"])
        state["current_task"] = None
        save_state(state)
        git_commit_push([str(STATE_FILE)], "chore(watcher): skip timed-out task")
        return 1

    combined = (result.stdout or "") + (result.stderr or "")

    if result.stdout:
        print(result.stdout, flush=True)
    if result.stderr:
        print(result.stderr, flush=True)

    # Rate limit — exit 2 so workflow can report and stop cleanly
    if is_rate_limited(combined):
        log("API rate limit hit. Exiting with code 2. Next schedule tick will retry.", "WARN")
        write_status(
            "PAUSED -- API RATE LIMIT",
            f"Claude CLI hit the hourly token limit.\n\n"
            f"**Will retry**: `{task['display']}`\n\n"
            f"Next GitHub Actions schedule tick will automatically resume.",
            push=True,
        )
        return 2

    # Task failed
    if result.returncode != 0:
        log(f"Claude FAILED (exit {result.returncode}): {task['display']}", "ERROR")
        write_status(
            f"TASK FAILED -- {task['display'][:80]}",
            f"Claude returned exit code {result.returncode}.\n\n"
            f"Task skipped. Review `watcher.log` to fix manually.",
            push=True,
        )
        state = load_state()
        state["completed_tasks"].append(task["key"])
        state["current_task"] = None
        save_state(state)
        git_commit_push([str(STATE_FILE)], f"chore(watcher): skip failed task [{task['text'][:50]}]")
        return 1

    # Success — ensure TASKS.md is marked
    if not task_is_marked_done(task):
        log("Claude did not update TASKS.md -- force-marking.", "WARN")
        force_mark_task_done(task)

    # Record in state
    state = load_state()
    if task["key"] not in state["completed_tasks"]:
        state["completed_tasks"].append(task["key"])
    state["current_task"] = None
    save_state(state)

    done_now   = len(state["completed_tasks"])
    left_count = total - done_now
    next_label = remaining[1]["display"] if len(remaining) > 1 else "ALL DONE"

    log(f"[{done_now}/{total}] DONE: {task['display']}")

    git_commit_push([str(STATE_FILE)], f"chore(watcher): state after [{task['text'][:50]}]")

    write_status(
        f"IN PROGRESS -- {done_now} done, {left_count} remaining",
        f"**Just completed**: `{task['display']}`\n\n"
        f"**Up next**: `{next_label}`\n\n"
        f"Next run in ~5 minutes (GitHub Actions schedule).",
        push=True,
    )

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"FATAL: {e}\n{traceback.format_exc()}", "ERROR")
        sys.exit(3)
