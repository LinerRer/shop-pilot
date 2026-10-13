@echo off
chcp 65001 >nul
cd /d %~dp0

echo ========================================
echo   ShopPilot 一键启动
echo ========================================
echo.

if not exist .venv (
    echo [1/4] 创建虚拟环境 .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo 创建虚拟环境失败，请确认已安装 Python 3.11 并加入 PATH
        pause
        exit /b 1
    )
) else (
    echo [1/4] 虚拟环境已存在
)

echo [2/4] 激活虚拟环境 ...
call .venv\Scripts\activate.bat

echo [3/4] 安装依赖（清华源）...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple -q
if errorlevel 1 (
    echo 依赖安装失败，请检查网络或 requirements.txt
    pause
    exit /b 1
)

if not exist data\shop.db (
    echo [4/4] 初始化模拟数据（约10秒）...
    python src\database\seed.py
    if errorlevel 1 (
        echo 数据初始化失败
        pause
        exit /b 1
    )
) else (
    echo [4/4] 数据库已存在，跳过初始化
)

if not exist .env (
    echo.
    echo [警告] 未找到 .env 文件，请先创建并填入 DeepSeek API Key：
    echo   DEEPSEEK_API_KEY=你的key
    echo   DEEPSEEK_BASE_URL=https://api.deepseek.com
    echo   DEEPSEEK_MODEL=deepseek-chat
    echo.
    pause
    exit /b 1
)

echo.
echo 启动 Streamlit ...
streamlit run src\ui\app.py
pause
