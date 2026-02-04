from bot.scanner import _parse_top_ask, compute_edge_bps


def test_parse_top_ask_dict():
    book = {"asks": [{"price": "0.42", "size": "10"}]}
    top = _parse_top_ask(book)
    assert top.price == 0.42
    assert top.size == 10


def test_parse_top_ask_tuple():
    book = {"asks": [[0.25, 3]]}
    top = _parse_top_ask(book)
    assert top.price == 0.25
    assert top.size == 3


def test_compute_edge_bps():
    edge = compute_edge_bps(0.45, 0.45, fee_bps=100, slippage_bps=50)
    assert edge < 1000
