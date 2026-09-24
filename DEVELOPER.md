# Hyperion — руководство разработчика

## Структура проекта

```text
Hyperion/
├── VERSION                    # Единый источник версии
├── run.py                     # Точка входа для разработки
├── logo.ico                   # Иконка приложения
├── config.example.json        # Пример конфигурации
├── requirements.txt           # Runtime-зависимости
├── requirements-build.txt     # Инструменты сборки и проверок
├── pyproject.toml              # Настройки проекта и Ruff
├── src/hyperion/
│   ├── main.py                 # Запуск приложения
│   ├── version.py              # Версия в dev/frozen-среде
│   ├── runtime/                # WinAPI hook, state machine, process monitor и SendInput
│   ├── services/               # JSON, single-instance, геометрия и локализация
│   └── ui/                     # Главное окно, One Dark и профильные mixin-модули
├── tests/                      # Автоматические тесты
└── Build_Tools/
    ├── Hyperion.spec           # PyInstaller onedir-конфигурация
    ├── file_version_info.txt   # Windows metadata EXE
    ├── post_build.py           # Проверка и перенос сборки без запуска EXE
    ├── build_installer.py      # Headless-сборка установщика Inno Setup
    ├── deploy_portable.py      # Обновление portable-каталога
    └── SpecCompiler.pyw        # Необязательный GUI-компилятор
```

Ключевые изменения архитектуры: вся отправка синтетического ввода проходит через
один FIFO-диспетчер, foreground-процесс кэшируется вне low-level hook callback,
JSON записывается атомарно, а повреждённые файлы сохраняются как `*.corrupt-*`.
Watchdog периодически переустанавливает hook, так как Windows не сообщает о его
тихом снятии по `LowLevelHooksTimeout`. Именованный Win32 mutex запрещает второй
экземпляр приложения. Главное окно разделено на runtime-, settings- и keys-mixin-модули.

## Локальное окружение

Используйте только виртуальное окружение проекта:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe run.py
```

Поддерживаемое окружение: Windows 10/11 x64, Python 3.12, PySide6 6.11.1,
PyInstaller 6.21.0 и Inno Setup 6 для установщика.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m compileall -q run.py src Build_Tools tests
.\.venv\Scripts\python.exe -m pip check
osv-scanner --lockfile=requirements-build.txt
```

Тесты покрывают CapsLock/Hyper state machine, полный путь hook → Hyper-комбинация,
калибровку, FIFO-отправку, process cache, atomic/corrupt JSON, single-instance,
видимую геометрию окна, lifecycle паузы, таблицу клавиш, автозагрузку,
64-битные WinAPI-структуры и русский перевод стандартных Qt-диалогов.
Те же pytest, Ruff и `pip check` выполняются в GitHub Actions на Windows/Python 3.12.

## Сборка

Сборка выполняется без открытия GUI и автоматического запуска приложения.
PyInstaller получает минимальный доверенный `PATH`; `.spec` останавливает сборку,
если источник бинарной библиотеки находится вне проекта, Python, виртуального
окружения или Windows. Корневой комплект MSVC runtime берётся целиком из PySide6.
До `post_build.py` проверьте `COLLECT-00.toc` и выполните неинтерактивную
frozen-проверку импорта Qt-модулей.

```powershell
# Перед PyInstaller явно удалить старую корневую папку .\Hyperion,
# предварительно проверив, что разрешённый путь находится внутри репозитория.
.\.venv\Scripts\python.exe -m PyInstaller .\Build_Tools\Hyperion.spec --clean --noconfirm --distpath .\Build_Tools\dist --workpath .\Build_Tools\build
.\.venv\Scripts\python.exe .\Build_Tools\post_build.py
```

`post_build.py` проверяет результат, переносит его в корневую папку `Hyperion`,
добавляет документацию и юридические уведомления, формирует runtime manifest и
удаляет временные каталоги PyInstaller. Он не запускает `Hyperion.exe`.

После проверки корневой сборки можно создать установщик и обновить portable-копию:

```powershell
.\.venv\Scripts\python.exe .\Build_Tools\build_installer.py
.\.venv\Scripts\python.exe .\Build_Tools\deploy_portable.py
```

Установщик создаётся на реальном рабочем столе. Portable-копия обновляется в
`D:\Portable_soft\Hyperion` с сохранением пользовательских `config.json` и
`settings.json`. Приложение и установщик автоматически не запускаются.

## Версионирование и релиз

Версия хранится в `VERSION`; `version.py` автоматически находит её в исходном и
замороженном приложении. Полный локальный релизный цикл:

1. Обновить `VERSION`, `Build_Tools/file_version_info.txt`, release notes и документацию.
2. Выполнить тесты, Ruff, compileall, `pip check` и аудит зависимостей.
3. Создать один release-коммит и два тега: `vX.Y.Z` и следующий свободный числовой тег.
4. Явно очистить старую корневую сборку, выполнить PyInstaller и `post_build.py`.
5. Создать установщик и обновить portable-каталог без запуска артефактов.
6. Выполнить dry-run orphan-публикации и приватное резервное копирование.
7. Только после отдельного подтверждения опубликовать orphan-ветку на GitHub.

Архив portable-версии в стандартный процесс не входит.
