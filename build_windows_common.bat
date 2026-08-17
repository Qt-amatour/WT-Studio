@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "BUILD_MODE=%~1"
if /I "%BUILD_MODE%"=="debug" (
    set "BUILD_LABEL=Debug"
    set "BUILD_ARGUMENT=--debug"
    set "OUTPUT_FILE=release\WT_Studio_0.9.1_Debug.zip"
) else (
    set "BUILD_LABEL=Release"
    set "BUILD_ARGUMENT="
    set "OUTPUT_FILE=release\WT_Studio_0.9.1_Windows_x64.zip"
)

echo ========================================================
echo WT Studio 0.9.1 - Windows Standalone %BUILD_LABEL% Build
echo ========================================================

set "PYTHON_CMD="

where py >nul 2>nul
if not errorlevel 1 (
    py -3.13 -c "import sys; raise SystemExit(0 if sys.maxsize > 2**32 else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.13"
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) and sys.maxsize > 2**32 else 1)" >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo.
    echo ERROR: Python 3.13 x64 was not found on the build computer.
    echo Python is required only on the computer that creates WT Studio.exe.
    echo The final tester will not need Python.
    goto :error
)

rem Use a new directory name. The old .venv-build may contain a partially
rem uninstalled pip from the failed self-update and is intentionally ignored.
set "VENV_DIR=%CD%\.venv-build-313"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import pip; import pip._internal.cli.main" >nul 2>nul
    if errorlevel 1 (
        echo Existing build environment has a damaged pip installation.
        echo Recreating %VENV_DIR% from scratch...
        rmdir /S /Q "%VENV_DIR%"

        if exist "%VENV_DIR%" (
            echo.
            echo ERROR: Windows could not remove the damaged build environment.
            echo Close terminals, Python processes, and VS Code interpreters
            echo using .venv-build-313, then run this build again.
            goto :error
        )
    )
)

if not exist "%VENV_PY%" (
    echo Creating clean Python 3.13 build environment...

    rem Create the venv without pip first, then bootstrap pip from the
    rem Python installation's embedded ensurepip wheels. This cannot inherit
    rem the partially damaged pip files from the previous environment.
    %PYTHON_CMD% -m venv --without-pip "%VENV_DIR%"
    if errorlevel 1 goto :venv_error

    "%VENV_PY%" -m ensurepip --default-pip
    if errorlevel 1 goto :pip_bootstrap_error
)

echo Verifying pip...
"%VENV_PY%" -c "import pip; import pip._internal.cli.main; print('pip', pip.__version__)"
if errorlevel 1 goto :pip_broken_error

echo.
echo Installing build dependencies...
"%VENV_PY%" -m pip install ^
    --disable-pip-version-check ^
    --no-cache-dir ^
    --upgrade-strategy only-if-needed ^
    -r requirements-build.txt
if errorlevel 1 (
    echo.
    echo ERROR: Dependency installation failed.
    echo The build environment itself is valid, but pip could not install
    echo one or more packages. Review the package error shown above.
    goto :error
)

echo.
echo Starting %BUILD_LABEL% build...
"%VENV_PY%" tools\build_standalone.py %BUILD_ARGUMENT%
if errorlevel 1 goto :error

echo.
echo READY:
echo %OUTPUT_FILE%
echo.
pause
exit /b 0

:venv_error
echo.
echo ERROR: Could not create .venv-build-313.
echo Close programs using the folder and try again.
goto :error

:pip_bootstrap_error
echo.
echo ERROR: Python ensurepip could not install a clean bundled pip.
echo Remove .venv-build-313 with reset_build_environment.bat and try again.
goto :error

:pip_broken_error
echo.
echo ERROR: pip verification failed in .venv-build-313.
echo Run reset_build_environment.bat and start this build again.
goto :error

:error
echo.
echo BUILD FAILED. Review the messages above.
pause
exit /b 1
