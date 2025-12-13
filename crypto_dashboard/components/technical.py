import os
import sys
import tkinter as tk
import threading
from datetime import datetime
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle

if __package__ is None or __package__ == "":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from utils.binance_rest import get_klines  # type: ignore
    from config import TECHNICAL_REFRESH_MS  # type: ignore
else:
    from ..utils.binance_rest import get_klines
    from ..config import TECHNICAL_REFRESH_MS

LIGHT_CHART_THEME = {
    "panel": "#ffffff",
    "panel_border": "#d1d5db",
    "bg": "#f5f7fb",
    "text_primary": "#0f172a",
    "text_muted": "#6b7280",
    "divider": "#e5e7eb",
    "accent_green": "#16a34a",
    "accent_red": "#dc2626",
    "accent_orange": "#f97316",
}


class TechnicalPanel:
    """Render a candlestick chart with SMA under a dark theme"""

    def __init__(self, parent, symbol, interval="1h", theme=None):
        self.parent = parent
        self.symbol = symbol.upper()
        self.interval = interval
        self.theme = {**LIGHT_CHART_THEME, **(theme or {})}
        self.is_running = False

        self.frame = tk.Frame(
            parent,
            bg=self.theme.get("panel", "#111"),
            padx=18,
            pady=14,
            highlightbackground=self.theme.get("panel_border", "#333"),
            highlightthickness=1,
        )

        self.fig = Figure(figsize=(7.2, 6.2), dpi=100)
        grid = self.fig.add_gridspec(6, 1, height_ratios=[4, 4, 4, 4, 4, 2.8], hspace=0.05)
        self.price_ax = self.fig.add_subplot(grid[:5, 0])
        self.volume_ax = self.fig.add_subplot(grid[5, 0], sharex=self.price_ax)
        self.fig.patch.set_facecolor(self.theme.get("panel", "#111"))
        for ax in (self.price_ax, self.volume_ax):
            ax.set_facecolor(self.theme.get("bg", "#000"))
            for spine in ax.spines.values():
                spine.set_color(self.theme.get("divider", "#2b2b2b"))
            ax.tick_params(colors=self.theme.get("text_muted", "#ccc"))
        self.price_ax.set_ylabel("Price", color=self.theme.get("text_muted", "#ccc"))
        self.volume_ax.set_ylabel("Volume", color=self.theme.get("text_muted", "#ccc"))
        self.fig.subplots_adjust(bottom=0.15, top=0.96)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=(10, 0))

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
        thread = threading.Thread(target=self.refresh_chart, daemon=True)
        thread.start()
        self.parent.after(TECHNICAL_REFRESH_MS, self.schedule_refresh)

    def refresh_chart(self):
        data = get_klines(self.symbol, interval=self.interval, limit=50)
        if not data:
            return

        opens = [float(candle[1]) for candle in data]
        highs = [float(candle[2]) for candle in data]
        lows = [float(candle[3]) for candle in data]
        closes = [float(candle[4]) for candle in data]
        volumes = [float(candle[5]) for candle in data]
        timestamps = [datetime.fromtimestamp(float(candle[0]) / 1000) for candle in data]
        x_dates = mdates.date2num(timestamps)

        def update_plot():
            self.price_ax.clear()
            self.volume_ax.clear()

            bg = self.theme.get("bg", "#000")
            divider = self.theme.get("divider", "#2b2b2b")
            text_muted = self.theme.get("text_muted", "#ccc")
            up_color = self.theme.get("accent_green", "#10b981")
            down_color = self.theme.get("accent_red", "#ef4444")
            last_point_color = self.theme.get("accent_orange", "#f59e0b")

            for ax in (self.price_ax, self.volume_ax):
                ax.set_facecolor(bg)
                for spine in ax.spines.values():
                    spine.set_color(divider)
                ax.grid(color=divider, linestyle="--", linewidth=0.6, alpha=0.35)
                ax.tick_params(colors=text_muted)

            candle_width = 0.6 * (x_dates[1] - x_dates[0]) if len(x_dates) > 1 else 0.02
            body_min_height = (max(highs) - min(lows)) * 0.001 or 0.1

            for idx, date in enumerate(x_dates):
                open_price = opens[idx]
                close_price = closes[idx]
                high = highs[idx]
                low = lows[idx]
                color = up_color if close_price >= open_price else down_color
                lower = min(open_price, close_price)
                height = max(abs(close_price - open_price), body_min_height)
                rect = Rectangle(
                    (date - candle_width / 2, lower),
                    candle_width,
                    height,
                    facecolor=color,
                    edgecolor=color,
                )
                self.price_ax.add_patch(rect)
                self.price_ax.vlines(
                    date,
                    low,
                    high,
                    color=color,
                    linewidth=1,
                )

                self.volume_ax.bar(
                    date,
                    volumes[idx],
                    width=candle_width * 0.7,
                    color=color,
                    alpha=0.6,
                    align="center",
                )

            self.price_ax.scatter(
                x_dates[-1],
                closes[-1],
                color=last_point_color,
                edgecolors=self.theme.get("panel", "#111"),
                linewidth=1,
                s=50,
                zorder=5,
            )

            self.price_ax.set_xlim(x_dates[0] - candle_width, x_dates[-1] + candle_width)
            max_volume = max(volumes) if volumes else 0
            self.volume_ax.set_ylim(0, max_volume * 1.25 if max_volume else 1)

            formatter = mdates.DateFormatter("%b %d, %H:%M")
            self.price_ax.xaxis.set_major_formatter(formatter)
            self.volume_ax.xaxis.set_major_formatter(formatter)
            self.price_ax.tick_params(axis="x", labelbottom=False)
            for label in self.volume_ax.get_xticklabels():
                label.set_rotation(25)
                label.set_horizontalalignment("right")

            self.price_ax.set_ylabel("Price", color=text_muted)
            self.volume_ax.set_ylabel("Volume", color=text_muted)
            self.price_ax.set_title(
                f"{self.symbol} {self.interval.upper()} Candlestick (Last 50)",
                color=self.theme.get("text_primary", "#fff"),
                fontsize=12,
            )
            self.volume_ax.set_xlabel("Time", color=text_muted)
            self.fig.tight_layout(rect=(0, 0, 1, 0.98))
            self.canvas.draw()

        self.parent.after(0, update_plot)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def set_symbol(self, symbol):
        new_symbol = symbol.upper()
        if new_symbol == self.symbol:
            return

        self.symbol = new_symbol
        if self.is_running:
            thread = threading.Thread(target=self.refresh_chart, daemon=True)
            thread.start()

    def set_interval(self, interval):
        normalized = (interval or self.interval).lower()
        if normalized == self.interval:
            return
        self.interval = normalized
        if self.is_running:
            thread = threading.Thread(target=self.refresh_chart, daemon=True)
            thread.start()
