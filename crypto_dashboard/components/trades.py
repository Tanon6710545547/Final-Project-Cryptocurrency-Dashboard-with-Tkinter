import os
import sys
import tkinter as tk
from tkinter import ttk
import websocket
import threading
import json

if __package__ is None or __package__ == "":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from config import MAX_TRADES_DISPLAY  # type: ignore
else:
    from ..config import MAX_TRADES_DISPLAY


class TradesPanel:
    """Real-time trade feed powered by the Binance @aggTrade WebSocket"""

    def __init__(self, parent, symbol):
        self.parent = parent
        self.symbol = symbol.lower()
        self.active = False
        self.ws = None
        self.trades = []

        self.frame = ttk.LabelFrame(parent, text=f"Recent Trades - {self.symbol.upper()}", padding=10)

        self.text = tk.Text(self.frame, height=15, width=60, state="disabled")
        self.text.pack(fill=tk.BOTH, expand=True)

    def start(self):
        if self.active:
            return
        self.active = True

        url = f"wss://stream.binance.com:9443/ws/{self.symbol}@aggTrade"

        self.ws = websocket.WebSocketApp(
            url,
            on_message=self.on_message,
            on_error=lambda ws, err: print(f"{self.symbol} trades error:", err),
            on_close=lambda ws, s, m: print(f"{self.symbol} trades closed"),
            on_open=lambda ws: print(f"{self.symbol} trades connected"),
        )

        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def stop(self):
        self.active = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

    def on_message(self, ws, msg):
        if not self.active:
            return
        data = json.loads(msg)
        try:
            price = float(data["p"])
            qty = float(data["q"])
            is_buyer_maker = data["m"]  # True = seller side, False = buyer side
        except (KeyError, ValueError):
            return

        side = "SELL" if is_buyer_maker else "BUY"
        line = f"{side:4}  {qty:.6f} @ {price:,.2f}"

        self.trades.insert(0, line)
        self.trades = self.trades[:MAX_TRADES_DISPLAY]

        self.parent.after(0, self.update_text)

    def update_text(self):
        if not self.active:
            return
        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)
        for line in self.trades:
            self.text.insert(tk.END, line + "\n")
        self.text.config(state="disabled")

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
