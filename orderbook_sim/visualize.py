"""
visualize.py

Depth-chart visualization for an OrderBook snapshot, extending the Day 4
lesson (bid/ask bars around the spread) into a reusable plotting function.
"""

import matplotlib.pyplot as plt
from .orderbook import OrderBook


def plot_depth(book: OrderBook, title: str = "Order Book Depth", ax=None):
    """
    Plot a simple depth chart: bid levels (green) to the left of the spread,
    ask levels (red) to the right, bar height = total size resting at that
    price level.
    """
    snap = book.snapshot()
    bid_prices = [lvl["price"] for lvl in snap["bids"]]
    bid_sizes = [sum(sz for _, sz in lvl["orders"]) for lvl in snap["bids"]]
    ask_prices = [lvl["price"] for lvl in snap["asks"]]
    ask_sizes = [sum(sz for _, sz in lvl["orders"]) for lvl in snap["asks"]]

    created_fig = ax is None
    if created_fig:
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor("#0A1416")
        ax.set_facecolor("#0F1C1F")
        for spine in ax.spines.values():
            spine.set_color("#223638")
        ax.tick_params(colors="#E7F1EE")
        ax.xaxis.label.set_color("#E7F1EE")
        ax.yaxis.label.set_color("#E7F1EE")
        ax.title.set_color("#E7F1EE")

    if bid_prices:
        ax.bar(bid_prices, bid_sizes, width=0.005, color="#3FBF7F", label="Bids")
    if ask_prices:
        ax.bar(ask_prices, ask_sizes, width=0.005, color="#F2617A", label="Asks")

    ax.set_xlabel("Price")
    ax.set_ylabel("Resting size")
    ax.set_title(title)
    ax.legend()

    spread = book.spread()
    if spread is not None:
        ax.annotate(
            f"spread = {spread:.2f}",
            xy=((book.best_bid() + book.best_ask()) / 2, max(bid_sizes + ask_sizes, default=1) * 0.95),
            ha="center", fontsize=9, color="#EFA65C",
        )

    if created_fig:
        plt.tight_layout()
        return fig, ax
    return ax
