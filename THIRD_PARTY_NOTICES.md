# Сторонние компоненты

## Qt for Python / PySide6 6.11.1

Hyperion использует Qt for Python (PySide6 и Shiboken6), распространяемый Qt
Company на условиях `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`, либо по
коммерческой лицензии Qt.

- Проект: <https://code.qt.io/cgit/pyside/pyside-setup.git/>
- Условия лицензирования: <https://www.qt.io/licensing/open-source-lgpl-obligations>
- Текст LGPL 3.0: <https://www.gnu.org/licenses/lgpl-3.0.html>
- Текст GPL 3.0: <https://www.gnu.org/licenses/gpl-3.0.html>

Файлы Qt/PySide6 остаются отдельными динамическими библиотеками в каталоге
`_internal`, чтобы пользователь мог заменить их совместимой сборкой.

## PyInstaller 6.21.0

PyInstaller используется только для сборки. Bootloader распространяется по
GPL с исключением, разрешающим поставку собранных приложений на иных условиях.

- Проект и лицензия: <https://github.com/pyinstaller/pyinstaller>
