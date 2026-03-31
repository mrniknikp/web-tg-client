"""
Скрипт для создания .exe файла Telegram Web Desktop Application
Запускать на Windows машине с установленным Python

Требования:
    pip install flask pysocks requests pyinstaller pywebview
"""

import PyInstaller.__main__
import os
import shutil

# Очистка предыдущих сборок
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

print("=" * 60)
print("Telegram Web Desktop - Создание EXE файла")
print("=" * 60)

PyInstaller.__main__.run([
    'app.py',
    '--name=TelegramWebDesktop',
    '--onefile',
    '--windowed',  # Без консольного окна (для GUI приложения)
    '--icon=NONE',  # Можно добавить свою иконку
    '--add-data=templates;templates',
    '--add-data=static;static',
    '--hidden-import=flask',
    '--hidden-import=socket',
    '--hidden-import=ssl',
    '--hidden-import=threading',
    '--hidden-import=webview',
    '--hidden-import=ctypes',
    '--hidden-import=platform',
    '--clean',
    '--noconfirm',
])

print("\n" + "=" * 60)
print("Сборка завершена!")
print("EXE файл находится в папке: dist/TelegramWebDesktop.exe")
print("=" * 60)
print("\nДля запуска просто откройте TelegramWebDesktop.exe")
print("Приложение откроется в собственном окне, а не в браузере!")
print("=" * 60)
