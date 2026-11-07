
@echo off
cd /d "%~dp0"
call .venv313\Scripts\activate.bat
python app\main.py
pause
