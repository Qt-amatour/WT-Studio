@echo off
call "%~dp0build_windows_common.bat" release
exit /b %errorlevel%
