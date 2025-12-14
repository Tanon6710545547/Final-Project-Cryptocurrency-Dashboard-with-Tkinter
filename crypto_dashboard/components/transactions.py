import os
import sys
import tkinter as tk
from tkinter import ttk
import threading
from datetime import datetime

if __package__ is None or __package__ == "":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from config import TRANSACTIONS_REFRESH_MS, THEME  # type: ignore
    from utils.binance_rest import get_recent_trades  # type: ignore
else:
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

        # Use light theme to match other pages
        self.bg = "#f5f7fb"
        self.surface = "#ffffff"
        self.panel_border = "#e5e7eb"

        self.frame = tk.Frame(
            parent,
            bg=self.bg,
            padx=18,
            pady=14,
            highlightbackground=self.panel_border,
            highlightthickness=1,
        )

        # Header removed - no "Market Transactions" title

        style = ttk.Style()
        style.configure(
            "Transactions.Treeview",
            background=self.surface,
            fieldbackground=self.surface,
            foreground="#111827",
            rowheight=32,
            borderwidth=0,
        )
        style.configure(
            "Transactions.Treeview.Heading",
            background="#f3f4f6",
            foreground="#374151",
            font=("Helvetica", 12, "bold"),
            relief="flat",
            padding=(0, 8),
        )
        style.map(
            "Transactions.Treeview",
            background=[("selected", "#e0e7ff")],
            foreground=[("selected", "#111827")],
        )

        # Market transactions section
        market_section = tk.Frame(
            self.frame,
            bg=self.surface,
            padx=12,
            pady=12,
            highlightthickness=1,
            highlightbackground="#e5e7eb"
        )
        market_section.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        tk.Label(
            market_section,
            text="Latest Market Executions",
            bg=self.surface,
            fg="#111827",
            font=("Helvetica", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        # Create scrollable frame for market tree
        market_tree_frame = tk.Frame(market_section, bg=self.surface)
        market_tree_frame.pack(fill=tk.BOTH, expand=True)

        market_scrollbar = tk.Scrollbar(
            market_tree_frame, orient="vertical", bg="#e5e7eb", troughcolor="#f3f4f6", width=12)
        market_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.market_tree = ttk.Treeview(
            market_tree_frame,
            columns=("time", "side", "qty", "price"),
            show="headings",
            height=10,
            style="Transactions.Treeview",
            yscrollcommand=market_scrollbar.set,
        )
        market_scrollbar.config(command=self.market_tree.yview)

        # Configure columns with proper widths and alignment
        columns_config = [
            ("time", "Time", 140, "center"),
            ("side", "Side", 80, "center"),
            ("qty", "Quantity", 120, "center"),
            ("price", "Price (USDT)", 140, "center"),
        ]
        for col, text, width, anchor in columns_config:
            self.market_tree.heading(col, text=text)
            self.market_tree.column(
                col, width=width, anchor=anchor, minwidth=width)

        self.market_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure alternating row colors
        self.market_tree.tag_configure("even", background="#ffffff")
        self.market_tree.tag_configure("odd", background="#f9fafb")

        # User transactions section
        user_section = tk.Frame(
            self.frame,
            bg=self.surface,
            padx=12,
            pady=12,
            highlightthickness=1,
            highlightbackground="#e5e7eb"
        )
        user_section.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            user_section,
            text="Mock User Transactions",
            bg=self.surface,
            fg="#111827",
            font=("Helvetica", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        # Create scrollable frame for user tree
        user_tree_frame = tk.Frame(user_section, bg=self.surface)
        user_tree_frame.pack(fill=tk.BOTH, expand=True)

        user_scrollbar = tk.Scrollbar(
            user_tree_frame, orient="vertical", bg="#e5e7eb", troughcolor="#f3f4f6", width=12)
        user_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.user_tree = ttk.Treeview(
            user_tree_frame,
            columns=("time", "action", "symbol", "qty", "price", "value"),
            show="headings",
            height=10,
            style="Transactions.Treeview",
            yscrollcommand=user_scrollbar.set,
        )
        user_scrollbar.config(command=self.user_tree.yview)

        # Configure columns with proper widths and alignment
        user_columns_config = [
            ("time", "Time", 120, "center"),
            ("action", "Action", 80, "center"),
            ("symbol", "Symbol", 100, "center"),
            ("qty", "Quantity", 120, "center"),
            ("price", "Price (USDT)", 130, "center"),
            ("value", "Notional (USDT)", 140, "center"),
        ]
        for col, text, width, anchor in user_columns_config:
            self.user_tree.heading(col, text=text)
            self.user_tree.column(
                col, width=width, anchor=anchor, minwidth=width)

        self.user_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure alternating row colors
        self.user_tree.tag_configure("even", background="#ffffff")
        self.user_tree.tag_configure("odd", background="#f9fafb")

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
        threading.Thread(target=self._refresh_market_trades,
                         daemon=True).start()
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
            rows.append((timestamp.strftime("%H:%M:%S"),
                        side, f"{qty:.5f}", f"{price:,.2f}"))
        if rows:
            self.parent.after(0, lambda: self._update_market_tree(rows))

    def _update_market_tree(self, rows):
        for child in self.market_tree.get_children():
            self.market_tree.delete(child)
        for idx, row in enumerate(rows):
            # Add color tags for BUY (green) and SELL (red)
            side = row[1] if len(row) > 1 else ""
            side_tag = "buy" if side == "BUY" else "sell" if side == "SELL" else ""
            row_tag = "even" if idx % 2 == 0 else "odd"
            self.market_tree.insert(
                "", tk.END, values=row, tags=(row_tag, side_tag))

        # Configure tag colors
        self.market_tree.tag_configure("buy", foreground="#16a34a")
        self.market_tree.tag_configure("sell", foreground="#dc2626")

    def set_symbol(self, symbol):
        new_symbol = symbol.upper()
        if new_symbol == self.symbol:
            return
        self.symbol = new_symbol
        threading.Thread(target=self._refresh_market_trades,
                         daemon=True).start()

    def record_user_trade(self, action, asset, amount, price, total):
        timestamp = datetime.now().strftime("%H:%M:%S")
        row = (timestamp, action, asset,
               f"{amount:.6f}", f"{price:,.2f}", f"{total:,.2f}")
        self.user_trades.insert(0, row)
        self.user_trades = self.user_trades[:30]

        # Add color tags for BUY (green) and SELL (red) with alternating row colors
        action_tag = "buy" if action == "BUY" else "sell" if action == "SELL" else ""
        row_tag = "even" if len(self.user_trades) % 2 == 0 else "odd"
        self.user_tree.insert("", 0, values=row, tags=(row_tag, action_tag))

        # Configure tag colors
        self.user_tree.tag_configure("buy", foreground="#16a34a")
        self.user_tree.tag_configure("sell", foreground="#dc2626")

        children = self.user_tree.get_children()
        if len(children) > 30:
            self.user_tree.delete(children[-1])
