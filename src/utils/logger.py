"""
Logger configuration usando loguru
"""

import sys
from loguru import logger
import os


def setup_logger(log_file: str = "logs/triunfobet_bot.log",
                level: str = "INFO",
                rotation: str = "10 MB",
                retention: str = "30 days"):
    """
    Configura el sistema de logging

    Args:
        log_file: Ruta al archivo de log
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        rotation: Tamaño para rotar logs
        retention: Tiempo de retención de logs antiguos
    """
    # Crear directorio de logs si no existe
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Remover handler por defecto
    logger.remove()

    # Console handler con formato colorido
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )

    # File handler con rotación
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
        rotation=rotation,
        retention=retention,
        compression="zip"
    )

    logger.info("Logger initialized")

    return logger


# Inicializar logger por defecto
if not os.path.exists("logs"):
    os.makedirs("logs")

logger.remove()  # Remove default handler
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
