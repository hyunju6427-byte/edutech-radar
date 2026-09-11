@echo off
REM Local collector for hstudy (Korean-IP-only site) + commit/push the result file.
REM Registered in Windows Task Scheduler to run daily, a bit before the
REM GitHub Actions workflow (08:00 KST). Log accumulates in hstudy_task.log.

set REPO=C:\Users\user\edutech-radar
set PYTHON=C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe
set GITEXE=C:\Program Files\Git\cmd\git.exe
set LOG=%REPO%\scraper\hstudy_task.log

cd /d "%REPO%"

echo ==== %date% %time% ==== >> "%LOG%"

"%PYTHON%" scraper\hstudy_only.py >> "%LOG%" 2>&1
if errorlevel 1 (
    echo hstudy_only.py failed, skipping commit >> "%LOG%"
    goto :eof
)

"%GITEXE%" add data\hstudy_raw.json >> "%LOG%" 2>&1
"%GITEXE%" commit -m "hstudy local collect (%date%)" >> "%LOG%" 2>&1
"%GITEXE%" push >> "%LOG%" 2>&1

echo. >> "%LOG%"
