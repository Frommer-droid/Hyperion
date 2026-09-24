"""Русская локаль и стандартные переводы Qt."""

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication


RUSSIAN_LOCALE = QLocale(QLocale.Language.Russian, QLocale.Country.Russia)


def set_russian_qt_locale() -> None:
    """Установить русскую локаль до создания QApplication."""
    QLocale.setDefault(RUSSIAN_LOCALE)


def install_russian_qt_translations(app: QApplication) -> bool:
    """Установить qtbase_ru.qm и сохранить translator на всё время жизни app."""
    translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    translator = QTranslator(app)
    loaded = translator.load(RUSSIAN_LOCALE, "qtbase", "_", translations_path)
    if loaded:
        app.installTranslator(translator)

    translators = list(getattr(app, "_hyperion_translators", []))
    translators.append(translator)
    app._hyperion_translators = translators
    return loaded
