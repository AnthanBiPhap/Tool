@echo off
REM TikTokSage Runner
REM This batch file runs the TikTokSage application

cd /d "%~dp0"
python main.py %*
