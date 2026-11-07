from decimal import Decimal

import pytest

from market_orderbook import OrderBook, apply_kraken_frame, kraken_checksum


def test_binance_snapshot_and_sequential_depth_updates():
    book = OrderBook("binance_spot", "BTCUSDT", depth=5)
    book.snapshot([["100", "2"], ["99", "3"]], [["101", "4"], ["102", "5"]], update_id=10)
    assert book.apply_binance({"U": 10, "u": 10, "b": [], "a": []}) == "stale_ignored"
    assert book.apply_binance({"U": 11, "u": 12, "b": [["100", "0"], ["98", "7"]],
                               "a": [["101", "6"]]}) == "applied"
    assert book.update_id == 12
    assert Decimal("100") not in book.bids
    assert book.bids[Decimal("98")] == Decimal("7")
    assert book.asks[Decimal("101")] == Decimal("6")


def test_binance_sequence_gap_invalidates_book():
    book = OrderBook("binance_spot", "BTCUSDT")
    book.snapshot([["100", "1"]], [["101", "1"]], update_id=100)
    result = book.apply_binance({"U": 102, "u": 103, "b": [], "a": []})
    assert result == "sequence_gap_resync_required"
    assert book.valid is False
    with pytest.raises(RuntimeError):
        book.analytics()


def test_coinbase_level2_absolute_size_updates_and_deletes():
    book = OrderBook("coinbase_exchange", "BTC-USD")
    book.snapshot([["100", "2"]], [["101", "3"]])
    book.apply_coinbase([["buy", "100", "4"], ["sell", "101", "0"],
                         ["sell", "102", "5"]])
    assert book.bids[Decimal("100")] == Decimal("4")
    assert Decimal("101") not in book.asks
    assert book.asks[Decimal("102")] == Decimal("5")


def test_kraken_documented_crc32_checksum_example():
    bids = [
        ("45283.5", "0.10000000"), ("45283.4", "1.54582015"),
        ("45282.1", "0.10000000"), ("45281.0", "0.10000000"),
        ("45280.3", "1.54592586"), ("45279.0", "0.07990000"),
        ("45277.6", "0.03310103"), ("45277.5", "0.30000000"),
        ("45277.3", "1.54602737"), ("45276.6", "0.15445238"),
    ]
    asks = [
        ("45285.2", "0.00100000"), ("45286.4", "1.54571953"),
        ("45286.6", "1.54571109"), ("45289.6", "1.54560911"),
        ("45290.2", "0.15890660"), ("45291.8", "1.54553491"),
        ("45294.7", "0.04454749"), ("45296.1", "0.35380000"),
        ("45297.5", "0.09945542"), ("45299.5", "0.18772827"),
    ]
    book = OrderBook("kraken_spot", "BTC/USD", depth=25)
    book.snapshot(bids, asks)
    assert kraken_checksum(book.bids, book.asks) == 3310070434


def test_kraken_snapshot_and_checksum_failure_invalidate_book():
    book = OrderBook("kraken_spot", "BTC/USD")
    good = {"channel": "book", "type": "snapshot", "data": [{
        "symbol": "BTC/USD", "bids": [{"price": "100", "qty": "2"}],
        "asks": [{"price": "101", "qty": "3"}], "checksum": 0,
        "timestamp": "2026-11-07T10:00:00Z"
    }]}
    # Deliberately wrong checksum must never produce a trusted book.
    assert apply_kraken_frame(book, good) is False
    assert book.valid is False


def test_orderbook_analytics_spread_imbalance_depth_and_vwap():
    book = OrderBook("coinbase_exchange", "BTC-USD", depth=10)
    book.snapshot([["99", "2"], ["98", "3"]], [["101", "1"], ["102", "4"]])
    stats = book.analytics()
    assert Decimal(stats["best_bid"]) == Decimal("99")
    assert Decimal(stats["best_ask"]) == Decimal("101")
    assert Decimal(stats["mid_price"]) == Decimal("100")
    assert Decimal(stats["spread_bps"]) == Decimal("200")
    assert Decimal(stats["top_level_imbalance"]) == Decimal("1") / Decimal("3")
    buy = book.simulate_market_order("buy", "3")
    assert Decimal(buy["filled_visible_base_quantity"]) == Decimal("3")
    assert Decimal(buy["visible_book_vwap"]) == Decimal("101.3333333333333333333333333")
    assert buy["complete"] is True


