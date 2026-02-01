@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
echo.
echo ======================================================================
echo === Asset Register ISO 55000 Specialist - Web UI ===
echo ======================================================================
echo.
echo Starting web server...
echo.
py web_app.py
pause
