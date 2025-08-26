import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

class Logger:
    _instance = None

    # Настройка логирования
    logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger = logging.getLogger(__name__)

    
    def __new__(cls, log_file='app.log', log_level='INFO'):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.logger = logging.getLogger('AppLogger')
            cls._instance.logger.setLevel(log_level)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(module)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=1024*1024*5,  # 5 MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            cls._instance.logger.addHandler(file_handler)
            
        return cls._instance

    @staticmethod
    def log(level, message, class_name=None, method_name=None):
        logger = Logger().logger
        extra = {}
        if class_name:
            extra['module'] = f"{class_name}"
        if method_name:
            extra['module'] = f"{class_name}.{method_name}"
        
        if level == 'DEBUG':
            logger.debug(message, extra=extra)
        elif level == 'INFO':
            logger.info(message, extra=extra)
        elif level == 'WARNING':
            logger.warning(message, extra=extra)
        elif level == 'ERROR':
            logger.error(message, extra=extra)
        elif level == 'CRITICAL':
            logger.critical(message, extra=extra)