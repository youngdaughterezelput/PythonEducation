import tkinter as tk

class MainMenu:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.menu_bar = tk.Menu(root)
        self._setup_menu()
    
    def _setup_menu(self):
        """Настройка структуры меню"""
        self.root.option_add("*tearOff", tk.FALSE)
        self._create_file_menu()
        self._create_settings_menu()
        self._add_about_menu()
        self.root.config(menu=self.menu_bar)
    
    def _create_file_menu(self):
        """Меню File"""
        file_menu = tk.Menu(self.menu_bar)
        
        open_submenu = tk.Menu(file_menu)
        open_submenu.add_command(label="Send API-methods", 
                               command=self.controller.open_sendApi)
        open_submenu.add_command(label="OMNI Multy-query", 
                               command=self.controller.openOmniPoint)
        
        open_submenu.add_command(label="Send messeges to Kafka", 
                               command=self.controller.sendKafka)
        
        file_menu.add_cascade(label="Open", menu=open_submenu)
        file_menu.add_command(label="Tools", 
                            command=self.controller.open_tools)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", 
                            command=self.controller.exit_click)
        
        self.menu_bar.add_cascade(label="File", menu=file_menu)
    
    def _create_settings_menu(self):
        """Меню Settings"""
        settings_menu = tk.Menu(self.menu_bar)
        settings_menu.add_command(label="App Settings", 
                                command=self.controller.openSetting)
        self.menu_bar.add_cascade(label="Settings", menu=settings_menu)
    
    def _add_about_menu(self):
        """Меню About с кнопкой проверки обновлений"""
        about_menu = tk.Menu(self.menu_bar)
        about_menu.add_command(label="О программе", command=self.controller.show_about)
        about_menu.add_command(label="Проверить обновления", command=self.controller.check_updates)
        self.menu_bar.add_cascade(label="Справка", menu=about_menu)