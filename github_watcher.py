#!/usr/bin/env python3
"""
SAATHI AI -- GitHub Command Board Watcher v3
============================================
Token-efficient, ordered, resumable, autonomous coding loop.

Features:
  - ONE TASK AT A TIME: scan -> execute -> commit -> next (no bulk loading)
  - Token-efficient prompts: minimal system prompt + phase-targeted blueprint
  - Per-task max-turns cap (--max-turns) to bound token spend per invocation
  - Inter-task cooldown to let the hourly token bucket partially refill
  - Rate-limit detection: auto-sleep until reset, then resume
  - Resumes from last stopped point after laptop shutdown or crash
  - Status reports to GitHub (WATCHER_STATUS.md) after every task

Usage:
    python github_watcher.py

Or double-click:
    start_watcher.bat
"""

import atexit
import hashlib
import io
import json
import os
import re
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Force UTF-8 output on Windows -- prevents UnicodeEncodeError for → ₹ etc.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REPO_DIR      = Path(r"c:\saath ai prototype")
TASKS_FILE    = REPO_DIR / "TASKS.md"
LOG_FILE      = REPO_DIR / "watcher.log"
STATE_FILE    = REPO_DIR / ".watcher_state.json"
STATUS_MD     = REPO_DIR / "WATCHER_STATUS.md"
LOCK_FILE     = REPO_DIR / ".watcher.lock"
POLL_INTERVAL      = 300   # seconds between polls for new tasks
INTER_TASK_DELAY   = 60    # seconds to wait between tasks (lets hourly token bucket refill)
MAX_TURNS_PER_TASK = 30    # cap Claude conversation turns per task (saves tokens)
BRANCH        = "main"
CLAUDE_CMD    = r"C:\Users\B P Verma\AppData\Roaming\npm\claude.cmd"

