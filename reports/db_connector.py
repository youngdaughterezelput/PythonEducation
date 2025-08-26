import os
import psycopg2
from typing import Dict, List, Tuple

class DatabaseConnector:
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.connection = None
        self.db_config = self._load_config()

    def _load_config(self) -> Dict:
        # Получаем значения из переменных окружения
        host = os.getenv(f'{self.prefix}_DB_HOST', 'localhost')
        port = os.getenv(f'{self.prefix}_DB_PORT', '5432')
        
        # Явно указываем использование TCP/IP соединения
        # Если хост не указан, используем localhost
        if not host or host.strip() == '':
            host = 'localhost'
        
        return {
            'dbname': os.getenv(f'{self.prefix}_DB_NAME'),
            'user': os.getenv(f'{self.prefix}_DB_USER'),
            'password': os.getenv(f'{self.prefix}_DB_PASSWORD'),
            'host': host,
            'port': port
        }

    def connect(self):
        """Устанавливает соединение с базой данных"""
        try:
            # Явно указываем использование TCP/IP соединения
            self.connection = psycopg2.connect(**self.db_config)
            return True
        except psycopg2.Error as e:
            raise Exception(f"Ошибка подключения к БД {self.prefix}: {str(e)}")

    def execute_query(self, query: str, params: Tuple = None) -> List[Tuple]:
        """Выполняет SQL-запрос и возвращает результаты"""
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except psycopg2.Error as e:
            raise Exception(f"Ошибка выполнения запроса: {str(e)}")

    def load_payment_types(self) -> Dict[str, str]:
        """Загружает типы оплаты"""
        if self.prefix == "PAYSET":
            query = """
                SELECT payment_type_id, payment_type_name 
                FROM paysetat.payment_type 
                ORDER BY payment_type_id
            """
        else:
            raise ValueError(f"Неизвестный префикс для загрузки типов оплаты: {self.prefix}")
            
        results = self.execute_query(query)
        return {row[0]: row[1] for row in results}

    def load_delivery_types(self) -> Dict[str, str]:
        """Загружает типы доставки"""
        if self.prefix == "DEL_ATOM":
            query = """
                SELECT delivery_type_id, name 
                FROM dlvatomc.delivery_type 
                ORDER BY delivery_type_id
            """
        else:
            raise ValueError(f"Неизвестный префикс для загрузки типов доставки: {self.prefix}")
            
        results = self.execute_query(query)
        return {row[0]: row[1] for row in results}

    def close(self):
        if self.connection:
            self.connection.close()