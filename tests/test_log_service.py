import logging
import os
import stat

from src.services.log_service import read_log_tail


def write_log(tmp_path):
    log = tmp_path / "buerokrator.log"
    log.write_text(
        "\n".join(
            [
                "2026-07-08 10:00:00,000 - INFO - Start",
                "2026-07-08 10:00:01,000 - ERROR - Kaputt",
                "2026-07-08 10:00:02,000 - INFO - Weiter",
                "2026-07-08 10:00:03,000 - WARNING - Achtung",
            ]
        ),
        encoding="utf-8",
    )
    return log


def test_read_log_tail_newest_first_and_limited(tmp_path):
    log = write_log(tmp_path)

    lines = read_log_tail(max_lines=2, log_file=log)

    assert len(lines) == 2
    assert "Achtung" in lines[0]
    assert "Weiter" in lines[1]


def test_read_log_tail_filters_by_level(tmp_path):
    log = write_log(tmp_path)

    lines = read_log_tail(level="ERROR", log_file=log)

    assert len(lines) == 1
    assert "Kaputt" in lines[0]

    # "ALLE" filtert nicht.
    assert len(read_log_tail(level="ALLE", log_file=log)) == 4


def test_read_log_tail_missing_file(tmp_path):
    assert read_log_tail(log_file=tmp_path / "fehlt.log") == []


def test_testlauf_schreibt_nicht_ins_log_des_nutzers():
    """Der Testlauf darf das echte Log nicht anfassen.

    Im Entwickler-Modus zeigt das App-Home auf das Repo — jeder Testlauf hing
    seine Zeilen an logs/buerokrator.log an, darunter ERROR-Einträge aus
    Fehlerpfad-Tests. Beim Diagnostizieren waren sie von echten Fehlern nicht
    zu unterscheiden.
    """
    from src.core.logger import LOG_FILE
    from src.core.logger import logger as app_logger

    def groesse():
        return LOG_FILE.stat().st_size if LOG_FILE.exists() else 0

    vorher = groesse()
    app_logger.error("Diese Zeile gehört nicht ins Nutzer-Log.")

    assert groesse() == vorher


def test_log_behaelt_eigentuemerrechte_ueber_die_rotation(tmp_path):
    """0600 muss auch die bei der Rotation neu angelegte Datei tragen.

    Das Log enthält Dateinamen (Aussteller, Beträge). Die Rechte einmal beim
    Prozessstart zu setzen genügt nicht: die Rotation legt eine neue Datei an,
    die sonst die umask erbt (verbreitet 0664 — für alle lesbar).
    """
    from src.core.logger import OwnerOnlyRotatingFileHandler

    alte_umask = os.umask(0o002)

    try:
        log_file = tmp_path / "buerokrator.log"
        handler = OwnerOnlyRotatingFileHandler(
            log_file, maxBytes=200, backupCount=1, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(message)s"))

        probe = logging.getLogger("rotationsprobe")
        probe.setLevel(logging.INFO)
        probe.addHandler(handler)

        try:
            for _ in range(20):
                probe.info("x" * 50)

        finally:
            probe.removeHandler(handler)
            handler.close()

        assert (tmp_path / "buerokrator.log.1").exists(), "keine Rotation ausgelöst"

        for datei in (log_file, tmp_path / "buerokrator.log.1"):
            assert stat.S_IMODE(datei.stat().st_mode) == 0o600, datei.name

    finally:
        os.umask(alte_umask)


def test_build_logger_creates_missing_parent_dirs(tmp_path, monkeypatch):
    """Frische Installation: auch das App-Home selbst existiert noch nicht."""
    import src.core.logger as logger_module

    nested = tmp_path / "app_home" / "logs"
    monkeypatch.setattr(logger_module, "LOG_DIR", nested)

    logger_module._build_logger()

    assert nested.is_dir()
