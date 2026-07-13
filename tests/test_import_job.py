import pytest

from src.services import import_job


@pytest.fixture(autouse=True)
def reset_state():
    import_job._reset_for_tests()
    yield
    import_job._reset_for_tests()


def test_initial_state_is_idle():
    state = import_job.get_state()

    assert state["running"] is False
    assert state["result"] is None


def test_start_sets_running_and_clears_previous_result():
    import_job.finish(["a"], [], [])
    import_job.start()

    state = import_job.get_state()
    assert state["running"] is True
    assert state["result"] is None
    assert state["index"] == 0
    assert state["total"] == 0


def test_start_twice_raises():
    import_job.start()

    with pytest.raises(RuntimeError):
        import_job.start()


def test_update_progress_and_finish():
    import_job.start()
    import_job.update_progress(1, 3, "beleg.pdf")

    state = import_job.get_state()
    assert (state["index"], state["total"], state["current_filename"]) == (
        1,
        3,
        "beleg.pdf",
    )

    import_job.finish(["ok"], ["dup"], ["fail"])

    state = import_job.get_state()
    assert state["running"] is False
    assert state["result"] == {
        "succeeded": ["ok"],
        "duplicates": ["dup"],
        "failed": ["fail"],
    }


def test_clear_result():
    import_job.finish([], [], [])
    import_job.clear_result()

    assert import_job.get_state()["result"] is None


def test_abort_frees_job_and_stores_error():
    import_job.start()
    import_job.abort(RuntimeError("OCR kaputt"))

    state = import_job.get_state()
    # Kern des Fixes: running wird freigegeben, sonst blockiert jeder
    # weitere Import bis zum App-Neustart.
    assert state["running"] is False
    assert state["result"] is None
    assert "OCR kaputt" in state["error"]

    # Neuer Lauf ist sofort wieder möglich und löscht den Fehler.
    import_job.start()
    assert import_job.get_state()["error"] is None


def test_clear_result_also_clears_error():
    import_job.start()
    import_job.abort("Fehler")
    import_job.clear_result()

    assert import_job.get_state()["error"] is None


def test_get_state_returns_a_copy():
    state = import_job.get_state()
    state["running"] = True

    assert import_job.get_state()["running"] is False
