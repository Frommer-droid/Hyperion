<p align="center"><img src="assets/icons/hyperion.png" alt="Hyperion" width="128"></p>
<h1 align="center">Hyperion</h1>
<p align="center">CapsLock как Hyper-модификатор независимо от раскладки клавиатуры.</p>
<p align="center"><a href="README.en.md">English</a> · <a href="https://github.com/Frommer-droid/Hyperion/releases/latest">Последний релиз</a></p>

Hyperion — Windows-приложение с системным треем, калибровкой физических клавиш
и настраиваемыми комбинациями. Короткое нажатие CapsLock сохраняет стандартное
поведение, а удержание вместе с клавишей отправляет Hyper-хоткей.

## Возможности

- `Tap CapsLock` — обычное переключение регистра.
- `Hold CapsLock + клавиша` — `Ctrl+Shift+Alt+Win+VK_A..Z` по умолчанию.
- Символы: `[` `]` `?` `,` `.` `'` `"` `\`.
- Навигация: `Space`, `PgUp`, `PgDown`, `Home`, `End`, `Insert`, стрелки.
- NumPad 0–9 и пользовательские действия F13–F24.
- Работа по scan code независимо от активной раскладки.
- Калибровка и переназначение через GUI.
- Blacklist процессов с индивидуальными переключателями.
- Системный трей, тема One Dark и сохранение геометрии окна.
- Совместимость с инжектированным вводом сторонних макросов.

## Установка

Готовый Windows-установщик доступен на странице
[GitHub Releases](https://github.com/Frommer-droid/Hyperion/releases/latest).

Требования для готовой сборки:

- Windows 10/11 x64;
- права администратора для стандартной установки в `D:\Apps\Hyperion`
  (`C:\Apps\Hyperion`, если дополнительного диска нет).

## Запуск из исходников

Требуется Python 3.11+; для разработки используется Python 3.12.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

## Калибровка

1. Откройте вкладку **Клавиши**.
2. Выберите действие и нажмите **Калибровать**.
3. Нажмите нужную физическую клавишу.
4. При необходимости откройте **Настроить** и выберите F13–F24 с модификаторами.

Калибровка сохраняется автоматически в `config.json` рядом с приложением.
Параметры окна и автозагрузки хранятся отдельно в `settings.json`.

## Разработка

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Архитектура и release-команды описаны в [DEVELOPER.md](DEVELOPER.md), история
изменений — в [RELEASE_NOTES.md](RELEASE_NOTES.md).

## Лицензия

Hyperion распространяется по [MIT License](LICENSE). Уведомления о PySide6/Qt
приведены в [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
