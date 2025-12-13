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

    def __init__(self, parent, theme=None, on_trade=None):
        self.parent = parent
        self.theme = theme or THEME
        self.on_trade = on_trade
        self.is_running = False
        self.cash_balance = WALLET_CASH_BALANCE
        self.holdings = WALLET_HOLDINGS.copy()
        self.prices = {asset: 0.0 for asset in self.holdings}
        self.asset_options = self._build_asset_options()
        self.asset_display_to_code = {label: code for code, label in self.asset_options}
        self.asset_code_to_display = {code: label for code, label in self.asset_options}
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

        self.total_value_var = tk.StringVar(value="Total: $ --")
        tk.Label(
            header,
            textvariable=self.total_value_var,
            bg=self.surface,
            fg="#16a34a",
            font=("Helvetica", 15, "bold"),
        ).pack(side=tk.RIGHT)

        balances = tk.Frame(self.frame, bg=self.surface)
        balances.pack(fill=tk.X, pady=(10, 0))
        self.cash_var = tk.StringVar(value="USDT Balance: --")
        tk.Label(
            balances,
            textvariable=self.cash_var,
            bg=self.surface,
            fg="#111827",
            font=("Helvetica", 12, "bold"),
        ).pack(anchor="w")

        # Add Exchange section
        self._build_exchange_section()

        controls = tk.Frame(self.frame, bg=self.surface)
        controls.pack(fill=tk.X, pady=(10, 0))
        tk.Label(
            controls,
            text="Asset (Coin)",
            bg=self.surface,
            fg="#111827",
            font=("Helvetica", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        tk.Label(
            controls,
            text="Amount",
            bg=self.surface,
            fg="#111827",
            font=("Helvetica", 11, "bold"),
        ).grid(row=0, column=1, sticky="w", pady=(0, 4))

        default_asset = self.asset_options[0][0]
        self.asset_var = tk.StringVar(value=default_asset)
        self.amount_entry = tk.Entry(controls)
        self.asset_display_var = tk.StringVar(value=self.asset_code_to_display[default_asset])
        asset_menu = ttk.Combobox(
            controls,
            values=list(self.asset_display_to_code.keys()),
            textvariable=self.asset_display_var,
            state="readonly",
            width=18,
        )
        asset_menu.grid(row=1, column=0, padx=(0, 10), pady=4, sticky="w")
        asset_menu.bind("<<ComboboxSelected>>", lambda _e: self._on_trade_asset_selected())
        self.asset_hint_var = tk.StringVar(value=self._format_asset_hint(default_asset))
        tk.Label(
            controls,
            textvariable=self.asset_hint_var,
            bg=self.surface,
            fg="#6b7280",
            font=("Helvetica", 9),
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))
        
        # Style the entry field
        self.amount_entry.config(
            bg="#ffffff",
            fg="#111827",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#d1d5db",
            highlightcolor="#3b82f6",
            insertbackground="#111827",
            font=("Helvetica", 12)
        )
        self.amount_entry.grid(row=1, column=1, padx=(0, 10), pady=4, sticky="w", ipady=6)

        buttons = tk.Frame(controls, bg=self.surface)
        buttons.grid(row=1, column=2, padx=6, sticky="w")
        
        # Style buttons to match app design
        buy_btn = tk.Button(
            buttons,
            text="Buy (Mock)",
            font=("Helvetica", 11, "bold"),
            bg="#16a34a",
            fg="white",
            relief="flat",
            padx=16,
            pady=6,
            command=lambda: self._execute_trade("BUY"),
            cursor="hand2",
            activebackground="#15803d",
            activeforeground="white",
            bd=0,
            highlightthickness=0
        )
        buy_btn.pack(side=tk.LEFT, padx=(0, 6))
        
        sell_btn = tk.Button(
            buttons,
            text="Sell (Mock)",
            font=("Helvetica", 11, "bold"),
            bg="#dc2626",
            fg="white",
            relief="flat",
            padx=16,
            pady=6,
            command=lambda: self._execute_trade("SELL"),
            cursor="hand2",
            activebackground="#b91c1c",
            activeforeground="white",
            bd=0,
            highlightthickness=0
        )
        sell_btn.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Create mock orders to rebalance the portfolio")
        tk.Label(
            self.frame,
            textvariable=self.status_var,
            bg=self.surface,
            fg="#6b7280",
            anchor="w",
            font=("Helvetica", 10),
        ).pack(fill=tk.X, pady=(10, 0))

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

        for row in self.tree.get_children():
            self.tree.delete(row)
        for asset, amount in self.holdings.items():
            price = self.prices.get(asset, 0)
            self.tree.insert(
                "",
                tk.END,
                values=(asset, f"{amount:.6f}", f"{price:,.2f}", f"{amount * price:,.2f}"),
                tags=(asset,),
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
        self.exchange_asset_display_var = tk.StringVar(value=self.asset_code_to_display[default_asset])

        # Conversion display
        display = tk.Frame(card, bg="#f9fafb")
        display.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            display,
            text="1 unit converts to",
            font=("Helvetica", 11),
            fg="#6b7280",
            bg="#f9fafb",
        ).pack(side=tk.LEFT)
        tk.Label(
            display,
            textvariable=self.exchange_quote_var,
            font=("Helvetica", 14, "bold"),
            fg="#111827",
            bg="#f9fafb",
        ).pack(side=tk.RIGHT)

        # Input section
        input_box = tk.Frame(card, bg="#f9fafb")
        input_box.pack(fill=tk.X, pady=(0, 10))
        
        amount_frame = tk.Frame(input_box, bg="#f9fafb")
        amount_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(
            amount_frame,
            text="Amount",
            font=("Helvetica", 10, "bold"),
            fg="#6b7280",
            bg="#f9fafb",
        ).pack(anchor="w", pady=(0, 4))
        
        asset_frame = tk.Frame(input_box, bg="#f9fafb")
        asset_frame.pack(side=tk.RIGHT, padx=(12, 0))
        tk.Label(
            asset_frame,
            text="Asset",
            font=("Helvetica", 10, "bold"),
            fg="#6b7280",
            bg="#f9fafb",
        ).pack(anchor="w", pady=(0, 4))
        
        entry_container = tk.Frame(amount_frame, bg="#ffffff", highlightthickness=1, highlightbackground="#d1d5db")
        entry_container.pack(fill=tk.X)
        amount_entry = tk.Entry(
            entry_container,
            textvariable=self.exchange_amount_var,
            bd=0,
            font=("Helvetica", 13, "bold"),
            bg="#ffffff",
            fg="#111827",
            highlightthickness=0,
            insertbackground="#111827"
        )
        amount_entry.pack(fill=tk.X, padx=10, pady=8)
        
        asset_combo = ttk.Combobox(
            asset_frame,
            values=list(self.asset_display_to_code.keys()),
            textvariable=self.exchange_asset_display_var,
            state="readonly",
            width=18,
            font=("Helvetica", 12, "bold")
        )
        asset_combo.pack(fill=tk.X)

        self.exchange_amount_var.trace_add("write", lambda *_: self._update_exchange_quote())
        asset_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_exchange_asset_selected())
        amount_entry.bind("<FocusOut>", lambda _e: self._update_exchange_quote())

        # Convert button
        action_row = tk.Frame(card, bg="#f9fafb")
        action_row.pack(fill=tk.X, pady=(0, 12))
        convert_btn = tk.Button(
            action_row,
            text="Convert to USD",
            font=("Helvetica", 11, "bold"),
            bg="#3b82f6",
            fg="white",
            relief="flat",
            padx=16,
            pady=8,
            command=self._convert_to_usd,
            cursor="hand2",
            activebackground="#2563eb",
            activeforeground="white",
            bd=0,
            highlightthickness=0
        )
        convert_btn.pack(side=tk.RIGHT)

        # Balance section
        tk.Label(
            card,
            text="Balance",
            font=("Helvetica", 12, "bold"),
            fg="#6b7280",
            bg="#f9fafb",
        ).pack(anchor="w", pady=(0, 4))

        balance_display = tk.Frame(card, bg="#ffffff", highlightthickness=1, highlightbackground="#e5e7eb")
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
        section = tk.Frame(self.frame, bg=self.surface)
        section.pack(fill=tk.X, pady=(12, 0))
        tk.Label(
            section,
            text="Wallet Actions",
            bg=self.surface,
            fg="#111827",
            font=("Helvetica", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        input_row = tk.Frame(section, bg=self.surface)
        input_row.pack(fill=tk.X, pady=(0, 8))
        
        # Entry field with styling
        entry_container = tk.Frame(input_row, bg="#ffffff", highlightthickness=1, highlightbackground="#d1d5db")
        entry_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.deposit_entry = tk.Entry(
            entry_container,
            bd=0,
            font=("Helvetica", 12),
            bg="#ffffff",
            fg="#111827",
            highlightthickness=0,
            insertbackground="#111827"
        )
        self.deposit_entry.pack(fill=tk.X, padx=10, pady=8)
        
        # Buttons with modern styling
        deposit_btn = tk.Button(
            input_row,
            text="Deposit",
            font=("Helvetica", 11, "bold"),
            bg="#16a34a",
            fg="white",
            relief="flat",
            padx=20,
            pady=8,
            command=lambda: self._handle_wallet_action("deposit"),
            cursor="hand2",
            activebackground="#15803d",
            activeforeground="white",
            bd=0,
            highlightthickness=0
        )
        deposit_btn.pack(side=tk.LEFT, padx=(0, 6))
        
        withdraw_btn = tk.Button(
            input_row,
            text="Withdraw",
            font=("Helvetica", 11, "bold"),
            bg="#dc2626",
            fg="white",
            relief="flat",
            padx=20,
            pady=8,
            command=lambda: self._handle_wallet_action("withdraw"),
            cursor="hand2",
            activebackground="#b91c1c",
            activeforeground="white",
            bd=0,
            highlightthickness=0
        )
        withdraw_btn.pack(side=tk.LEFT)

        # Quick action frames with better styling
        self.quick_deposit_frame = tk.Frame(section, bg=self.surface)
        self.quick_withdraw_frame = tk.Frame(section, bg=self.surface)
        
        # Quick deposit section
        deposit_label = tk.Label(
            self.quick_deposit_frame,
            text="Quick Deposit",
            bg=self.surface,
            fg="#6b7280",
            font=("Helvetica", 10, "bold"),
        )
        deposit_label.pack(anchor="w", pady=(0, 6))
        
        deposit_buttons = tk.Frame(self.quick_deposit_frame, bg=self.surface)
        deposit_buttons.pack(fill=tk.X)
        
        # Quick withdraw section
        withdraw_label = tk.Label(
            self.quick_withdraw_frame,
            text="Quick Withdraw",
            bg=self.surface,
            fg="#6b7280",
            font=("Helvetica", 10, "bold"),
        )
        withdraw_label.pack(anchor="w", pady=(0, 6))
        
        withdraw_buttons = tk.Frame(self.quick_withdraw_frame, bg=self.surface)
        withdraw_buttons.pack(fill=tk.X)
        
        for amount in (1000, 5000, 10000):
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
                activebackground="#e5e7eb",
                activeforeground="#111827",
                bd=0,
                highlightthickness=0
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
        
        for amount in (1000, 5000, 10000):
            btn = tk.Button(
                withdraw_buttons,
                text=f"{amount:,}",
                font=("Helvetica", 10, "bold"),
                bg="#f3f4f6",
                fg="#111827",
                relief="flat",
                padx=16,
                pady=6,
                command=lambda amt=amount: self._withdraw_quick(amt),
                cursor="hand2",
                activebackground="#e5e7eb",
                activeforeground="#111827",
                bd=0,
                highlightthickness=0
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))

        self._show_quick_panel(None)


    def _show_quick_panel(self, mode):
        self.wallet_action_mode = mode
        if hasattr(self, "quick_deposit_frame"):
            self.quick_deposit_frame.pack_forget()
        if hasattr(self, "quick_withdraw_frame"):
            self.quick_withdraw_frame.pack_forget()
        if mode == "deposit" and hasattr(self, "quick_deposit_frame"):
            self.quick_deposit_frame.pack(fill=tk.X, pady=(4, 0))
        elif mode == "withdraw" and hasattr(self, "quick_withdraw_frame"):
            self.quick_withdraw_frame.pack(fill=tk.X, pady=(4, 0))


    def _handle_wallet_action(self, mode):
        self._show_quick_panel(mode)
        entry_value = self.deposit_entry.get().strip()
        if not entry_value:
            return
        if mode == "deposit":
            self._deposit_custom()
        else:
            self._withdraw_custom()

    def _deposit_custom(self):
        try:
            amount = float(self.deposit_entry.get().strip())
        except (TypeError, ValueError):
            self.status_var.set("Enter a numeric amount to deposit")
            return
        if amount <= 0:
            self.status_var.set("Amount must be greater than 0")
            return
        self._apply_deposit(amount)
        self.deposit_entry.delete(0, tk.END)

    def _deposit_quick(self, amount):
        self._apply_deposit(float(amount))

    def _apply_deposit(self, amount):
        self.cash_balance += amount
        self.status_var.set(f"Deposited +{amount:,.2f} USDT")
        self._apply_price_update({})

    def _withdraw_custom(self):
        try:
            amount = float(self.deposit_entry.get().strip())
        except (TypeError, ValueError):
            self.status_var.set("Enter a numeric amount to withdraw")
            return
        if amount <= 0:
            self.status_var.set("Amount must be greater than 0")
            return
        self.deposit_entry.delete(0, tk.END)
        self._apply_withdraw(amount)

    def _withdraw_quick(self, amount):
        self._apply_withdraw(float(amount))

    def _apply_withdraw(self, amount):
        if amount > self.cash_balance:
            self.status_var.set("Insufficient balance to withdraw")
            return
        self.cash_balance -= amount
        self.status_var.set(f"Withdrew -{amount:,.2f} USDT")
        self._apply_price_update({})

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
        self.status_var.set(f"Converted {amount:.6f} {asset} to $ {quote:,.2f} USD (mock)")
        self._apply_price_update({})

    def _update_exchange_quote(self):
        try:
            amount = float(self.exchange_amount_var.get())
        except (TypeError, ValueError):
            amount = 0
        asset = self.exchange_asset_var.get()
        price = self.prices.get(asset, 0)
        quote = amount * price
        self.exchange_quote_var.set(f"$ {quote:,.2f} USD" if quote else "$ -- USD")
        if hasattr(self, "balance_display_var"):
            self.balance_display_var.set(f"$ {self.cash_balance:,.2f} USD")

    def _on_trade_asset_selected(self):
        asset = self.asset_display_to_code.get(self.asset_display_var.get())
        if not asset:
            return
        self.asset_var.set(asset)
        self.asset_hint_var.set(self._format_asset_hint(asset))

    def _on_exchange_asset_selected(self):
        asset = self.asset_display_to_code.get(self.exchange_asset_display_var.get())
        if not asset:
            return
        self.exchange_asset_var.set(asset)
        self._update_exchange_quote()

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
