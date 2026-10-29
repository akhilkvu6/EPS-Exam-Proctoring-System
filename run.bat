@echo off
setlocal enabledelayedexpansion

title EPS - Exam Proctoring System

echo ==============================================================================
echo                 EPS (Exam Proctoring System) Launcher
echo ==============================================================================
echo.

:: Detect Python launcher (prefers 'py' launcher if available)
set "PY_CMD=python"
where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py"
) else (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found in your system PATH.
        echo Please install Python 3.10+ from python.org and ensure "Add Python to PATH" is checked.
        echo.
        pause
        exit /b 1
    )
)

echo [*] Detected Python launcher: %PY_CMD%

:: Step 1: Create virtual environment if missing
if not exist "venv\Scripts\activate.bat" (
    echo [*] Virtual environment 'venv' not found. Creating it now...
    %PY_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        echo.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
)

:: Step 2: Activate virtual environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    echo.
    pause
    exit /b 1
)

:: Step 3: Install / verify dependencies
echo [*] Checking dependencies from requirements.txt...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install requirements.
    echo.
    pause
    exit /b 1
)

:: Step 4: Run database migrations
echo [*] Applying database migrations...
python manage.py migrate --noinput
if %errorlevel% neq 0 (
    echo [ERROR] Database migration failed.
    echo.
    pause
    exit /b 1
)

:: Step 5: Display quick credentials and launch server
echo.
echo ==============================================================================
echo   Server ready! Open your browser at: http://127.0.0.1:8000/
echo.
echo   Demo Login Accounts:
echo     - Admin:   Username: admin            Password: admin123
echo     - Teacher: Username: teacher_test_01  Password: teacher123
echo     - Student: Username: student_test_01  Password: student123
echo.
echo   Press CTRL + C to stop the server at any time.
echo ==============================================================================
echo.

python manage.py runserver 127.0.0.1:8000

if %errorlevel% neq 0 (
    echo.
    echo [INFO] Server stopped.
    pause
)
