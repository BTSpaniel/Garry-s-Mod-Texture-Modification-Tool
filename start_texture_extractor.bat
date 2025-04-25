@echo off
:: Change to the directory where this batch file is located
cd /d "%~dp0"

:: Check Python installation, install/update if needed, and run the application
call check_and_install_python.bat
