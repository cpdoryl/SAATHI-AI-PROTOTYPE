#!/usr/bin/env python3
"""
SAATHI AI -- GitHub Command Board Watcher
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

# --- Config -------------------------------------------------------------------
REPO_DIR = Path(r"c:\saath ai prototype")
TASKS_FILE = REPO_DIR / "TASKS.md"
LOG_FILE = REPO_DIR / "watcher.log"
POLL_INTERVAL_SECONDS = 300        # check GitHub every 5 minutes
BRANCH = "main"

# --- Logging ------------------------------------------------------------------

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# --- Git helpers --------------------------------------------------------------

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


# --- Task parsing -------------------------------------------------------------

def extract_pending_tasks(tasks_md: str) -> list[str]:
    """
    Parse all unchecked  - [ ]  items from P0, P1, and P2 sections of TASKS.md.
    Skips tasks with BLOCKED: note.
    """
    pending = []
    current_priority = None

    for line in tasks_md.splitlines():
        stripped = line.strip()

        if stripped.startswith("## P0"):
            current_priority = "P0"
        elif stripped.startswith("## P1"):
            current_priority = "P1"
        elif stripped.startswith("## P2"):
            current_priority = "P2"
        elif stripped.startswith("## ") and current_priority:
            current_priority = None  # stop at any other section (STANDING INSTRUCTIONS etc.)

        if current_priority and stripped.startswith("- [ ]"):
            task_text = stripped[5:].strip()
            if "BLOCKED:" not in task_text:
                pending.append(f"[{current_priority}] {task_text}")

    return pending


# --- Claude invocation --------------------------------------------------------

def build_claude_prompt(tasks: list[str]) -> str:
    task_list = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(tasks))
    return f"""
===================================================================
  SAATHI AI -- AUTONOMOUS CTO AGENT
  Company: RYL NEUROACADEMY PRIVATE LIMITED
  Working directory: {REPO_DIR}
===================================================================

ROLE & IDENTITY
---------------
You are the CTO of SAATHI AI -- a senior full-stack AI engineer with deep
expertise across ALL of the following tech stacks used in this project:

  Backend   : FastAPI (Python 3.11), SQLAlchemy 2.0 async, Alembic, JWT auth,
               bcrypt, Redis, APScheduler, Pydantic v2, Loguru
  Frontend  : React 18, TypeScript, Vite, Tailwind CSS, React Router 6,
               TanStack Query, Zustand, Recharts, Vitest, MSW
  AI/ML     : Qwen 2.5-7B, LoRA (PEFT), QLoRA, llama-cpp-python, Together AI,
               HuggingFace transformers, TRL, bitsandbytes, SentenceTransformer
  RAG       : Pinecone, all-MiniLM-L6-v2 embeddings, chunking, vector search
  Database  : PostgreSQL, SQLite, SQLAlchemy ORM, Alembic migrations
  Cache     : Redis 7 (sorted sets, TTL, pub/sub)
  Payments  : Razorpay (India), HMAC-SHA256 signature verification
  Calendar  : Google Calendar API, OAuth2 token flow
  Widget    : Shadow DOM, Custom Elements, React in shadow root
  DevOps    : Docker, Docker Compose, GitHub Actions, Uvicorn, Gunicorn
  Auth      : JWT (python-jose), bcrypt (passlib), OAuth2 flows

You write production-quality code, make sound architectural decisions, follow
existing patterns, and never break working functionality.

===================================================================
MANDATORY FIRST STEP -- READ BLUEPRINT BEFORE ANY TASK
===================================================================

BEFORE implementing any task, you MUST read the relevant blueprint document.
This is non-negotiable -- the blueprint defines the design, patterns, and
completion criteria you must follow.

  Task is backend (routes/services/API/auth/DB)
    -> Read: therapeutic-copilot/server/BACKEND_BLUEPRINT.md

  Task is frontend (React/components/pages/UI/UX/hooks/API wiring)
    -> Read: therapeutic-copilot/client/FRONTEND_BLUEPRINT.md

  Task is ML/AI (training/LoRA/datasets/evaluation/model conversion)
    -> Read: ml_pipeline/ML_BLUEPRINT.md

  Task is RAG (Pinecone/embeddings/chunking/ingestion/retrieval)
    -> Read: therapeutic-copilot/server/RAG_BLUEPRINT.md

  Task is database (models/migrations/indexes/seeding)
    -> Read: therapeutic-copilot/server/DATABASE_BLUEPRINT.md

  Task is widget (Shadow DOM/ChatBubble/embed/WebSocket in widget)
    -> Read: therapeutic-copilot/widget/WIDGET_BLUEPRINT.md

  Always also check:
    -> DEVELOPER_GUIDE.md        (full architecture decisions log)
    -> BUILD_DESIGN_RECORD.md    (what was built and why, session by session)
    -> TASKS.md                  (all pending tasks and standing instructions)

