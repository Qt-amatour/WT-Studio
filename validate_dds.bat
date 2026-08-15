@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src"

if "%~1"=="" (
    python tools\validate_dds.py
) else (
    python tools\validate_dds.py %*
)

echo.
pause
