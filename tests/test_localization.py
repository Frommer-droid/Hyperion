from PySide6.QtCore import QLocale

from hyperion.services import localization


def test_set_russian_qt_locale():
    previous = QLocale()
    try:
        localization.set_russian_qt_locale()
        assert QLocale().language() == QLocale.Language.Russian
    finally:
        QLocale.setDefault(previous)
