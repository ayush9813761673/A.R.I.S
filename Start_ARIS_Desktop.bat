@echo off
cd /d "%~dp0"
where.exe pythonw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pythonw.exe "%~dp0ARIS_DESKTOP.py"
) else (
    python "%~dp0ARIS_DESKTOP.py"
)
