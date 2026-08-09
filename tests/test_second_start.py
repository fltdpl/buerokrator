"""Zweitstart-Verhalten: laufende Instanz öffnen statt stumm sterben.

src.frontend.main wird bewusst erst IN den Tests importiert: pytest
importiert beim Einsammeln alle Testmodule, und ein Modul-Import von main
verstellt die App-Registrierung der User-Fixture-Tests (frontend_smoke).
"""

import http.server
import sys
import threading

import pytest


@pytest.fixture(autouse=True)
def main_nicht_in_sys_modules_zuruecklassen():
    """Räumt src.frontend.main nach jedem Test wieder aus sys.modules.

    Sonst zahlt JEDES alphabetisch nachfolgende Modul mit User-Fixture den
    Preis: die Fixture baut die App neu auf und importiert main erneut —
    ein Modul, das schon in sys.modules liegt, wird dabei nicht noch einmal
    ausgeführt, die @ui.page-Dekoratoren laufen also nicht, und alle Seiten
    antworten mit 404. Der Import in den Test zu verlegen (siehe Docstring)
    verhindert nur den Schaden beim Einsammeln, nicht diesen.

    Es reicht NICHT, nur main zu entfernen: die Dekoratoren stehen in den
    Seitenmodulen (src.frontend.pages.*), und die bleiben sonst geladen.
    """
    yield

    for name in [
        name for name in sys.modules if name == "src.frontend" or name.startswith("src.frontend.")
    ]:
        del sys.modules[name]


def _main():
    import src.frontend.main as main

    return main


@pytest.fixture
def fake_server():
    """Lokaler HTTP-Server auf freiem Port; liefert den konfigurierten Body."""
    state = {"body": b""}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(state["body"])

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield state, server.server_address[1]

    server.shutdown()


def test_free_port_reports_frei(monkeypatch):
    main = _main()
    # Reservieren-und-schließen: der Port ist danach mit hoher
    # Wahrscheinlichkeit unbelegt.
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        free_port = sock.getsockname()[1]

    monkeypatch.setattr(main, "PORT", free_port)

    assert main._port_status() == "frei"


def test_running_buerokrator_is_recognized(monkeypatch, fake_server):
    main = _main()
    state, port = fake_server
    state["body"] = b"<html><title>Dashboard - Buerokrator</title></html>"
    monkeypatch.setattr(main, "PORT", port)

    assert main._port_status() == "buerokrator"


def test_foreign_service_is_not_claimed(monkeypatch, fake_server):
    main = _main()
    state, port = fake_server
    state["body"] = b"<html>Anderes Programm</html>"
    monkeypatch.setattr(main, "PORT", port)

    assert main._port_status() == "fremd"


def test_run_opens_browser_instead_of_second_instance(monkeypatch, fake_server):
    main = _main()
    state, port = fake_server
    state["body"] = b"Buerokrator"
    monkeypatch.setattr(main, "PORT", port)
    # Der Port-Check ist unter pytest deaktiviert (Smoke-Tests) — hier
    # testen wir genau ihn, also Markierung entfernen.
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    opened = []
    monkeypatch.setattr(main.webbrowser, "open", opened.append)
    monkeypatch.setattr(
        main.ui,
        "run",
        lambda **kwargs: pytest.fail("ui.run darf nicht starten"),
    )

    main.run()

    assert opened == [f"http://127.0.0.1:{port}"]


def test_run_aborts_on_foreign_service(monkeypatch, fake_server):
    main = _main()
    state, port = fake_server
    state["body"] = b"<html>Anderes Programm</html>"
    monkeypatch.setattr(main, "PORT", port)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        main.ui,
        "run",
        lambda **kwargs: pytest.fail("ui.run darf nicht starten"),
    )

    with pytest.raises(SystemExit):
        main.run()
