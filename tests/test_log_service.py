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
