@echo off
cd /d "%~dp0"
echo ========================================
echo Starting Asset Management System
echo ========================================
echo.
echo Initializing server...
echo.
C:\Users\eralu\AppData\Local\Programs\Python\Launcher\py.exe web_app.py
echo.
echo Server stopped.
pause