def test_book_rejects_crossed_book_and_invalid_quantities():
    book = OrderBook("venue", "X-Y")
    book.snapshot([["102", "1"]], [["101", "1"]])
    with pytest.raises(ValueError, match="Crossed"):
        book.analytics()
    with pytest.raises(ValueError, match="non-negative"):
        book.snapshot([["100", "-1"]], [["101", "1"]])


def test_depth_is_bounded_and_trims_worst_levels():
    book = OrderBook("venue", "X-Y", depth=2)
    book.snapshot([["100", "1"], ["99", "1"], ["98", "1"]],
                  [["101", "1"], ["102", "1"], ["103", "1"]])
    assert len(book.bids) == 2
    assert len(book.asks) == 2


def test_kraken_frame_selects_requested_symbol_from_multi_symbol_message():
    from market_orderbook import apply_kraken_frame

    first = OrderBook("kraken_spot", "BTC/USD", depth=10)
    second = OrderBook("kraken_spot", "ETH/USD", depth=10)
    btc = OrderBook("kraken_spot", "BTC/USD", depth=10)
    btc.snapshot([["100", "2"]], [["101", "3"]])
    btc_checksum = kraken_checksum(btc.bids, btc.asks)
    eth = OrderBook("kraken_spot", "ETH/USD", depth=10)
    eth.snapshot([["200", "4"]], [["201", "5"]])
    eth_checksum = kraken_checksum(eth.bids, eth.asks)
    frame = {"channel": "book", "type": "snapshot", "data": [
        {"symbol": "BTC/USD", "bids": [{"price": "100", "qty": "2"}],
         "asks": [{"price": "101", "qty": "3"}], "checksum": btc_checksum},
        {"symbol": "ETH/USD", "bids": [{"price": "200", "qty": "4"}],
         "asks": [{"price": "201", "qty": "5"}], "checksum": eth_checksum},
    ]}
    assert apply_kraken_frame(first, frame) is True
    assert apply_kraken_frame(second, frame) is True
    assert first.bids[Decimal("100")] == Decimal("2")
    assert second.bids[Decimal("200")] == Decimal("4")


def test_kraken_checksum_verified_incremental_update():
    from market_orderbook import apply_kraken_frame

    book = OrderBook("kraken_spot", "BTC/USD", depth=10)
    initial = OrderBook("kraken_spot", "BTC/USD", depth=10)
    initial.snapshot([["100", "2"]], [["101", "3"]])
    frame = {"channel": "book", "type": "snapshot", "data": [{
        "symbol": "BTC/USD", "bids": [{"price": "100", "qty": "2"}],
        "asks": [{"price": "101", "qty": "3"}],
        "checksum": kraken_checksum(initial.bids, initial.asks)
    }]}
    assert apply_kraken_frame(book, frame) is True
    expected = OrderBook("kraken_spot", "BTC/USD", depth=10)
    expected.snapshot([["100", "2"], ["99", "1"]], [["101", "3"]])
    update = {"channel": "book", "type": "update", "data": [{
        "symbol": "BTC/USD", "bids": [{"price": "99", "qty": "1"}], "asks": [],
        "checksum": kraken_checksum(expected.bids, expected.asks)
    }]}
    assert apply_kraken_frame(book, update) is True
    assert book.bids[Decimal("99")] == Decimal("1")


def test_kraken_wrong_incremental_checksum_invalidates_book():
    from market_orderbook import apply_kraken_frame

    book = OrderBook("kraken_spot", "BTC/USD", depth=10)
    book.snapshot([["100", "2"]], [["101", "3"]])
    frame = {"channel": "book", "type": "update", "data": [{
        "symbol": "BTC/USD", "bids": [{"price": "99", "qty": "1"}],
        "asks": [], "checksum": 123
    }]}
    assert apply_kraken_frame(book, frame) is False
    assert book.valid is False
