import tkinter as tk
from tkinter import ttk
import threading
from ..utils.binance_rest import get_order_book
from ..config import (
    ORDERBOOK_REFRESH_MS,
    ORDERBOOK_DEFAULT_LEVELS,
    ORDERBOOK_ALL_LEVELS,
)


class OrderBookPanel:
    """Display an order book snapshot styled like the mockup"""

    def __init__(self, parent, symbol, theme):
        self.parent = parent
        self.symbol = symbol.upper()
        self.theme = theme
        self.is_running = False
        self.level_limit = ORDERBOOK_DEFAULT_LEVELS
        self.show_all = False

        self._configure_style()

        self.frame = tk.Frame(
            parent,
            bg=self.theme["panel"],
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground=self.theme["panel_border"],
        )

        header = tk.Frame(self.frame, bg=self.theme["panel"])
        header.pack(fill=tk.X)
        self.title_label = tk.Label(
            header,
            text=f"Order Book Snapshot - {self.symbol}",
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
            font=("Helvetica", 15, "bold"),
        )
        self.title_label.pack(side=tk.LEFT)

        self.toggle_button = ttk.Button(
            header,
            text="Show All 20 Levels",
            style="Orderbook.TButton",
            command=self.toggle_levels,
        )
        self.toggle_button.pack(side=tk.RIGHT)

        columns_frame = tk.Frame(self.frame, bg=self.theme["panel"])
        columns_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        bids_frame = tk.Frame(columns_frame, bg=self.theme["panel"])
        bids_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        asks_frame = tk.Frame(columns_frame, bg=self.theme["panel"])
        asks_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        tk.Label(
            bids_frame,
            text="BIDS (Buys - Highest to Lowest Price)",
            bg=self.theme["panel"],
            fg=self.theme["accent_green"],
            font=("Helvetica", 12, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        tk.Label(
            asks_frame,
            text="ASKS (Sells - Lowest to Highest Price)",
            bg=self.theme["panel"],
            fg=self.theme["accent_red"],
            font=("Helvetica", 12, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        self.bids_tree = self._create_tree(bids_frame, tag="bid")
        self.asks_tree = self._create_tree(asks_frame, tag="ask")

    def _configure_style(self):
        style = ttk.Style()
        style.configure(
            "Orderbook.Treeview",
            background=self.theme["panel"],
            fieldbackground=self.theme["panel"],
            foreground=self.theme["text_primary"],
            rowheight=18,
            borderwidth=0,
        )
        style.configure(
            "Orderbook.Treeview.Heading",
            background=self.theme["panel"],
            foreground=self.theme["text_muted"],
            font=("Helvetica", 11, "bold"),
        )
        style.map(
            "Orderbook.Treeview",
            background=[("selected", self.theme["divider"])],
            foreground=[("selected", self.theme["text_primary"])],
        )
        style.configure(
            "Orderbook.TButton",
            background=self.theme["divider"],
            foreground=self.theme["text_primary"],
            padding=6,
        )
        style.map(
            "Orderbook.TButton",
            background=[("active", self.theme["panel_border"])],
            foreground=[("active", self.theme["text_primary"])],
        )

    def _create_tree(self, parent, tag):
        tree = ttk.Treeview(
            parent,
            columns=("price", "qty"),
            show="headings",
            style="Orderbook.Treeview",
            height=7,
        )
        tree.heading("price", text="Price")
        tree.heading("qty", text="Quantity")
        tree.column("price", anchor="center", width=120, stretch=True)
        tree.column("qty", anchor="center", width=120, stretch=True)
        tree.tag_configure(
            "bid",
            foreground=self.theme["accent_green"],
        )
        tree.tag_configure(
            "ask",
            foreground=self.theme["accent_red"],
        )
        tree.pack(fill=tk.BOTH, expand=True)
        return tree

    def toggle_levels(self):
        self.show_all = not self.show_all
        if self.show_all:
            self.level_limit = ORDERBOOK_ALL_LEVELS
            self.toggle_button.config(text="Show Top 10 Levels")
        else:
            self.level_limit = ORDERBOOK_DEFAULT_LEVELS
            self.toggle_button.config(text="Show All 20 Levels")
        # Refresh immediately
        threading.Thread(target=self.refresh_data, daemon=True).start()

    def set_symbol(self, symbol):
        new_symbol = symbol.upper()
        if new_symbol == self.symbol:
            return

        self.symbol = new_symbol
        self.title_label.config(text=f"Order Book Snapshot - {self.symbol}")

        if self.is_running:
            threading.Thread(target=self.refresh_data, daemon=True).start()

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.schedule_refresh()

    def stop(self):
        self.is_running = False

    def schedule_refresh(self):
        if not self.is_running:
            return
        thread = threading.Thread(target=self.refresh_data, daemon=True)
        thread.start()
        self.parent.after(ORDERBOOK_REFRESH_MS, self.schedule_refresh)

    def refresh_data(self):
        data = get_order_book(self.symbol, limit=self.level_limit)
        if not data:
            return

        bids = data.get("bids", [])[: self.level_limit]
        asks = data.get("asks", [])[: self.level_limit]

        def update():
            self._update_tree(self.bids_tree, bids, tag="bid")
            self._update_tree(self.asks_tree, asks, tag="ask")

        self.parent.after(0, update)

    def _update_tree(self, tree, rows, tag):
        for child in tree.get_children():
            tree.delete(child)
        for price, qty, *_ in rows:
            tree.insert(
                "",
                tk.END,
                values=(f"{float(price):,.2f}", f"{float(qty):,.4f}"),
                tags=(tag,),
            )

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
