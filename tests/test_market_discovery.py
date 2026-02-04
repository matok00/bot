from bot.market_discovery import _extract_tokens, _parse_markets


def test_extract_tokens_direct_fields():
    market = {"yes_token_id": "1", "no_token_id": "2"}
    yes, no = _extract_tokens(market)
    assert yes == "1"
    assert no == "2"


def test_extract_tokens_outcomes():
    market = {
        "outcomes": [
            {"outcome": "Yes", "token_id": "11"},
            {"outcome": "No", "token_id": "22"},
        ]
    }
    yes, no = _extract_tokens(market)
    assert yes == "11"
    assert no == "22"


def test_parse_markets_shapes():
    assert list(_parse_markets([{ "id": 1 }]))[0]["id"] == 1
    assert list(_parse_markets({"data": [{"id": 2}]}))[0]["id"] == 2
    assert list(_parse_markets({"markets": [{"id": 3}]}))[0]["id"] == 3
