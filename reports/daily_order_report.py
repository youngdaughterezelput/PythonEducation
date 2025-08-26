import os
from datetime import datetime, timedelta
from db_connector import DatabaseConnector
import csv
from base_report import BaseReport

class DailyOrderReport(BaseReport):
    def __init__(self):
        super().__init__()
        self.report_type = "daily"  
        self.payment_conditions = ""
        self.delivery_conditions = ""
        self.excluded_names = """
            исключаем имена
        """
    
    def get_report_type(self):
        return self.report_type
        
    def generate(self, report_date=None):
        if report_date is None:
            report_date = datetime.now() - timedelta(days=1)
        start_date = report_date.strftime("%Y-%m-%d")
        end_date = report_date.strftime("%Y-%m-%d")
        
        # Создаем директорию reports если её нет
        os.makedirs('reports', exist_ok=True)
        
        # Подключение к базам данных
        db_connector = DatabaseConnector("ORDER")
        payset_connector = DatabaseConnector("PAYSET")
        delivery_connector = DatabaseConnector("DEL_ATOM")
        
        # Загрузка условий оплаты и доставки
        self.load_conditions(payset_connector, delivery_connector)
        
        # Формирование и выполнение запроса
        query = self.build_query(start_date, end_date)
        results = db_connector.execute_query(query)
        
        # Обработка результатов
        processed_results = self.process_results(results)
        
        # Сохранение в файл в папке reports
        filename = f"reports/order_report_{start_date}.csv"
        self.save_to_csv(processed_results, filename)
        
        # Закрытие соединений
        db_connector.close()
        payset_connector.close()
        delivery_connector.close()
        
        return filename, len(processed_results) > 0
        
    def load_conditions(self, payset_connector, delivery_connector):
        # Загрузка условий оплаты
        try:
            payment_types = payset_connector.load_payment_types()
            self.payment_conditions = "\n".join([
                f"WHEN '{pt_id}' THEN '{pt_name}'" 
                for pt_id, pt_name in payment_types.items()
            ])
        except:
            self.set_default_payment_conditions()
            
        # Загрузка условий доставки
        try:
            delivery_types = delivery_connector.load_delivery_types()
            self.delivery_conditions = "\n".join([
                f"WHEN '{dt_id}' THEN '{dt_name}'" 
                for dt_id, dt_name in delivery_types.items()
            ])
        except:
            self.set_default_delivery_conditions()
    
    def build_query(self, start_date, end_date):
        return f"""
        WITH FI AS (
            SELECT DISTINCT
                o.order_uid,
                CONCAT_WS(' ',
                    o.order_json->'shipment'->0->'userData'->>'lastName', 
                    o.order_json->'shipment'->0->'userData'->>'firstName'
                ) AS full_name
            FROM ordercmp."order" o
            WHERE 1=1
            AND o.order_status_id = 'CONFIRMED'
            AND '[{start_date}, {end_date}]'::daterange @> o.created_dt::date 
        )
        SELECT DISTINCT
            CASE o.payment_type_id
                {self.payment_conditions}
                ELSE 'Неизвестный способ (' || o.payment_type_id || ')'
            END,
            o.payment_type_id,
            CASE o.delivery_type_id
                {self.delivery_conditions}
                ELSE 'Неизвестный способ (' || o.delivery_type_id || ')'
            END,
            (o.order_json->'shipment'->0->'delivery'->>'pickPointId'),
            (o.order_json->'shipment'->0->>'totalAmountFinal')::numeric,
            o.order_num,
            os.order_status_name,
            o.created_dt::date,
            fi.full_name
        FROM ordercmp."order" o
        JOIN ordercmp.order_status os ON os.order_status_id = o.order_status_id
        LEFT JOIN ordercmp.order_payment op ON op.order_uid = o.order_uid
        JOIN FI fi ON fi.order_uid = o.order_uid
        WHERE 1=1 
            AND fi.full_name NOT IN ({self.excluded_names})
            AND NOT (fi.full_name ~* '.*(тест|test).*')
        ORDER BY o.order_num;
        """
    
    def process_results(self, results):
        seen_orders = set()
        unique_results = []
        
        for row in results:
            order_key = (row[5], row[7])
            if order_key not in seen_orders:
                seen_orders.add(order_key)
                unique_results.append([
                    str(item) if isinstance(item, float) else item 
                    for item in row
                ])
                
        return unique_results
    
    def save_to_csv(self, results, filename):
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                # Заголовки
                writer.writerow([
                    "Способ оплаты", "Код способа оплаты", "Способ получения", 
                    "код ПВЗ//БЮ", "Сумма заказа", "Номер заказа", "Статус", 
                    "Дата заказа", "ФИО"
                ])
                
                # Данные
                for row in results:
                    # Обеспечиваем правильную кодировку для каждой ячейки
                    encoded_row = []
                    for cell in row:
                        if isinstance(cell, str):
                            # Убедимся, что строка в UTF-8
                            try:
                                # Если есть проблемы с кодировкой, пытаемся исправить
                                cell.encode('utf-8')
                            except UnicodeEncodeError:
                                # Пробуем преобразовать из другой кодировки
                                try:
                                    cell = cell.encode('latin-1').decode('utf-8')
                                except:
                                    cell = ''  # Если не получается, оставляем пустым
                        encoded_row.append(cell)
                    writer.writerow(encoded_row)
                    
        except Exception as e:
            print(f"Ошибка при сохранении CSV: {e}")
            raise
    
    def set_default_payment_conditions(self):
        self.payment_conditions = """
            WHEN 'bankCard' THEN 'Банковская карта'
            WHEN 'qrCode' THEN 'Qr-код'
            WHEN 'onDelivery' THEN 'Наличными или при получении'
            WHEN 'yandexSplit' THEN 'Яндекс Сплит'
            WHEN 'sberSplit' THEN 'Сбер Сплит'
            WHEN 'yandexPay' THEN 'Яндекс Пэй'
            WHEN 'jurPerson' THEN 'Выставить счет ЮЛ'
            WHEN 'credit' THEN 'Кредитный брокер'
        """
    
    def set_default_delivery_conditions(self):
        self.delivery_conditions = """
            WHEN '1' THEN 'Самовывоз'
            WHEN '2' THEN 'Доставка курьером'
            WHEN '5' THEN 'Доставка курьером'
            WHEN '4' THEN 'Самовывоз со склада'
            WHEN '8' THEN 'Самовывоз из ПВЗ'
        """