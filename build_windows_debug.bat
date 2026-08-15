@echo off
call "%~dp0build_windows_common.bat" debug
exit /b %errorlevel%
