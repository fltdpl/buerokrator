"""Wache gegen Echtdaten in versionierten Dateien.

Das Repo ist öffentlich; die Projektregel lautet „Zahlen und Namen in Tests
immer erfinden" (AGENT_CONTEXT.md). Diese Wache prüft, was sich maschinell
prüfen lässt: Kennzeichen-MUSTER, die praktisch nur aus echten Belegen
stammen (maskierte Kartennummern, IBANs, Steuer-IDs).

Bewusste Grenze: Anbieter- und Personennamen erkennt sie NICHT — dafür gibt
es keine verlässliche Signatur, und eine Sperrliste echter Namen würde genau
die Daten ins öffentliche Repo schreiben, die sie schützen soll. Namen
bleiben Sache des Datenschutz-Checks vor dem Commit.
"""

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Jedes Muster: (Name für die Fehlermeldung, kompiliertes Regex).
PATTERNS = (
    (
        "maskierte Kartennummer (BIN + Endziffern, PCI-Schema)",
        re.compile(r"\d{6}[X*x]{4,}\d{4}"),
    ),
    (
        "vollständige deutsche IBAN",
        re.compile(r"\bDE\d{2}[ ]?(?:\d{4}[ ]?){4}\d{2}\b"),
    ),
    (
        "16-stellige Kartennummer",
        re.compile(r"\b(?:\d{4}[ -]){3}\d{4}\b"),
    ),
    (
        "Steuer-Identifikationsnummer (11 Ziffern)",
        re.compile(r"\bSteuer-?ID\D{0,20}\d{11}\b", re.IGNORECASE),
    ),
)

# Textdateien, die überhaupt Prosa/Testdaten enthalten können.
SUFFIXES = {".py", ".md", ".txt", ".yaml", ".yml", ".json", ".sh", ".cfg", ".ini"}


def _tracked_text_files():
    """Von Git verfolgte Textdateien — nur die landen im öffentlichen Repo."""
    output = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    for name in output.split("\0"):
        if not name:
            continue

        path = REPO / name
        if path.suffix.lower() in SUFFIXES and path.is_file():
            yield path


def test_keine_echtdaten_muster_in_versionierten_dateien():
    own_path = Path(__file__).resolve()
    findings = []

    for path in _tracked_text_files():
        # Diese Datei enthält die Muster selbst.
        if path.resolve() == own_path:
            continue

        try:
            content = path.read_text(encoding="utf-8")

        except (UnicodeDecodeError, OSError):
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    relative = path.relative_to(REPO)
                    findings.append(f"{relative}:{line_number}: {label}")

    assert not findings, "Mögliche Echtdaten im öffentlichen Repo:\n" + "\n".join(
        findings
    )


def test_wache_erkennt_die_muster():
    """Gegenprobe: die Wache darf nicht still immer grün sein."""
    samples = (
        "account_number = '123456XXXXXX7890'",
        "iban = 'DE12 3456 7890 1234 5678 90'",
        "iban = 'DE12345678901234567890'",
        "karte = '1234 5678 9012 3456'",
        "Steuer-ID: 12345678901",
    )

    for sample in samples:
        assert any(
            pattern.search(sample) for _, pattern in PATTERNS
        ), f"kein Muster greift auf: {sample}"