# ---------------------------------------------------------------------------
# Phase -> blueprint mapping  (only load the ONE relevant blueprint per task)
# ---------------------------------------------------------------------------
PHASE_BLUEPRINTS = {
    "P1-BE":  "therapeutic-copilot/server/BACKEND_BLUEPRINT.md",
    "P2-FE":  "therapeutic-copilot/client/FRONTEND_BLUEPRINT.md",
    "P3-WI":  "therapeutic-copilot/widget/WIDGET_BLUEPRINT.md",
    "P4-RAG": "therapeutic-copilot/server/RAG_BLUEPRINT.md",
    "P5-ML":  "ml_pipeline/ML_BLUEPRINT.md",
    "P6-DB":  "therapeutic-copilot/server/DATABASE_BLUEPRINT.md",
    "P7-TEST":"therapeutic-copilot/server/BACKEND_BLUEPRINT.md",  # tests live near backend
    "P8-OPS": "therapeutic-copilot/server/BACKEND_BLUEPRINT.md",  # ops/infra
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git(args: list, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=REPO_DIR,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def fetch_remote_tasks() -> tuple:
    """Fetch origin without touching local files. Returns (md5_hash, content)."""
    git(["fetch", "origin", BRANCH])
    result = git(["show", f"origin/{BRANCH}:TASKS.md"])
    content = result.stdout if result.returncode == 0 else ""
    return hashlib.md5(content.encode()).hexdigest(), content


def pull_latest():
    result = git(["pull", "--ff-only", "origin", BRANCH])
    if result.returncode != 0:
        log(f"Pull failed: {result.stderr.strip()}", "WARN")


def commit_and_push(files: list, message: str) -> bool:
    """Stage specified files, commit, push. Returns True on success."""
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
# State persistence  (.watcher_state.json)
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "completed_tasks": [],   # list of task keys already done
        "current_task":    None, # key of task being worked on right now
        "session_started": None,
        "tasks_total":     0,
    }


def save_state(state: dict):
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

# ---------------------------------------------------------------------------
# Task parsing -- ordered, all phases
# ---------------------------------------------------------------------------

def extract_ordered_pending_tasks(tasks_md: str) -> list:
    """
    Parse all unchecked - [ ] tasks in document order.

    TASKS.md structure:
      ## STANDING INSTRUCTIONS ...  <- stop here
      ## ══════...                  <- decorative separator, skip
      ## PHASE N — ...              <- phase title, skip (not a task section)
      ### P1-BE — Backend ...       <- REAL task section header (### level)
      - [ ] task text               <- pending task
      - [x] task text               <- done, skip

    Stops when it hits ## STANDING INSTRUCTIONS or ## COMPLETED LOG.
    Returns list of dicts: {phase, text, key, display}
    """
    pending = []
    current_phase = None
    in_task_zone = False   # False until we pass STANDING INSTRUCTIONS block

    for line in tasks_md.splitlines():
        stripped = line.strip()

        # -- ## level headers --------------------------------------------------
        if stripped.startswith("## "):
            header = stripped[3:].strip()
            upper = header.upper()

            # Stop parsing tasks in admin/meta sections
            if "STANDING" in upper or "COMPLETED" in upper or "INSTRUCTION" in upper:
                current_phase = None
                in_task_zone = False
                continue

            # Skip decorative separator lines (all box-drawing chars)
            if header and all(c in "\u2550\u2500\u2014-= " for c in header):
                continue

            # Skip "HOW TO WRITE", "RYL NEUROACADEMY", blueprint refs, etc.
            # These are not task sections
            current_phase = None   # ## level resets phase; ### level sets it
            continue

        # -- ### level headers (real task sections) ----------------------------
        if stripped.startswith("### "):
            header = stripped[4:].strip()
            upper = header.upper()
            if "STANDING" in upper or "COMPLETED" in upper:
                current_phase = None
                continue
            # Extract phase label: first token before " -- " or " -"
            first_word = header.split()[0] if header.split() else header
            current_phase = first_word   # e.g. "P1-BE", "P2-FE", "P3-WI"
            in_task_zone = True
            continue

        # -- Task lines --------------------------------------------------------
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
# WATCHER_STATUS.md  (GitHub status dashboard)
# ---------------------------------------------------------------------------

def write_status(status: str, details: str = "", push: bool = True):
    """Write WATCHER_STATUS.md and optionally commit+push to GitHub."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state = load_state()
    completed = len(state.get("completed_tasks", []))
    total     = state.get("tasks_total", 0)
    current   = state.get("current_task") or "None"

    # Last 20 log lines
    try:
        log_lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
        log_block = "\n".join(log_lines)
    except Exception:
        log_block = "(log unavailable)"

    content = f"""# WATCHER STATUS

**Updated**: {ts}
**Status**:  {status}

## Progress

- Tasks completed : {completed} / {total}
- Last task       : `{current}`

## Details

{details or "(no additional details)"}

## Recent Log

```
{log_block}
```
"""
    STATUS_MD.write_text(content, encoding="utf-8")

    if push:
        try:
            commit_and_push(
                [str(STATUS_MD)],
                f"chore(watcher): status -- {status[:80]}",
            )
        except Exception as e:
            log(f"Could not push WATCHER_STATUS.md: {e}", "WARN")

# ---------------------------------------------------------------------------
# Shutdown / crash handlers
# ---------------------------------------------------------------------------

# Possible values: "RUNNING", "STOPPED_BY_USER", "CRASH", "DONE"
_shutdown_reason = "RUNNING"


def _atexit_handler():
    """Called by Python atexit on any normal process exit."""
    global _shutdown_reason
    if _shutdown_reason == "DONE":
        return   # already reported normally
    if _shutdown_reason == "STOPPED_BY_USER":
        write_status(
            "STOPPED BY USER (Ctrl+C)",
            "The watcher was stopped manually (Ctrl+C or terminal close).\n\n"
            "Restart `start_watcher.bat` to resume from the last completed task automatically.",
            push=True,
        )
    else:
        # Anything else = unexpected exit (laptop shutdown, process killed, etc.)
        write_status(
            "LAPTOP SHUTDOWN or PROCESS KILLED",
            "The watcher process exited without an explicit stop signal.\n\n"
            "**Likely cause**: laptop was turned off, or the OS killed the process.\n\n"
            "**Action required**: Restart `start_watcher.bat` -- the watcher will automatically "
            "resume from the last completed task.",
            push=True,
        )


def _report_crash(exc: Exception):
    """Called when an unhandled exception crashes the main loop."""
    tb = traceback.format_exc()
    write_status(
        f"WATCHER CRASH -- {type(exc).__name__}: {str(exc)[:120]}",
        f"An unhandled exception crashed the watcher:\n\n"
        f"```\n{tb}\n```\n\n"
        f"Please check `watcher.log` for details.\n\n"
        f"Restart `start_watcher.bat` -- the watcher will resume from the last completed task.",
        push=True,
    )


def register_shutdown_handlers():
    atexit.register(_atexit_handler)

    try:
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    except (OSError, ValueError):
        pass

# ---------------------------------------------------------------------------
# Lock file (prevent two Claude processes running at once)
# ---------------------------------------------------------------------------

def acquire_lock() -> bool:
    if LOCK_FILE.exists():
        pid = LOCK_FILE.read_text(encoding="utf-8").strip()
        log(f"Lock held by PID {pid}. Skipping.", "WARN")
        return False
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    return True


def release_lock():
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Claude invocation -- ONE TASK AT A TIME
# ---------------------------------------------------------------------------

def build_claude_prompt(task: dict) -> str:
    """
    Compact, token-efficient prompt.
    Only the ONE relevant blueprint is named — Claude reads that single file,
    not all six. This is the primary token-saving change.
    """
    phase     = task["phase"]
    text      = task["text"]
    blueprint = PHASE_BLUEPRINTS.get(phase, "DEVELOPER_GUIDE.md")

    return f"""You are a senior engineer on SAATHI AI (RYL NEUROACADEMY PRIVATE LIMITED).
Working directory: {REPO_DIR}
Stack: FastAPI/Python3.11, React18/TS/Vite/Tailwind, SQLAlchemy async, Redis, Razorpay, Pinecone, Shadow DOM widget, Docker.

TASK ({phase}): {text}

STEPS — do exactly these, nothing more:
1. Read blueprint: {blueprint}
2. Read only the files directly needed for this task.
3. Implement. Production code only — no placeholders, no TODO, no hardcoded secrets.
   Backend rules: logic in services/, HTTP in routes/, Loguru logging, HTTPException errors.
   Frontend rules: API calls only in lib/api.ts or hooks, handle loading+error states.
   DB rules: SQLAlchemy ORM only, schema changes via Alembic migration.
4. git add <changed files only — never .env>
   git commit -m "feat({phase.lower()}): <short description>"
   git push origin main
5. In TASKS.md change: - [ ] {text}
                    to: - [x] {text}
   git commit -m "chore(tasks): mark task complete"
   git push origin main
6. Append one entry to BUILD_DESIGN_RECORD.md: date, task, files changed, decision.
   git commit -m "docs(build-record): {text[:50]}"
   git push origin main

Do not read blueprints or files unrelated to this task. Stop as soon as step 6 is done.
"""


# ---------------------------------------------------------------------------
# Rate limit detection
# ---------------------------------------------------------------------------

class RateLimitHit(Exception):
    """Raised when Claude CLI reports the API usage limit is reached."""
    def __init__(self, reset_str: str = ""):
        self.reset_str = reset_str
        super().__init__(f"Claude rate limit hit. {reset_str}")

RATE_LIMIT_PHRASES = [
    "you've hit your limit",
    "you have exceeded your",
    "rate limit",
    "too many requests",
]

def _is_rate_limited(output: str) -> bool:
    lo = output.lower()
    return any(phrase in lo for phrase in RATE_LIMIT_PHRASES)


def _parse_reset_seconds(output: str) -> int:
    """
    Parse the reset time from Claude's rate-limit message, e.g.:
        "You've hit your limit · resets 1:30pm (Asia/Calcutta)"
    Returns seconds to sleep. Falls back to 3600 (1 hour) if unparseable.
    """
    match = re.search(
        r"resets\s+(\d{1,2}):(\d{2})\s*(am|pm)",
        output,
        re.IGNORECASE,
    )
    if not match:
        return 3600  # Default: wait 1 hour

    hour   = int(match.group(1))
    minute = int(match.group(2))
    ampm   = match.group(3).lower()

    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0

    # IST = UTC+5:30; use UTC arithmetic to avoid needing zoneinfo db
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    reset_ist = now_ist.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if reset_ist <= now_ist:
        reset_ist += timedelta(days=1)

    secs = int((reset_ist - now_ist).total_seconds()) + 120  # +2 min buffer
    return max(secs, 120)


# ---------------------------------------------------------------------------
# Claude invocation
# ---------------------------------------------------------------------------

def invoke_claude(task: dict) -> bool:
    """
    Call Claude Code CLI for a single task.

    Token-saving flags:
      --max-turns MAX_TURNS_PER_TASK  caps conversation length per task
      --allowedTools                  restricts to only needed tools
      --print                         non-interactive, no REPL overhead

    Returns True on success.
    Raises RateLimitHit if the API usage limit is detected in output.
    """
    prompt = build_claude_prompt(task)
    log(f"Invoking Claude: {task['display']}")

    try:
        result = subprocess.run(
            [
                CLAUDE_CMD,
                "--dangerously-skip-permissions",
                "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep",
                "--max-turns", str(MAX_TURNS_PER_TASK),
                "--print",
            ],
            input=prompt,
            cwd=REPO_DIR,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,   # 30-min max per task (was 1h; tasks should finish faster now)
        )
    except subprocess.TimeoutExpired:
        log(f"Claude timed out (30 min) on: {task['display']}", "ERROR")
        return False

    combined = (result.stdout or "") + (result.stderr or "")

    # Check for API rate limit BEFORE printing output
    if _is_rate_limited(combined):
        raise RateLimitHit(combined[:300])

    if result.stdout:
        print(result.stdout, flush=True)
    if result.stderr:
        print(result.stderr, flush=True)

    return result.returncode == 0

# ---------------------------------------------------------------------------
# Task verification helpers
# ---------------------------------------------------------------------------

def task_is_marked_done(task: dict) -> bool:
    """Check local TASKS.md to confirm Claude marked this task [x]."""
    try:
        content = TASKS_FILE.read_text(encoding="utf-8", errors="replace")
        return f"- [x] {task['text']}" in content
    except Exception:
        return False


def force_mark_task_done(task: dict):
    """
    If Claude forgot to mark the task [x], do it ourselves.
    This keeps TASKS.md consistent with state.
    """
    try:
        content = TASKS_FILE.read_text(encoding="utf-8", errors="replace")
        new_content = content.replace(
            f"- [ ] {task['text']}",
            f"- [x] {task['text']}",
            1,
        )
        if new_content != content:
            TASKS_FILE.write_text(new_content, encoding="utf-8")
            commit_and_push(
                [str(TASKS_FILE)],
                f"chore(tasks): watcher force-marked [{task['text'][:60]}] complete",
            )
            log(f"Force-marked task done in TASKS.md: {task['text'][:80]}", "WARN")
    except Exception as e:
        log(f"Could not force-mark task done: {e}", "WARN")

# ---------------------------------------------------------------------------
# Main task queue runner
# ---------------------------------------------------------------------------

def run_task_queue():
    """
    Pull all pending tasks from TASKS.md in document order.
    Execute one task at a time. Persist state after each task.
    On resume, skip already-completed tasks.
    """
    state = load_state()
    completed_keys = set(state.get("completed_tasks", []))

    # Pull latest code before scanning
    pull_latest()

    content = TASKS_FILE.read_text(encoding="utf-8", errors="replace")
    all_pending = extract_ordered_pending_tasks(content)

    # Remove tasks already done in previous runs
    remaining = [t for t in all_pending if t["key"] not in completed_keys]

    if not remaining:
        log("No pending tasks found. All done!")
        state["tasks_total"] = len(all_pending)
        save_state(state)
        write_status(
            "ALL TASKS COMPLETE",
            "Every task in TASKS.md has been implemented and pushed to GitHub.\n\n"
            "To continue: add new tasks to TASKS.md on GitHub. "
            "The watcher will detect them within 5 minutes.",
            push=True,
        )
        return

    log(f"Task queue: {len(remaining)} task(s) to execute "
        f"(skipped {len(completed_keys)} already completed).")

    state["tasks_total"] = len(all_pending)
    if not state.get("session_started"):
        state["session_started"] = datetime.now().isoformat()

    # If watcher was killed mid-task, resume that task first
    resume_key = state.get("current_task")
    if resume_key and resume_key not in completed_keys:
        # Reorder so interrupted task is first
        interrupted = [t for t in remaining if t["key"] == resume_key]
        rest        = [t for t in remaining if t["key"] != resume_key]
        remaining   = interrupted + rest
        if interrupted:
            log(f"Resuming interrupted task: {interrupted[0]['display']}", "WARN")

    save_state(state)

    # Initial status push
    write_status(
        f"RUNNING -- {len(remaining)} task(s) in queue",
        f"Watcher executing tasks in TASKS.md order.\n\n"
        f"**First task**: `{remaining[0]['display']}`",
        push=True,
    )

    total = len(remaining)
    idx = 0
    while idx < len(remaining):
        task = remaining[idx]

        # Mark as "currently running" in state (for crash recovery)
        state = load_state()
        state["current_task"] = task["key"]
        save_state(state)

        log(f"[{idx+1}/{total}] START: {task['display']}")

        if not acquire_lock():
            log("Could not acquire lock -- waiting 60s...", "WARN")
            time.sleep(60)
            if not acquire_lock():
                log("Lock still held. Skipping task this cycle.", "WARN")
                idx += 1
                continue

        success = False
        rate_limited = False
        try:
            success = invoke_claude(task)
        except RateLimitHit as rl:
            rate_limited = True
            secs = _parse_reset_seconds(rl.reset_str)
            mins = secs // 60
            reset_msg = f"Sleeping {mins} min until limit resets, then retrying."
            log(f"API rate limit hit. {reset_msg}", "WARN")
            write_status(
                "PAUSED -- API RATE LIMIT HIT",
                f"Claude Code has hit its hourly API usage limit.\n\n"
                f"**Next task** (will retry): `{task['display']}`\n\n"
                f"**Action**: Watcher is sleeping for **{mins} minutes** and will "
                f"automatically resume when the limit resets.\n\n"
                f"No action needed from you.",
                push=True,
            )
            release_lock()
            time.sleep(secs)
            log("Waking up after rate-limit sleep. Retrying task...")
            continue   # retry same task (idx not incremented)
        finally:
            if not rate_limited:
                release_lock()

        if not success:
            log(f"Claude FAILED for: {task['display']}", "ERROR")
            write_status(
                f"TASK FAILED -- {task['display'][:100]}",
                f"Claude Code returned a non-zero exit code.\n\n"
                f"**Likely cause**: implementation error in the task itself.\n\n"
                f"**Task**: `{task['display']}`\n\n"
                f"The watcher has skipped this task and moved to the next one.\n"
                f"Review `watcher.log` and fix manually if needed.",
                push=True,
            )
            # Count as done so we don't re-run forever
            state = load_state()
            if task["key"] not in state["completed_tasks"]:
                state["completed_tasks"].append(task["key"])
            state["current_task"] = None
            save_state(state)
            log(f"[{idx+1}/{total}] SKIP (task error): {task['display']}")
            idx += 1
            continue

        # Verify and ensure TASKS.md is updated
        if not task_is_marked_done(task):
            log("Claude did not update TASKS.md -- force-marking.", "WARN")
            force_mark_task_done(task)

        # Record completion in state
        state = load_state()
        if task["key"] not in state["completed_tasks"]:
            state["completed_tasks"].append(task["key"])
        state["current_task"] = None
        save_state(state)

        done_count = len(state["completed_tasks"])
        left_count = total - (idx + 1)
        next_label = remaining[idx+1]["display"] if idx + 1 < total else "ALL DONE"

        log(f"[{idx+1}/{total}] DONE: {task['display']}")

        write_status(
            f"IN PROGRESS -- {done_count} done, {left_count} remaining",
            f"**Just completed**: `{task['display']}`\n\n"
            f"**Up next**: `{next_label}`",
            push=True,
        )
        idx += 1

        # Inter-task cooldown: pause between tasks so the hourly token bucket
        # partially refills before the next Claude invocation.
        if idx < len(remaining):
            log(f"Cooldown {INTER_TASK_DELAY}s before next task (token budget recovery)...")
            time.sleep(INTER_TASK_DELAY)

    # All tasks finished
    write_status(
        "ALL TASKS COMPLETE",
        "Every task in TASKS.md has been implemented and pushed to GitHub.\n\n"
        "To continue: add new tasks to TASKS.md on GitHub. "
        "The watcher will detect them and resume within 5 minutes.",
        push=True,
    )
    log("All tasks complete!")

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    global _shutdown_reason

    register_shutdown_handlers()

    log("=" * 60)
    log("SAATHI AI GitHub Watcher v2 started")
    log(f"Repo  : {REPO_DIR}")
    log(f"Branch: {BRANCH}")
    log(f"Poll  : every {POLL_INTERVAL // 60} min for new tasks")
    log(f"Log   : {LOG_FILE}")
    log(f"State : {STATE_FILE}")
    log("=" * 60)
    log("Runs all pending TASKS.md tasks in order. Resumes after restart.")
    log("Press Ctrl+C to stop cleanly.")

    # Clean up stale lock from a previous crash
    if LOCK_FILE.exists():
        log("Removing stale lock file from previous run.", "WARN")
        release_lock()

    last_hash = None

    while True:
        try:
            remote_hash, _remote_content = fetch_remote_tasks()

            if last_hash != remote_hash:
                if last_hash is None:
                    log("Starting up -- scanning all pending tasks from TASKS.md...")
                else:
                    log("TASKS.md changed on GitHub -- rescanning tasks...")

                last_hash = remote_hash
                run_task_queue()

            else:
                log(f"No changes on GitHub. Next check in {POLL_INTERVAL // 60} min.")

        except KeyboardInterrupt:
            _shutdown_reason = "STOPPED_BY_USER"
            log("Stopped by user (Ctrl+C).")
            release_lock()
            sys.exit(0)

        except Exception as e:
            log(f"Watcher loop error: {e}", "ERROR")
            log(traceback.format_exc(), "ERROR")
            _shutdown_reason = "CRASH"
            _report_crash(e)
            _shutdown_reason = "DONE"   # prevent atexit double-report
            release_lock()
            log("Recovering -- waiting 60s before retry...")
            time.sleep(60)
            continue

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
