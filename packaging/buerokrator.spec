# PyInstaller-Spec für Buerokrator (Linux, onedir).
#
# Build (aus dem Repo-Root, venv aktiv):
#     pyinstaller --noconfirm packaging/buerokrator.spec
# Ergebnis: dist/buerokrator/buerokrator
#
# Onedir statt onefile: schnellerer Start, direkt AppImage-/Tarball-tauglich.
# Tesseract und Ollama bleiben Systemabhängigkeiten (siehe todo Schritt 4).

from pathlib import Path

REPO = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(REPO / "packaging" / "entry.py")],
    pathex=[str(REPO)],
    datas=[
        # config._TEMPLATE erwartet die Vorlage unter <Bundle>/config/settings.yaml
        (str(REPO / "config" / "settings.yaml"), "config"),
        # prompt_loader liest relativ zum Modul: <Bundle>/src/classifier/prompts/
        (str(REPO / "src" / "classifier" / "prompts"), "src/classifier/prompts"),
    ],
    hiddenimports=[
        # Seiten werden nur per Import-Nebenwirkung registriert — sicherstellen,
        # dass die Analyse sie mitnimmt.
        "src.frontend.pages.dashboard",
        "src.frontend.pages.document_detail",
        "src.frontend.pages.documents",
        "src.frontend.pages.help_page",
        "src.frontend.pages.import_page",
        "src.frontend.pages.settings",
        "src.frontend.pages.setup_page",
        "src.frontend.pages.tax",
        "src.frontend.pages.trash",
    ],
    excludes=[
        "pytest",
        "selenium",
        # Optionale NiceGUI-Integrationen, die wir nicht nutzen — der
        # nicegui-Hook sammelt sie sonst ein (allein pyarrow ~146 MB).
        "pandas",
        "pyarrow",
        "numpy",
        "altair",
        "plotly",
        "matplotlib",
        "lxml",
    ],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="buerokrator",
    console=True,  # Spike: Konsole für Diagnose; später False + Logdatei
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="buerokrator",
)
