@echo off
cd /d "%~dp0"
title Customer Change Request Simulator - Version 2
if exist "venv\Scripts\python.exe" goto check_package
echo Creating the project Python environment...
py -m venv venv
if errorlevel 1 goto setup_error
:check_package
"venv\Scripts\python.exe" -c "import streamlit" >nul 2>&1
if not errorlevel 1 goto run_app
echo Installing required packages. Please wait...
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto setup_error
:run_app
echo Starting the simulator. Keep this window open.
"venv\Scripts\python.exe" -m streamlit run app.py --server.headless false
pause
exit /b
:setup_error
echo Setup could not finish. Take a screenshot of this window for help.
pause
exit /b 1
