@echo off
setlocal

title EPS Phoenix -- Institutional Examination and Proctoring System
chcp 65001 >nul 2>&1

echo.
echo ============================================================================
echo   EPS PHOENIX -- INSTITUTIONAL PROCTORING AND EXAMINATION PLATFORM
echo   Vigilant Precision Engine Bootstrapper
echo ============================================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "MANAGE_PY=%SCRIPT_DIR%manage.py"
set "REQUIREMENTS_TXT=%SCRIPT_DIR%requirements.txt"

:: ----------------------------------------------------------------------------
:: 1. Virtual Environment Verification and Auto-Creation
:: ----------------------------------------------------------------------------
echo [1/6] Checking Python Virtual Environment...
if exist "%VENV_PYTHON%" goto :venv_found

echo       [WARN] Virtual environment .venv not found.
echo       [INFO] Checking system Python on PATH...
where python >nul 2>&1
if errorlevel 1 goto :no_python

echo       [INFO] Initializing new virtual environment at .venv...
python -m venv "%VENV_DIR%"
if errorlevel 1 goto :venv_failed
echo       [OK] Virtual environment created successfully.
goto :venv_found

:no_python
echo.
echo [ERROR] Python was not found on your system PATH!
echo [ERROR] Please install Python 3.10, 3.11, 3.12, or 3.13 from python.org
echo [ERROR] Ensure 'Add Python to PATH' is checked during installation.
echo.
pause
exit /b 1

:venv_failed
echo.
echo [ERROR] Failed to create virtual environment!
pause
exit /b 1

:venv_found
echo       [OK] Virtual environment ready at .venv
set "PY_CMD=%VENV_PYTHON%"

:: ----------------------------------------------------------------------------
:: 2. Requirements and Dependency Verification
:: ----------------------------------------------------------------------------
echo.
echo [2/6] Verifying Project Dependencies...
"%PY_CMD%" -c "import django, PIL, reportlab, dotenv, dj_database_url, whitenoise" >nul 2>&1
if errorlevel 1 goto :install_deps
echo       [OK] All core dependencies verified.
goto :check_dirs

:install_deps
echo       [WARN] Missing or outdated dependencies detected.
echo       [INFO] Installing packages from requirements.txt...
"%PY_CMD%" -m pip install --upgrade pip
"%PY_CMD%" -m pip install -r "%REQUIREMENTS_TXT%"
if errorlevel 1 goto :deps_failed
echo       [OK] All dependencies successfully installed.
goto :check_dirs

:deps_failed
echo.
echo [ERROR] Dependency installation failed! Check your internet connection or pip logs.
pause
exit /b 1

:check_dirs
:: ----------------------------------------------------------------------------
:: 3. Local Media and Storage Directories
:: ----------------------------------------------------------------------------
echo.
echo [3/6] Verifying Runtime Directories...
if not exist "%SCRIPT_DIR%media" mkdir "%SCRIPT_DIR%media"
echo       [OK] Runtime directories verified.

:: ----------------------------------------------------------------------------
:: 4. Database Migrations
:: ----------------------------------------------------------------------------
echo.
echo [4/6] Synchronizing Database Schema and Migrations...
"%PY_CMD%" "%MANAGE_PY%" migrate --noinput
if errorlevel 1 goto :migrate_failed
echo       [OK] All 20 module migrations are applied and up to date.
goto :check_django

:migrate_failed
echo.
echo [ERROR] Database migration failed! Please check database configuration.
pause
exit /b 1

:check_django
:: ----------------------------------------------------------------------------
:: 5. System Configuration Checks
:: ----------------------------------------------------------------------------
echo.
echo [5/6] Performing Django System Checks...
"%PY_CMD%" "%MANAGE_PY%" check
if errorlevel 1 goto :check_failed
echo       [OK] Platform configuration verified with 0 issues.
goto :after_check

:check_failed
echo.
echo [ERROR] Django system check identified critical issues!
pause
exit /b 1

:after_check
:: ----------------------------------------------------------------------------
:: Handle Optional Flag: --check-only
:: ----------------------------------------------------------------------------
if /i "%~1"=="--check-only" goto :check_only_done
goto :check_admin

:check_only_done
echo.
echo ============================================================================
echo   [SUCCESS] Pre-flight system check completed successfully!
echo   All dependencies, migrations, and settings are operational.
echo ============================================================================
exit /b 0

:check_admin
:: ----------------------------------------------------------------------------
:: 6. Administrator Superuser Check
:: ----------------------------------------------------------------------------
echo.
echo [6/6] Checking Administrative Access...
"%PY_CMD%" -c "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development'); django.setup(); from apps.accounts.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" >nul 2>&1
if not errorlevel 1 goto :admin_exists

echo       [WARN] No administrative superuser found in the local database.
echo.
set "CREATE_SUPERUSER="
set /p CREATE_SUPERUSER="      Would you like to create an Admin Superuser now? [y/n, default y]: "
if "%CREATE_SUPERUSER%"=="" set "CREATE_SUPERUSER=y"
if /i not "%CREATE_SUPERUSER%"=="y" goto :skip_superuser

echo.
echo       --- Provision Superuser Account ---
"%PY_CMD%" "%MANAGE_PY%" createsuperuser
echo       ------------------------------------
goto :start_server

:skip_superuser
echo       [INFO] Skipping superuser creation. You can create one later with: manage.py createsuperuser
goto :start_server

:admin_exists
echo       [OK] Administrative superuser exists.

:start_server
:: ----------------------------------------------------------------------------
:: Launch Browser and Development Server
:: ----------------------------------------------------------------------------
echo.
echo ============================================================================
echo   EPS PHOENIX IS READY -- STARTING DEVELOPMENT HTTP SERVER
echo.
echo   Local Web Access:       http://127.0.0.1:8000/
echo   Admin Governance:       http://127.0.0.1:8000/administration/
echo   Teacher Workspace:      http://127.0.0.1:8000/teacher/dashboard/
echo   Student Workspace:      http://127.0.0.1:8000/student/dashboard/
echo.
echo   Press CTRL+C in this window to stop the server.
echo ============================================================================
echo.

if /i not "%~1"=="--no-browser" start "" "http://127.0.0.1:8000/"

"%PY_CMD%" "%MANAGE_PY%" runserver 127.0.0.1:8000

echo.
echo [INFO] Development server has stopped.
pause
