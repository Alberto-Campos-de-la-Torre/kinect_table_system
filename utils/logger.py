"""
Sistema de Logging para Kinect Table System
============================================
Configuración centralizada de logging usando loguru
"""

import sys
from pathlib import Path
from loguru import logger
from config import LogConfig


def setup_logger(level="INFO", log_file=None):
    """
    Configurar el sistema de logging
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Archivo de log personalizado (opcional)
    
    Returns:
        logger: Instancia del logger configurado
    """
    # Remover configuración por defecto
    logger.remove()
    
    # Configurar output a consola si está habilitado
    if LogConfig.CONSOLE_LOG:
        logger.add(
            sys.stderr,
            format=LogConfig.LOG_FORMAT,
            level=level,
            colorize=True
        )
    
    # Configurar archivo de log
    log_path = log_file or LogConfig.LOG_FILE
    logger.add(
        log_path,
        format=LogConfig.LOG_FORMAT,
        level=level,
        rotation=LogConfig.LOG_ROTATION,
        retention=LogConfig.LOG_RETENTION,
        compression="zip"
    )
    
    logger.info(f"Logger configurado - Nivel: {level}")
    logger.info(f"Archivo de log: {log_path}")
    
    return logger


# Configuración por defecto
default_logger = setup_logger()


if __name__ == "__main__":
    # Test del logger
    logger.debug("Mensaje de DEBUG")
    logger.info("Mensaje de INFO")
    logger.warning("Mensaje de WARNING")
    logger.error("Mensaje de ERROR")
    logger.critical("Mensaje de CRITICAL")
