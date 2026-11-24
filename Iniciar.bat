@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 -m vidalia %*) || (python -m vidalia %*)
if errorlevel 1 pause
