@echo off
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
    playwright install chromium
) else (
    call venv\Scripts\activate
)

echo Starting Crawler...
python -m src.main
pause
