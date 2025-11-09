@echo off
echo ========================================
echo TriunfoBet Bot - Setup (Fixed)
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en PATH
    echo Por favor instala Python 3.10+ desde https://www.python.org/
    pause
    exit /b 1
)

echo [1/6] Eliminando entorno virtual anterior (si existe)...
if exist "venv" rmdir /s /q venv

echo [2/6] Creando nuevo entorno virtual...
python -m venv venv
if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual
    pause
    exit /b 1
)

echo [3/6] Activando entorno virtual...
call venv\Scripts\activate.bat

echo [4/6] Actualizando pip, setuptools y wheel...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo ERROR: No se pudo actualizar pip
    pause
    exit /b 1
)

echo [5/6] Instalando dependencias (esto puede tardar unos minutos)...
pip install --no-cache-dir numpy pandas scikit-learn
pip install --no-cache-dir xgboost
pip install --no-cache-dir loguru pyyaml python-dotenv
pip install --no-cache-dir sqlalchemy psycopg2-binary pymongo
pip install --no-cache-dir APScheduler
pip install --no-cache-dir requests beautifulsoup4
pip install --no-cache-dir streamlit plotly
pip install --no-cache-dir pytest pytest-mock

echo [6/6] Creando directorios...
if not exist "data" mkdir data
if not exist "models" mkdir models
if not exist "logs" mkdir logs

echo Copiando archivo de configuracion...
if not exist ".env" (
    copy .env.example .env
    echo NOTA: Edita .env con tus credenciales si es necesario
)

echo.
echo ========================================
echo Setup completado exitosamente!
echo ========================================
echo.
echo Proximos pasos:
echo 1. (Opcional) Edita .env con tus credenciales
echo 2. Ejecuta: python verify_installation.py
echo 3. Ejecuta: python daily_bot.py
echo.
pause
