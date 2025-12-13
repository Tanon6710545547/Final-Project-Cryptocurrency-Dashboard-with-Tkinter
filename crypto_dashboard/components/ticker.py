import tkinter as tk
import websocket
import threading
import json


class CryptoTicker:
    """Display a price/statistics summary card similar to the mockup"""

    def __init__(self, parent, symbol, display_name, theme):
        self.parent = parent
        self.symbol = symbol.lower()
        self.display_name = display_name
        self.theme = theme
        self.active = False
        self.ws = None

        self.frame = tk.Frame(
            parent,
            bg=self.theme["panel"],
            padx=24,
            pady=20,
            highlightbackground=self.theme["panel_border"],
            highlightthickness=1,
        )

        self._build_cards()

    def _build_cards(self):
        self.title_label = tk.Label(
            self.frame,
            text=self.display_name,
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
            font=("Helvetica", 16, "bold"),
        )
        self.title_label.pack(anchor="w")

        cards = tk.Frame(self.frame, bg=self.theme["panel"])
        cards.pack(fill=tk.X, pady=(10, 0))

        self.price_card = self._create_card(cards, "Last Traded Price")
        self.bid_card = self._create_card(cards, "Best Bid / Ask & Spread")
        self.volume_card = self._create_card(cards, "24h Stats")

        self.price_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.bid_card.grid(row=0, column=1, sticky="nsew", padx=5)
        self.volume_card.grid(row=0, column=2, sticky="nsew", padx=(10, 0))

        cards.columnconfigure((0, 1, 2), weight=1)

        self.price_value = tk.Label(
            self.price_card,
            text="--,--",
            bg=self.theme["panel"],
            fg=self.theme["text_primary"],
            font=("Helvetica", 36, "bold"),
        )
        self.price_value.pack(anchor="w", pady=(8, 0))

        self.change_label = tk.Label(
            self.price_card,
            text="--",
            bg=self.theme["panel"],
            fg=self.theme["text_muted"],
            font=("Helvetica", 14),
        )
        self.change_label.pack(anchor="w")

        self.bid_value = self._create_stat_row(
            self.bid_card, "Bid (Buy)", fg=self.theme["accent_green"]
        )
        self.ask_value = self._create_stat_row(
            self.bid_card, "Ask (Sell)", fg=self.theme["accent_red"]
        )
        self.spread_value = self._create_stat_row(
            self.bid_card, "Spread", fg=self.theme["accent_orange"]
        )

        self.high_value = self._create_stat_row(self.volume_card, "High")
        self.low_value = self._create_stat_row(self.volume_card, "Low")
        self.vol_value = self._create_stat_row(self.volume_card, "Quote Volume")

    def _create_card(self, parent, title):
        card = tk.Frame(
            parent,
            bg=self.theme["panel"],
        )
        tk.Label(
            card,
            text=title,
            bg=self.theme["panel"],
            fg=self.theme["text_muted"],
            font=("Helvetica", 12, "bold"),
        ).pack(anchor="w")
        tk.Frame(card, bg=self.theme["divider"], height=2).pack(fill=tk.X, pady=(4, 6))
        return card

    def _create_stat_row(self, parent, label, fg=None):
        row = tk.Frame(parent, bg=self.theme["panel"])
        row.pack(fill=tk.X, pady=2)
        tk.Label(
            row,
            text=label,
            bg=self.theme["panel"],
            fg=self.theme["text_muted"],
            font=("Helvetica", 11),
        ).pack(side=tk.LEFT)
        value_label = tk.Label(
            row,
            text="--",
            bg=self.theme["panel"],
            fg=fg or self.theme["text_primary"],
            font=("Helvetica", 12, "bold"),
        )
        value_label.pack(side=tk.RIGHT)
        return value_label

    def start(self):
        """Open the WebSocket stream and start receiving prices"""
        if self.active:
            return
        self.active = True

        url = f"wss://stream.binance.com:9443/ws/{self.symbol}@ticker"

        self.ws = websocket.WebSocketApp(
            url,
            on_message=self.on_message,
            on_error=lambda ws, err: print(f"{self.symbol} error:", err),
            on_close=lambda ws, status, msg: print(f"{self.symbol} closed"),
            on_open=lambda ws: print(f"{self.symbol} connected"),
        )

        thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        thread.start()

    def stop(self):
        """Close the WebSocket connection"""
        self.active = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        self.ws = None

    def set_symbol(self, symbol, display_name):
        """Change the ticker symbol and restart the socket if needed"""
        new_symbol = symbol.lower()
        if new_symbol == self.symbol and display_name == self.display_name:
            return

        was_active = self.active
        if was_active:
            self.stop()

        self.symbol = new_symbol
        self.display_name = display_name
        self.title_label.config(text=self.display_name)

        if was_active:
            self.start()

    def on_message(self, ws, msg):
        if not self.active:
            return

        data = json.loads(msg)
        try:
            price = float(data["c"])
            change = float(data["p"])
            percent = float(data["P"])
            bid = float(data["b"])
            ask = float(data["a"])
            high = float(data["h"])
            low = float(data["l"])
            quote_volume = float(data["q"])
        except (KeyError, ValueError):
            return

        payload = {
            "price": price,
            "change": change,
            "percent": percent,
            "bid": bid,
            "ask": ask,
            "high": high,
            "low": low,
            "quote_volume": quote_volume,
        }
        self.parent.after(0, self.update_display, payload)

    def update_display(self, payload):
        if not self.active:
            return

        price = payload["price"]
        change = payload["change"]
        percent = payload["percent"]
        bid = payload["bid"]
        ask = payload["ask"]
        high = payload["high"]
        low = payload["low"]
        quote_volume = payload["quote_volume"]

        color = self.theme["accent_green"] if change >= 0 else self.theme["accent_red"]
        sign = "+" if change >= 0 else ""

        self.price_value.config(text=f"{price:,.2f}", fg=color)
        self.change_label.config(
            text=f"{sign}{change:,.2f} ({sign}{percent:.2f}%)",
            fg=color,
        )

        spread = ask - bid if ask and bid else 0.0
        self.bid_value.config(text=f"{bid:,.2f}")
        self.ask_value.config(text=f"{ask:,.2f}")
        self.spread_value.config(text=f"{spread:,.4f}")

        self.high_value.config(text=f"{high:,.2f}")
        self.low_value.config(text=f"{low:,.2f}")
        self.vol_value.config(text=f"{quote_volume:,.0f}")

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def pack_forget(self):
        self.frame.pack_forget()
