@echo off
setlocal EnableExtensions

title Font to Webfont Converter
cls

echo.
echo ========================================================
echo              Font to Webfont Converter
echo ========================================================
echo.

REM Always run from the project directory so relative paths work.
cd /d "%~dp0"
if errorlevel 1 (
    echo [ERROR] Could not open the project directory.
    set "APP_EXIT_CODE=1"
    goto :finish
)

echo [INFO] Working directory: %CD%

REM Validate the files required to launch the application.
if not exist "app.py" (
    echo [ERROR] Required file not found: app.py
    set "APP_EXIT_CODE=1"
    goto :finish
)

if not exist "requirements.txt" (
    echo [ERROR] Required file not found: requirements.txt
    set "APP_EXIT_CODE=1"
    goto :finish
)

if exist "icons\add.png" if exist "icons\clear.png" if exist "icons\convert.png" if exist "icons\folder.png" goto :assets_ready
echo [WARN] One or more UI icons are missing. The app can run, but some buttons may not display icons.
goto :fonts_check

:assets_ready
echo [OK] UI assets found.

:fonts_check
if exist "fonts\adobe-caslon\adobe-caslon-regular.ttf" if exist "fonts\adobe-caslon\adobe-caslon-italic.ttf" if exist "fonts\adobe-caslon\adobe-caslon-semibold.ttf" if exist "fonts\adobe-caslon\adobe-caslon-semibold-italic.ttf" if exist "fonts\adobe-caslon\adobe-caslon-bold.ttf" if exist "fonts\adobe-caslon\adobe-caslon-bold-italic.ttf" goto :fonts_ready
echo [WARN] One or more Adobe Caslon font files are missing. The app will use the system fallback font.
goto :select_python

:fonts_ready
echo [OK] Adobe Caslon font family found.

:select_python
set "VENV_DIR=.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "PYTHON_EXE="
set "PYTHON_ARGS="
set "PYTHON_SOURCE="

REM Prefer the project virtual environment. Activation is unnecessary when
REM its Python executable is called directly.
if exist "%VENV_PYTHON%" (
    set "PYTHON_EXE=%VENV_PYTHON%"
    set "PYTHON_SOURCE=project virtual environment"
    goto :python_ready
)

echo [WARN] Virtual environment not found at %VENV_DIR%.
echo [INFO] Looking for a system Python installation...

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
    set "PYTHON_SOURCE=Windows Python Launcher"
    goto :python_ready
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    set "PYTHON_SOURCE=system PATH"
    goto :python_ready
)

echo.
echo [ERROR] Python 3 was not found.
echo.
echo Install Python from https://www.python.org/downloads/ and then run:
echo   python -m venv .venv
echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
set "APP_EXIT_CODE=1"
goto :finish

:python_ready
"%PYTHON_EXE%" %PYTHON_ARGS% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] The selected Python interpreter could not be started.
    set "APP_EXIT_CODE=1"
    goto :finish
)

echo [OK] Python found via %PYTHON_SOURCE%.
"%PYTHON_EXE%" %PYTHON_ARGS% --version

REM Fail early with a precise recovery command when dependencies are absent.
"%PYTHON_EXE%" %PYTHON_ARGS% -c "import PyQt5, fontTools, brotli" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] One or more Python dependencies are missing.
    echo [INFO] Install them with:
    echo   "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install -r requirements.txt
    set "APP_EXIT_CODE=1"
    goto :finish
)

echo [OK] Python dependencies found.
echo.
echo [INFO] Starting application...
echo --------------------------------------------------------

"%PYTHON_EXE%" %PYTHON_ARGS% app.py
set "APP_EXIT_CODE=%ERRORLEVEL%"

echo --------------------------------------------------------
if "%APP_EXIT_CODE%"=="0" (
    echo [OK] Application closed normally.
) else (
    echo [ERROR] Application exited with code %APP_EXIT_CODE%.
)

:finish
echo.
echo Press any key to close this window...
pause >nul
endlocal & exit /b %APP_EXIT_CODE%
