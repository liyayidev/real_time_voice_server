import logging
import sys
import json
from logging.handlers import RotatingFileHandler
from .config import settings

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    logger.handlers = [] # Clear existing

    # Console Handler
    if settings.APP_ENV == "production":
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())
    else:
        # Development logging with color
        try:
            import colorlog
            console_handler = colorlog.StreamHandler()
            console_handler.setFormatter(colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            ))
        except ImportError:
            console_handler = logging.StreamHandler(sys.stdout)

    logger.addHandler(console_handler)

    # File Handler
    file_handler = RotatingFileHandler(
        settings.LOG_FILE, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.INFO) # Always log INFO+ to file
    logger.addHandler(file_handler)
    
    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    
    return logger

logger = setup_logging()
