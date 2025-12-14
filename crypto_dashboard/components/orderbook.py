import os
import sys
import tkinter as tk
from tkinter import ttk
import threading

if __package__ is None or __package__ == "":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from utils.binance_rest import get_order_book  # type: ignore
    from config import (  # type: ignore
        ORDERBOOK_REFRESH_MS,
        ORDERBOOK_DEFAULT_LEVELS,
        ORDERBOOK_ALL_LEVELS,
    )
else:
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
        separator_color = self.theme.get("panel_border", "#242c37")
        # Use lighter background for better readability if using light theme
        bg_color = self.theme.get("panel", "#161b22")
        header_bg = self.theme.get("divider", "#1f2933") if bg_color == "#161b22" else "#f3f4f6"
        
        style.configure(
            "Orderbook.Treeview",
            background=bg_color,
            fieldbackground=bg_color,
            foreground=self.theme["text_primary"],
            rowheight=28,  # Increased row height for better readability
            borderwidth=1,
            relief="solid",
            font=("Helvetica", 11),  # Larger font
        )
        style.configure(
            "Orderbook.Treeview.Heading",
            background=header_bg,
            foreground=self.theme["text_muted"],
            font=("Helvetica", 12, "bold"),  # Larger, bolder header font
            borderwidth=1,
            relief="solid",
            padding=(8, 6),  # Add padding to headers
        )
        style.map(
            "Orderbook.Treeview",
            background=[("selected", self.theme["divider"])],
            foreground=[("selected", self.theme["text_primary"])],
        )
        # Configure column separators by setting borders
        style.configure(
            "Orderbook.Treeview",
            bordercolor=separator_color,
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
        # Set equal column widths for perfect balance
        tree.column("price", anchor="center", width=125, stretch=True, minwidth=125)
        tree.column("qty", anchor="center", width=125, stretch=True, minwidth=125)
        
        # Configure alternating row colors for better readability
        bg_color = self.theme.get("panel", "#161b22")
        if bg_color == "#161b22":  # Dark theme
            even_bg = bg_color
            odd_bg = self.theme.get("divider", "#1f2933")
        else:  # Light theme
            even_bg = "#ffffff"
            odd_bg = "#f9fafb"
        
        tree.tag_configure(
            "bid",
            foreground=self.theme["accent_green"],
        )
        tree.tag_configure(
            "ask",
            foreground=self.theme["accent_red"],
        )
        tree.tag_configure("even", background=even_bg)
        tree.tag_configure("odd", background=odd_bg)
        
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
        for idx, (price, qty, *_) in enumerate(rows):
            # Add alternating row colors for better readability
            row_tag = "even" if idx % 2 == 0 else "odd"
            tree.insert(
                "",
                tk.END,
                values=(f"{float(price):,.2f}", f"{float(qty):,.4f}"),
                tags=(tag, row_tag),
            )

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
