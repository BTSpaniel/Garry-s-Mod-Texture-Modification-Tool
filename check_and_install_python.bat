@echo off
setlocal enabledelayedexpansion

:: Hide command output
echo Checking Python installation...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Installing Python...
    call :InstallPython
) else (
    :: Get Python version
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "pyversion=%%i"
    echo Found Python !pyversion!
    
    :: Check if version is at least 3.13.3 (current recommended version)
    for /f "tokens=1,2,3 delims=." %%a in ("!pyversion!") do (
        set "pymajor=%%a"
        set "pyminor=%%b"
        set "pypatch=%%c"
    )
    
    if !pymajor! lss 3 (
        echo Python version is too old. Installing newer version...
        call :InstallPython
    ) else if !pymajor! equ 3 (
        if !pyminor! lss 13 (
            echo Python version is too old. Installing newer version...
            call :InstallPython
        ) else if !pyminor! equ 13 (
            if !pypatch! lss 3 (
                echo Python version is too old. Installing newer version...
                call :InstallPython
            ) else (
                echo Python version is adequate.
            )
        ) else (
            echo Python version is adequate.
        )
    )
)

:: Check if pip is installed and install required packages
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing pip...
    python -m ensurepip --upgrade --default-pip >nul 2>&1
)

:: Install required packages
echo Installing required packages...
python -m pip install -r requirements.txt >nul 2>&1

:: Run the main application
echo Starting application...

:: Run the application with error handling
python debug_app.py
if %errorlevel% neq 0 (
    echo Application encountered an error.
    exit /b %errorlevel%
)

exit /b 0

:InstallPython
:: Create a temporary directory
set "tempdir=%temp%\python_installer"
mkdir "%tempdir%" 2>nul

:: Download Python installer silently
echo Downloading Python installer...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.13.3/python-3.13.3-amd64.exe' -OutFile '%tempdir%\python_installer.exe'}"

:: Install Python silently
echo Installing Python silently...
"%tempdir%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_doc=0 Include_launcher=1 Include_tcltk=1 >nul 2>&1

:: Clean up
del "%tempdir%\python_installer.exe" >nul 2>&1
rmdir "%tempdir%" >nul 2>&1

:: Refresh environment variables
call :RefreshEnv

echo Python installation completed.
exit /b 0

:RefreshEnv
:: Refresh environment variables without restarting the batch file
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path') do set "syspath=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path') do set "userpath=%%b"
set "PATH=%syspath%;%userpath%"
exit /b 0
