"""Bequemer Start aus der Repo-Wurzel: ``python main.py``.

Gleichwertig zum dokumentierten ``python -m src.frontend.main`` — diese
Datei leitet nur dorthin um.

Der Import steht bewusst INNERHALB von ``__main__``: ``src.frontend.main``
registriert beim Import die NiceGUI-Seiten, und das darf nicht passieren,
wenn ein Werkzeug diese Datei bloß einliest. (Aus demselben Grund zeigt
``main_file`` in pytest.ini auf die echte App-Datei.)
"""

if __name__ == "__main__":
    from src.frontend.main import run

    run()
