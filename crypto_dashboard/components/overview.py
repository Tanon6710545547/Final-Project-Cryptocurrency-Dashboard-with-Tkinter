import tkinter as tk
from tkinter import ttk
import threading
from datetime import datetime
from ..config import OVERVIEW_REFRESH_MS, THEME
from ..utils.binance_rest import get_24hr_ticker, get_klines


FAVORITE_LAYOUT = [
    ("BTC", {"bg": "#fde68a", "fg": "#1f2937", "accent": "#10b981"}),
    ("ETH", {"bg": "#e0e7ff", "fg": "#1e1b4b", "accent": "#6366f1"}),
    ("LTC", {"bg": "#c7d2fe", "fg": "#1d4ed8", "accent": "#f97316"}),
    ("ADA", {"bg": "#bbf7d0", "fg": "#064e3b", "accent": "#22c55e"}),
]

SPARKLINE_STYLES = {
    "BTC": {"line": "#4f46e5", "fill": "#c7d2fe", "border": "#4f46e5"},
    "ETH": {"line": "#0ea5e9", "fill": "#bae6fd", "border": "#0ea5e9"},
    "SOL": {"line": "#8b5cf6", "fill": "#ddd6fe", "border": "#8b5cf6"},
    "ADA": {"line": "#22c55e", "fill": "#d1fae5", "border": "#22c55e"},
}

