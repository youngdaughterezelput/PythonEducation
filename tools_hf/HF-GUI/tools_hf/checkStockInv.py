import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import psycopg2
import json
from tkinter.simpledialog import Dialog
from .database_connector import DatabaseConnector

class JsonViewerDialog(Dialog):
    """Диалоговое окно для просмотра JSON"""
    def __init__(self, parent, title, json_data):
        self.json_data = json_data
        super().__init__(parent, title=title)

    def body(self, master):
        self.text = scrolledtext.ScrolledText(master, width=80, height=20, wrap=tk.WORD)
        self.text.pack(fill=tk.BOTH, expand=True)
        self.text.insert(tk.END, json.dumps(self.json_data, indent=4, ensure_ascii=False))
        self.text.config(state=tk.DISABLED)
        return self.text

    def buttonbox(self):
        box = ttk.Frame(self)
        ttk.Button(box, text="Закрыть", command=self.ok).pack(pady=5)
        self.bind("<Return>", self.ok)
        box.pack()

class InvCheck:
    def __init__(self, parent):
        self.parent = parent
        self.window = ttk.Frame(parent)  
        self.window.pack(fill=tk.BOTH, expand=True)
        
        # Подключение к базе данных
        self.db_connector = DatabaseConnector(prefix="INV", parent_window=self.window)
        
        # Основные элементы интерфейса
        self.create_input_section()
        self.create_results_section()
        
        # Привязка событий
        self.setup_event_bindings()
        
        # Проверка подключения к БД
        self.check_db_connection()

    def create_input_section(self):
        """Создает секцию ввода параметров"""
        input_frame = ttk.LabelFrame(self.window, text="Параметры запроса", padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Поле ввода артикула
        ttk.Label(input_frame, text="Артикул:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.item_id_entry = ttk.Entry(input_frame)
        self.item_id_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        
        # Поле ввода БЮ назначения
        ttk.Label(input_frame, text="БЮ назначения:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.bu_destination_entry = ttk.Entry(input_frame)
        self.bu_destination_entry.grid(row=0, column=3, sticky=tk.EW, padx=5, pady=2)
        
        # Комбобокс для типа остатка
        ttk.Label(input_frame, text="Тип остатка:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.stock_type_combobox = ttk.Combobox(input_frame, state="disabled")
        self.stock_type_combobox.grid(row=1, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=2)
        
        # Кнопки управления
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=5)
        
        ttk.Button(button_frame, text="Проверить остатки", command=self.execute_query).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        
        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(3, weight=1)

    def create_results_section(self):
        """Создает секцию вывода результатов"""
        results_frame = ttk.LabelFrame(self.window, text="Результаты запроса", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Таблица для отображения результатов
        self.tree = ttk.Treeview(results_frame, selectmode="extended")
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Полосы прокрутки
        v_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Контекстное меню для JSON полей
        self.json_context_menu = tk.Menu(self.tree, tearoff=0)
        self.json_context_menu.add_command(label="Просмотр JSON", command=self.view_json_data)
        
        self.tree.bind("<Button-3>", self.show_json_context_menu)

    def setup_event_bindings(self):
        """Настраивает привязки событий"""
        self.item_id_entry.bind("<FocusOut>", self.load_stock_types)
        self.bu_destination_entry.bind("<FocusOut>", self.load_stock_types)

    def show_json_context_menu(self, event):
        """Показывает контекстное меню для JSON полей"""
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        
        if item and col:
            column_name = self.tree.heading(col)["text"]
            if column_name in ["delivery", "pickup", "showroom"]:
                self.tree.selection_set(item)
                self.json_context_menu.post(event.x_root, event.y_root)

    def view_json_data(self):
        """Отображает JSON данные в диалоговом окне"""
        selected_item = self.tree.selection()
        if not selected_item:
            return
            
        item = selected_item[0]
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        column_name = self.tree.heading(col)["text"]
        
        if column_name in ["delivery", "pickup", "showroom"]:
            json_data = self.tree.item(item, "values")[int(col[1:])-1]
            try:
                parsed_json = json.loads(json_data)
                JsonViewerDialog(self.parent, f"Просмотр {column_name}", parsed_json)
            except json.JSONDecodeError:
                messagebox.showerror("Ошибка", "Невозможно разобрать JSON данные")

    def check_db_connection(self):
        """Проверяет подключение к базе данных"""
        if not self.db_connector.check_connection(self.window):
            messagebox.showwarning("Предупреждение", "Подключение к базе данных не установлено!")
            return False
        return True

    def load_stock_types(self, event=None):
        """Загружает доступные типы остатков"""
        item_id = self.item_id_entry.get().strip()
        bu_destination = self.bu_destination_entry.get().strip()
        
        if not item_id or not bu_destination or not self.check_db_connection():
            self.stock_type_combobox["state"] = "disabled"
            self.stock_type_combobox["values"] = []
            return
            
        try:
            query = """
            SELECT DISTINCT stock_type 
            FROM invnatom.remains 
            WHERE item_id = %s
            AND business_unit_destination = %s
            """
            
            results = self.db_connector.execute_query(query, (item_id, bu_destination))
            stock_types = [row[0] for row in results]
            
            if stock_types:
                self.stock_type_combobox["values"] = stock_types
                self.stock_type_combobox["state"] = "readonly"
                self.stock_type_combobox.current(0)
            else:
                self.stock_type_combobox["state"] = "disabled"
                self.stock_type_combobox["values"] = []
                messagebox.showinfo("Информация", f"Для артикула {item_id} и БЮ {bu_destination} не найдены типы остатков")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке типов остатков: {str(e)}")

    def execute_query(self):
        """Выполняет запрос к базе данных"""
        if not self.check_db_connection():
            return

        item_id = self.item_id_entry.get().strip()
        bu_destination = self.bu_destination_entry.get().strip()
        stock_type = self.stock_type_combobox.get()

        if not item_id or not bu_destination:
            messagebox.showwarning("Ошибка", "Введите артикул и БЮ назначения!")
            return

        try:
            # Основной запрос
            query = """
            SELECT 
                r.item_id,
                r.stock_type,
                r.delivery::text,
                r.pickup::text,
                r.showroom::text,
                ROUND((r.delivery::json->0->>'remain')::NUMERIC),
                r.ecom_status,
                i.item_type,
                i.invent_style_id,
                r.site_text
            FROM invnatom.remains r
            JOIN invnatom.inventory i ON i.item_id = r.item_id
            WHERE r.item_id = %s
            AND r.business_unit_destination = %s
            """
            
            params = [item_id, bu_destination]
            
            if stock_type:
                query += " AND r.stock_type = %s"
                params.append(stock_type)
            
            query += " ORDER BY r.stock_type"
            
            # Очищаем предыдущие результаты
            self.clear_results()
            
            # Выполняем запрос
            results = self.db_connector.execute_query(query, params)
            
            if not results:
                messagebox.showinfo("Информация", "Данные не найдены")
                return
            
            # Настраиваем колонки таблицы
            columns = (
                "Артикул", "Тип остатка", "delivery", "pickup", "showroom",
                "Остаток", "Статус", "Тип товара", "Стиль", "Описание"
            )
            
            self.tree["columns"] = columns
            for col in columns:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=100, anchor=tk.W, stretch=True)  # Добавлен stretch=True
            
            # Заполняем таблицу данными
            for row in results:
                self.tree.insert("", tk.END, values=row)
            
            # Автоматически подбираем ширину колонок
            for col in columns:
                max_width = tk.font.Font().measure(col)  # Ширина заголовка
                
                # Находим максимальную ширину данных в колонке
                for row in results:
                    value = str(row[columns.index(col)])
                    cell_width = tk.font.Font().measure(value)
                    if cell_width > max_width:
                        max_width = cell_width
                
                # Устанавливаем ширину колонки с небольшим запасом
                self.tree.column(col, width=max_width + 50)
                
            # Разрешаем изменение ширины колонок пользователем
            for col in columns:
                self.tree.column(col, stretch=True)
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка выполнения запроса: {str(e)}")

    def clear_results(self):
        """Очищает результаты запроса"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree["columns"] = []

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Проверка остатков товаров")
    app = InvCheck(root)
    root.mainloop()