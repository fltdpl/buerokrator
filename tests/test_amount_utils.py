from src.core.amount_utils import normalize_amount


def test_german_format_with_comma():
    assert normalize_amount("1.234,56") == 1234.56
    assert normalize_amount("12.345.678,90") == 12345678.90
    assert normalize_amount("0,50") == 0.5


def test_german_thousands_without_comma():
    # Kritischer Fall aus dem Review: "1.234" ist 1234, nicht 1,234
    # (Faktor-1000-Fehler bei Beträgen).
    assert normalize_amount("1.234") == 1234.0
    assert normalize_amount("12.345") == 12345.0
    assert normalize_amount("12.345.678") == 12345678.0
    assert normalize_amount("-1.234") == -1234.0


def test_english_decimal_stays_decimal():
    # Kein Dreiergruppen-Muster -> englische Dezimalzahl.
    assert normalize_amount("1.23") == 1.23
    assert normalize_amount("1234.56") == 1234.56
    assert normalize_amount("1.2345") == 1.2345


def test_currency_symbols_and_whitespace():
    assert normalize_amount("1.234,56 €") == 1234.56
    assert normalize_amount("42 EUR") == 42.0


def test_passthrough_and_invalid():
    assert normalize_amount(42) == 42.0
    assert normalize_amount(42.5) == 42.5
    assert normalize_amount(None) is None
    assert normalize_amount("") is None
    assert normalize_amount("kein Betrag") is None
