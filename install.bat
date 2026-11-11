@echo off
title Installer - Prompt Workbench
cd /d "%~dp0"
echo.
echo Starting installer, please wait...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
pause