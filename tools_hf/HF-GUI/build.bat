@echo off
chcp 1251 > nul
SETLOCAL EnableDelayedExpansion

:: ========================
:: ��������� ���������
:: ========================
reg add "HKCU\Console\%~nx0" /v "FaceName" /t REG_SZ /d "Lucida Console" /f > nul 2>&1
reg add "HKCU\Console\%~nx0" /v "CodePage" /t REG_DWORD /d 1251 /f > nul 2>&1

:: ========================
:: �������� ������������
:: ========================
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo [������] Python �� ������ � �������.
    echo.
    choice /c YN /m "������ ���������� Python �������������? (Y/N)"
    if %ERRORLEVEL% equ 1 (
        echo ��������� Python...
        :: ��������� ���������� Python
        curl -o python_installer.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
        
        if exist python_installer.exe (
            echo ������ ��������� Python...
            start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
            del python_installer.exe
            echo.
            echo ��������� ���������. ����������, ������������� ������.
        ) else (
            echo.
            echo [������] �� ������� ������� ���������� Python
            echo ���������� Python 3.11 ������� � https://www.python.org/downloads/
        )
        pause
        exit /b
    ) else (
        echo.
        echo ���������� Python 3.11 ������� � https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

:: �������� ������ Python
for /f "tokens=2 delims= " %%A in ('python --version 2^>^&1') do set "python_version=%%A"
echo ��������� Python ������ !python_version!

:: �������� ������� PyInstaller
python -m PyInstaller --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo [����] PyInstaller �� ������.
    echo.
    choice /c YN /m "������ ���������� PyInstaller �������������? (Y/N)"
    if %ERRORLEVEL% equ 1 (
        echo ��������� PyInstaller...
        python -m pip install --upgrade pip
        python -m pip install --upgrade pyinstaller
        python -m pip install pyinstaller-hooks-contrib==2024.8
    ) else (
        echo.
        echo ���������� PyInstaller ������� ��������: python -m pip install pyinstaller
        pause
        exit /b 1
    )
)

:: ��������� ���� ����������� ���������
echo.
echo ��������� ������������ �� requirements.txt...
if exist "requirements.txt" (
    python -m pip install -r requirements.txt
) else (
    echo [����] ���� requirements.txt �� ������, ������������� �������� �����������...
    python -m pip install tkinter matplotlib requests pandas python-dotenv tkcalendar
)

:: ========================
:: �������� ����������� ������
:: ========================
if not exist "icon.ico" (
    echo.
    echo [������] ���� icon.ico �� ������ � ������� ����������
    pause
    exit /b 1
)

if not exist "main.py" (
    echo.
    echo [������] ���� main.py �� ������ � ������� ����������
    pause
    exit /b 1
)

:: ========================
:: ������� ������
:: ========================
echo.
echo ������� ���������� ������...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del *.spec

echo.
echo ���������� ����������...
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
:: �������� ����������
:: ========================
if exist "dist\HF_GUI.exe" (
    echo.
    echo ========================================
    echo ������ ������� ���������!
    echo ���������������� ����: dist\HF_GUI.exe
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ������ ��� ������!
    echo ========================================
    echo ��������� ��� ������ � ����� build\HF_GUI\warn-HF_GUI.txt
)

:: �������� ����� � �����������
if exist "dist" explorer.exe dist

pause