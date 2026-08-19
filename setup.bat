@echo off
setlocal
cd /d "%~dp0"
title SpotifyWidget Setup

echo.
echo ========================================
echo          SpotifyWidget Setup
echo ========================================
echo.

if not exist "requirements.txt" (
    echo ERROR: requirements.txt was not found beside setup.bat.
    goto :fail
)

if not exist "credentials.py" (
    echo ERROR: credentials.py was not found beside setup.bat.
    goto :fail
)

rem Find a usable Python installation only if the virtual environment
rem does not already exist.
if not exist "MediaWidget\Scripts\python.exe" (
    echo [1/3] Creating Python environment...
    set "VENV_CREATED="

    where py.exe >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv MediaWidget
        if not errorlevel 1 set "VENV_CREATED=1"
    )

    if not defined VENV_CREATED (
        where python.exe >nul 2>&1
        if errorlevel 1 goto :python_missing

        python -m venv MediaWidget
        if errorlevel 1 goto :python_fail
    )
) else (
    echo [1/3] Existing Python environment found.
)

echo [2/3] Installing/updating dependencies...
"MediaWidget\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :pip_fail

"MediaWidget\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :pip_fail

echo [3/3] Checking Spotify credentials...
findstr /C:"client ID" "credentials.py" >nul 2>&1
if not errorlevel 1 goto :credentials_missing
findstr /C:"client Secret" "credentials.py" >nul 2>&1
if not errorlevel 1 goto :credentials_missing

echo.
echo ========================================
echo              Setup complete!
echo ========================================
echo.
echo From now on, launch SpotifyWidget by double-clicking:
echo.
echo     MediaWidget.bat
echo.
echo On first launch, Spotify will open a browser window so you can
echo authorize the app.
echo.
pause
exit /b 0

:credentials_missing
echo.
echo The Python environment is ready, but credentials.py still contains
echo the distribution placeholder credentials.
echo.
echo A Spotify Developer app needs to be created and its Client ID and
echo Client Secret copied into credentials.py.
echo.
echo Required redirect URI:
echo     http://127.0.0.1:25566/callback
echo.
echo Opening credentials.py now...
start "" notepad.exe "%~dp0credentials.py"
echo.
echo After saving your credentials, run setup.bat again to verify them.
echo.
pause
exit /b 1

:python_missing
echo.
echo ERROR: Python 3 was not found.
echo Install Python 3, make sure the Python launcher or python.exe is
echo available, then run setup.bat again.
goto :fail

:python_fail
echo.
echo ERROR: Could not create the MediaWidget Python environment.
goto :fail

:pip_fail
echo.
echo ERROR: Dependency installation failed.
echo Check the output above for the package or network error.
goto :fail

:fail
echo.
echo Setup did not complete.
echo.
pause
exit /b 1
