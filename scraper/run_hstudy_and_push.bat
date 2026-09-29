@echo off
REM Local collector for Korea-IP-only sites (hstudy, edulove, tsherpa) plus commit and push.
REM Registered in Windows Task Scheduler to run daily, a bit before the
REM GitHub Actions workflow (08:00 KST). Log accumulates in hstudy_task.log.

set REPO=C:\Users\user\edutech-radar
set PYTHON=C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe
set GITEXE=C:\Program Files\Git\cmd\git.exe
set LOG=%REPO%\scraper\hstudy_task.log

cd /d "%REPO%"

echo ==== %date% %time% ==== >> "%LOG%"

"%PYTHON%" scraper\local_only.py >> "%LOG%" 2>&1
if errorlevel 1 (
    echo local_only.py failed on every site, skipping commit >> "%LOG%"
    goto :eof
)

"%GITEXE%" add data\hstudy_raw.json data\edulove_raw.json data\tsherpa_raw.json >> "%LOG%" 2>&1
"%GITEXE%" commit -m "local collect (%date%)" >> "%LOG%" 2>&1

REM GitHub Actions usually commits to main around the same time (08:00 KST) - sync with
REM the remote before pushing or this fails silently every day the two race each other
REM (this happened for real 2026-09-22 ~ 2026-09-29, commits piled up unpushed).
"%GITEXE%" fetch origin >> "%LOG%" 2>&1
"%GITEXE%" rebase origin/main >> "%LOG%" 2>&1
if errorlevel 1 (
    echo git rebase failed - aborting rebase, leaving local commit unpushed for manual look >> "%LOG%"
    "%GITEXE%" rebase --abort >> "%LOG%" 2>&1
    goto :eof
)

"%GITEXE%" push >> "%LOG%" 2>&1

echo. >> "%LOG%"
