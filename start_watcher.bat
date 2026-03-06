@echo off
title SAATHI AI — GitHub Watcher
color 0A
echo.
echo  =========================================
echo   SAATHI AI — GitHub Command Board Watcher
echo  =========================================
echo.
echo  This window must stay open.
echo  Claude will auto-run when you edit TASKS.md on GitHub.
echo.
echo  How to use:
echo    1. Go to github.com/cpdoryl/SAATHI-AI-PROTOTYPE
echo    2. Open TASKS.md ^> click Edit (pencil icon)
echo    3. Add:  - [ ] your task description
echo    4. Commit to main
echo    5. Watch this window — Claude will start in ~5 min
echo.
echo  Press Ctrl+C to stop the watcher.
echo.
echo  =========================================
echo.

cd /d "c:\saath ai prototype"
python github_watcher.py

echo.
echo Watcher stopped.
pause
