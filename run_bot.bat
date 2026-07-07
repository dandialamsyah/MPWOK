@echo off
cd /d "%~dp0"
echo %date% %time% - Memulai Bot... > bot.log
.venv\Scripts\python -u main.py >> bot.log 2>&1
