@echo off
REM Called by the Windows Task Scheduler: activate the venv, run one snapshot, append to a log
cd /d C:\Users\Erik\MyDealz
call venv\Scripts\activate.bat
python run_snapshot.py >> run.log 2>&1
