from pathlib import Path
import dotenv
import keyring
import os
from dotenv import load_dotenv

class SecurityManager:
    """Централизованное управление безопасностью и паролями"""
    SERVICE_NAME = "AppSecuritySystem"
    
    @classmethod
    def store_password(cls, key, password, storage='keyring'):
        """Хранение пароля"""
        if storage == 'keyring':
            keyring.set_password(cls.SERVICE_NAME, key, password)
        elif storage == 'env':
            # Записываем значение в .env файл
            dotenv_path = Path('.env')
            dotenv_path.touch()  # Создаем файл если не существует
            
            # ИСПРАВЛЕНИЕ: Правильное сохранение ключа и значения
            dotenv.set_key(dotenv_path, key, password)
    
    @classmethod
    def get_password(cls, key, storage='keyring'):
        """Получение пароля"""
        if storage == 'keyring':
            return keyring.get_password(cls.SERVICE_NAME, key)
        elif storage == 'env':
            # ИСПРАВЛЕНИЕ: Загружаем .env перед получением значения
            dotenv_path = Path('.env')
            if dotenv_path.exists():
                dotenv.load_dotenv(dotenv_path)
            return os.getenv(key)
        return None
    
    @classmethod
    def clear_all_passwords(cls):
        """Очистка всех сохраненных паролей"""
        # Очистка keyring
        for key in keyring.get_password(cls.SERVICE_NAME, None) or []:
            keyring.delete_password(cls.SERVICE_NAME, key)
        
        # Очистка .env файла
        env_path = os.path.join(os.getcwd(), '.env')
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    lines = f.readlines()
                
                # Удаляем строки с паролями
                with open(env_path, 'w') as f:
                    for line in lines:
                        if 'PASS' not in line and 'PASSWORD' not in line:
                            f.write(line)
            except Exception:
                pass
        
        # Очистка переменных окружения
        for key in list(os.environ.keys()):
            if 'PASS' in key or 'PASSWORD' in key:
                os.environ.pop(key, None)
    
    @classmethod
    def clear_credentials(cls, connection_name):
        """Очистка учетных данных для конкретного подключения"""
        keyring.delete_password(cls.SERVICE_NAME, f"{connection_name}_user")
        keyring.delete_password(cls.SERVICE_NAME, f"{connection_name}_pass")