import os
import sys
import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageTk, ImageChops
except ImportError:
    Image = ImageTk = ImageChops = None

if __package__ is None or __package__ == "":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from crypto_dashboard.config import (
    DEFAULT_SYMBOLS,
    THEME,
    CHART_THEME,
    DEFAULT_TECH_INTERVAL,
)
from crypto_dashboard.components.ticker import CryptoTicker
from crypto_dashboard.components.orderbook import OrderBookPanel
from crypto_dashboard.components.technical import TechnicalPanel
from crypto_dashboard.components.overview import OverviewPanel
from crypto_dashboard.components.wallet import WalletPanel
from crypto_dashboard.components.transactions import TransactionsPanel


class CryptoDashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BTCUSDT Dashboard")
        self.root.geometry("1440x900")
        self.root.minsize(1200, 720)
        self.root.configure(bg=THEME["bg"])

        self.current_symbol_key = (
            "BTC" if "BTC" in DEFAULT_SYMBOLS else next(iter(DEFAULT_SYMBOLS))
        )
        self.symbol = DEFAULT_SYMBOLS[self.current_symbol_key]
        self.display_symbol = self._format_display_name(
            self.current_symbol_key)
        self.status_var = tk.StringVar(value="LIVE • Connected to Binance")
        self.details_visible = False
        self.detail_panels_started = False
        self._scroll_drag_enabled = False
        self._scroll_drag_active = False
        self._scroll_drag_start = (0, 0)
        self.interval_var = tk.StringVar(value=DEFAULT_TECH_INTERVAL)
        self.chart_symbol_var = tk.StringVar(value=self.current_symbol_key)
        self.nav_buttons = {}
        self.nav_callbacks = {}
        self.active_nav = None

        self._configure_styles()
        self._build_layout()
        self.start_all()

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Dashboard.TFrame",
            background=THEME["panel"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Dashboard.TLabel",
            background=THEME["panel"],
            foreground=THEME["text_primary"],
            font=("Helvetica", 11)
        )
        style.configure(
            "Muted.TLabel",
            background=THEME["panel"],
            foreground=THEME["text_muted"],
            font=("Helvetica", 10)
        )
        style.configure(
            "Header.TLabel",
            background=THEME["header"],
            foreground=THEME["text_primary"],
            font=("Helvetica", 20, "bold")
        )
        style.configure(
            "HeaderStatus.TLabel",
            background=THEME["header"],
            foreground=THEME["accent_green"],
            font=("Helvetica", 12, "bold")
        )

    def _build_layout(self):
        self.container = tk.Frame(self.root, bg=THEME["bg"])
        self.container.pack(fill=tk.BOTH, expand=True)

        self.sidebar_logo_photo = self._compose_sidebar_logo()
        logo_width = self.sidebar_logo_photo.width() if self.sidebar_logo_photo else 0
        sidebar_width = max(260, logo_width + 48)
        self.sidebar = tk.Frame(
            self.container,
            bg=THEME["sidebar_bg"],
            width=sidebar_width,
            padx=24,
            pady=32,
            highlightbackground="#d1d5db",
            highlightthickness=1,
        )
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        content_wrapper = tk.Frame(
            self.container, bg=THEME["bg"], highlightthickness=1)
        content_wrapper.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.main_canvas = tk.Canvas(
            content_wrapper, bg=THEME["bg"], highlightthickness=0)
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.content_frame = tk.Frame(self.main_canvas, bg=THEME["bg"])
        self.canvas_window = self.main_canvas.create_window(
            (0, 0), window=self.content_frame, anchor="nw"
        )
        self.content_frame.bind(
            "<Configure>",
            lambda _e: self.main_canvas.configure(
                scrollregion=self.main_canvas.bbox("all")
            ),
        )
        self.main_canvas.bind(
            "<Configure>",
            lambda e: self._update_canvas_window_size(e),
        )
        self.root.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.root.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.root.bind_all("<Button-5>", self._on_mousewheel, add="+")
        self.root.bind_all("<ButtonPress-1>", self._start_scroll_drag, add="+")
        self.root.bind_all("<B1-Motion>", self._perform_scroll_drag, add="+")
        self.root.bind_all("<ButtonRelease-1>",
                           self._stop_scroll_drag, add="+")
        self._set_content_background(THEME["bg"])

        # Create header bar with dark background
        self.header_bar = tk.Frame(
            self.content_frame,
            bg=THEME["header"],
            height=80,
            padx=28,
            pady=16
        )
        self.header_bar.pack(fill=tk.X, side=tk.TOP)
        self.header_bar.pack_propagate(False)

        # Header title and status in header bar
        header_content = tk.Frame(self.header_bar, bg=THEME["header"])
        header_content.pack(fill=tk.X)

        self.header_title = tk.Label(
            header_content,
            bg=THEME["header"],
            fg=THEME["text_primary"],
            font=("Helvetica", 20, "bold")
        )
        self.header_title.pack(side=tk.LEFT)

        self.status_label = tk.Label(
            header_content,
            textvariable=self.status_var,
            bg=THEME["header"],
            fg=THEME["accent_green"],
            font=("Helvetica", 12, "bold")
        )
        self.status_label.pack(side=tk.RIGHT)

        self._build_detail_section()
        self._build_transactions_section()
        self._build_wallet_section()

        self.overview_panel = OverviewPanel(
            self.content_frame,
            DEFAULT_SYMBOLS,
            on_select=self.switch_symbol,
            theme=THEME,
            on_trade=self._record_overview_trade,
        )
        self.overview_panel.pack(fill=tk.BOTH, expand=True)
        self.overview_panel.set_active_symbol(self.current_symbol_key)

        self.header_title.config(text="Live Markets Overview")

    def _build_sidebar(self):
        logo_frame = tk.Frame(self.sidebar, bg=THEME["sidebar_bg"])
        logo_frame.pack(fill=tk.X, pady=(0, 24))
        if self.sidebar_logo_photo:
            tk.Label(
                logo_frame,
                image=self.sidebar_logo_photo,
                bg=THEME["sidebar_bg"],
            ).pack(anchor="w")
        else:
            self._draw_sidebar_logo_placeholder(logo_frame)

        self.sidebar_insight_var = tk.StringVar(
            value="Keep your portfolio tidy with live USDT balance and holdings"
        )

        nav_items = [
            ("Overview", "grid", self.navigate_overview, True),
            ("Chart", "detail", self.navigate_detail, False),
            ("Transactions", "transactions", self.navigate_transactions, False),
            ("Wallet", "wallet", self.navigate_wallet, False),
        ]

        for label, shape, callback, active in nav_items:
            self._create_nav_item(label, shape, callback, active)

        insight = tk.Frame(self.sidebar, bg=THEME["sidebar_bg"], pady=20)
        insight.pack(fill=tk.X, expand=True)
        tk.Label(
            insight,
            text="Quick Insight",
            font=("Helvetica", 12, "bold"),
            fg=THEME["sidebar_text"],
            bg=THEME["sidebar_bg"],
        ).pack(anchor="w")
        tk.Label(
            insight,
            textvariable=self.sidebar_insight_var,
            font=("Helvetica", 11),
            wraplength=160,
            justify="left",
            fg=THEME["sidebar_text"],
            bg=THEME["sidebar_bg"],
            pady=6,
        ).pack(anchor="w")

        if self.active_nav:
            self._set_active_nav(self.active_nav)

    def _compose_sidebar_logo(self):
        if Image is None or ImageTk is None:
            return None
        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        cat = self._load_logo_image_asset(
            os.path.join(project_root, "Subject 3.png"),
            target_height=138,
            add_padding=20,
        ) or self._load_logo_image_asset(
            os.path.join(project_root, "ChatGPT Image Nov 29 2025 (1).png"),
            target_height=138,
            add_padding=20,
        )
        wordmark = self._load_logo_image_asset(
            os.path.join(project_root, "MagicEraser_5681129_194136.PNG"),
            target_height=60,
        ) or self._load_logo_image_asset(
            os.path.join(project_root, "ChatGPT Image Nov 29 2025 (1).png"),
            target_height=60,
        )
        if not cat or not wordmark:
            return None
        spacing = 0
        combined_height = max(cat.height, wordmark.height + 16)
        combined_width = cat.width + spacing + wordmark.width
        composed = Image.new(
            "RGBA", (combined_width, combined_height), (0, 0, 0, 0))
        top_margin = (combined_height - cat.height) // 2
        composed.paste(cat, (0, top_margin), cat)
        wordmark_y = (combined_height - wordmark.height) // 2 + 2
        composed.paste(wordmark, (cat.width + spacing, wordmark_y), wordmark)

        pad_right = 18
        if pad_right > 0:
            padded = Image.new(
                "RGBA",
                (composed.width + pad_right, composed.height),
                (0, 0, 0, 0),
            )
            padded.paste(composed, (0, 0), composed)
            composed = padded

        max_width = 260
        if composed.width > max_width:
            scale = max_width / composed.width
            new_size = (int(composed.width * scale),
                        int(composed.height * scale))
            composed = composed.resize(new_size, Image.LANCZOS)
        return ImageTk.PhotoImage(composed)

    def _load_logo_image_asset(self, path, target_height, add_padding=0):
        if not os.path.exists(path):
            return None
        try:
            img = Image.open(path).convert("RGBA")
        except Exception:
            return None
        img = self._trim_logo_image(img)
        ratio = target_height / img.height
        width = max(1, int(img.width * ratio))
        img = img.resize((width, target_height), Image.LANCZOS)
        if add_padding:
            padded = Image.new(
                "RGBA",
                (img.width + add_padding * 2, img.height + add_padding * 2),
                (0, 0, 0, 0),
            )
            padded.paste(img, (add_padding, add_padding), img)
            img = padded
        return img

    def _trim_logo_image(self, img):
        if ImageChops is None:
            return img
        alpha = img.split()[-1]
        if alpha.getextrema()[0] == 0:
            bbox = alpha.getbbox()
            if bbox:
                return img.crop(bbox)
        background = Image.new("RGBA", img.size, img.getpixel((0, 0)))
        diff = ImageChops.difference(img, background)
        bbox = diff.getbbox()
        if bbox:
            return img.crop(bbox)
        return img

    def _draw_sidebar_logo_placeholder(self, parent):
        logo_canvas = tk.Canvas(
            parent,
            width=220,
            height=100,
            bg=THEME["sidebar_bg"],
            highlightthickness=0,
        )
        logo_canvas.pack(anchor="w")
        bg_color = "#fef6ea"
        stroke = "#1d3557"
        accent = "#1e90cf"
        logo_canvas.create_oval(
            5, 5, 85, 85, outline=stroke, width=4, fill=bg_color)
        logo_canvas.create_polygon(
            20, 12, 32, -5, 44, 12, fill=accent, outline=stroke, width=3)
        logo_canvas.create_polygon(
            46, 12, 58, -5, 70, 12, fill=accent, outline=stroke, width=3)
        logo_canvas.create_oval(
            18, 20, 72, 72, fill="#fffdfa", outline=stroke, width=3)
        logo_canvas.create_oval(30, 38, 38, 46, fill=stroke, outline=stroke)
        logo_canvas.create_oval(52, 38, 60, 46, fill=stroke, outline=stroke)
        logo_canvas.create_line(27, 54, 33, 52, 47, 52,
                                53, 54, fill=stroke, width=3, smooth=True)
        logo_canvas.create_oval(24, 46, 31, 54, fill="#f9a8d4", outline="")
        logo_canvas.create_oval(49, 46, 56, 54, fill="#f9a8d4", outline="")
        logo_canvas.create_rectangle(
            18, 60, 72, 92, fill=stroke, outline=stroke)
        logo_canvas.create_polygon(
            30, 60, 45, 75, 60, 60, fill="#bfe7ff", outline=stroke, width=2)
        logo_canvas.create_oval(
            36, 72, 50, 86, fill="#ffd166", outline="#b45309", width=3)
        logo_canvas.create_text(43, 79, text="฿", font=(
            "Helvetica", 16, "bold"), fill="#b45309")
        logo_canvas.create_text(
            130,
            34,
            text="AquaNeko",
            font=("Times New Roman", 24, "bold"),
            fill="#0075bb",
            anchor="w",
        )
        logo_canvas.create_text(
            140,
            64,
            text="EXCHANGE",
            font=("Helvetica", 13, "bold"),
            fill="#0f4c81",
            anchor="w",
        )

    def _create_nav_item(self, label, shape, callback, active=False):
        bg = THEME["sidebar_active_bg"] if active else THEME["sidebar_bg"]
        fg = THEME["sidebar_active"] if active else THEME["sidebar_text"]
        frame = tk.Frame(self.sidebar, bg=bg)
        frame.pack(fill=tk.X, pady=6)
        frame.configure(padx=14, pady=10)

        icon_canvas = tk.Canvas(
            frame,
            width=28,
            height=28,
            bg=bg,
            highlightthickness=0,
        )
        icon_canvas.pack(side=tk.LEFT)
        self._draw_nav_icon(icon_canvas, shape, fg, bg)

        text_label = tk.Label(
            frame,
            text=label,
            font=("Helvetica", 13, "bold" if active else "normal"),
            fg=fg,
            bg=bg,
            padx=10,
        )
        text_label.pack(side=tk.LEFT)

        indicator = tk.Canvas(
            frame,
            width=14,
            height=14,
            bg=bg,
            highlightthickness=0,
        )
        indicator.pack(side=tk.RIGHT)
        if active:
            indicator.create_oval(
                4, 4, 10, 10, fill=THEME["sidebar_active"], outline="")

        elements = (frame, icon_canvas, text_label, indicator)
        for element in elements:
            element.bind("<Button-1>", lambda _e,
                         key=label: self._handle_nav_click(key))

        self.nav_buttons[label] = {
            "frame": frame,
            "icon": icon_canvas,
            "text": text_label,
            "indicator": indicator,
            "shape": shape,
        }
        self.nav_callbacks[label] = callback
        if active and not self.active_nav:
            self.active_nav = label

    def _draw_nav_icon(self, canvas, shape, color, bg):
        canvas.delete("all")
        canvas.configure(bg=bg)
        if shape == "grid":
            size = 8
            padding = 4
            for row in range(2):
                for col in range(2):
                    x0 = padding + col * (size + 4)
                    y0 = padding + row * (size + 4)
                    canvas.create_rectangle(
                        x0,
                        y0,
                        x0 + size,
                        y0 + size,
                        fill=color,
                        outline="",
                    )
        elif shape == "detail":
            canvas.create_rectangle(6, 8, 22, 20, outline=color, width=2)
            canvas.create_line(10, 15, 18, 11, fill=color, width=2)
            canvas.create_line(18, 11, 22, 15, fill=color, width=2)
        elif shape in ("order", "transactions"):
            for x in (8, 14, 20):
                canvas.create_line(x, 7, x, 21, fill=color, width=2)
            canvas.create_rectangle(6, 11, 10, 17, outline=color, width=2)
            canvas.create_rectangle(20, 13, 24, 19, outline=color, width=2)
        elif shape == "chart":
            canvas.create_line(5, 20, 10, 14, 16, 18, 22, 8,
                               fill=color, width=2, smooth=True)
            canvas.create_oval(20, 6, 24, 10, outline=color, width=2)
        elif shape == "wallet":
            canvas.create_rectangle(6, 9, 22, 19, outline=color, width=2)
            canvas.create_rectangle(6, 13, 22, 23, outline=color, width=2)
            canvas.create_rectangle(15, 14, 21, 18, fill=color, outline=color)
        elif shape == "bell":
            canvas.create_arc(7, 6, 21, 20, start=210, extent=120,
                              style="arc", outline=color, width=2)
            canvas.create_line(10, 18, 18, 18, fill=color, width=2)
            canvas.create_oval(12, 21, 14, 23, fill=color, outline=color)
        else:
            canvas.create_oval(6, 6, 22, 22, outline=color, width=2)

    def _handle_nav_click(self, label):
        callback = self.nav_callbacks.get(label)
        if callback:
            callback()
        self._set_active_nav(label)

    def _set_active_nav(self, label):
        if not self.nav_buttons:
            self.active_nav = label
            return
        self.active_nav = label
        for name, widgets in self.nav_buttons.items():
            active = name == label
            bg = THEME["sidebar_active_bg"] if active else THEME["sidebar_bg"]
            fg = THEME["sidebar_active"] if active else THEME["sidebar_text"]
            widgets["frame"].config(bg=bg)
            self._draw_nav_icon(widgets["icon"], widgets["shape"], fg, bg)
            widgets["text"].config(
                bg=bg,
                fg=fg,
                font=("Helvetica", 13, "bold" if active else "normal"),
            )
            indicator = widgets["indicator"]
            indicator.delete("all")
            indicator.configure(bg=bg)
            if active:
                indicator.create_oval(
                    4, 4, 10, 10, fill=THEME["sidebar_active"], outline="")

    def _scroll_to_widget(self, widget):
        if not widget or not hasattr(self, "main_canvas"):
            return
        if not widget.winfo_ismapped():
            return
        self.main_canvas.update_idletasks()
        widget_y = widget.winfo_rooty() - self.content_frame.winfo_rooty()
        frame_height = max(1, self.content_frame.winfo_height())
        target = max(0, min(widget_y / frame_height, 1))
        self.main_canvas.yview_moveto(target)

    def _scroll_to_top(self):
        if hasattr(self, "main_canvas"):
            self.main_canvas.yview_moveto(0)

    def _on_interval_selected(self, _event=None):
        interval = self.interval_var.get().lower()
        if hasattr(self, "technical_panel"):
            self.technical_panel.set_interval(interval)
        self.sidebar_insight_var.set(
            f"View {interval.upper()} candlesticks for {self.display_symbol}"
        )

    def _on_chart_symbol_selected(self, _event=None):
        selected = (self.chart_symbol_var.get() or "").upper()
        if selected and selected in DEFAULT_SYMBOLS:
            self.switch_symbol(selected)

    def navigate_overview(self):
        self.hide_detail()
        self._hide_transactions_section()
        self._hide_wallet_section()
        # Show header bar for overview page
        if hasattr(self, "header_bar") and not self.header_bar.winfo_ismapped():
            self.header_bar.pack(fill=tk.X, side=tk.TOP)
        self._show_overview_section()
        if hasattr(self, "overview_panel"):
            self._scroll_to_widget(self.overview_panel.frame)
        else:
            self._scroll_to_top()
        self.status_var.set("LIVE • Connected to Binance")
        self._set_active_nav("Overview")
        self.sidebar_insight_var.set(
            "Review the market and pick any token to focus on")

    def navigate_detail(self):
        self.show_detail()
        self._scroll_to_widget(self.detail_container)
        self.status_var.set(f"CHART • {self.display_symbol} dashboards")
        self._set_active_nav("Chart")
        self.sidebar_insight_var.set(
            f"Access price, order book and indicator data for {self.display_symbol}"
        )
        current = getattr(self.technical_panel, "interval",
                          self.interval_var.get().lower())
        self.interval_var.set(current.upper())

    def navigate_transactions(self):
        self._show_transactions_section()
        target = getattr(self.transactions_panel, "frame", None)
        self._scroll_to_widget(target or self.transactions_container)
        self.status_var.set("TRANSACTIONS • Market + mock trade logs")
        self._set_active_nav("Transactions")
        self.sidebar_insight_var.set(
            "See latest market trades and your mock orders")

    def navigate_wallet(self):
        self._show_wallet_section()
        target = getattr(self.wallet_panel, "frame", None)
        self._scroll_to_widget(target or self.wallet_container)
        self.status_var.set("WALLET • Portfolio allocation view")
        self._set_active_nav("Wallet")
        self.sidebar_insight_var.set(
            "Manage holdings easily with live USDT balances")

    def show_alerts_center(self):
        self.status_var.set("ALERTS • No critical crypto alerts right now")
        self._set_active_nav("Alerts")
        self.sidebar_insight_var.set(
            "No new price alerts yet — set your targets ahead of time")

    def _build_detail_section(self):
        self.detail_container = tk.Frame(
            self.content_frame, bg=CHART_THEME["bg"])

        # Banner removed - no header bar for chart page

        detail_header = tk.Frame(
            self.detail_container, bg=CHART_THEME["bg"], padx=15, pady=8)
        detail_header.pack(fill=tk.X)

        controls = tk.Frame(self.detail_container,
                            bg=CHART_THEME["bg"], padx=15)
        controls.pack(fill=tk.X, pady=(0, 10))
        tk.Label(
            controls,
            text="Chart Interval",
            fg=CHART_THEME["text_primary"],
            bg=CHART_THEME["bg"],
            font=("Helvetica", 11, "bold"),
        ).pack(side=tk.LEFT)
        interval_box = ttk.Combobox(
            controls,
            values=("1m", "5m", "1h", "1d"),
            textvariable=self.interval_var,
            state="readonly",
            width=6,
        )
        interval_box.pack(side=tk.LEFT, padx=(8, 18))
        interval_box.bind("<<ComboboxSelected>>", self._on_interval_selected)

        tk.Label(
            controls,
            text="Symbol",
            fg=CHART_THEME["text_primary"],
            bg=CHART_THEME["bg"],
            font=("Helvetica", 11, "bold"),
        ).pack(side=tk.LEFT)
        symbol_box = ttk.Combobox(
            controls,
            values=list(DEFAULT_SYMBOLS.keys()),
            textvariable=self.chart_symbol_var,
            state="readonly",
            width=6,
        )
        symbol_box.pack(side=tk.LEFT, padx=(8, 0))
        symbol_box.bind("<<ComboboxSelected>>", self._on_chart_symbol_selected)

        ticker_wrapper = tk.Frame(
            self.detail_container, bg=CHART_THEME["bg"], padx=15)
        ticker_wrapper.pack(fill=tk.X, pady=(0, 10))
        self.ticker_panel = CryptoTicker(
            ticker_wrapper,
            self.symbol,
            self.display_symbol,
            theme=CHART_THEME,
        )
        self.ticker_panel.frame.pack(fill=tk.X)

        self.chart_header = tk.Frame(
            self.detail_container, bg=CHART_THEME["panel"], padx=15, pady=12)
        self.chart_header.pack(fill=tk.X)
        self.chart_header_label = tk.Label(
            self.chart_header,
            text=f"{self.display_symbol} Chart View",
            font=("Helvetica", 20, "bold"),
            fg=CHART_THEME["text_primary"],
            bg=CHART_THEME["panel"],
        )
        self.chart_header_label.pack(anchor="w")

        body = tk.Frame(self.detail_container,
                        bg=CHART_THEME["bg"], padx=15, pady=10)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self.orderbook_panel = OrderBookPanel(
            body,
            self.symbol,
            theme=CHART_THEME,
        )
        self.orderbook_panel.frame.grid(
            row=0, column=0, sticky="nsew", padx=(0, 12))

        self.technical_panel = TechnicalPanel(
            body,
            self.symbol,
            interval=DEFAULT_TECH_INTERVAL,
            theme=CHART_THEME,
        )
        self.technical_panel.frame.grid(row=0, column=1, sticky="nsew")

        self.detail_container.pack_forget()

    def _build_transactions_section(self):
        # Use light theme background to match other pages
        light_bg = "#f5f7fb"
        self.transactions_container = tk.Frame(
            self.content_frame, bg=light_bg, padx=15, pady=10)
        header = tk.Frame(self.transactions_container, bg=light_bg)
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(
            header,
            text="Market Transactions",
            font=("Helvetica", 18, "bold"),
            fg="#111827",
            bg=light_bg,
        ).pack(anchor="w")
        self.transactions_panel = TransactionsPanel(
            self.transactions_container,
            self.symbol,
            theme=THEME,
        )
        self.transactions_panel.pack(fill=tk.BOTH, expand=True)
        self.transactions_container.pack_forget()

    def _build_wallet_section(self):
        # Use light theme background to match other pages
        light_bg = "#f5f7fb"
        self.wallet_container = tk.Frame(
            self.content_frame, bg=light_bg, padx=15, pady=10)
        self.wallet_panel = WalletPanel(
            self.wallet_container,
            theme=THEME,
            on_trade=self._record_mock_trade,
            on_balance_change=self._on_wallet_balance_change,
        )
        self.wallet_panel.pack(fill=tk.BOTH, expand=True)
        self.wallet_container.pack_forget()

        # Sync initial balance and holdings from wallet to overview
        if hasattr(self, "overview_panel"):
            balance, holdings = self.wallet_panel.get_balance_and_holdings()
            self.overview_panel.sync_from_wallet(balance, holdings)

        # Also sync when wallet panel is shown
        if hasattr(self, "overview_panel") and hasattr(self, "wallet_panel"):
            balance, holdings = self.wallet_panel.get_balance_and_holdings()
            self.overview_panel.sync_from_wallet(balance, holdings)

    def _hide_transactions_section(self):
        if hasattr(self, "transactions_container") and self.transactions_container.winfo_ismapped():
            self.transactions_container.pack_forget()
            if hasattr(self, "transactions_panel"):
                self.transactions_panel.stop()

    def _hide_wallet_section(self):
        if hasattr(self, "wallet_container") and self.wallet_container.winfo_ismapped():
            self.wallet_container.pack_forget()
            if hasattr(self, "wallet_panel"):
                self.wallet_panel.stop()

    def _record_mock_trade(self, action, asset, amount, price, notional):
        """Record trade from wallet panel and sync to overview"""
        if hasattr(self, "transactions_panel"):
            self.transactions_panel.record_user_trade(
                action, asset, amount, price, notional)
        direction = "Buy" if action == "BUY" else "Sell"
        self.status_var.set(
            f"WALLET • {direction} {amount:.4f} {asset} @ {price:,.2f} (value {notional:,.2f})"
        )
        # Sync wallet data to overview
        if hasattr(self, "wallet_panel") and hasattr(self, "overview_panel"):
            balance, holdings = self.wallet_panel.get_balance_and_holdings()
            self.overview_panel.sync_from_wallet(balance, holdings)

    def _record_overview_trade(self, action, asset, amount, price, notional):
        """Record trade from overview panel and sync to wallet"""
        if hasattr(self, "transactions_panel"):
            self.transactions_panel.record_user_trade(
                action, asset, amount, price, notional)
        direction = "Buy" if action == "BUY" else "Sell"
        self.status_var.set(
            f"OVERVIEW • {direction} {amount:.4f} {asset} @ {price:,.2f} (value {notional:,.2f})"
        )
        # Sync overview data to wallet
        if hasattr(self, "overview_panel") and hasattr(self, "wallet_panel"):
            balance, holdings = self.overview_panel.get_balance_and_holdings()
            self.wallet_panel.sync_from_overview(balance, holdings)

    def _on_wallet_balance_change(self, balance, holdings, total_value):
        """Callback when wallet balance/total changes - sync to overview in real-time"""
        if hasattr(self, "overview_panel"):
            self.overview_panel.sync_from_wallet(
                balance, holdings, total_value)

    def _format_display_name(self, symbol_key):
        symbol_value = DEFAULT_SYMBOLS[symbol_key].upper()
        if symbol_value.startswith(symbol_key):
            quote = symbol_value[len(symbol_key):]
            if quote:
                return f"{symbol_key}/{quote}"
        return symbol_value

    def switch_symbol(self, symbol_key):
        symbol_key = symbol_key.upper()
        if symbol_key not in DEFAULT_SYMBOLS:
            return

        symbol_changed = symbol_key != self.current_symbol_key
        if symbol_changed:
            self.current_symbol_key = symbol_key
            self.symbol = DEFAULT_SYMBOLS[symbol_key]
            self.display_symbol = self._format_display_name(symbol_key)

            self.ticker_panel.set_symbol(self.symbol, self.display_symbol)
            self.orderbook_panel.set_symbol(self.symbol)
            self.technical_panel.set_symbol(self.symbol)
            if hasattr(self, "overview_panel"):
                self.overview_panel.set_active_symbol(symbol_key)

        if hasattr(self, "chart_header_label"):
            self.chart_header_label.config(
                text=f"{self.display_symbol} Chart View")
        # Banner removed
        if hasattr(self, "chart_symbol_var"):
            self.chart_symbol_var.set(symbol_key)
        if self.details_visible:
            self.header_title.config(text=f"{self.display_symbol} Dashboard")
        self.show_detail()
        self._set_active_nav("Chart")
        self.sidebar_insight_var.set(
            f"Access price, order book and indicator data for {self.display_symbol}"
        )

    def start_all(self):
        self.overview_panel.start()
        # Sync overview with wallet after both are initialized
        if hasattr(self, "overview_panel") and hasattr(self, "wallet_panel"):
            balance, holdings = self.wallet_panel.get_balance_and_holdings()
            self.overview_panel.sync_from_wallet(balance, holdings)

    def start_detail_panels(self):
        if self.detail_panels_started:
            return
        self.ticker_panel.start()
        self.orderbook_panel.start()
        self.technical_panel.start()
        self.detail_panels_started = True

    def stop_detail_panels(self):
        if not self.detail_panels_started:
            return
        self.ticker_panel.stop()
        self.orderbook_panel.stop()
        self.technical_panel.stop()
        self.detail_panels_started = False

    def show_detail(self):
        if self.details_visible:
            return
        self._hide_transactions_section()
        self._hide_wallet_section()
        self._hide_overview_section()
        # Hide header bar for chart page
        if hasattr(self, "header_bar"):
            self.header_bar.pack_forget()
        self.detail_container.pack(fill=tk.BOTH, expand=True)
        self._set_content_background(CHART_THEME["bg"])
        self.details_visible = True
        self.header_title.config(text=f"{self.display_symbol} Dashboard")
        self.start_detail_panels()

    def hide_detail(self):
        if not self.details_visible:
            return
        self.detail_container.pack_forget()
        self._set_content_background(THEME["bg"])
        self.details_visible = False
        self.header_title.config(text="Live Markets Overview")
        self.stop_detail_panels()

    def _show_transactions_section(self):
        self.hide_detail()
        self._hide_wallet_section()
        # Hide header bar for transactions page
        if hasattr(self, "header_bar"):
            self.header_bar.pack_forget()
        if hasattr(self, "transactions_container"):
            self._hide_overview_section()
            self.transactions_container.pack(
                fill=tk.BOTH,
                expand=True,
            )
            if hasattr(self, "transactions_panel"):
                self.transactions_panel.start()
            self.header_title.config(text="Transactions Stream")

    def _show_wallet_section(self):
        self.hide_detail()
        self._hide_transactions_section()
        # Hide header bar for wallet page
        if hasattr(self, "header_bar"):
            self.header_bar.pack_forget()
        if hasattr(self, "wallet_container"):
            self._hide_overview_section()
            self.wallet_container.pack(
                fill=tk.BOTH,
                expand=True,
            )
            if hasattr(self, "wallet_panel"):
                self.wallet_panel.start()
            self.header_title.config(text="Wallet Overview")

    def _on_mousewheel(self, event):
        if event.delta:
            if sys.platform == "darwin":
                step = max(1, int(abs(event.delta)))
                move = -step if event.delta > 0 else step
            else:
                move = int(-1 * (event.delta / 120))
                if move == 0:
                    move = -1 if event.delta > 0 else 1
        elif event.num == 4:
            move = -1
        else:
            move = 1
        if hasattr(self, "main_canvas"):
            self.main_canvas.yview_scroll(move, "units")

    def _start_scroll_drag(self, event):
        self._scroll_drag_enabled = True
        self._scroll_drag_active = False
        self._scroll_drag_start = (event.x_root, event.y_root)
        x, y = self._canvas_local_coordinates(event)
        if x is not None:
            self.main_canvas.scan_mark(x, y)

    def _perform_scroll_drag(self, event):
        if not self._scroll_drag_enabled:
            return
        if not self._scroll_drag_active:
            dx = abs(event.x_root - self._scroll_drag_start[0])
            dy = abs(event.y_root - self._scroll_drag_start[1])
            if max(dx, dy) < 3:
                return
            self._scroll_drag_active = True
        x, y = self._canvas_local_coordinates(event)
        if x is None:
            return
        self.main_canvas.scan_dragto(x, y, gain=1)
        return "break"

    def _stop_scroll_drag(self, _event):
        if self._scroll_drag_active:
            self._scroll_drag_active = False
            self._scroll_drag_enabled = False
            return "break"
        self._scroll_drag_enabled = False

    def _canvas_local_coordinates(self, event):
        if not hasattr(self, "main_canvas"):
            return None, None
        canvas = self.main_canvas
        return (
            event.x_root - canvas.winfo_rootx(),
            event.y_root - canvas.winfo_rooty(),
        )

    def _hide_overview_section(self):
        if hasattr(self, "overview_panel") and self.overview_panel.frame.winfo_ismapped():
            self.overview_panel.pack_forget()

    def _show_overview_section(self):
        if hasattr(self, "overview_panel") and not self.overview_panel.frame.winfo_ismapped():
            self.overview_panel.pack(fill=tk.X)

    def _update_canvas_window_size(self, event):
        """Update canvas window size to fill the canvas"""
        if hasattr(self, "canvas_window") and hasattr(self, "main_canvas"):
            self.main_canvas.itemconfigure(
                self.canvas_window, width=event.width)
            # Always make content_frame fill the full height of the canvas
            canvas_height = event.height
            if canvas_height > 1:
                self.main_canvas.itemconfigure(
                    self.canvas_window, height=canvas_height)

    def _set_content_background(self, color):
        if hasattr(self, "content_frame"):
            self.content_frame.configure(bg=color)
        if hasattr(self, "main_canvas"):
            self.main_canvas.configure(bg=color)

    def on_close(self):
        self.overview_panel.stop()
        self.stop_detail_panels()
        self._hide_wallet_section()
        self._hide_transactions_section()
        self.root.destroy()


def run():
    root = tk.Tk()
    app = CryptoDashboardApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    run()
