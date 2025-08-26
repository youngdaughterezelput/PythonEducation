@echo off

set "vscode_path=%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"

if exist "%vscode_path%" (
    "%vscode_path%" .
) else (
    echo Не удалось найти VS Code
    echo Попробуйте установить или добавить в PATH
    pause
)
