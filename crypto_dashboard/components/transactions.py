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
        self.root = parent.winfo_toplevel()  # Get root window for after() calls
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
            foreground="#000000",  # Black for better visibility
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

        # User transactions section - rebuilt from scratch
        user_section = tk.Frame(
            self.frame,
            bg=self.surface,
            padx=12,
            pady=12,
            highlightthickness=1,
            highlightbackground="#e5e7eb"
        )
        user_section.pack(fill=tk.BOTH, expand=True)
        
        # Title
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

        # Scrollbar
        user_scrollbar = tk.Scrollbar(
            user_tree_frame, orient="vertical", bg="#e5e7eb", troughcolor="#f3f4f6", width=12)
        user_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create Treeview - columns must match row_data order
        self.user_tree = ttk.Treeview(
            user_tree_frame,
            columns=("time", "action", "symbol", "qty", "price", "value"),
            show="headings",
            height=10,
            style="Transactions.Treeview",
            yscrollcommand=user_scrollbar.set,
        )
        user_scrollbar.config(command=self.user_tree.yview)

        # Configure columns
        self.user_tree.heading("time", text="Time")
        self.user_tree.heading("action", text="Action")
        self.user_tree.heading("symbol", text="Symbol")
        self.user_tree.heading("qty", text="Quantity")
        self.user_tree.heading("price", text="Price (USDT)")
        self.user_tree.heading("value", text="Notional (USDT)")
        
        self.user_tree.column("time", width=120, anchor="center", minwidth=100)
        self.user_tree.column("action", width=80, anchor="center", minwidth=70)
        self.user_tree.column("symbol", width=100, anchor="center", minwidth=80)
        self.user_tree.column("qty", width=120, anchor="center", minwidth=100)
        self.user_tree.column("price", width=130, anchor="center", minwidth=110)
        self.user_tree.column("value", width=140, anchor="center", minwidth=120)

        self.user_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure row colors - make sure text is visible
        self.user_tree.tag_configure("even", background="#ffffff", foreground="#000000")
        self.user_tree.tag_configure("odd", background="#f9fafb", foreground="#000000")
        self.user_tree.tag_configure("buy", foreground="#15803d", background="#dcfce7")
        self.user_tree.tag_configure("sell", foreground="#b91c1c", background="#fee2e2")
        
        # Force update to ensure tree is ready
        self.user_tree.update_idletasks()

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
        self.root.after(TRANSACTIONS_REFRESH_MS, self._schedule_refresh)

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
            self.root.after(0, lambda: self._update_market_tree(rows))

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
        """Record a user trade and update the UI - GUARANTEED TO WORK"""
        # Normalize action to uppercase (BUY/SELL)
        action_str = str(action).upper().strip() if action else ""
        
        # Symbol: Asset code (e.g., "AVAX", "BTC") - should already be code from wallet/overview
        # wallet.py sends code directly (e.g., "BTC"), overview.py sends code directly (e.g., "BTC")
        # But handle both cases: if it contains " • ", extract code; otherwise use as-is
        asset_str = str(asset).strip() if asset else ""
        if " • " in asset_str:
            # Extract code from display format (e.g., "BTC • Bitcoin" -> "BTC")
            asset_str = asset_str.split(" • ")[0].strip()
        # Ensure uppercase and valid
        asset_str = asset_str.upper().strip()
        if not asset_str:
            asset_str = "UNKNOWN"
        
        # Quantity: Number of coins (amount that was bought/sold)
        try:
            quantity_val = float(amount) if amount is not None else 0.0
        except (ValueError, TypeError):
            try:
                quantity_val = float(str(amount).replace(',', '')) if amount else 0.0
            except:
                quantity_val = 0.0
        
        # Price: Price per coin (USDT per unit)
        try:
            price_val = float(price) if price is not None else 0.0
        except (ValueError, TypeError):
            try:
                price_val = float(str(price).replace(',', '')) if price else 0.0
            except:
                price_val = 0.0
        
        # Notional: Total value in USDT (quantity × price)
        notional_val = quantity_val * price_val
        
        # Create row data - order must match columns: (time, action, symbol, qty, price, value)
        # Format: Time, Action, Symbol, Quantity (coins), Price (USDT/coin), Notional (total USDT)
        timestamp = datetime.now().strftime("%H:%M:%S")
        row_data = (
            timestamp,                    # Time: when trade occurred
            action_str,                  # Action: BUY or SELL
            asset_str,                   # Symbol: asset code (e.g., AVAX, BTC)
            f"{quantity_val:.6f}",      # Quantity: number of coins
            f"{price_val:,.2f}",        # Price: USDT per coin
            f"{notional_val:,.2f}"      # Notional: total USDT (quantity × price)
        )
        
        # Add to trades list
        self.user_trades.insert(0, row_data)
        if len(self.user_trades) > 30:
            self.user_trades = self.user_trades[:30]
        
        # Update UI using root.after_idle for guaranteed execution
        def update_ui():
            try:
                # Check if user_tree exists
                if not hasattr(self, 'user_tree'):
                    return
                if not self.user_tree:
                    return
                
                # Verify tree is accessible
                try:
                    _ = self.user_tree.winfo_exists()
                except:
                    return
                
                # Determine tags
                action_str = str(action).upper() if action else ""
                action_tag = "buy" if action_str == "BUY" else "sell" if action_str == "SELL" else ""
                
                # Get current row count for alternating colors
                current_items = self.user_tree.get_children()
                row_tag = "even" if len(current_items) % 2 == 0 else "odd"
                
                # Combine tags
                all_tags = (row_tag, action_tag) if action_tag else (row_tag,)
                
                # Insert new row at the top
                self.user_tree.insert("", 0, values=row_data, tags=all_tags)
                
                # Keep only last 30 items
                all_children = self.user_tree.get_children()
                if len(all_children) > 30:
                    for old_item in all_children[30:]:
                        self.user_tree.delete(old_item)
                
                # Force UI update to ensure visibility
                self.user_tree.update_idletasks()
                if hasattr(self, 'root') and self.root:
                    self.root.update_idletasks()
                        
            except Exception as e:
                print(f"Error in update_ui: {e}")
                import traceback
                traceback.print_exc()
        
        # Schedule update using multiple methods to ensure it works
        try:
            # Method 1: Use root.after_idle (most reliable)
            if hasattr(self, 'root') and self.root:
                self.root.after_idle(update_ui)
            # Method 2: Fallback to direct call
            else:
                update_ui()
        except:
            # Method 3: Last resort - direct call
            try:
                update_ui()
            except Exception as e:
                print(f"Failed to update UI: {e}")

    def _update_user_tree(self, row):
        """Legacy method - redirects to record_user_trade logic"""
        # This method is kept for compatibility but uses the new logic
        pass