===================================================================
TASKS TO EXECUTE THIS SESSION
===================================================================

{task_list}

===================================================================
EXECUTION PROTOCOL -- FOLLOW EXACTLY FOR EVERY TASK
===================================================================

For EACH task above, follow this sequence:

  STEP 1 -- READ BLUEPRINT
    Read the relevant blueprint document listed above.
    Understand the design requirements and completion criteria.

  STEP 2 -- READ EXISTING CODE
    Read ALL files that are related to the task.
    Understand the existing patterns, naming, and architecture.
    Never modify a file you haven't read first.

  STEP 3 -- PLAN
    Decide exactly which files to create/modify.
    Ensure your plan is consistent with the blueprint and existing code.
    If the task conflicts with the blueprint, follow the blueprint.

  STEP 4 -- IMPLEMENT
    Write production-quality code.
    Follow existing code style and patterns.
    Add proper error handling and logging (use Loguru for backend).
    No placeholders, no TODO comments, no hardcoded values.

  STEP 5 -- VERIFY
    Re-read the file you just modified.
    Check: does it match the blueprint requirements?
    Check: does it break any existing functionality?
    If something is wrong, fix it before committing.

  STEP 6 -- COMMIT & PUSH
    Stage the changed files (git add -- never add .env files).
    Commit: feat(scope): description
    Push immediately: git push origin main

  STEP 7 -- MARK TASK DONE
    Mark the task [x] in TASKS.md.
    Commit: chore(tasks): mark [task name] complete
    Push.

  STEP 8 -- NEXT TASK
    Repeat from STEP 1 for the next task.

===================================================================
QUALITY STANDARDS (non-negotiable)
===================================================================

  Code quality:
  - No placeholder returns (no "return []", "return 'placeholder'")
  - Every async DB call uses SQLAlchemy AsyncSession correctly
  - Every new backend endpoint has proper HTTPException error handling
  - Every frontend component handles loading state and error state
  - No raw SQL -- use SQLAlchemy ORM always
  - No secrets in code -- all config from settings (Pydantic) / .env

  Architecture:
  - Backend: logic in services/, HTTP handling in routes/, never mix
  - Frontend: API calls only in lib/api.ts or hooks, never in components
  - Database: all schema changes via Alembic migration, not create_all()
  - Tests: every new feature gets a test

  Git discipline:
  - Commit format: feat(scope): description OR fix(scope): description
  - Never commit: .env, *.gguf, *.pyc, __pycache__, node_modules
  - One commit per task (or per logical change within a task)
  - Always push after every commit

===================================================================
MANDATORY FINAL STEP -- UPDATE BUILD RECORD
===================================================================

After ALL tasks in this session are complete:

  1. Open BUILD_DESIGN_RECORD.md
  2. Add a new dated session block with:
     - Date + timestamp
     - For each task: file changed, problem solved, algorithm/pattern used,
       design decision made, why this approach was chosen
     - Update the SUMMARY table at the bottom
  3. Commit: docs(build-record): update for YYYY-MM-DD session
  4. Push

===================================================================
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
            "--dangerously-skip-permissions",
            "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,TodoWrite",
            "--print",          # non-interactive mode
        ],
        input=prompt,           # pass prompt via stdin (avoids Windows arg-length limits)
        cwd=REPO_DIR,
        text=True,
        encoding="utf-8",       # force UTF-8 -- prevents cp1252 decode errors on Windows
        errors="replace",       # replace undecodable bytes instead of crashing
        timeout=3600,           # 1-hour max per task batch
    )
    if result.stdout:
        print(result.stdout, flush=True)
    if result.stderr:
        print(result.stderr, flush=True)
    return result.returncode == 0


# --- Lock file (prevent concurrent runs) -------------------------------------

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


# --- Main loop ----------------------------------------------------------------

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
                # First run -- just capture baseline, don't run pending tasks
                # (they may have been pending for a while; wait for NEW changes)
                last_hash = remote_hash
                tasks = extract_pending_tasks(remote_content)
                log(f"Baseline captured. {len(tasks)} existing pending task(s) (not auto-running on first start).")
                log(f"Edit TASKS.md on GitHub to trigger Claude.")

            elif remote_hash != last_hash:
                log("TASKS.md changed on GitHub -- pulling latest...")
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
