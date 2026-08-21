"""
demo.py

Replays a message stream through the OrderBook, prints the resulting book
state, executes a market order, and saves a depth chart -- end-to-end
demonstration of everything in orderbook_sim.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orderbook_sim.orderbook import OrderBook
from orderbook_sim.visualize import plot_depth
import matplotlib.pyplot as plt


def main():
    book = OrderBook()

    messages = [
        {"type": "ADD", "id": "A", "side": "bid", "price": 50.08, "size": 200},
        {"type": "ADD", "id": "B", "side": "bid", "price": 50.08, "size": 150},
        {"type": "ADD", "id": "C", "side": "bid", "price": 50.07, "size": 300},
        {"type": "ADD", "id": "F", "side": "ask", "price": 50.10, "size": 150},
        {"type": "ADD", "id": "G", "side": "ask", "price": 50.10, "size": 100},
        {"type": "ADD", "id": "H", "side": "ask", "price": 50.11, "size": 250},
        {"type": "CANCEL", "id": "B"},
        {"type": "MODIFY", "id": "A", "size": 120},  # decrease, keeps priority
    ]

    print("Replaying message stream...")
    for msg in messages:
        book.apply_message(msg)

    print("\nBook state after messages:")
    snap = book.snapshot()
    for lvl in snap["bids"]:
        print(f"  BID {lvl['price']:.2f}: {lvl['orders']}")
    for lvl in snap["asks"]:
        print(f"  ASK {lvl['price']:.2f}: {lvl['orders']}")
    print(f"\nBest bid: {book.best_bid()}, Best ask: {book.best_ask()}, Spread: {book.spread()}")

    print("\nSending market buy for 300 shares...")
    fills = book.market_order("buy", 300)
    for f in fills:
        print(f"  filled {f['size']} @ {f['price']} from order {f['order_id']}")

    fig, ax = plot_depth(book, title="Book depth after replay + market order")
    out_path = os.path.join(os.path.dirname(__file__), "depth_snapshot.png")
    fig.savefig(out_path, dpi=140, facecolor="#0A1416")
    print(f"\nSaved depth chart to {out_path}")


if __name__ == "__main__":
    main()
