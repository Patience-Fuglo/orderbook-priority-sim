# orderbook-priority-sim

A minimal limit order book engine implementing **price-time priority (FIFO)
matching**, built as the Phase 0 capstone project of a self-directed HFT
market microstructure curriculum.

This is a teaching and portfolio project, not a production matching engine —
built to demonstrate genuine, hands-on understanding of order book mechanics,
not to claim production HFT experience.

## What it does

- **Price priority, then time priority (FIFO)**: incoming market orders match
  the best available price first; among orders resting at the same price,
  whoever arrived first fills first.
- **Message-driven book state**: the book isn't a static table — it's built
  entirely by replaying a stream of `ADD` / `CANCEL` / `MODIFY` / `TRADE`
  events, the same four event types a real exchange feed publishes.
- **Correct modify semantics**: a size *decrease* keeps an order's queue
  priority; a size increase or any price change loses priority (the order is
  treated as new, placed at the back of the queue).
- **Multi-level walking**: a market order that exhausts one price level
  automatically continues into the next-best level until it's fully filled
  or liquidity runs out.
- **Queue analytics**: `queue_ahead()` reports how much size is resting in
  front of a given order at its price level.
- **Depth visualization**: `visualize.plot_depth()` renders a bid/ask depth
  chart from a live book snapshot.

## Structure

```
orderbook_sim/
  orderbook.py    # OrderBook engine: add / cancel / modify / market_order
  visualize.py    # depth chart plotting
tests/
  test_orderbook.py   # 10 tests, traced directly to hand-worked examples
examples/
  demo.py         # end-to-end replay + market order + chart
```

## Quickstart

```bash
pip install matplotlib pytest
python -m pytest tests/ -v
python examples/demo.py
```

## Example

```python
from orderbook_sim.orderbook import OrderBook

book = OrderBook()
book.add_limit_order("A", "bid", 50.08, 200)
book.add_limit_order("B", "bid", 50.08, 150)
book.add_limit_order("F", "ask", 50.10, 150)

fills = book.market_order("buy", 100)
# -> [{"order_id": "F", "price": 50.10, "size": 100}]

print(book.best_bid(), book.best_ask(), book.spread())
# -> 50.08 50.1 0.02
```

## Why this exists

This repo is Phase 0's deliverable in a longer curriculum working toward
genuine competence in market microstructure and market-making research —
order book mechanics first, then Avellaneda-Stoikov market-making theory,
then a full market-making simulation with latency-sensitivity analysis.
Each phase produces a real, testable artifact rather than notes alone.
# orderbook-priority-sim
