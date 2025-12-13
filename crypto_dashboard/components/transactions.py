import tkinter as tk
from tkinter import ttk
import threading
from datetime import datetime
from ..config import TRANSACTIONS_REFRESH_MS, THEME
from ..utils.binance_rest import get_recent_trades


class TransactionsPanel:
    """Panel showing market transactions plus mock user history"""

    def __init__(self, parent, symbol, theme=None):
        self.parent = parent
        self.symbol = symbol.upper()
        self.theme = theme or THEME
        self.is_running = False
        self.user_trades = []

        self.frame = tk.Frame(
            parent,
            bg=self.theme["panel"],
            padx=18,
            pady=14,
            highlightbackground=self.theme["panel_border"],
            highlightthickness=1,
        )

        header = tk.Frame(self.frame, bg=self.theme["panel"])
        header.pack(fill=tk.X)
        self.title_var = tk.StringVar(value=f"Market Transactions - {self.symbol}")
        tk.Label(
            header,
            textvariable=self.title_var,
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
            font=("Helvetica", 15, "bold"),
        ).pack(anchor="w")

        style = ttk.Style()
        style.configure(
            "Transactions.Treeview",
            background=self.theme["panel"],
            fieldbackground=self.theme["panel"],
            foreground=self.theme["text_primary"],
        )
        style.configure(
            "Transactions.Treeview.Heading",
            background=self.theme["panel"],
            foreground=self.theme["text_muted"],
            font=("Helvetica", 11, "bold"),
        )

        self.market_tree = ttk.Treeview(
            self.frame,
            columns=("time", "side", "qty", "price"),
            show="headings",
            height=8,
            style="Transactions.Treeview",
        )
        for col, text in zip(("time", "side", "qty", "price"), ("Time", "Side", "Qty", "Price (USDT)")):
            self.market_tree.heading(col, text=text)
        self.market_tree.column("time", width=110, anchor="center")
        self.market_tree.column("side", width=60, anchor="center")
        self.market_tree.column("qty", width=90, anchor="center")
        self.market_tree.column("price", width=110, anchor="center")
        tk.Label(
            self.frame,
            text="Latest market executions",
            bg=self.theme["panel"],
            fg=self.theme["text_muted"],
            font=("Helvetica", 11),
        ).pack(anchor="w", pady=(10, 0))
        self.market_tree.pack(fill=tk.X, pady=(4, 12))

        tk.Label(
            self.frame,
            text="Mock user transactions",
            bg=self.theme["panel"],
            fg=self.theme["text_muted"],
            font=("Helvetica", 11),
        ).pack(anchor="w")

        self.user_tree = ttk.Treeview(
            self.frame,
            columns=("time", "action", "symbol", "qty", "price", "value"),
            show="headings",
            height=6,
            style="Transactions.Treeview",
        )
        headings = [
            ("time", "Time"),
            ("action", "Action"),
            ("symbol", "Symbol"),
            ("qty", "Qty"),
            ("price", "Price"),
            ("value", "Notional"),
        ]
        for col, text in headings:
            self.user_tree.heading(col, text=text)
            anchor = "center" if col != "time" else "w"
            width = 90 if col not in ("time", "symbol") else 100
            self.user_tree.column(col, width=width, anchor=anchor)
        self.user_tree.pack(fill=tk.X, pady=(4, 0))

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._schedule_refresh()

    def stop(self):
        self.is_running = False

    def _schedule_refresh(self):
        if not self.is_running:
            return
        threading.Thread(target=self._refresh_market_trades, daemon=True).start()
        self.parent.after(TRANSACTIONS_REFRESH_MS, self._schedule_refresh)

    def _refresh_market_trades(self):
        data = get_recent_trades(self.symbol, limit=15)
        if not data:
            return
        rows = []
        for trade in data:
            try:
                timestamp = datetime.fromtimestamp(trade["time"] / 1000)
                side = "SELL" if trade.get("isBuyerMaker") else "BUY"
                qty = float(trade["qty"])
                price = float(trade["price"])
            except (KeyError, ValueError, TypeError):
                continue
            rows.append((timestamp.strftime("%H:%M:%S"), side, f"{qty:.5f}", f"{price:,.2f}"))
        if rows:
            self.parent.after(0, lambda: self._update_market_tree(rows))

    def _update_market_tree(self, rows):
        for child in self.market_tree.get_children():
            self.market_tree.delete(child)
        for row in rows:
            self.market_tree.insert("", tk.END, values=row)

    def set_symbol(self, symbol):
        new_symbol = symbol.upper()
        if new_symbol == self.symbol:
            return
        self.symbol = new_symbol
        self.title_var.set(f"Market Transactions - {self.symbol}")
        threading.Thread(target=self._refresh_market_trades, daemon=True).start()

    def record_user_trade(self, action, asset, amount, price, total):
        timestamp = datetime.now().strftime("%H:%M:%S")
        row = (timestamp, action, asset, f"{amount:.6f}", f"{price:,.2f}", f"{total:,.2f}")
        self.user_trades.insert(0, row)
        self.user_trades = self.user_trades[:30]
        self.user_tree.insert("", 0, values=row)
        children = self.user_tree.get_children()
        if len(children) > 30:
            self.user_tree.delete(children[-1])
