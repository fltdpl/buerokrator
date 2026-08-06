import logging
import os
from logging.handlers import RotatingFileHandler

from src.core.app_home import get_app_home

# Einmal beim Prozessstart aufgelöst (der Handler hält die Datei offen);
# im Entwickler-Modus ist das wie bisher <repo>/logs.
LOG_DIR = get_app_home() / "logs"
LOG_FILE = LOG_DIR / "buerokrator.log"


class OwnerOnlyRotatingFileHandler(RotatingFileHandler):
    """Rotierender Handler, der 0600 auch nach der Rotation hält.

    Das Log enthält Dateinamen (Aussteller, Beträge). Die Rechte einmal beim
    Prozessstart zu setzen genügt nicht: bei der Rotation entsteht eine NEUE
    Datei, die die umask erbt — bei verbreiteten Einstellungen 0664, also für
    alle lesbar. _open() läuft beim Anlegen und nach jeder Rotation, deshalb
    sitzt der chmod hier.
    """

    def _open(self):
        stream = super()._open()

        try:
            os.chmod(self.baseFilename, 0o600)

        except OSError:
            pass

        return stream


def _configured_level():
    """Log-Level aus config/settings.yaml (logging.level), Fallback INFO.

    Lazy und defensiv: der Logger muss auch dann funktionieren, wenn die
    Config fehlt oder kaputt ist (er wird von fast jedem Modul importiert).
    """
    try:
        from src.core.config import load_config

        name = str(load_config().get("logging", {}).get("level", "INFO"))
        return getattr(logging, name.upper(), logging.INFO)

    except Exception:
        return logging.INFO


def _build_logger():
    # parents=True: bei frischer Installation existiert auch das App-Home
    # (~/.local/share/buerokrator) selbst noch nicht.
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log = logging.getLogger("buerokrator")

    # Idempotent: bei erneutem Aufbau (z. B. Modul-Reload in Tests) keinen
    # zweiten Handler anhängen — sonst doppelte Logzeilen.
    if log.handlers:
        return log

    log.setLevel(_configured_level())

    # Rotation statt endlosem Wachstum: 2 MB pro Datei, 3 Altbestände.
    # Der Handler setzt die Rechte selbst (0600, auch nach der Rotation).
    handler = OwnerOnlyRotatingFileHandler(
        LOG_FILE,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    log.addHandler(handler)

    return log


logger = _build_logger()
