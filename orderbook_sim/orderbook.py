"""
orderbook.py

A minimal limit order book implementing price-time priority (FIFO) matching,
built as the Phase 0 capstone project of a self-directed HFT training curriculum.

Core ideas implemented here:
- Price priority: best price always matches first (lowest ask for buys,
  highest bid for sells).
- Time priority (FIFO): among orders at the same price, earliest arrival
  fills first.
- Message-driven updates: the book state is built and changed entirely by
  applying a stream of ADD / CANCEL / MODIFY / TRADE events, not by starting
  from a static table.
- Modify semantics: a size *decrease* keeps queue priority; a size increase
  or any price change loses priority and is treated as a new order.

This is a teaching/portfolio artifact, not a production matching engine.
"""

from dataclasses import dataclass, field
from typing import Optional
import itertools

_id_counter = itertools.count(1)


@dataclass
class Order:
    id: str
    side: str      # "bid" or "ask"
    price: float
    size: float
    seq: int = field(default_factory=lambda: next(_id_counter))
    # seq is the true arrival-order tiebreaker; using a monotonic counter
    # rather than wall-clock time avoids ambiguity when multiple orders
    # arrive "at the same instant" in a replay.


class OrderBook:
    """
    A single-instrument limit order book.

    Internal structure: two dicts, `bids` and `asks`, each mapping
    price -> list[Order], with each list kept in FIFO (arrival) order.
    """

    def __init__(self):
        self.bids: dict[float, list[Order]] = {}
        self.asks: dict[float, list[Order]] = {}
        self._order_index: dict[str, Order] = {}  # order_id -> Order, for O(1) lookup on cancel/modify
        self.trade_log: list[dict] = []

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    def add_limit_order(self, order_id: str, side: str, price: float, size: float) -> None:
        """Handle an 'Order Added' message: a new limit order joins the book."""
        if order_id in self._order_index:
            raise ValueError(f"Order id {order_id} already exists")
        order = Order(id=order_id, side=side, price=price, size=size)
        book_side = self.bids if side == "bid" else self.asks
        book_side.setdefault(price, []).append(order)  # append = back of the FIFO queue
        self._order_index[order_id] = order

    def cancel_order(self, order_id: str) -> None:
        """Handle a 'Order Cancelled' message: remove a resting order before it trades."""
        order = self._order_index.pop(order_id, None)
        if order is None:
            return  # silently ignore cancels of unknown/already-filled orders
        book_side = self.bids if order.side == "bid" else self.asks
        level = book_side.get(order.price)
        if level is not None:
            level[:] = [o for o in level if o.id != order_id]
            if not level:
                del book_side[order.price]

    def modify_order(self, order_id: str, new_price: Optional[float] = None,
                      new_size: Optional[float] = None) -> None:
        """
        Handle an 'Order Modified' message.

        Priority rule (matches the curriculum's Week 1 Day 1 discussion):
          - size decrease -> keeps queue priority (in place, size just shrinks)
          - size increase, or any price change -> loses priority; removed and
            re-added at the back of the (possibly new) price level's queue
        """
        order = self._order_index.get(order_id)
        if order is None:
            raise ValueError(f"Unknown order id {order_id}")

        price_changed = new_price is not None and new_price != order.price
        size_increased = new_size is not None and new_size > order.size

        if price_changed or size_increased:
            # loses priority: cancel + re-add at the back of the queue
            side = order.side
            final_price = new_price if new_price is not None else order.price
            final_size = new_size if new_size is not None else order.size
            self.cancel_order(order_id)
            self.add_limit_order(order_id, side, final_price, final_size)
        else:
            # size-decrease-only (or no-op): keeps its spot in line
            if new_size is not None:
                order.size = new_size

    def market_order(self, side: str, size: float) -> list[dict]:
        """
        Handle an incoming market order ('Trade Executed' events).

        side: "buy" walks the ask side (lowest price first);
              "sell" walks the bid side (highest price first).

        Returns a list of fill dicts: {"order_id", "price", "size"}.
        Matches happen strictly in price-then-time priority order, across as
        many price levels as needed. Fully-filled resting orders are removed;
        partially-filled ones shrink in place.
        """
        if side not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")

        book_side = self.asks if side == "buy" else self.bids
        remaining = size
        fills: list[dict] = []

        # buys want the lowest ask first; sells want the highest bid first
        price_levels = sorted(book_side.keys(), reverse=(side == "sell"))

        for price in price_levels:
            if remaining <= 0:
                break
            queue = book_side[price]
            i = 0
            while i < len(queue) and remaining > 0:
                order = queue[i]
                fill_amt = min(order.size, remaining)
                fills.append({"order_id": order.id, "price": price, "size": fill_amt})
                order.size -= fill_amt
                remaining -= fill_amt
                if order.size <= 0:
                    del self._order_index[order.id]
                    queue.pop(i)
                    # don't advance i; the next order has shifted into this slot
                else:
                    i += 1
            if not queue:
                del book_side[price]

        self.trade_log.extend(fills)
        return fills

    # ------------------------------------------------------------------
    # Read-only helpers
    # ------------------------------------------------------------------

    def best_bid(self) -> Optional[float]:
        return max(self.bids.keys(), default=None)

    def best_ask(self) -> Optional[float]:
        return min(self.asks.keys(), default=None)

    def spread(self) -> Optional[float]:
        bb, ba = self.best_bid(), self.best_ask()
        if bb is None or ba is None:
            return None
        return round(ba - bb, 10)

    def depth_at(self, side: str, price: float) -> float:
        """Total resting size at a given price level on a given side."""
        book_side = self.bids if side == "bid" else self.asks
        return sum(o.size for o in book_side.get(price, []))

    def queue_ahead(self, order_id: str) -> float:
        """Total size resting ahead of a given order at its own price level."""
        order = self._order_index.get(order_id)
        if order is None:
            raise ValueError(f"Unknown order id {order_id}")
        book_side = self.bids if order.side == "bid" else self.asks
        level = book_side[order.price]
        ahead = 0.0
        for o in level:
            if o.id == order_id:
                break
            ahead += o.size
        return ahead

    def snapshot(self) -> dict:
        """A plain-dict view of the current book, sorted best-price-first each side."""
        return {
            "bids": [
                {"price": p, "orders": [(o.id, o.size) for o in self.bids[p]]}
                for p in sorted(self.bids.keys(), reverse=True)
            ],
            "asks": [
                {"price": p, "orders": [(o.id, o.size) for o in self.asks[p]]}
                for p in sorted(self.asks.keys())
            ],
        }

    def apply_message(self, msg: dict) -> Optional[list[dict]]:
        """
        Convenience dispatcher for a message stream, matching the curriculum's
        four message types: ADD / CANCEL / MODIFY / TRADE.
        Returns fills for TRADE messages, None otherwise.
        """
        mtype = msg["type"]
        if mtype == "ADD":
            self.add_limit_order(msg["id"], msg["side"], msg["price"], msg["size"])
        elif mtype == "CANCEL":
            self.cancel_order(msg["id"])
        elif mtype == "MODIFY":
            self.modify_order(msg["id"], msg.get("price"), msg.get("size"))
        elif mtype == "TRADE":
            return self.market_order(msg["side"], msg["size"])
        else:
            raise ValueError(f"Unknown message type: {mtype}")
        return None
