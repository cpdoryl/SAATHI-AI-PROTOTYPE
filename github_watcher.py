#!/usr/bin/env python3
"""
SAATHI AI — GitHub Command Board Watcher
========================================
Runs permanently on your local PC.
Every 5 minutes it checks if TASKS.md changed on GitHub.
When you add a new  - [ ] task  from the GitHub web UI,
this script automatically calls Claude Code to implement it,
then pushes the result back to GitHub.

Usage:
    python github_watcher.py

Or double-click:
    start_watcher.bat
"""

import subprocess
import time
import hashlib
import os
import sys
from pathlib import Path
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────
REPO_DIR = Path(r"c:\saath ai prototype")
TASKS_FILE = REPO_DIR / "TASKS.md"
LOG_FILE = REPO_DIR / "watcher.log"
POLL_INTERVAL_SECONDS = 300        # check GitHub every 5 minutes
BRANCH = "main"

# ─── Logging ──────────────────────────────────────────────────────────────────

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ─── Git helpers ──────────────────────────────────────────────────────────────

def git(args: list, capture=True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=REPO_DIR,
        capture_output=capture,
        text=True,
    )


def fetch_remote_tasks() -> tuple[str, str]:
    """
    Fetch origin/main without touching local files.
    Returns (md5_hash, raw_content) of the remote TASKS.md.
    """
    git(["fetch", "origin", BRANCH])
    result = git(["show", f"origin/{BRANCH}:TASKS.md"])
    content = result.stdout if result.returncode == 0 else ""
    content_hash = hashlib.md5(content.encode()).hexdigest()
    return content_hash, content


def pull_latest():
    """Fast-forward local branch to match remote."""
    result = git(["pull", "--ff-only", "origin", BRANCH])
    if result.returncode != 0:
        log(f"Pull failed: {result.stderr}", "WARN")


# ─── Task parsing ─────────────────────────────────────────────────────────────

def extract_pending_tasks(tasks_md: str) -> list[str]:
    """
    Parse all unchecked  - [ ]  items from P0 and P1 sections of TASKS.md.
    Stops at ## P2 (production tasks) to avoid running heavy infra work remotely.
    Skips tasks with BLOCKED: note.
    """
    pending = []
    current_priority = None
    stop_at = "## P2"

    for line in tasks_md.splitlines():
        stripped = line.strip()

        if stripped.startswith("## P0"):
            current_priority = "P0"
        elif stripped.startswith("## P1"):
            current_priority = "P1"
        elif stripped.startswith(stop_at):
            break  # Don't auto-run P2 infra tasks

        if current_priority and stripped.startswith("- [ ]"):
            task_text = stripped[5:].strip()
            if "BLOCKED:" not in task_text:
                pending.append(f"[{current_priority}] {task_text}")

    return pending


# ─── Claude invocation ────────────────────────────────────────────────────────

def build_claude_prompt(tasks: list[str]) -> str:
    task_list = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(tasks))
    return f"""You are the CTO-level AI engineer for the Saathi AI project.
Working directory: {REPO_DIR}

New tasks have been committed to TASKS.md on GitHub. Implement ALL of the following:

{task_list}

Rules (follow exactly):
1. Read the relevant source files BEFORE making any changes
2. Implement each task following existing code patterns in the codebase
3. After implementing each task, mark it [x] in TASKS.md
4. Commit each completed task separately with message format: feat(scope): description
5. Push every commit immediately: git push origin main
6. If a task is unclear or blocked, add a BLOCKED: note below it in TASKS.md and commit that
7. Update DEVELOPER_GUIDE.md if you make significant architectural changes
8. Do NOT break existing functionality — read related code before touching it

Reference docs:
- Architecture: DEVELOPER_GUIDE.md
- Plain-English guide: CODEBASE_EXPLAINED.md
- All pending tasks: TASKS.md
"""


def invoke_claude(tasks: list[str]) -> bool:
    """
    Call Claude Code CLI in non-interactive mode.
    Returns True if invocation succeeded.
    """
    prompt = build_claude_prompt(tasks)
    log(f"Invoking Claude Code for {len(tasks)} task(s)...")
    for t in tasks:
        log(f"  Task: {t}")

    claude_cmd = r"C:\Users\B P Verma\AppData\Roaming\npm\claude.cmd"
    result = subprocess.run(
        [
            claude_cmd,
            "--dangerouslySkipPermissions",  # needed for unattended automation
            "--allowedTools",
            "Bash,Read,Write,Edit,Glob,Grep,TodoWrite",
            "-p",
            prompt,
        ],
        cwd=REPO_DIR,
        capture_output=False,   # stream output so you can see progress in terminal
        text=True,
        timeout=3600,           # 1-hour max per task batch
    )
    return result.returncode == 0


# ─── Lock file (prevent concurrent runs) ─────────────────────────────────────

LOCK_FILE = REPO_DIR / ".watcher.lock"


def acquire_lock() -> bool:
    if LOCK_FILE.exists():
        pid = LOCK_FILE.read_text().strip()
        log(f"Claude already running (PID {pid}). Skipping this cycle.", "WARN")
        return False
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def release_lock():
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log("SAATHI AI GitHub Watcher started")
    log(f"Repo:   {REPO_DIR}")
    log(f"Branch: {BRANCH}")
    log(f"Poll:   every {POLL_INTERVAL_SECONDS // 60} minutes")
    log(f"Log:    {LOG_FILE}")
    log("=" * 60)
    log("Add tasks to TASKS.md on GitHub and this script will auto-implement them.")
    log("Watching... (press Ctrl+C to stop)")

    last_hash = None

    while True:
        try:
            remote_hash, remote_content = fetch_remote_tasks()

            if last_hash is None:
                # First run — just capture baseline, don't run pending tasks
                # (they may have been pending for a while; wait for NEW changes)
                last_hash = remote_hash
                tasks = extract_pending_tasks(remote_content)
                log(f"Baseline captured. {len(tasks)} existing pending task(s) (not auto-running on first start).")
                log(f"Edit TASKS.md on GitHub to trigger Claude.")

            elif remote_hash != last_hash:
                log("TASKS.md changed on GitHub — pulling latest...")
                pull_latest()
                tasks = extract_pending_tasks(remote_content)

                if not tasks:
                    log("No pending [ ] tasks found (all done or no P0/P1 tasks).")
                else:
                    log(f"Found {len(tasks)} pending task(s).")
                    if acquire_lock():
                        try:
                            success = invoke_claude(tasks)
                            if success:
                                log("Claude finished. Check GitHub for updates.")
                            else:
                                log("Claude exited with non-zero code. Check output above.", "WARN")
                        finally:
                            release_lock()

                last_hash = remote_hash

            else:
                log(f"No changes. Next check in {POLL_INTERVAL_SECONDS // 60} min.")

        except KeyboardInterrupt:
            log("Watcher stopped by user.")
            release_lock()
            sys.exit(0)
        except Exception as e:
            log(f"ERROR: {e}", "ERROR")
            release_lock()

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
