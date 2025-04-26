@echo off
REM install_windows.bat — Setup script for Windows

IF NOT EXIST ".venv" (
    echo Creating virtual environment in '.venv'...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Upgrading pip...
pip install --upgrade pip

echo Installing project requirements...
pip install -r requirements.txt

echo Setup completed successfully!
echo.
echo To activate your environment later, use:
echo   call .venv\Scripts\activate.bat