class OverviewPanel:
    """AquaNeko inspired overview with favorites, live market, and exchange card"""

    def __init__(self, parent, symbols, on_select, theme=None):
        self.parent = parent
        self.symbols = symbols
        self.on_select = on_select
        self.theme = theme or THEME
        self.is_running = False
        self.bg = "#f5f7fb"
        self.surface = "#ffffff"
        self.favorite_cards = {}
        self.market_rows = {}
        self.spark_canvases = {}
        self.latest_prices = {symbol: 0.0 for symbol in symbols}
        self.price_history = {symbol: [] for symbol in symbols}
        self.chart_symbol = next(iter(symbols))
        self.chart_selector_var = tk.StringVar(value=self.chart_symbol)
        self.chart_candles = []
        self._chart_fetch_inflight = False
        self.sparkline_initialized = set()

        self.exchange_asset_var = tk.StringVar(value=self.chart_symbol)
        self.exchange_amount_var = tk.StringVar(value="1.0")
        self.exchange_quote_var = tk.StringVar(value="$ -- USD")
        self.frame = tk.Frame(parent, bg=self.bg, padx=28, pady=26)
        tk.Label(
            self.frame,
            text="Overview",
            font=("Helvetica", 22, "bold"),
            bg=self.bg,
            fg="#0f172a",
        ).pack(anchor="w")
        self._build_main_layout()
        self.set_active_symbol(self.chart_symbol)
        self._trigger_chart_refresh()

    def _build_main_layout(self):
        grid = tk.Frame(self.frame, bg=self.bg)
        grid.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)

        favorites_holder = tk.Frame(grid, bg=self.bg)
        favorites_holder.grid(row=0, column=0, padx=(0, 12), pady=(0, 12), sticky="nsew")
        self._build_favorites(favorites_holder)

        chart_holder = tk.Frame(grid, bg=self.bg)
        chart_holder.grid(row=0, column=1, padx=(12, 0), pady=(0, 12), sticky="nsew")
        self._build_chart_preview(chart_holder)

        live_holder = tk.Frame(grid, bg=self.bg)
        live_holder.grid(row=1, column=0, padx=(0, 12), sticky="nsew")
        self._build_live_market(live_holder)

        exchange_holder = tk.Frame(grid, bg=self.bg)
        exchange_holder.grid(row=1, column=1, padx=(12, 0), sticky="nsew")
        self._build_exchange_card(exchange_holder)

    def _build_favorites(self, parent):
        tk.Label(parent, text="Favorites", font=("Helvetica", 16, "bold"), bg=self.bg, fg="#111827").pack(anchor="w")
        grid = tk.Frame(parent, bg=self.bg)
        grid.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        grid.columnconfigure((0, 1), weight=1)

        row_index = 0
        col_index = 0
        for symbol, palette in FAVORITE_LAYOUT:
            if symbol not in self.symbols:
                continue
            card = tk.Frame(grid, bg=self.surface, bd=0, relief="flat", padx=2, pady=2)
            card.grid(row=row_index, column=col_index, sticky="nsew", padx=8, pady=8)
            inner = tk.Frame(card, bg=palette["bg"], padx=18, pady=16)
            inner.pack(fill=tk.BOTH, expand=True)
            inner.bind("<Button-1>", lambda _e, s=symbol: self._handle_symbol_select(s))
            for child in inner.winfo_children():
                child.bind("<Button-1>", lambda _e, s=symbol: self._handle_symbol_select(s))

            price_label = tk.Label(inner, text="$ --", font=("Helvetica", 24, "bold"), bg=palette["bg"], fg=palette["fg"])
            price_label.pack(anchor="w", pady=(30, 0))
            subtitle = tk.Label(inner, text=f"{symbol} / USDT", font=("Helvetica", 12), bg=palette["bg"], fg=palette["fg"])
            subtitle.pack(anchor="w")
            change_label = tk.Label(inner, text="--", font=("Helvetica", 11, "bold"), bg=palette["bg"], fg=palette["accent"])
            change_label.pack(anchor="ne")

            self.favorite_cards[symbol] = {
                "frame": card,
                "price": price_label,
                "change": change_label,
                "palette": palette,
            }
            col_index = (col_index + 1) % 2
            if col_index == 0:
                row_index += 1

    def _build_chart_preview(self, parent):
        holder = tk.Frame(parent, bg=self.surface, padx=18, pady=16, highlightthickness=2, highlightbackground="#93c5fd")
        holder.pack(fill=tk.BOTH, expand=True)
        self.chart_price_var = tk.StringVar(value="$ --")
        self.chart_change_var = tk.StringVar(value="--")
        self.chart_title_var = tk.StringVar(value="Bitcoin - BTC")
        header = tk.Frame(holder, bg=self.surface)
        header.pack(fill=tk.X)
        left_labels = tk.Frame(header, bg=self.surface)
        left_labels.pack(side=tk.LEFT)
        tk.Label(left_labels, textvariable=self.chart_price_var, font=("Helvetica", 20, "bold"), bg=self.surface, fg="#111827").pack(anchor="w")
        tk.Label(left_labels, textvariable=self.chart_change_var, font=("Helvetica", 12), bg=self.surface, fg="#047857").pack(anchor="w")
        selector = tk.Frame(header, bg=self.surface)
        selector.pack(side=tk.RIGHT)
        asset_combo = ttk.Combobox(
            selector,
            values=list(self.symbols.keys()),
            textvariable=self.chart_selector_var,
            state="readonly",
            width=10,
        )
        asset_combo.pack(side=tk.TOP, anchor="e")
        asset_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_chart_selector_change())
        tk.Label(selector, textvariable=self.chart_title_var, font=("Helvetica", 12, "bold"), bg=self.surface, fg="#111827").pack(side=tk.TOP, anchor="e")
        self.chart_canvas = tk.Canvas(holder, height=240, bg="#f3f4f6", highlightthickness=0)
        self.chart_canvas.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def _build_live_market(self, parent):
        card = tk.Frame(parent, bg=self.surface, padx=18, pady=16)
        card.pack(fill=tk.BOTH, expand=True)
        tk.Label(card, text="Live Market", font=("Helvetica", 16, "bold"), bg=self.surface, fg="#111827").pack(anchor="w")
        rows_container = tk.Frame(card, bg=self.surface)
        rows_container.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        for idx, symbol in enumerate(sorted(self.symbols.keys())):
            row = tk.Frame(rows_container, bg=self.surface, pady=10, cursor="hand2")
            row.pack(fill=tk.X, pady=2)
            row.columnconfigure(2, weight=1)
            row.bind("<Button-1>", lambda _e, s=symbol: self._handle_symbol_select(s))
            title = tk.Label(row, text=f"{symbol} / USDT", font=("Helvetica", 12, "bold"), bg=self.surface, fg="#111827")
            title.grid(row=0, column=0, sticky="w")
            change = tk.Label(row, text="--", font=("Helvetica", 12, "bold"), bg=self.surface, fg="#16a34a")
            change.grid(row=0, column=1, padx=20, sticky="w")
            price = tk.Label(row, text="--", font=("Helvetica", 12, "bold"), bg=self.surface, fg="#111827")
            price.grid(row=0, column=2, sticky="w")
            canvas = tk.Canvas(row, width=180, height=50, bg=self.surface, highlightthickness=0)
            canvas.grid(row=0, column=3, padx=(10, 0), sticky="e")
            self.market_rows[symbol] = {"frame": row, "change": change, "price": price}
            self.spark_canvases[symbol] = canvas

    def _build_exchange_card(self, parent):
        card = tk.Frame(parent, bg=self.surface, padx=18, pady=16)
        card.pack(fill=tk.BOTH, expand=True)
        tk.Label(card, text="Exchange", font=("Helvetica", 16, "bold"), bg=self.surface, fg="#111827").pack(anchor="w")
        display = tk.Frame(card, bg=self.surface)
        display.pack(fill=tk.X, pady=(6, 10))
        tk.Label(display, textvariable=self.exchange_quote_var, font=("Helvetica", 18, "bold"), bg=self.surface, fg="#111827").pack(side=tk.RIGHT)
        tk.Label(display, text="1 unit converts to", font=("Helvetica", 11), bg=self.surface, fg="#6b7280").pack(side=tk.LEFT)

        entry_frame = tk.Frame(card, bg="#f1f5f9", padx=12, pady=10)
        entry_frame.pack(fill=tk.X, pady=(4, 8))
        amount_entry = tk.Entry(entry_frame, textvariable=self.exchange_amount_var, bd=0, font=("Helvetica", 14, "bold"), justify="center")
        amount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        asset_combo = ttk.Combobox(entry_frame, values=list(self.symbols.keys()), textvariable=self.exchange_asset_var, state="readonly", width=8)
        asset_combo.pack(side=tk.LEFT, padx=(8, 0))

        self.exchange_amount_var.trace_add("write", lambda *_: self._update_exchange_quote())
        asset_combo.bind("<<ComboboxSelected>>", lambda _e: self._handle_exchange_select())
        amount_entry.bind("<FocusOut>", lambda _e: self._update_exchange_quote())

        tk.Label(card, text="Balance", font=("Helvetica", 13, "bold"), bg=self.surface, fg="#111827").pack(anchor="w", pady=(6, 0))
        self.exchange_balance_var = tk.StringVar(value="$ -- USD")
        tk.Label(card, textvariable=self.exchange_balance_var, font=("Helvetica", 18, "bold"), bg=self.surface, fg="#16a34a").pack(anchor="w")

    def _handle_symbol_select(self, symbol):
        self.chart_symbol = symbol
        self.exchange_asset_var.set(symbol)
        self.chart_selector_var.set(symbol)
        self._update_exchange_quote()
        self.on_select(symbol)
        self.set_active_symbol(symbol)

    def _handle_exchange_select(self):
        symbol = self.exchange_asset_var.get()
        self.chart_symbol = symbol
        self.chart_selector_var.set(symbol)
        self._update_exchange_quote()
        self.on_select(symbol)
        self.set_active_symbol(symbol)

    def _on_chart_selector_change(self):
        symbol = self.chart_selector_var.get()
        if symbol and symbol in self.symbols and symbol != self.chart_symbol:
            self.on_select(symbol)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._schedule_next_refresh()

    def stop(self):
        self.is_running = False

    def _schedule_next_refresh(self):
        if not self.is_running:
            return
        threading.Thread(target=self.refresh_data, daemon=True).start()
        self.parent.after(OVERVIEW_REFRESH_MS, self._schedule_next_refresh)

    def refresh_data(self):
        results = {}
        for symbol_key, symbol in self.symbols.items():
            if symbol_key not in self.sparkline_initialized:
                self._prime_price_history(symbol_key)
            data = get_24hr_ticker(symbol)
            if not data:
                continue
            try:
                price = float(data.get("lastPrice", 0))
                change_percent = float(data.get("priceChangePercent", 0))
            except (TypeError, ValueError):
                continue
            results[symbol_key] = {"price": price, "change_percent": change_percent}
        if results:
            self.parent.after(0, lambda: self._apply_updates(results))

    def _apply_updates(self, data):
        balance = 0.0
        for symbol_key, payload in data.items():
            price = payload["price"]
            change_percent = payload["change_percent"]
            self.latest_prices[symbol_key] = price
            history = self.price_history[symbol_key]
            history.append(price)
            self.price_history[symbol_key] = history[-120:]
            balance += price

            favorite = self.favorite_cards.get(symbol_key)
            if favorite:
                favorite["price"].config(text=f"$ {price:,.2f}")
                color = favorite["palette"]["accent"] if change_percent >= 0 else "#dc2626"
                sign = "+" if change_percent >= 0 else ""
                favorite["change"].config(text=f"{sign}{change_percent:.2f}%", fg=color)

            row = self.market_rows.get(symbol_key)
            if row:
                sign = "+" if change_percent >= 0 else ""
                fg = "#16a34a" if change_percent >= 0 else "#dc2626"
                row["change"].config(text=f"{sign}{change_percent:.2f}%", fg=fg)
                row["price"].config(text=f"{price:,.2f} USD")
                canvas = self.spark_canvases.get(symbol_key)
                if canvas:
                    self._draw_sparkline(canvas, self.price_history[symbol_key], symbol_key)

        self.exchange_balance_var.set(f"$ {balance:,.2f} USD")
        self._update_exchange_quote()
        self._trigger_chart_refresh()
        self._update_chart_preview()

    def _draw_sparkline(self, canvas, data, symbol):
        canvas.delete("all")
        if len(data) < 2:
            return
        canvas.update_idletasks()
        w = max(10, int(canvas.winfo_width() or canvas["width"]))
        h = max(10, int(canvas.winfo_height() or canvas["height"]))
        margin = 8
        usable_w = w - margin * 2
        usable_h = h - margin * 2
        normalized = self._resample_series(data, 60)
        min_price = min(normalized)
        max_price = max(normalized)
        span = max(max_price - min_price, 1e-6)
        style = SPARKLINE_STYLES.get(symbol, {})
        base_line = style.get("line", "#3b82f6")
        base_fill = style.get("fill", "#dbeafe")
        actual_trend_up = normalized[-1] >= normalized[0]
        line_color = "#16a34a" if actual_trend_up else "#dc2626"
        fill_color = base_fill if actual_trend_up else "#fee2e2"

        points = []
        total_points = len(normalized)
        for idx, price in enumerate(normalized):
            x = margin + (idx / max(1, total_points - 1)) * usable_w
            y = margin + usable_h - ((price - min_price) / span * usable_h)
            points.extend([x, y])
        baseline = margin + usable_h
        point_pairs = list(zip(points[0::2], points[1::2]))
        for (x0, y0), (x1, y1) in zip(point_pairs[:-1], point_pairs[1:]):
            avg_ratio = 1 - ((y0 + y1) / 2 - margin) / usable_h
            shade = self._soften_color(fill_color, 1 - avg_ratio * 0.8)
            canvas.create_polygon(
                x0,
                baseline,
                x0,
                y0,
                x1,
                y1,
                x1,
                baseline,
                fill=shade,
                outline="",
            )
        canvas.create_line(points, fill=line_color, width=3, smooth=True)

    def _update_chart_preview(self):
        symbol = self.chart_symbol
        price = self.latest_prices.get(symbol)
        history = self.price_history.get(symbol, [])
        change = 0.0
        candles = self.chart_candles
        if candles:
            start = candles[0]["open"]
            end = candles[-1]["close"]
            change = ((end - start) / start * 100) if start else 0.0
        elif history:
            change = ((history[-1] - history[0]) / history[0] * 100) if history[0] else 0.0
        if price:
            self.chart_price_var.set(f"$ {price:,.2f}")
        updates = len(candles) if candles else len(history)
        label = "candles" if candles else "updates"
        self.chart_change_var.set(f"{change:+.2f}% (last {updates} {label})")
        self.chart_title_var.set(f"{symbol} Overview")
        self.chart_canvas.delete("all")
        if len(self.chart_candles) < 1:
            return
        self.chart_canvas.update_idletasks()
        w = self.chart_canvas.winfo_width() or 320
        h = self.chart_canvas.winfo_height() or 220
        margin = 18
        usable_w = max(10, w - margin * 2)
        usable_h = max(10, h - margin * 2)
        highs = [c["high"] for c in self.chart_candles]
        lows = [c["low"] for c in self.chart_candles]
        max_price = max(highs)
        min_price = min(lows)
        span = max(max_price - min_price, 1e-6)
        candle_count = len(self.chart_candles)
        gap = usable_w / candle_count
        body_width = max(4, gap * 0.4)
        grid_lines = 6
        for i in range(grid_lines):
            y = margin + usable_h * (i / (grid_lines - 1))
            self.chart_canvas.create_line(margin, y, margin + usable_w, y, fill="#d1d5db", dash=(2,))
            price_level = max_price - (span * i / (grid_lines - 1))
            self.chart_canvas.create_text(margin + usable_w + 50, y, text=f"$ {price_level:,.0f}", fill="#6b7280", font=("Helvetica", 10))

        for idx, candle in enumerate(self.chart_candles):
            open_p = candle["open"]
            close_p = candle["close"]
            high_p = candle["high"]
            low_p = candle["low"]
            color = "#16a34a" if close_p >= open_p else "#dc2626"

            x_center = margin + idx * gap + gap / 2
            x0 = x_center - body_width / 2
            x1 = x_center + body_width / 2

            def y(price):
                return margin + usable_h - ((price - min_price) / span * usable_h)

            y_open = y(open_p)
            y_close = y(close_p)
            y_high = y(high_p)
            y_low = y(low_p)

            self.chart_canvas.create_line(x_center, y_high, x_center, y_low, fill=color, width=2)
            self.chart_canvas.create_rectangle(
                x0,
                min(y_open, y_close),
                x1,
                max(y_open, y_close),
                fill=color,
                outline=color,
            )
        time_labels = self._build_time_labels(self.chart_candles)
        for ratio, label in time_labels:
            x = margin + usable_w * ratio
            y = margin + usable_h + 12
            self.chart_canvas.create_text(x, y, text=label, fill="#0f172a", font=("Helvetica", 11, "bold"))

    def _update_exchange_quote(self):
        symbol = self.exchange_asset_var.get()
        try:
            amount = float(self.exchange_amount_var.get())
        except (TypeError, ValueError):
            amount = 0.0
        price = self.latest_prices.get(symbol, 0.0)
        quote = amount * price
        self.exchange_quote_var.set(f"$ {quote:,.2f} USD" if quote else "$ -- USD")

    def set_active_symbol(self, symbol_key):
        self.chart_symbol = symbol_key
        self.chart_selector_var.set(symbol_key)
        self.exchange_asset_var.set(symbol_key)
        for symbol, card in self.favorite_cards.items():
            highlight = 2 if symbol == symbol_key else 1
            card["frame"].config(highlightthickness=highlight, highlightbackground="#60a5fa")
        for symbol, row in self.market_rows.items():
            bg = "#e0ecff" if symbol == symbol_key else self.surface
            row["frame"].config(bg=bg)
            for child in row["frame"].winfo_children():
                child.config(bg=bg)
        self._trigger_chart_refresh()
        self._update_chart_preview()

    def _trigger_chart_refresh(self):
        if self._chart_fetch_inflight:
            return
        self._chart_fetch_inflight = True
        threading.Thread(target=self._refresh_chart_candles, args=(self.chart_symbol,), daemon=True).start()

    def _refresh_chart_candles(self, symbol_key):
        symbol = self.symbols.get(symbol_key)
        candles = []
        try:
            if symbol:
                data = get_klines(symbol, interval="1h", limit=60)
                if data:
                    for entry in data:
                        try:
                            candles.append(
                                {
                                    "open": float(entry[1]),
                                    "high": float(entry[2]),
                                    "low": float(entry[3]),
                                    "close": float(entry[4]),
                                    "time": float(entry[0]),
                                }
                            )
                        except (TypeError, ValueError):
                            continue
        finally:
            self._chart_fetch_inflight = False
        self.parent.after(0, lambda: self._apply_chart_candles(symbol_key, candles))

    def _apply_chart_candles(self, symbol_key, candles):
        self._chart_fetch_inflight = False
        if symbol_key != self.chart_symbol:
            return
        if candles:
            self.chart_candles = candles[-40:]
        self._update_chart_preview()

    def _build_time_labels(self, candles):
        if not candles:
            return [(0.0, "--")]
        total = len(candles) - 1
        if total <= 0:
            ts = candles[0].get("time")
            dt = datetime.fromtimestamp(ts / 1000) if ts else None
            return [(0.0, dt.strftime("%H:%M") if dt else "--")]
        labels = []
        labels = []
        prev_hour = None
        for idx, candle in enumerate(candles[:-1]):
            candle = candles[idx]
            ts = candle.get("time")
            if not ts:
                continue
            dt = datetime.fromtimestamp(ts / 1000)
            if dt.hour % 4 != 0 or dt.hour == prev_hour:
                continue
            prev_hour = dt.hour
            ratio = idx / total
            labels.append((ratio, dt.strftime("%H:%M")))
        return labels if labels else [(0.0, "--")]

    def _soften_color(self, hex_color, t):
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            hex_color = "3b82f6"
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = int(r + (255 - r) * t)
        g = int(g + (255 - g) * t)
        b = int(b + (255 - b) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _resample_series(self, data, length):
        if len(data) >= length:
            return data[-length:]
        if len(data) < 2:
            return [data[0]] * length
        resampled = []
        last_index = len(data) - 1
        for i in range(length):
            target = i * last_index / (length - 1)
            low = int(target)
            high = min(last_index, low + 1)
            blend = target - low
            value = data[low] * (1 - blend) + data[high] * blend
            resampled.append(value)
        return resampled

    def _prime_price_history(self, symbol_key):
        if symbol_key in self.sparkline_initialized:
            return
        symbol = self.symbols.get(symbol_key)
        if not symbol:
            return
        data = get_klines(symbol, interval="1h", limit=80)
        if not data:
            return
        prices = []
        for entry in data:
            try:
                prices.append(float(entry[4]))
            except (TypeError, ValueError):
                continue
        if prices:
            self.price_history[symbol_key] = prices[-120:]
            self.sparkline_initialized.add(symbol_key)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def pack_forget(self):
        self.frame.pack_forget()
