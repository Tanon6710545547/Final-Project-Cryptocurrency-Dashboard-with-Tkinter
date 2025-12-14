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
    # Add crypto_dashboard to path
    crypto_dashboard_dir = os.path.join(parent_dir, "crypto_dashboard")
    if crypto_dashboard_dir not in sys.path:
        sys.path.insert(0, crypto_dashboard_dir)
    from config import (  # type: ignore
        THEME,
        DEFAULT_SYMBOLS,
        WALLET_HOLDINGS,
        WALLET_CASH_BALANCE,
        WALLET_REFRESH_MS,
    )
    from utils.binance_rest import get_24hr_ticker  # type: ignore
else:
    from ..config import (
        THEME,
        DEFAULT_SYMBOLS,
        WALLET_HOLDINGS,
        WALLET_CASH_BALANCE,
        WALLET_REFRESH_MS,
    )
    from ..utils.binance_rest import get_24hr_ticker


ASSET_DISPLAY_NAMES = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "BNB": "BNB Chain",
    "XRP": "XRP",
    "ADA": "Cardano",
    "DOGE": "Dogecoin",
    "MATIC": "Polygon",
    "LTC": "Litecoin",
    "AVAX": "Avalanche",
}


class WalletPanel:
    """Mock wallet panel with buy/sell buttons"""

    def __init__(self, parent, theme=None, on_trade=None, on_balance_change=None):
        self.parent = parent
        self.theme = theme or THEME
        self.on_trade = on_trade
        self.on_balance_change = on_balance_change
        self.is_running = False
        self.cash_balance = WALLET_CASH_BALANCE
        self.holdings = WALLET_HOLDINGS.copy()
        self.prices = {asset: 0.0 for asset in self.holdings}
        self.asset_options = self._build_asset_options()
        self.asset_display_to_code = {
            label: code for code, label in self.asset_options}
        self.asset_code_to_display = {
            code: label for code, label in self.asset_options}
        self.wallet_action_mode = None

        # Use light theme to match Overview page
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

        header = tk.Frame(self.frame, bg=self.surface)
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            header,
            text="Wallet Portfolio (Mock)",
            bg=self.surface,
            fg="#111827",
            font=("Helvetica", 18, "bold"),
        ).pack(side=tk.LEFT)

        # Initialize cash_var for internal use (not displayed)
        self.cash_var = tk.StringVar(value="USDT Balance: --")

        # Add Exchange section
        self._build_exchange_section()

        # Initialize variables for internal use (not displayed)
        default_asset = self.asset_options[0][0]
        self.asset_var = tk.StringVar(value=default_asset)
        self.asset_display_var = tk.StringVar(
            value=self.asset_code_to_display[default_asset])

        self._build_deposit_section()

        # Build Holdings section at the bottom
        self._build_holdings_section()

        self._apply_price_update({})

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
        threading.Thread(target=self._refresh_prices, daemon=True).start()
        self.parent.after(WALLET_REFRESH_MS, self._schedule_refresh)

    def _refresh_prices(self):
        updated = {}
        for asset in self.holdings.keys():
            pair = DEFAULT_SYMBOLS.get(asset, f"{asset.lower()}usdt")
            data = get_24hr_ticker(pair)
            if not data:
                continue
            try:
                updated[asset] = float(data.get("lastPrice", 0))
            except (TypeError, ValueError):
                continue
        if updated:
            self.parent.after(0, lambda: self._apply_price_update(updated))

    def _apply_price_update(self, values):
        self.prices.update(values)
        total_value = self.cash_balance
        for asset, amount in self.holdings.items():
            total_value += amount * self.prices.get(asset, 0)
        self.total_value_var.set(f"Total: $ {total_value:,.2f}")
        self.cash_var.set(f"USDT Balance: $ {self.cash_balance:,.2f}")
        if hasattr(self, "balance_display_var"):
            self.balance_display_var.set(f"$ {self.cash_balance:,.2f} USD")
        if hasattr(self, "exchange_quote_var"):
            self._update_exchange_quote()

        # Update buy/sell holdings displays if they exist
        if hasattr(self, "buy_holdings_display_var"):
            self._update_buy_holdings_display()
        if hasattr(self, "sell_holdings_display_var"):
            self._update_sell_holdings_display()

        # Notify overview of balance/total change
        if callable(self.on_balance_change):
            self.on_balance_change(
                self.cash_balance, self.holdings.copy(), total_value)

        for row in self.tree.get_children():
            self.tree.delete(row)

        # Configure alternating row colors
        self.tree.tag_configure("even", background="#ffffff")
        self.tree.tag_configure("odd", background="#f9fafb")

        for idx, (asset, amount) in enumerate(self.holdings.items()):
            price = self.prices.get(asset, 0)
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert(
                "",
                tk.END,
                values=(asset, f"{price:,.2f}",
                        f"{amount:.6f}", f"{amount * price:,.2f}"),
                tags=(asset, tag),
            )

    def _update_balance_only(self):
        """อัปเดตเฉพาะ Balance และ Total ทันที - ไม่ delay และไม่กระทบส่วนอื่น"""
        # คำนวณ total value - ใช้ sum() เพื่อให้เร็วขึ้น
        holdings_value = sum(amount * self.prices.get(asset, 0)
                             for asset, amount in self.holdings.items())
        total_value = self.cash_balance + holdings_value

        # อัปเดตเฉพาะส่วนที่จำเป็น - ไม่ต้องอัปเดต holdings table
        self.total_value_var.set(f"Total: $ {total_value:,.2f}")
        self.cash_var.set(f"USDT Balance: $ {self.cash_balance:,.2f}")
        if hasattr(self, "balance_display_var"):
            self.balance_display_var.set(f"$ {self.cash_balance:,.2f} USD")

        # บังคับให้ UI อัปเดตทันที
        self.frame.update_idletasks()

        # Notify overview of balance/total change
        if callable(self.on_balance_change):
            self.on_balance_change(
                self.cash_balance, self.holdings.copy(), total_value)

    def _apply_price_update_immediate(self, values):
        """อัปเดตทันทีโดยไม่ delay สำหรับ deposit/withdraw"""
        self.prices.update(values)
        # คำนวณ total value
        total_value = self.cash_balance
        for asset, amount in self.holdings.items():
            total_value += amount * self.prices.get(asset, 0)

        # อัปเดตส่วนที่จำเป็น
        self.total_value_var.set(f"Total: $ {total_value:,.2f}")
        self.cash_var.set(f"USDT Balance: $ {self.cash_balance:,.2f}")
        if hasattr(self, "balance_display_var"):
            self.balance_display_var.set(f"$ {self.cash_balance:,.2f} USD")

        # Notify overview of balance/total change
        if callable(self.on_balance_change):
            self.on_balance_change(
                self.cash_balance, self.holdings.copy(), total_value)

        # อัปเดต holdings table - แสดงตามที่กำหนด
        if hasattr(self, "tree"):
            for row in self.tree.get_children():
                self.tree.delete(row)

            # Configure alternating row colors
            self.tree.tag_configure("even", background="#ffffff")
            self.tree.tag_configure("odd", background="#f9fafb")

            for idx, (asset, amount) in enumerate(self.holdings.items()):
                price = self.prices.get(asset, 0)
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert(
                    "",
                    tk.END,
                    values=(asset, f"{price:,.2f}",
                            f"{amount:.6f}", f"{amount * price:,.2f}"),
                    tags=(asset, tag),
                )

    def _execute_trade(self, action):
        try:
            amount = float(self.amount_entry.get())
        except (TypeError, ValueError):
            self.status_var.set("Enter the amount in numeric form")
            return
        if amount <= 0:
            self.status_var.set("Amount must be greater than 0")
            return

        asset = self.asset_var.get()
        price = self.prices.get(asset, 0)
        if price <= 0:
            self.status_var.set("Market price not available yet, try again")
            return

        notional = amount * price
        if action == "BUY":
            if notional > self.cash_balance:
                self.status_var.set("Insufficient USDT balance")
                return
            self.cash_balance -= notional
            self.holdings[asset] = self.holdings.get(asset, 0) + amount
        else:
            holding = self.holdings.get(asset, 0)
            if amount > holding:
                self.status_var.set("Not enough holdings to sell")
                return
            self.holdings[asset] = holding - amount
            self.cash_balance += notional

        self.status_var.set(f"{action} {amount} {asset} @ {price:,.2f} (mock)")
        self.amount_entry.delete(0, tk.END)
        self._apply_price_update({})
        if callable(self.on_trade):
            self.on_trade(action, asset, amount, price, notional)

    def _build_exchange_section(self):
        card = tk.Frame(self.frame, bg="#f9fafb", padx=18, pady=16,
                        highlightthickness=1, highlightbackground="#e5e7eb")
        card.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            card,
            text="Exchange",
            font=("Helvetica", 14, "bold"),
            fg="#111827",
            bg="#f9fafb",
        ).pack(anchor="w", pady=(0, 10))

        default_asset = self.asset_options[0][0]
        self.exchange_asset_var = tk.StringVar(value=default_asset)
        self.exchange_amount_var = tk.StringVar(value="1.0")
        self.exchange_quote_var = tk.StringVar(value="$ -- USD")
        self.exchange_asset_display_var = tk.StringVar(
            value=self.asset_code_to_display[default_asset])

        # Buy section (Top) - separated from Sell - made more compact
        buy_section = tk.Frame(card, bg="#f9fafb", padx=0, pady=4,
                               highlightthickness=1, highlightbackground="#e5e7eb")
        buy_section.pack(fill=tk.X, pady=(0, 0))

        # Buy section title
        tk.Label(
            buy_section,
            text="Buy",
            font=("Helvetica", 11, "bold"),
            bg="#f9fafb",
            fg="#111827",
        ).pack(anchor="w", padx=12, pady=(0, 4))

        # Buy input row
        buy_input_row = tk.Frame(buy_section, bg="#f9fafb")
        buy_input_row.pack(fill=tk.X, padx=12, pady=(6, 3))

        # Asset selector for buy
        buy_asset_col = tk.Frame(buy_input_row, bg="#f9fafb")
        buy_asset_col.pack(side=tk.LEFT, fill=tk.BOTH,
                           expand=True, padx=(0, 8))
        tk.Label(
            buy_asset_col,
            text="Asset (Coin)",
            bg="#f9fafb",
            fg="#6b7280",
            font=("Helvetica", 9, "bold"),
        ).pack(anchor="w", pady=(0, 2))

        buy_asset_selector_frame = tk.Frame(
            buy_asset_col, bg="#ffffff", highlightthickness=2, highlightbackground="#9ca3af", highlightcolor="#9ca3af")
        buy_asset_selector_frame.pack(fill=tk.X)
        self.buy_asset_display_var = tk.StringVar(
            value=self.exchange_asset_display_var.get())
        buy_asset_combo = ttk.Combobox(
            buy_asset_selector_frame,
            values=list(self.asset_display_to_code.keys()),
            textvariable=self.buy_asset_display_var,
            state="readonly",
            width=15,
            font=("Helvetica", 12, "bold")
        )
        buy_asset_combo.pack(fill=tk.X, padx=6, pady=4)
        buy_asset_combo.bind("<<ComboboxSelected>>",
                             lambda _e: self._update_buy_holdings_display())

        # Holdings display for buy
        self.buy_holdings_display_var = tk.StringVar(
            value="Holdings: 0.000000")
        tk.Label(
            buy_asset_col,
            textvariable=self.buy_holdings_display_var,
            bg="#f9fafb",
            fg="#6b7280",
            font=("Helvetica", 8),
        ).pack(anchor="w", pady=(2, 0))

        # Amount input for buy
        buy_amount_col = tk.Frame(buy_input_row, bg="#f9fafb")
        buy_amount_col.pack(side=tk.LEFT, fill=tk.BOTH,
                            expand=True, padx=(8, 8))
        tk.Label(
            buy_amount_col,
            text="Amount",
            bg="#f9fafb",
            fg="#6b7280",
            font=("Helvetica", 9, "bold"),
        ).pack(anchor="w", pady=(0, 2))

        buy_amount_entry_frame = tk.Frame(
            buy_amount_col, bg="#ffffff", highlightthickness=2, highlightbackground="#9ca3af", highlightcolor="#9ca3af")
        buy_amount_entry_frame.pack(fill=tk.X)
        # Store reference for button alignment
        self.buy_amount_entry_frame = buy_amount_entry_frame
        self.buy_amount_entry = tk.Entry(
            buy_amount_entry_frame,
            bd=0,
            font=("Helvetica", 12, "bold"),
            bg="#ffffff",
            fg="#111827",
            relief="flat",
            highlightthickness=0,
            insertbackground="#111827"
        )
        self.buy_amount_entry.pack(fill=tk.X, padx=6, pady=6)

        # Price display for buy (1 crypto = X USD)
        self.buy_price_display_var = tk.StringVar(value="1 BTC = $0.00")
        tk.Label(
            buy_amount_col,
            textvariable=self.buy_price_display_var,
            bg="#f9fafb",
            fg="#6b7280",
            font=("Helvetica", 8),
        ).pack(anchor="w", pady=(2, 0))

        # Buy button - same size as amount field and aligned
        buy_button_col = tk.Frame(buy_input_row, bg="#f9fafb")
        buy_button_col.pack(side=tk.LEFT, padx=(8, 0))
        # Spacer to align with Amount label - removed to move button up
        # (No spacer label - button will align with input field directly)

        # Button frame to match amount entry frame height - สีเทาเหมือนช่อง input
        buy_btn_frame = tk.Frame(buy_button_col, bg="#ffffff", highlightthickness=2,
                                 highlightbackground="#9ca3af", highlightcolor="#9ca3af")
        buy_btn_frame.pack(fill=tk.BOTH, expand=True)
        buy_btn = tk.Button(
            buy_btn_frame,
            text="Buy",
            font=("Helvetica", 9, "bold"),
            bg="#f3f4f6",
            fg="#111827",
            relief="flat",
            padx=12,
            pady=4,
            command=lambda: self._execute_trade_from_exchange(
                "BUY", self.buy_amount_entry, self.buy_asset_display_var),
            cursor="hand2",
            activebackground="#f3f4f6",  # ไม่เปลี่ยนสีเมื่อกด
            activeforeground="#111827",
            bd=0,
            highlightthickness=0
        )
        buy_btn.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Status message for buy
        self.buy_status_var = tk.StringVar(value="")
        tk.Label(
            buy_section,
            textvariable=self.buy_status_var,
            bg="#f9fafb",
            fg="#6b7280",
            anchor="w",
            font=("Helvetica", 8),
        ).pack(fill=tk.X, padx=12, pady=(3, 4))

        # Sell section (Bottom) - separated from Buy - made more compact
        sell_section = tk.Frame(card, bg="#f9fafb", padx=0, pady=4,
                                highlightthickness=1, highlightbackground="#e5e7eb")
        sell_section.pack(fill=tk.X, pady=(0, 0))

        # Sell section title
        tk.Label(
            sell_section,
            text="Sell",
            font=("Helvetica", 11, "bold"),
            bg="#f9fafb",
            fg="#111827",
        ).pack(anchor="w", padx=12, pady=(0, 4))

        # Sell input row
        sell_input_row = tk.Frame(sell_section, bg="#f9fafb")
        sell_input_row.pack(fill=tk.X, padx=12, pady=(6, 3))

        # Asset selector for sell
        sell_asset_col = tk.Frame(sell_input_row, bg="#f9fafb")
        sell_asset_col.pack(side=tk.LEFT, fill=tk.BOTH,
                            expand=True, padx=(0, 8))
        tk.Label(
            sell_asset_col,
            text="Asset (Coin)",
            bg="#f9fafb",
            fg="#6b7280",
            font=("Helvetica", 9, "bold"),
        ).pack(anchor="w", pady=(0, 2))

        sell_asset_selector_frame = tk.Frame(
            sell_asset_col, bg="#ffffff", highlightthickness=2, highlightbackground="#9ca3af", highlightcolor="#9ca3af")
        sell_asset_selector_frame.pack(fill=tk.X)
        self.sell_asset_display_var = tk.StringVar(
            value=self.exchange_asset_display_var.get())
        sell_asset_combo = ttk.Combobox(
            sell_asset_selector_frame,
            values=list(self.asset_display_to_code.keys()),
            textvariable=self.sell_asset_display_var,
            state="readonly",
            width=15,
            font=("Helvetica", 12, "bold")
        )
        sell_asset_combo.pack(fill=tk.X, padx=6, pady=4)
        sell_asset_combo.bind("<<ComboboxSelected>>",
                              lambda _e: self._update_sell_holdings_display())

        # Holdings display for sell
        self.sell_holdings_display_var = tk.StringVar(
            value="Holdings: 0.000000")
        tk.Label(
            sell_asset_col,
            textvariable=self.sell_holdings_display_var,
            bg="#f9fafb",
            fg="#6b7280",
            font=("Helvetica", 8),
        ).pack(anchor="w", pady=(2, 0))

        # Amount input for sell
        sell_amount_col = tk.Frame(sell_input_row, bg="#f9fafb")
        sell_amount_col.pack(side=tk.LEFT, fill=tk.BOTH,
                             expand=True, padx=(8, 8))
        tk.Label(
            sell_amount_col,
            text="Amount",
            bg="#f9fafb",
            fg="#6b7280",
            font=("Helvetica", 9, "bold"),
        ).pack(anchor="w", pady=(0, 2))

        sell_amount_entry_frame = tk.Frame(
            sell_amount_col, bg="#ffffff", highlightthickness=2, highlightbackground="#9ca3af", highlightcolor="#9ca3af")
        sell_amount_entry_frame.pack(fill=tk.X)
        # Store reference for button alignment
        self.sell_amount_entry_frame = sell_amount_entry_frame
        self.sell_amount_entry = tk.Entry(
            sell_amount_entry_frame,
            bd=0,
            font=("Helvetica", 12, "bold"),
            bg="#ffffff",
            fg="#111827",
            relief="flat",
            highlightthickness=0,
            insertbackground="#111827"
        )
        self.sell_amount_entry.pack(fill=tk.X, padx=6, pady=6)

        # Price display for sell (1 crypto = X USD)
        self.sell_price_display_var = tk.StringVar(value="1 BTC = $0.00")
        tk.Label(
            sell_amount_col,
            textvariable=self.sell_price_display_var,
            bg="#f9fafb",
            fg="#6b7280",
            font=("Helvetica", 8),
        ).pack(anchor="w", pady=(2, 0))

        # Sell button - same size as amount field and aligned
        sell_button_col = tk.Frame(sell_input_row, bg="#f9fafb")
        sell_button_col.pack(side=tk.LEFT, padx=(8, 0))
        # Spacer to align with Amount label - removed to move button up
        # (No spacer label - button will align with input field directly)

        # Button frame to match amount entry frame height - สีเทาเหมือนช่อง input
        sell_btn_frame = tk.Frame(sell_button_col, bg="#ffffff", highlightthickness=2,
                                  highlightbackground="#9ca3af", highlightcolor="#9ca3af")
        sell_btn_frame.pack(fill=tk.BOTH, expand=True)
        sell_btn = tk.Button(
            sell_btn_frame,
            text="Sell",
            font=("Helvetica", 9, "bold"),
            bg="#f3f4f6",
            fg="#111827",
            relief="flat",
            padx=12,
            pady=4,
            command=lambda: self._execute_trade_from_exchange(
                "SELL", self.sell_amount_entry, self.sell_asset_display_var),
            cursor="hand2",
            activebackground="#f3f4f6",  # ไม่เปลี่ยนสีเมื่อกด
            activeforeground="#111827",
            bd=0,
            highlightthickness=0
        )
        sell_btn.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Status message for sell
        self.sell_status_var = tk.StringVar(value="")
        tk.Label(
            sell_section,
            textvariable=self.sell_status_var,
            bg="#f9fafb",
            fg="#6b7280",
            anchor="w",
            font=("Helvetica", 8),
        ).pack(fill=tk.X, padx=12, pady=(3, 4))

        # Initialize holdings displays
        self._update_buy_holdings_display()
        self._update_sell_holdings_display()

        # Total and Balance section - side by side with separate borders
        total_balance_row = tk.Frame(card, bg="#f9fafb")
        total_balance_row.pack(fill=tk.X, pady=(4, 0))

        # Total section
        total_frame = tk.Frame(total_balance_row, bg="#f9fafb")
        total_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        tk.Label(
            total_frame,
            text="Total",
            font=("Helvetica", 12, "bold"),
            fg="#6b7280",
            bg="#f9fafb",
        ).pack(anchor="w", pady=(0, 4))

        total_display = tk.Frame(
            total_frame, bg="#ffffff", highlightthickness=1, highlightbackground="#e5e7eb")
        total_display.pack(fill=tk.X)
        self.total_value_var = tk.StringVar(value="Total: $ --")
        tk.Label(
            total_display,
            textvariable=self.total_value_var,
            font=("Helvetica", 16, "bold"),
            fg="#16a34a",
            bg="#ffffff",
            anchor="w",
        ).pack(fill=tk.X, padx=12, pady=10)

        # Balance section
        balance_frame = tk.Frame(total_balance_row, bg="#f9fafb")
        balance_frame.pack(side=tk.RIGHT, fill=tk.BOTH,
                           expand=True, padx=(6, 0))
        tk.Label(
            balance_frame,
            text="Balance",
            font=("Helvetica", 12, "bold"),
            fg="#6b7280",
            bg="#f9fafb",
        ).pack(anchor="w", pady=(0, 4))

        balance_display = tk.Frame(
            balance_frame, bg="#ffffff", highlightthickness=1, highlightbackground="#e5e7eb")
        balance_display.pack(fill=tk.X)
        self.balance_display_var = tk.StringVar(value="$ -- USD")
        tk.Label(
            balance_display,
            textvariable=self.balance_display_var,
            font=("Helvetica", 16, "bold"),
            fg="#16a34a",
            bg="#ffffff",
            anchor="w",
        ).pack(fill=tk.X, padx=12, pady=10)

    def _build_deposit_section(self):
        section = tk.Frame(self.frame, bg=self.surface,
                           highlightthickness=1, highlightbackground="#e5e7eb",
                           # ตรงกับ Exchange (padx=18, pady=16)
                           padx=18, pady=16)
        section.pack(fill=tk.X, pady=(12, 16))  # เพิ่ม padding ด้านล่าง
        tk.Label(
            section,
            text="Wallet Actions",
            bg=self.surface,
            fg="#111827",
            font=("Helvetica", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        input_row = tk.Frame(section, bg=self.surface)
        # ตรงกับ Total section: card padx=18 + total_frame padx=0 + total_display padx=12 = 30
        # section มี padx=18, ดังนั้น input_row ต้องมี padx=0, entry_container padx=0, deposit_entry padx=12
        input_row.pack(fill=tk.X, pady=(0, 8), padx=(0, 0))

        # Entry field with styling - มีกรอบชัดเจน, ขยายเต็มพื้นที่แต่ลดความกว้างลง 30%
        entry_container = tk.Frame(
            input_row,
            bg="#ffffff",
            highlightthickness=2,
            highlightbackground="#9ca3af",
            highlightcolor="#9ca3af",
        )
        entry_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.deposit_entry = tk.Entry(
            entry_container,
            bd=0,
            font=("Helvetica", 12),
            bg="#ffffff",
            fg="#111827",
            highlightthickness=0,
            insertbackground="#111827",
            width=20,
            justify="center",
        )
        self.deposit_entry.pack(fill=tk.X, padx=12, pady=8)

        # Buttons container - จัดกึ่งกลาง
        buttons_container = tk.Frame(input_row, bg=self.surface)
        # เพิ่มช่องว่างหน้า buttons เท่ากับช่องว่างระหว่างปุ่ม
        buttons_container.pack(side=tk.LEFT, padx=(6, 0))

        # Buttons with modern styling - ไม่เปลี่ยนสีเมื่อกด
        deposit_btn = tk.Button(
            buttons_container,
            text="Deposit",
            font=("Helvetica", 11, "bold"),
            bg="#16a34a",
            fg="#111827",
            relief="flat",
            padx=20,
            pady=8,
            command=lambda: self._handle_wallet_action("deposit"),
            cursor="hand2",
            activebackground="#16a34a",  # ไม่เปลี่ยนสีเมื่อกด
            activeforeground="#111827",
            bd=0,
            highlightthickness=0,
            state="normal"
        )
        deposit_btn.pack(side=tk.LEFT, padx=(0, 6))

        withdraw_btn = tk.Button(
            buttons_container,
            text="Withdraw",
            font=("Helvetica", 11, "bold"),
            bg="#dc2626",
            fg="#111827",
            relief="flat",
            padx=20,
            pady=8,
            command=lambda: self._handle_wallet_action("withdraw"),
            cursor="hand2",
            activebackground="#dc2626",  # ไม่เปลี่ยนสีเมื่อกด
            activeforeground="#111827",
            bd=0,
            highlightthickness=0,
            state="normal"
        )
        withdraw_btn.pack(side=tk.LEFT)

        # Quick action frames with better styling - ย้ายขึ้นมา
        self.quick_deposit_frame = tk.Frame(section, bg=self.surface)

        # Quick deposit section - ตรงกับ Total section
        deposit_label = tk.Label(
            self.quick_deposit_frame,
            text="Quick Deposit",
            bg=self.surface,
            fg="#6b7280",
            font=("Helvetica", 10, "bold"),
        )
        # ตรงกับ Total label: card padx=18 + total_frame padx=0 = 18, section มี padx=18, ดังนั้น padx=0
        deposit_label.pack(anchor="w", padx=(0, 0), pady=(0, 6))

        deposit_buttons = tk.Frame(self.quick_deposit_frame, bg=self.surface)
        # ให้ขอบปุ่มตรงกับกรอบ Total/Balance (ไม่มีระยะขอบเพิ่มเติม)
        deposit_buttons.pack(fill=tk.X, padx=0)

        for idx, amount in enumerate((1000, 5000, 10000)):
            btn = tk.Button(
                deposit_buttons,
                text=f"{amount:,}",
                font=("Helvetica", 10, "bold"),
                bg="#f3f4f6",
                fg="#111827",
                relief="flat",
                padx=16,
                pady=6,
                command=lambda amt=amount: self._deposit_quick(amt),
                cursor="hand2",
                activebackground="#f3f4f6",  # ไม่เปลี่ยนสีเมื่อกด
                activeforeground="#111827",
                bd=0,
                highlightthickness=0,
                state="normal"
            )
            # deposit_buttons มี padx=(12, 0) แล้ว ดังนั้นปุ่มไม่ต้องมี padding ซ้ายเพิ่ม
            # ปุ่มทั้งหมดใช้ padding เดียวกัน
            btn.pack(side=tk.LEFT, padx=(0, 6))

        # Status message for Wallet Actions
        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(
            section,
            textvariable=self.status_var,
            bg=self.surface,
            fg="#6b7280",
            anchor="w",
            font=("Helvetica", 10),
        )
        self.status_label.pack(fill=tk.X, pady=(8, 0))

        # Show Quick Deposit by default - ย้ายขึ้นมาใกล้ input row และเพิ่มพื้นที่ล่าง
        # ลดพื้นที่ล่าง 3 เท่า (จาก 20 เป็น 7)
        self.quick_deposit_frame.pack(fill=tk.X, pady=(4, 7))

    def _build_holdings_section(self):
        """Build the Holdings table section"""
        # Create a card frame with border for the table
        table_card = tk.Frame(
            self.frame,
            bg="#f9fafb",
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground="#e5e7eb"
        )
        table_card.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        # Table title - larger font
        tk.Label(
            table_card,
            text="Holdings",
            bg="#f9fafb",
            fg="#111827",
            font=("Helvetica", 18, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        # Create scrollable frame for table
        canvas_frame = tk.Frame(table_card, bg="#f9fafb")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(
            canvas_frame, orient="vertical", bg="#e5e7eb", troughcolor="#f3f4f6", width=12)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        table_canvas = tk.Canvas(
            canvas_frame,
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#e5e7eb",
            yscrollcommand=scrollbar.set
        )
        table_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=table_canvas.yview)

        # Create frame inside canvas for treeview
        tree_container = tk.Frame(table_canvas, bg="#ffffff")
        canvas_window = table_canvas.create_window(
            (0, 0), window=tree_container, anchor="nw")

        # Configure canvas scrolling
        def configure_scroll_region(event=None):
            table_canvas.configure(scrollregion=table_canvas.bbox("all"))
            canvas_width = table_canvas.winfo_width()
            if canvas_width > 1:
                table_canvas.itemconfig(canvas_window, width=canvas_width)

        def on_canvas_configure(event):
            canvas_width = event.width
            table_canvas.itemconfig(canvas_window, width=canvas_width)
            configure_scroll_region()

        tree_container.bind("<Configure>", configure_scroll_region)
        table_canvas.bind("<Configure>", on_canvas_configure)

        # Mousewheel scrolling
        def on_mousewheel(event):
            if hasattr(event, 'delta'):
                table_canvas.yview_scroll(
                    int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                table_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                table_canvas.yview_scroll(1, "units")
            return "break"

        table_canvas.bind("<MouseWheel>", on_mousewheel)
        table_canvas.bind("<Button-4>", on_mousewheel)
        table_canvas.bind("<Button-5>", on_mousewheel)
        tree_container.bind("<MouseWheel>", on_mousewheel)
        tree_container.bind("<Button-4>", on_mousewheel)
        tree_container.bind("<Button-5>", on_mousewheel)

        style = ttk.Style()
        style.configure(
            "Wallet.Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#111827",
            borderwidth=0,
            rowheight=42,  # Increased row height for better readability
            font=("Helvetica", 12),  # Larger font for better readability
        )
        style.configure(
            "Wallet.Treeview.Heading",
            background="#f3f4f6",
            foreground="#374151",
            font=("Helvetica", 12, "bold"),
            relief="flat",
            padding=(10, 8),  # Add padding to headers
        )
        style.map(
            "Wallet.Treeview",
            background=[("selected", "#e0e7ff")],
            foreground=[("selected", "#111827")],
        )
        # Configure alternating row colors for better readability
        style.configure(
            "Wallet.Treeview",
            fieldbackground=[("readonly", "#ffffff")],
        )

        self.tree = ttk.Treeview(
            tree_container,
            columns=("asset", "price", "amount", "value"),
            show="headings",
            style="Wallet.Treeview",
        )
        self.tree.heading("asset", text="Asset")
        self.tree.heading("price", text="Price (USDT)")
        self.tree.heading("amount", text="Amount")
        self.tree.heading("value", text="Value (USDT)")
        # Increased column widths and added padding
        self.tree.column("asset", width=100, anchor="center", minwidth=80)
        self.tree.column("price", width=140, anchor="center", minwidth=110)
        self.tree.column("amount", width=130, anchor="center", minwidth=100)
        self.tree.column("value", width=140, anchor="center", minwidth=110)

        # Configure alternating row colors for better readability
        self.tree.tag_configure("even", background="#ffffff")
        self.tree.tag_configure("odd", background="#f9fafb")

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Store canvas reference
        self.table_canvas = table_canvas

    def _show_quick_panel(self, mode):
        self.wallet_action_mode = mode
        # Quick Deposit จะแสดงอยู่เสมอ ไม่ว่าจะกด Deposit หรือ Withdraw
        if hasattr(self, "quick_deposit_frame"):
            if not self.quick_deposit_frame.winfo_viewable():
                self.quick_deposit_frame.pack(fill=tk.X, pady=(4, 7))

    def _handle_wallet_action(self, mode):
        self._show_quick_panel(mode)
        entry_value = self.deposit_entry.get().strip()
        # ถ้ามีค่าใน entry field ให้ทำงาน
        if entry_value:
            if mode == "deposit":
                self._deposit_custom()
            else:
                self._withdraw_custom()
        # ถ้าไม่มีค่าใน entry field ก็แค่แสดง quick panel

    def _deposit_custom(self):
        try:
            amount = float(self.deposit_entry.get().strip())
        except (TypeError, ValueError):
            self.status_var.set("Enter a numeric amount to deposit")
            if hasattr(self, "status_label"):
                self.status_label.config(fg="#6b7280")
            return
        if amount <= 0:
            self.status_var.set("Amount must be greater than 0")
            if hasattr(self, "status_label"):
                self.status_label.config(fg="#6b7280")
            return
        # ลบ entry ทันทีก่อนทำงาน
        self.deposit_entry.delete(0, tk.END)
        self._apply_deposit(amount)

    def _deposit_quick(self, amount):
        # ลบ entry ทันทีก่อนทำงาน
        self.deposit_entry.delete(0, tk.END)
        self._apply_deposit(float(amount))

    def _apply_deposit(self, amount):
        self.cash_balance += amount
        # อัปเดต balance ก่อน - ให้เห็นทันที
        self._update_balance_only()
        # อัปเดต status หลังจากนั้น - เปลี่ยนสีกลับเป็นปกติ
        self.status_var.set(f"Deposited +{amount:,.2f} USDT")
        if hasattr(self, "status_label"):
            self.status_label.config(fg="#6b7280")

    def _withdraw_custom(self):
        try:
            amount = float(self.deposit_entry.get().strip())
        except (TypeError, ValueError):
            self.status_var.set("Enter a numeric amount to withdraw")
            if hasattr(self, "status_label"):
                self.status_label.config(fg="#6b7280")
            return
        if amount <= 0:
            self.status_var.set("Amount must be greater than 0")
            if hasattr(self, "status_label"):
                self.status_label.config(fg="#6b7280")
            return
        # ลบ entry ทันทีก่อนทำงาน
        self.deposit_entry.delete(0, tk.END)
        self._apply_withdraw(amount)

    def _withdraw_quick(self, amount):
        # ลบ entry ทันทีก่อนทำงาน
        self.deposit_entry.delete(0, tk.END)
        self._apply_withdraw(float(amount))

    def _apply_withdraw(self, amount):
        if amount > self.cash_balance:
            self.status_var.set("Insufficient balance to withdraw")
            # เปลี่ยนสีเป็นแดงเมื่อถอนเงินเกิน
            if hasattr(self, "status_label"):
                self.status_label.config(fg="#dc2626")
            return
        self.cash_balance -= amount
        # อัปเดต balance ก่อน - ให้เห็นทันที
        self._update_balance_only()
        # อัปเดต status หลังจากนั้น - เปลี่ยนสีกลับเป็นปกติ
        self.status_var.set(f"Withdrew -{amount:,.2f} USDT")
        if hasattr(self, "status_label"):
            self.status_label.config(fg="#6b7280")

    def _convert_to_usd(self):
        try:
            amount = float(self.exchange_amount_var.get().strip())
        except (TypeError, ValueError):
            self.status_var.set("Enter a numeric amount to convert")
            return
        if amount <= 0:
            self.status_var.set("Amount must be greater than 0")
            return
        asset = self.exchange_asset_var.get()
        holding = self.holdings.get(asset, 0)
        if amount > holding:
            self.status_var.set("Not enough holdings to convert to USD")
            return
        price = self.prices.get(asset, 0)
        if price <= 0:
            self.status_var.set("Market price not available yet, try again")
            return
        quote = amount * price
        self.holdings[asset] = holding - amount
        self.cash_balance += quote
        self.status_var.set(
            f"Converted {amount:.6f} {asset} to $ {quote:,.2f} USD (mock)")
        self._apply_price_update({})

    def _update_exchange_quote(self):
        try:
            amount = float(self.exchange_amount_var.get())
        except (TypeError, ValueError):
            amount = 0
        asset = self.exchange_asset_var.get()
        price = self.prices.get(asset, 0)
        quote = amount * price
        self.exchange_quote_var.set(
            f"$ {quote:,.2f} USD" if quote else "$ -- USD")
        if hasattr(self, "balance_display_var"):
            self.balance_display_var.set(f"$ {self.cash_balance:,.2f} USD")

    def _on_trade_asset_selected(self):
        asset = self.asset_display_to_code.get(self.asset_display_var.get())
        if not asset:
            return
        self.asset_var.set(asset)

    def _on_exchange_asset_selected(self):
        asset = self.asset_display_to_code.get(
            self.exchange_asset_display_var.get())
        if not asset:
            return
        self.exchange_asset_var.set(asset)
        self._update_exchange_quote()
        # Update buy/sell asset selectors if they exist
        if hasattr(self, "buy_asset_display_var"):
            self.buy_asset_display_var.set(
                self.exchange_asset_display_var.get())
            self._update_buy_holdings_display()
        if hasattr(self, "sell_asset_display_var"):
            self.sell_asset_display_var.set(
                self.exchange_asset_display_var.get())
            self._update_sell_holdings_display()

    def _update_buy_holdings_display(self):
        """Update holdings display for buy section"""
        if hasattr(self, "buy_holdings_display_var"):
            asset_display = self.buy_asset_display_var.get() if hasattr(
                self, "buy_asset_display_var") else ""
            if asset_display:
                asset = self.asset_display_to_code.get(asset_display)
                if asset:
                    holdings = self.holdings.get(asset, 0.0)
                    self.buy_holdings_display_var.set(
                        f"Holdings: {holdings:.6f} {asset}")
                    # Update price display (1 crypto = X USD)
                    if hasattr(self, "buy_price_display_var"):
                        price = self.prices.get(asset, 0)
                        self.buy_price_display_var.set(
                            f"1 {asset} = ${price:,.2f}")
                else:
                    self.buy_holdings_display_var.set("Holdings: 0.000000")
                    if hasattr(self, "buy_price_display_var"):
                        self.buy_price_display_var.set("1 BTC = $0.00")
            else:
                self.buy_holdings_display_var.set("Holdings: 0.000000")
                if hasattr(self, "buy_price_display_var"):
                    self.buy_price_display_var.set("1 BTC = $0.00")

    def _update_sell_holdings_display(self):
        """Update holdings display for sell section"""
        if hasattr(self, "sell_holdings_display_var"):
            asset_display = self.sell_asset_display_var.get() if hasattr(
                self, "sell_asset_display_var") else ""
            if asset_display:
                asset = self.asset_display_to_code.get(asset_display)
                if asset:
                    holdings = self.holdings.get(asset, 0.0)
                    self.sell_holdings_display_var.set(
                        f"Holdings: {holdings:.6f} {asset}")
                    # Update price display (1 crypto = X USD)
                    if hasattr(self, "sell_price_display_var"):
                        price = self.prices.get(asset, 0)
                        self.sell_price_display_var.set(
                            f"1 {asset} = ${price:,.2f}")
                else:
                    self.sell_holdings_display_var.set("Holdings: 0.000000")
                    if hasattr(self, "sell_price_display_var"):
                        self.sell_price_display_var.set("1 BTC = $0.00")
            else:
                self.sell_holdings_display_var.set("Holdings: 0.000000")
                if hasattr(self, "sell_price_display_var"):
                    self.sell_price_display_var.set("1 BTC = $0.00")

    def _execute_trade_from_exchange(self, action, amount_entry, asset_display_var):
        """Execute buy/sell trade from Exchange section"""
        try:
            amount = float(amount_entry.get())
        except (TypeError, ValueError):
            status_var = self.buy_status_var if action == "BUY" else self.sell_status_var
            if hasattr(self, "buy_status_var") if action == "BUY" else hasattr(self, "sell_status_var"):
                status_var.set("Enter the amount in numeric form")
            # Clear amount field even on error (like wallet action)
            amount_entry.delete(0, tk.END)
            return
        if amount <= 0:
            status_var = self.buy_status_var if action == "BUY" else self.sell_status_var
            if hasattr(self, "buy_status_var") if action == "BUY" else hasattr(self, "sell_status_var"):
                status_var.set("Amount must be greater than 0")
            # Clear amount field even on error (like wallet action)
            amount_entry.delete(0, tk.END)
            return

        asset_display = asset_display_var.get()
        asset = self.asset_display_to_code.get(asset_display)
        if not asset:
            status_var = self.buy_status_var if action == "BUY" else self.sell_status_var
            if hasattr(self, "buy_status_var") if action == "BUY" else hasattr(self, "sell_status_var"):
                status_var.set("Please select an asset")
            # Clear amount field even on error (like wallet action)
            amount_entry.delete(0, tk.END)
            return

        price = self.prices.get(asset, 0)
        if price <= 0:
            status_var = self.buy_status_var if action == "BUY" else self.sell_status_var
            if hasattr(self, "buy_status_var") if action == "BUY" else hasattr(self, "sell_status_var"):
                status_var.set("Market price not available yet, try again")
            # Clear amount field even on error (like wallet action)
            amount_entry.delete(0, tk.END)
            return

        notional = amount * price
        if action == "BUY":
            if notional > self.cash_balance:
                if hasattr(self, "buy_status_var"):
                    self.buy_status_var.set("Insufficient USDT balance")
                # Clear amount field even on error (like wallet action)
                amount_entry.delete(0, tk.END)
                return
            # Clear amount field immediately after validation (like wallet action)
            amount_entry.delete(0, tk.END)
            self.cash_balance -= notional
            self.holdings[asset] = self.holdings.get(asset, 0) + amount
        else:  # SELL
            holding = self.holdings.get(asset, 0)
            if amount > holding:
                if hasattr(self, "sell_status_var"):
                    self.sell_status_var.set("Not enough holdings to sell")
                # Clear amount field even on error (like wallet action)
                amount_entry.delete(0, tk.END)
                return
            # Clear amount field immediately after validation (like wallet action)
            amount_entry.delete(0, tk.END)
            self.holdings[asset] = holding - amount
            self.cash_balance += notional

        # Update displays
        self._update_buy_holdings_display()
        self._update_sell_holdings_display()
        # Update cash balance display
        self.cash_var.set(f"USDT Balance: $ {self.cash_balance:,.2f}")
        # Update total value
        total = self.cash_balance
        for asset, amount in self.holdings.items():
            price = self.prices.get(asset, 0)
            total += amount * price
        self.total_value_var.set(f"Total: $ {total:,.2f}")
        if hasattr(self, "balance_display_var"):
            self.balance_display_var.set(f"$ {self.cash_balance:,.2f} USD")
        # Update holdings table
        self._apply_price_update({})

        # Update status message
        status_var = self.buy_status_var if action == "BUY" else self.sell_status_var
        if hasattr(self, "buy_status_var") if action == "BUY" else hasattr(self, "sell_status_var"):
            status_var.set(
                f"{action} {amount:.6f} {asset} @ {price:,.2f} (mock)")

        # Call trade callback if available - ensure asset is code, not display name
        if callable(self.on_trade):
            # asset should already be the code from asset_display_to_code.get()
            # Ensure it's uppercase and valid - same logic as overview.py
            asset_code = str(asset).strip().upper() if asset else None
            # Validate asset code is in holdings
            if asset_code and asset_code in self.holdings:
                # Call callback with validated asset code (uppercase string)
                self.on_trade(action, asset_code, amount, price, notional)
            else:
                # Fallback: try to get asset code again from display name
                fallback_asset = self.asset_display_to_code.get(asset_display)
                if fallback_asset:
                    fallback_asset = str(fallback_asset).strip().upper()
                    if fallback_asset and fallback_asset in self.holdings:
                        self.on_trade(action, fallback_asset,
                                      amount, price, notional)

        # Notify overview of balance/total change after trade
        # (balance already updated via _apply_price_update, but we need to notify here too)
        if callable(self.on_balance_change):
            holdings_value = sum(amt * self.prices.get(ast, 0)
                                 for ast, amt in self.holdings.items())
            total_value = self.cash_balance + holdings_value
            self.on_balance_change(
                self.cash_balance, self.holdings.copy(), total_value)

        # Notify overview of balance/total change after trade
        if callable(self.on_balance_change):
            holdings_value = sum(amt * self.prices.get(ast, 0)
                                 for ast, amt in self.holdings.items())
            total_value = self.cash_balance + holdings_value
            self.on_balance_change(
                self.cash_balance, self.holdings.copy(), total_value)

    def _build_asset_options(self):
        options = []
        for asset in self.holdings.keys():
            name = self._get_asset_display_name(asset)
            label = f"{asset} • {name}" if name != asset else asset
            options.append((asset, label))
        return options

    def _get_asset_display_name(self, asset):
        return ASSET_DISPLAY_NAMES.get(asset, asset)

    def _format_asset_hint(self, asset):
        name = self._get_asset_display_name(asset)
        return f"{name} ({asset})" if name != asset else asset

    def sync_from_overview(self, balance, holdings):
        """Sync balance and holdings from overview panel"""
        self.cash_balance = balance
        # Update holdings for all assets
        for asset in self.holdings.keys():
            self.holdings[asset] = holdings.get(asset, 0.0)
        # Update displays
        self._update_buy_holdings_display()
        self._update_sell_holdings_display()
        self._update_balance_only()
        # Update holdings table
        self._apply_price_update({})

    def get_balance_and_holdings(self):
        """Get current balance and holdings for syncing"""
        return self.cash_balance, self.holdings.copy()
