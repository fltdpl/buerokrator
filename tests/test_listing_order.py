from src.frontend.listing_order import (
    adjacent_id,
    get_listing_order,
    set_listing_order,
)


def test_adjacent_id_forward_and_backward():
    order = [30, 20, 10]

    assert adjacent_id(order, 30, 1) == 20
    assert adjacent_id(order, 20, 1) == 10
    assert adjacent_id(order, 20, -1) == 30


def test_adjacent_id_edges_and_missing():
    order = [30, 20, 10]

    assert adjacent_id(order, 10, 1) is None
    assert adjacent_id(order, 30, -1) is None
    # Nicht in der Liste -> None (Detail fällt dann auf Standardreihenfolge zurück).
    assert adjacent_id(order, 999, 1) is None


def test_set_and_get_listing_order_normalizes_ints():
    set_listing_order(["3", "2", "1"])

    assert get_listing_order() == [3, 2, 1]
