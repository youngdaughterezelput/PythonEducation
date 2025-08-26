@echo off
chcp 1251 > nul
SETLOCAL EnableDelayedExpansion

:: ========================
:: Настройки кодировки
:: ========================
reg add "HKCU\Console\%~nx0" /v "FaceName" /t REG_SZ /d "Lucida Console" /f > nul 2>&1
reg add "HKCU\Console\%~nx0" /v "CodePage" /t REG_DWORD /d 1251 /f > nul 2>&1

:: ========================
:: Проверка зависимостей
:: ========================
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ОШИБКА] Python не найден в системе.
    echo.
    choice /c YN /m "Хотите установить Python автоматически? (Y/N)"
    if %ERRORLEVEL% equ 1 (
        echo Установка Python...
        :: Скачиваем установщик Python
        curl -o python_installer.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
        
        if exist python_installer.exe (
            echo Запуск установки Python...
            start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
            del python_installer.exe
            echo.
            echo Установка завершена. Пожалуйста, перезапустите скрипт.
        ) else (
            echo.
            echo [ОШИБКА] Не удалось скачать установщик Python
            echo Установите Python 3.11 вручную с https://www.python.org/downloads/
        )
        pause
        exit /b
    ) else (
        echo.
        echo Установите Python 3.11 вручную с https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

:: Проверка версии Python
for /f "tokens=2 delims= " %%A in ('python --version 2^>^&1') do set "python_version=%%A"
echo Обнаружен Python версии !python_version!

:: Проверка наличия PyInstaller
python -m PyInstaller --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ИНФО] PyInstaller не найден.
    echo.
    choice /c YN /m "Хотите установить PyInstaller автоматически? (Y/N)"
    if %ERRORLEVEL% equ 1 (
        echo Установка PyInstaller...
        python -m pip install --upgrade pip
        python -m pip install --upgrade pyinstaller
        python -m pip install pyinstaller-hooks-contrib==2024.8
    ) else (
        echo.
        echo Установите PyInstaller вручную командой: python -m pip install pyinstaller
        pause
        exit /b 1
    )
)

:: Установка всех необходимых библиотек
echo.
echo Установка зависимостей из requirements.txt...
if exist "requirements.txt" (
    python -m pip install -r requirements.txt
) else (
    echo [ИНФО] Файл requirements.txt не найден, устанавливаем основные зависимости...
    python -m pip install tkinter matplotlib requests pandas python-dotenv tkcalendar
)

:: ========================
:: Проверка необходимых файлов
:: ========================
if not exist "icon.ico" (
    echo.
    echo [ОШИБКА] Файл icon.ico не найден в текущей директории
    pause
    exit /b 1
)

if not exist "main.py" (
    echo.
    echo [ОШИБКА] Файл main.py не найден в текущей директории
    pause
    exit /b 1
)

:: ========================
:: Процесс сборки
:: ========================
echo.
echo Очистка предыдущих сборок...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del *.spec

echo.
echo Компиляция приложения...
python -m PyInstaller --onefile --windowed ^
    --add-data "icon.ico;." ^
    --icon=icon.ico ^
    --name=HF_GUI ^
    --hidden-import=tkinter ^
    --hidden-import=matplotlib ^
    --hidden-import=requests ^
    --hidden-import=pandas ^
    --hidden-import=dotenv ^
    --hidden-import=tkcalendar ^
    --hidden-import=webbrowser ^
    --hidden-import=logging ^
    --hidden-import=json ^
    --hidden-import=os ^
    --hidden-import=re ^
    --hidden-import=urllib.parse ^
    --hidden-import=datetime ^
    --hidden-import=html ^
    --hidden-import=csv ^
    --collect-all ldap3 ^
    --collect-all matplotlib.backends.backend_tkagg ^
    main.py

:: ========================
:: Проверка результата
:: ========================
if exist "dist\HF_GUI.exe" (
    echo.
    echo ========================================
    echo СБОРКА УСПЕШНО ЗАВЕРШЕНА!
    echo Скомпилированный файл: dist\HF_GUI.exe
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ОШИБКА ПРИ СБОРКЕ!
    echo ========================================
    echo Проверьте лог сборки в файле build\HF_GUI\warn-HF_GUI.txt
)

:: Открытие папки с результатом
if exist "dist" explorer.exe dist

pause