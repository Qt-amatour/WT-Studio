@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src"
python tools\check_texture_engine.py
echo.
pause
