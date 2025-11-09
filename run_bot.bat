@echo off
echo ========================================
echo TriunfoBet Bot - Daily Analysis
echo ========================================
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Entorno virtual no encontrado
    echo Ejecuta setup.bat primero
    pause
    exit /b 1
)

REM Run the bot
python daily_bot.py

echo.
echo ========================================
echo Analisis completado
echo ========================================
echo.
pause
