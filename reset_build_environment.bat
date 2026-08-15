@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo WT Studio - Reset Standalone Build Environments
echo ========================================================
echo.
echo The following temporary build folders may be removed:
echo   %CD%\.venv-build
echo   %CD%\.venv-build-313
echo.
echo WT Studio source files, projects, texconv.exe, builds, and release
echo archives will not be removed.
echo.

choice /C YN /N /M "Remove temporary build environments now? [Y/N]: "
if errorlevel 2 exit /b 0

call :remove_folder ".venv-build"
if errorlevel 1 goto :locked

call :remove_folder ".venv-build-313"
if errorlevel 1 goto :locked

echo.
echo Build environments removed successfully.
echo Run build_windows_release.bat or build_windows_debug.bat.
pause
exit /b 0

:remove_folder
if not exist "%~1" exit /b 0
rmdir /S /Q "%~1"
if exist "%~1" exit /b 1
exit /b 0

:locked
echo.
echo RESET FAILED.
echo A process is locking one of the build environments.
echo.
echo Close:
echo - Python terminals and previous build windows,
echo - VS Code if it selected either build environment as interpreter,
echo - File Explorer windows opened inside those folders.
echo.
echo Then run this reset script again.
pause
exit /b 1
