import os
import logging
from abc import ABC, abstractmethod
from datetime import datetime

class BaseReport(ABC):
    def __init__(self):
        self.report_type = self.__class__.__name__.replace('Report', '').lower()
        self.report_name = self.report_type  # По умолчанию название = тип
        
    @abstractmethod
    def generate(self, report_date: datetime) -> tuple:
        """Генерирует отчет и возвращает (filename, has_data)"""
        pass
    
    def get_report_type(self) -> str:
        return self.report_type
        
    def get_report_name(self) -> str:
        return self.report_name