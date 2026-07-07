from src.core.document_fields import normalize_subtype, whitelist_fields
from src.core.document_types import HOUSING, PENSION, TAX


def test_aliases_map_to_canonical_values():
    assert normalize_subtype(PENSION, "Bauspar-Urkunde") == "contract"
    assert normalize_subtype(PENSION, "Jahreskontoauszug") == "bauspar_jahresauszug"
    assert normalize_subtype(HOUSING, "Nebenkostenabrechnung") == "nebenkostenabrechnung"
    assert normalize_subtype(HOUSING, "Betriebskostenabrechnung") == "nebenkostenabrechnung"


def test_unknown_values_survive_lowercased():
    assert normalize_subtype(PENSION, "Sonderfall XY") == "sonderfall xy"
    assert normalize_subtype(TAX, None) is None
    assert normalize_subtype(TAX, "") == ""


def test_whitelist_normalizes_subtype():
    data = {"issuer": "Debeka", "document_subtype": "Jahreskontoauszug", "interest": 5.0}
    result = whitelist_fields(PENSION, data)
    # Alias wird normalisiert UND das Feldset des Ziel-Subtyps greift
    assert result["document_subtype"] == "bauspar_jahresauszug"
    assert result["interest"] == 5.0


def test_whitelist_housing_keeps_amount():
    data = {"issuer": "Hausverwaltung", "document_subtype": "nebenkostenabrechnung", "amount": 348.0}
    assert whitelist_fields(HOUSING, data)["amount"] == 348.0
