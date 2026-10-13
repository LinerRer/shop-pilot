@echo off
cd /d %~dp0

echo ========================================
echo   ShopPilot - One Click Start
echo ========================================
echo.

if not exist .venv (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create venv. Please install Python 3.11 and add to PATH.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Virtual environment exists.
)

echo [2/4] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [3/4] Installing dependencies...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple -q
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

if not exist data\shop.db (
    echo [4/4] Initializing database...
    python src\database\seed.py
    if errorlevel 1 (
        echo Failed to initialize database.
        pause
        exit /b 1
    )
) else (
    echo [4/4] Database exists, skipping init.
)

if not exist .env (
    echo.
    echo [WARNING] .env file not found.
    echo Please copy .env.example to .env and fill in your DEEPSEEK_API_KEY.
    echo.
    pause
    exit /b 1
)

echo.
echo Starting Streamlit...
streamlit run src\ui\app.py
