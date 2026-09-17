@echo off
echo Limpiando builds anteriores...
rmdir /s /q build
rmdir /s /q dist

echo Instalando dependencias...
pip install -r requirements.txt

echo Construyendo ejecutable con PyInstaller...
python -m PyInstaller --noconsole --onefile --add-data "logos;logos" --add-data "app_icon.ico;." --collect-all customtkinter --icon="app_icon.ico" arbitraje.py

echo.
echo Compilacion terminada. El ejecutable esta en la carpeta dist/
pause

