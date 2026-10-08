import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """Intercepta los logs estándar de Python y los redirige a Loguru."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            if frame.f_back:
                frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    """Configura Loguru para cumplir con el Factor 11 (Solo stdout)."""
    logger.remove()

    # Log en consola (stdout) como flujo continuo de eventos
    logger.add(
        sys.stdout, 
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}", 
        level="INFO",
        colorize=True
    )

    # Interceptar logs de Uvicorn y FastAPI
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
    logging.getLogger("fastapi").handlers = [InterceptHandler()]
