# SAATHI AI — Remote Claude Workflow

How to control Claude Code on your local PC from anywhere using only GitHub.

---

## ONE-TIME SETUP (do this once on your PC)

### 1. Verify Claude Code CLI is installed
Open a terminal and run:
```
claude --version
```
If not found, install it: https://claude.ai/download (install Claude Code desktop app — it includes the CLI)

### 2. Start the watcher (keep this terminal open)
Double-click `start_watcher.bat`

OR run in terminal:
```
cd "c:\saath ai prototype"
python github_watcher.py
```

You will see:
```
[2026-03-06 12:00:00] [INFO] SAATHI AI GitHub Watcher started
[2026-03-06 12:00:00] [INFO] Baseline captured. Watching for changes.
```

**This terminal window must stay open while you are away.**
If your PC sleeps/hibernates, wake it and re-run `start_watcher.bat`.

### 3. Keep the PC awake (recommended)
Open PowerShell as Admin and run:
```powershell
powercfg /change standby-timeout-ac 0
```
This prevents sleep while plugged in. Reverse it later with `powercfg /change standby-timeout-ac 30`.

---

## HOW TO GIVE COMMANDS FROM GITHUB

### Step 1 — Open TASKS.md on GitHub
Go to: https://github.com/cpdoryl/SAATHI-AI-PROTOTYPE/blob/main/TASKS.md

### Step 2 — Click the pencil icon (Edit)

### Step 3 — Add your task under P0 or P1
```
- [ ] Your task description here — any extra context
```

Example tasks you can add:
```
- [ ] Wire ClinicianDashboard to real /api/v1/patients endpoint, show live patient list
- [ ] Complete Razorpay sandbox test — create order, verify webhook in test mode
- [ ] Add PHQ-9 assessment form to PatientPortal frontend
- [ ] Write end-to-end test for /api/v1/auth/login
```

### Step 4 — Commit directly to main
Scroll down, write commit message, click "Commit changes".

### Step 5 — Wait ~5 minutes
The watcher on your PC will detect the change, pull it, and start Claude.
You can watch progress in the watcher terminal window (if you have remote desktop).

### Step 6 — Check GitHub for results
Refresh TASKS.md. Completed tasks will show `[x]`.
Check the commit history to see what Claude built.

---

## CHECKING PROGRESS REMOTELY

**Option A — GitHub web UI**
- Go to your repo's commits tab: https://github.com/cpdoryl/SAATHI-AI-PROTOTYPE/commits/main
- New commits from Claude will appear as: `feat(scope): description`

**Option B — GitHub mobile app**
- Install GitHub mobile → get push notifications for every commit

**Option C — Remote desktop**
- Use Windows Remote Desktop to see the watcher terminal live

---

## TASK WRITING GUIDE

### Good task format
```
- [ ] Task description — context about what file/area to work on
```

### Examples of clear tasks
```
- [ ] Complete /api/v1/chat/session/{id}/end — generate AI session summary using last 10 messages
- [ ] Add Redis caching to RAG query results (TTL 1 hour) — see rag_service.py
- [ ] Fix bug: TherapySession.current_step not resetting when new session starts
- [ ] Add PHQ-9 frontend form in PatientPortal — wire to POST /api/v1/assessments
```

### Examples of unclear tasks (avoid these)
```
- [ ] fix the dashboard        ← too vague, which dashboard, what's broken?
- [ ] add more features        ← no context
- [ ] make it better           ← Claude cannot act on this
```

### Special commands
```
- [ ] URGENT: [task] — Claude will prioritise this above other tasks
- [ ] REVIEW: check the auth flow for security issues and report findings in a new file SECURITY_REVIEW.md
- [ ] EXPLAIN: how does the crisis detection scoring work, write to NOTES.md
```

---

## WATCHER BEHAVIOUR

| Situation | What happens |
|-----------|-------------|
| You add `- [ ]` task to TASKS.md and commit | Watcher detects change in ~5 min, triggers Claude |
| Task completed | Claude marks `[x]`, commits, pushes |
| Task is unclear/blocked | Claude adds `BLOCKED: reason` under the task, commits |
| Multiple tasks added at once | Claude gets all of them in one session |
| P2 tasks added | NOT auto-run (infra tasks need manual review) |
| Watcher terminal is closed | No auto-runs until you reopen `start_watcher.bat` |
| PC is sleeping | Watcher paused; wake PC and it resumes automatically |

---

## WATCHER LOG

The watcher writes a log file at:
```
c:\saath ai prototype\watcher.log
```

You can check this remotely if you have file sync (OneDrive/Dropbox) on that folder,
or view it via Remote Desktop.

---

## ARCHITECTURE DIAGRAM

```
You (anywhere)
     |
     | edit TASKS.md
     v
GitHub Web UI
     |
     | git push to main
     v
github.com/cpdoryl/SAATHI-AI-PROTOTYPE
     |
     | git fetch (every 5 min)
     v
github_watcher.py  (running on your PC)
     |
     | detects TASKS.md changed
     | git pull
     | parses new [ ] tasks
     v
claude --dangerouslySkipPermissions -p "implement these tasks..."
     |
     | reads files, writes code, runs git commands
     v
Local codebase updated
     |
     | git push origin main
     v
GitHub updated — you see [x] and new commits
```

---

## TROUBLESHOOTING

**Watcher says "claude: command not found"**
- Claude Code CLI is not in PATH
- Fix: Open Claude Code app first, or add it to PATH:
  `C:\Users\B P Verma\AppData\Local\Programs\Claude\claude.exe`
- Add that folder to your Windows PATH environment variable

**Watcher is not detecting changes**
- Check your internet connection on the PC
- Check `watcher.log` for errors
- Make sure you committed to `main` (not another branch)

**Claude started but made wrong changes**
- Check the commit on GitHub — Claude always commits what it does
- You can revert: go to the commit on GitHub → click "Revert"
- Add a clearer task description explaining what went wrong

**PC went to sleep and missed tasks**
- Just wake the PC — watcher will detect the pending tasks on next poll
- Or run `start_watcher.bat` again (it safely re-initialises)

**Multiple tasks piling up**
- All pending `[ ]` tasks are sent to Claude in one batch
- Claude works through them sequentially

---

## SECURITY NOTE

The watcher uses `--dangerouslySkipPermissions` which allows Claude to:
- Read and write any file in the repo
- Run git commands
- Execute bash commands

It does NOT have access to:
- Files outside `c:\saath ai prototype\`
- Your browser, email, or other apps
- The internet (except via git and API calls already in the code)

Only use this on a PC you control and trust.
