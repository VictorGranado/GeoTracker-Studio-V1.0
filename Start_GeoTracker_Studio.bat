@echo off
cd /d "%~dp0"
python -m geotracker_studio.app
if errorlevel 1 pause
