import tkinter as tk
from tkinter import ttk
import threading
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
        tk.Label(
            header,
            text="Wallet Overview (Mock)",
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
            font=("Helvetica", 15, "bold"),
        ).pack(side=tk.LEFT)

        self.total_value_var = tk.StringVar(value="Total: $ --")
        tk.Label(
            header,
            textvariable=self.total_value_var,
            bg=self.theme["panel"],
            fg=self.theme["accent_green"],
            font=("Helvetica", 13, "bold"),
        ).pack(side=tk.RIGHT)

        self._build_exchange_section()

        balances = tk.Frame(self.frame, bg=self.theme["panel"])
        balances.pack(fill=tk.X, pady=(10, 0))
        self.cash_var = tk.StringVar(value="USDT Balance: --")
        tk.Label(
            balances,
            textvariable=self.cash_var,
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
            font=("Helvetica", 12),
        ).pack(anchor="w")

        style = ttk.Style()
        style.configure(
            "Wallet.Treeview",
            background=self.theme["panel"],
            fieldbackground=self.theme["panel"],
            foreground=self.theme["text_primary"],
        )
        style.configure(
            "Wallet.Treeview.Heading",
            background=self.theme["panel"],
            foreground=self.theme["text_muted"],
            font=("Helvetica", 11, "bold"),
        )

        self.tree = ttk.Treeview(
            self.frame,
            columns=("amount", "price", "value"),
            show="headings",
            height=7,
            style="Wallet.Treeview",
        )
        self.tree.heading("amount", text="Amount")
        self.tree.heading("price", text="Price (USDT)")
        self.tree.heading("value", text="Value (USDT)")
        self.tree.column("amount", width=90, anchor="center")
        self.tree.column("price", width=110, anchor="center")
        self.tree.column("value", width=110, anchor="center")
        self.tree.pack(fill=tk.X, pady=10)

        controls = tk.Frame(self.frame, bg=self.theme["panel"])
        controls.pack(fill=tk.X, pady=(5, 0))
        tk.Label(
            controls,
            text="Asset (Coin)",
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            controls,
            text="Amount",
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
        ).grid(row=0, column=1, sticky="w")

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
            bg=self.theme["panel"],
            fg=self.theme["text_muted"],
            font=("Helvetica", 9),
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        self.amount_entry.grid(row=1, column=1, padx=(0, 10), pady=4, sticky="w")

        buttons = tk.Frame(controls, bg=self.theme["panel"])
        buttons.grid(row=1, column=2, padx=6, sticky="w")
        ttk.Button(buttons, text="Buy (Mock)", command=lambda: self._execute_trade("BUY")).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(buttons, text="Sell (Mock)", command=lambda: self._execute_trade("SELL")).pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Create mock orders to rebalance the portfolio")
        tk.Label(
            self.frame,
            textvariable=self.status_var,
            bg=self.theme["panel"],
            fg=self.theme["text_muted"],
            anchor="w",
        ).pack(fill=tk.X, pady=(8, 0))

        self._build_deposit_section()
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
                values=(f"{amount:.6f}", f"{price:,.2f}", f"{amount * price:,.2f}"),
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
        card = tk.Frame(self.frame, bg="#f5f5f5", padx=16, pady=14)
        card.pack(fill=tk.X, pady=(10, 12))
        tk.Label(
            card,
            text="Exchange",
            font=("Helvetica", 13, "bold"),
            fg="#111",
            bg="#f5f5f5",
        ).pack(anchor="w")

        default_asset = self.asset_options[0][0]
        self.exchange_asset_var = tk.StringVar(value=default_asset)
        self.exchange_amount_var = tk.StringVar(value="1.0")
        self.exchange_quote_var = tk.StringVar(value="$ -- USD")
        self.exchange_asset_display_var = tk.StringVar(value=self.asset_code_to_display[default_asset])

        display = tk.Frame(card, bg="#f5f5f5")
        display.pack(fill=tk.X, pady=(6, 8))
        self.exchange_label_var = tk.StringVar(value=f"1 {self._format_asset_hint(default_asset)} >>>")
        tk.Label(
            display,
            textvariable=self.exchange_label_var,
            font=("Helvetica", 12),
            fg="#4b5563",
            bg="#f5f5f5",
        ).pack(side=tk.LEFT)
        tk.Label(
            display,
            textvariable=self.exchange_quote_var,
            font=("Helvetica", 12, "bold"),
            fg="#4b5563",
            bg="#f5f5f5",
        ).pack(side=tk.RIGHT)

        input_box = tk.Frame(card, bg="#f5f5f5")
        input_box.pack(fill=tk.X, pady=4)
        asset_frame = tk.Frame(input_box, bg="#fff", bd=0, relief="flat")
        asset_frame.pack(fill=tk.X)
        amount_entry = tk.Entry(asset_frame, textvariable=self.exchange_amount_var, bd=0, font=("Helvetica", 13))
        amount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0), pady=6)
        asset_combo = ttk.Combobox(
            asset_frame,
            values=list(self.asset_display_to_code.keys()),
            textvariable=self.exchange_asset_display_var,
            state="readonly",
            width=18,
        )
        asset_combo.pack(side=tk.RIGHT, padx=8, pady=6)

        self.exchange_amount_var.trace_add("write", lambda *_: self._update_exchange_quote())
        asset_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_exchange_asset_selected())
        amount_entry.bind("<FocusOut>", lambda _e: self._update_exchange_quote())

        action_row = tk.Frame(card, bg="#f5f5f5")
        action_row.pack(fill=tk.X, pady=(4, 4))
        ttk.Button(action_row, text="Convert to USD", command=self._convert_to_usd).pack(side=tk.RIGHT)

        tk.Label(
            card,
            text="Balance",
            font=("Helvetica", 12, "bold"),
            fg="#111",
            bg="#f5f5f5",
        ).pack(anchor="w", pady=(8, 0))

        balance_display = tk.Frame(card, bg="#fff")
        balance_display.pack(fill=tk.X, pady=(4, 0))
        self.balance_display_var = tk.StringVar(value="$ -- USD")
        tk.Label(
            balance_display,
            textvariable=self.balance_display_var,
            font=("Helvetica", 13, "bold"),
            fg="#111",
            bg="#fff",
            anchor="w",
        ).pack(fill=tk.X, padx=10, pady=8)

    def _build_deposit_section(self):
        section = tk.Frame(self.frame, bg=self.theme["panel"])
        section.pack(fill=tk.X, pady=(12, 0))
        tk.Label(
            section,
            text="Wallet actions",
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
            font=("Helvetica", 12, "bold"),
        ).pack(anchor="w")

        input_row = tk.Frame(section, bg=self.theme["panel"])
        input_row.pack(fill=tk.X, pady=(6, 2))
        self.deposit_entry = tk.Entry(input_row)
        self.deposit_entry.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            input_row,
            text="Deposit",
            command=lambda: self._handle_wallet_action("deposit"),
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            input_row,
            text="Withdraw",
            command=lambda: self._handle_wallet_action("withdraw"),
        ).pack(side=tk.LEFT)

        self.quick_deposit_frame = tk.LabelFrame(
            section,
            text="Quick deposit",
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
        )
        self.quick_withdraw_frame = tk.LabelFrame(
            section,
            text="Quick withdraw",
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
        )
        for amount in (1000, 5000, 10000):
            ttk.Button(
                self.quick_deposit_frame,
                text=f"{amount:,}",
                command=lambda amt=amount: self._deposit_quick(amt),
            ).pack(side=tk.LEFT, padx=(0, 6), pady=4)
        for amount in (1000, 5000, 10000):
            ttk.Button(
                self.quick_withdraw_frame,
                text=f"{amount:,}",
                command=lambda amt=amount: self._withdraw_quick(amt),
            ).pack(side=tk.LEFT, padx=(0, 6), pady=4)

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
        self.balance_display_var.set(f"$ {self.cash_balance:,.2f} USD")
        amount_label = "0" if amount == 0 else f"{amount:.6g}"
        self.exchange_label_var.set(f"{amount_label} {self._format_asset_hint(asset)} >>>")

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
