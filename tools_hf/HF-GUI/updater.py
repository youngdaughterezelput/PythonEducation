import requests
import json
import tkinter as tk
from tkinter import messagebox
import zipfile
import subprocess
import sys
from threading import Thread
from urllib.parse import urljoin

class Updater:
    def __init__(self, root, current_version):
        self.root = root
        self.current_version = current_version
        self.repo_url = "https://gitlab.hoff.ru/api/v4/projects/Sofiya.Orehova%2Ftools-hf-l2"
        self.releases_url = urljoin(self.repo_url, "/releases")
        self.update_zip = "update.zip"
        self.latest_release = None
        self.update_available = False
        
    def check_for_updates(self, silent=False):
        Thread(target=self._check_updates_thread, args=(silent,), daemon=True).start()
        
    def _check_updates_thread(self, silent=False):
        try:
            headers = {"Private-Token": "YOUR_ACCESS_TOKEN"}  # Замените на реальный токен
            response = requests.get(self.releases_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
                
            releases = response.json()
            self.latest_release = releases[0] if releases else None
                
            if self.latest_release and self.latest_release['tag_name'] != self.current_version:
                self.update_available = True
                if not silent:
                    self.root.after(0, self._show_update_dialog, self.latest_release)
            else:
                if not silent:
                    self.root.after(0, lambda: messagebox.showinfo("Обновления", "Установлена последняя версия"))
                    
        except Exception as e:
            error_msg = f"Ошибка проверки обновлений: {str(e)}"
            print(error_msg)
            if not silent:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", error_msg))
    
    def manual_check_update(self):
        self.check_for_updates(silent=False)
    
    def _show_update_dialog(self, release):
        answer = messagebox.askyesno(
            "Доступно обновление",
            f"Доступна версия {release['tag_name']}\n\nОбновить сейчас?",
            detail=f"Текущая версия: {self.current_version}"
        )
        if answer:
            self._download_update(release)
            
    def _download_update(self, release):
        try:
            asset = next((a for a in release['assets']['links'] if a['name'].endswith('.zip')), None)
            if asset:
                response = requests.get(asset['url'], stream=True)
                with open(self.update_zip, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                self._install_update()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки: {str(e)}")
            
    def _install_update(self):
        try:
            with zipfile.ZipFile(self.update_zip, 'r') as zip_ref:
                zip_ref.extractall("temp_update")
            
            if sys.platform == 'win32':
                subprocess.Popen(["temp_update/build_scripts/install_update.bat"])
            else:
                subprocess.Popen(["sh", "temp_update/build_scripts/install_update.sh"])
            
            self.root.after(1000, self.root.destroy)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка установки: {str(e)}")