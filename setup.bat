@echo off
echo ========================================
echo TriunfoBet Bot - Setup
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

echo [1/5] Creando entorno virtual...
python -m venv venv
if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual
    pause
    exit /b 1
)

echo [2/5] Activando entorno virtual...
call venv\Scripts\activate.bat

echo [3/5] Instalando dependencias...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias
    pause
    exit /b 1
)

echo [4/5] Creando directorios...
if not exist "data" mkdir data
if not exist "models" mkdir models
if not exist "logs" mkdir logs

echo [5/5] Copiando archivo de configuracion...
if not exist ".env" (
    copy .env.example .env
    echo NOTA: Edita .env con tus credenciales
)

echo.
echo ========================================
echo Setup completado exitosamente!
echo ========================================
echo.
echo Proximos pasos:
echo 1. Edita .env con tus credenciales
echo 2. Ejecuta: python daily_bot.py
echo.
pause
