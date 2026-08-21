"""
Tests for OrderBook, tracing directly back to the curriculum's Week 1
worked examples so the results are independently checkable by hand.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orderbook_sim.orderbook import OrderBook


def build_reference_book() -> OrderBook:
    """The exact book used throughout Week 1's lessons."""
    book = OrderBook()
    book.add_limit_order("A", "bid", 50.08, 200)
    book.add_limit_order("B", "bid", 50.08, 150)
    book.add_limit_order("C", "bid", 50.07, 300)
    book.add_limit_order("D", "bid", 50.06, 400)
    book.add_limit_order("E", "bid", 50.06, 100)
    book.add_limit_order("F", "ask", 50.10, 150)
    book.add_limit_order("G", "ask", 50.10, 100)
    book.add_limit_order("H", "ask", 50.11, 250)
    book.add_limit_order("I", "ask", 50.12, 300)
    book.add_limit_order("J", "ask", 50.12, 200)
    return book


def test_best_bid_ask_and_spread():
    book = build_reference_book()
    assert book.best_bid() == 50.08
    assert book.best_ask() == 50.10
    assert round(book.spread(), 2) == 0.02


def test_price_priority_buy_hits_lowest_ask_first():
    book = build_reference_book()
    fills = book.market_order("buy", 200)
    # 150 from F, 50 from G -- price priority (both at 50.10) then FIFO
    assert fills == [
        {"order_id": "F", "price": 50.10, "size": 150},
        {"order_id": "G", "price": 50.10, "size": 50},
    ]


def test_price_priority_sell_hits_highest_bid_first():
    book = build_reference_book()
    fills = book.market_order("sell", 300)
    # A (200) then B (100 of 150) at the best bid, 50.08
    assert fills == [
        {"order_id": "A", "price": 50.08, "size": 200},
        {"order_id": "B", "price": 50.08, "size": 100},
    ]
    assert book.depth_at("bid", 50.08) == 50  # 50 left resting on B


def test_order_walks_multiple_price_levels():
    book = build_reference_book()
    # ask side: 250 @ 50.10, 250 @ 50.11, 500 @ 50.12 = 1000 total
    fills = book.market_order("buy", 400)
    total_filled = sum(f["size"] for f in fills)
    assert total_filled == 400
    prices_touched = {f["price"] for f in fills}
    assert prices_touched == {50.10, 50.11}  # shouldn't have needed to reach 50.12


def test_cancel_removes_order_without_trading():
    book = build_reference_book()
    book.cancel_order("B")
    assert book.depth_at("bid", 50.08) == 200  # only A remains
    fills = book.market_order("sell", 200)
    assert fills == [{"order_id": "A", "price": 50.08, "size": 200}]


def test_modify_size_decrease_keeps_priority():
    book = OrderBook()
    book.add_limit_order("X", "bid", 50.08, 200)
    book.add_limit_order("Y", "bid", 50.08, 100)
    book.modify_order("X", new_size=50)  # decrease -- X should stay first in line
    fills = book.market_order("sell", 60)
    assert fills == [
        {"order_id": "X", "price": 50.08, "size": 50},
        {"order_id": "Y", "price": 50.08, "size": 10},
    ]


def test_modify_size_increase_loses_priority():
    book = OrderBook()
    book.add_limit_order("X", "bid", 50.08, 100)
    book.add_limit_order("Y", "bid", 50.08, 100)
    book.modify_order("X", new_size=300)  # increase -- X should lose priority, go to back
    fills = book.market_order("sell", 150)
    assert fills == [
        {"order_id": "Y", "price": 50.08, "size": 100},
        {"order_id": "X", "price": 50.08, "size": 50},
    ]


def test_modify_price_change_loses_priority():
    book = OrderBook()
    book.add_limit_order("X", "bid", 50.08, 100)
    book.add_limit_order("Y", "bid", 50.07, 100)
    book.modify_order("X", new_price=50.07)  # price change -- goes to back of 50.07's queue
    fills = book.market_order("sell", 150)
    assert fills == [
        {"order_id": "Y", "price": 50.07, "size": 100},
        {"order_id": "X", "price": 50.07, "size": 50},
    ]


def test_queue_ahead():
    book = build_reference_book()
    assert book.queue_ahead("B") == 200  # A (200) is ahead of B at 50.08
    assert book.queue_ahead("A") == 0    # nothing ahead of the first order


def test_message_stream_dispatch_matches_direct_calls():
    book = OrderBook()
    messages = [
        {"type": "ADD", "id": "A", "side": "bid", "price": 50.08, "size": 200},
        {"type": "ADD", "id": "B", "side": "bid", "price": 50.08, "size": 100},
        {"type": "ADD", "id": "C", "side": "ask", "price": 50.10, "size": 150},
        {"type": "CANCEL", "id": "B"},
        {"type": "ADD", "id": "D", "side": "ask", "price": 50.10, "size": 300},
    ]
    for msg in messages:
        book.apply_message(msg)

    assert book.depth_at("bid", 50.08) == 200
    assert book.depth_at("ask", 50.10) == 450


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
