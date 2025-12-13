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


class WalletPanel:
    """กระเป๋าเงินจำลอง + ปุ่ม Buy/Sell (mock)"""

    def __init__(self, parent, theme=None, on_trade=None):
        self.parent = parent
        self.theme = theme or THEME
        self.on_trade = on_trade
        self.is_running = False
        self.cash_balance = WALLET_CASH_BALANCE
        self.holdings = WALLET_HOLDINGS.copy()
        self.prices = {asset: 0.0 for asset in self.holdings}

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
            text="Asset",
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            controls,
            text="Amount",
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
        ).grid(row=0, column=1, sticky="w")

        self.asset_var = tk.StringVar(value=list(self.holdings.keys())[0])
        self.amount_entry = tk.Entry(controls)
        asset_menu = ttk.Combobox(
            controls,
            values=list(self.holdings.keys()),
            textvariable=self.asset_var,
            state="readonly",
            width=8,
        )
        asset_menu.grid(row=1, column=0, padx=(0, 10), pady=4, sticky="w")
        self.amount_entry.grid(row=1, column=1, padx=(0, 10), pady=4, sticky="w")

        buttons = tk.Frame(controls, bg=self.theme["panel"])
        buttons.grid(row=1, column=2, padx=6, sticky="w")
        ttk.Button(buttons, text="Buy (Mock)", command=lambda: self._execute_trade("BUY")).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(buttons, text="Sell (Mock)", command=lambda: self._execute_trade("SELL")).pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="ตั้งคำสั่ง mock เพื่อปรับพอร์ต")
        tk.Label(
            self.frame,
            textvariable=self.status_var,
            bg=self.theme["panel"],
            fg=self.theme["text_muted"],
            anchor="w",
        ).pack(fill=tk.X, pady=(8, 0))

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
            self.status_var.set("ระบุจำนวนในรูปแบบตัวเลข")
            return
        if amount <= 0:
            self.status_var.set("จำนวนต้องมากกว่า 0")
            return

        asset = self.asset_var.get()
        price = self.prices.get(asset, 0)
        if price <= 0:
            self.status_var.set("ยังไม่มีราคาจากตลาด ลองใหม่อีกครั้ง")
            return

        notional = amount * price
        if action == "BUY":
            if notional > self.cash_balance:
                self.status_var.set("ยอด USDT ไม่พอ")
                return
            self.cash_balance -= notional
            self.holdings[asset] = self.holdings.get(asset, 0) + amount
        else:
            holding = self.holdings.get(asset, 0)
            if amount > holding:
                self.status_var.set("ถือเหรียญไม่พอจะขาย")
                return
            self.holdings[asset] = holding - amount
            self.cash_balance += notional

        self.status_var.set(f"{action} {amount} {asset} @ {price:,.2f} (mock)")
        self.amount_entry.delete(0, tk.END)
        self._apply_price_update({})
        if callable(self.on_trade):
            self.on_trade(action, asset, amount, price, notional)
