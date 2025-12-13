import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime

if __package__ is None or __package__ == "":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from config import OVERVIEW_REFRESH_MS, THEME  # type: ignore
    from utils.binance_rest import get_24hr_ticker, get_klines  # type: ignore
else:
    from ..config import OVERVIEW_REFRESH_MS, THEME
    from ..utils.binance_rest import get_24hr_ticker, get_klines


# Default favorite colors palette (4 colors for 4 favorites max)
FAVORITE_COLORS = [
    {"bg": "#fde68a", "fg": "#1f2937", "accent": "#10b981"},  # Yellow
    {"bg": "#e0e7ff", "fg": "#1e1b4b", "accent": "#6366f1"},  # Purple
    {"bg": "#c7d2fe", "fg": "#1d4ed8", "accent": "#f97316"},  # Blue
    {"bg": "#bbf7d0", "fg": "#064e3b", "accent": "#22c55e"},  # Green
]

# Default favorites
DEFAULT_FAVORITES = ["BTC", "ETH", "LTC", "ADA"]

def get_favorites_file_path():
    """Get the path to the favorites config file"""
    if __package__ is None or __package__ == "":
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(os.path.dirname(current_dir))
    else:
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(parent_dir, "favorites.json")

def load_favorites():
    """Load favorites from file, return default if file doesn't exist"""
    file_path = get_favorites_file_path()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data.get("favorites", DEFAULT_FAVORITES)
        except Exception:
            return DEFAULT_FAVORITES
    return DEFAULT_FAVORITES

def save_favorites(favorites):
    """Save favorites to file"""
    file_path = get_favorites_file_path()
    try:
        with open(file_path, 'w') as f:
            json.dump({"favorites": favorites}, f, indent=2)
        return True
    except Exception:
        return False

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
        # Use light background for overview section (overview has its own light theme)
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
        
        # Load user favorites
        self.user_favorites = load_favorites()
        # Filter to only include symbols that exist
        self.user_favorites = [f for f in self.user_favorites if f in self.symbols]
        # If no valid favorites, use defaults
        if not self.user_favorites:
            self.user_favorites = [f for f in DEFAULT_FAVORITES if f in self.symbols]
        
        self.frame = tk.Frame(parent, bg=self.bg, padx=28, pady=16)
        self.frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            self.frame,
            text="Overview",
            font=("Helvetica", 22, "bold"),
            bg=self.bg,
            fg="#0f172a",
        ).pack(anchor="w", pady=(0, 10))
        self._build_main_layout()
        self.set_active_symbol(self.chart_symbol)
        self._trigger_chart_refresh()

    def _build_main_layout(self):
        grid = tk.Frame(self.frame, bg=self.bg)
        grid.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        grid.columnconfigure(0, weight=1, uniform="col")
        grid.columnconfigure(1, weight=1, uniform="col")
        grid.rowconfigure(0, weight=1, minsize=300)  # Top row for favorites and chart
        grid.rowconfigure(1, weight=3, minsize=400)  # Bottom row for live market and exchange

        favorites_holder = tk.Frame(grid, bg=self.bg)
        favorites_holder.grid(row=0, column=0, padx=(0, 12), pady=(0, 12), sticky="nsew")
        self._build_favorites(favorites_holder)

        chart_holder = tk.Frame(grid, bg=self.bg)
        chart_holder.grid(row=0, column=1, padx=(12, 0), pady=(0, 12), sticky="nsew")
        self._build_chart_preview(chart_holder)

        live_holder = tk.Frame(grid, bg=self.bg)
        live_holder.grid(row=1, column=0, padx=(0, 12), pady=(0, 0), sticky="nsew")
        self._build_live_market(live_holder)

        exchange_holder = tk.Frame(grid, bg=self.bg)
        exchange_holder.grid(row=1, column=1, padx=(12, 0), pady=(0, 0), sticky="nsew")
        self._build_exchange_card(exchange_holder)

    def _build_favorites(self, parent):
        # Header with title and edit button
        header = tk.Frame(parent, bg=self.bg)
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header, text="Favorites", font=("Helvetica", 16, "bold"), bg=self.bg, fg="#111827").pack(side=tk.LEFT)
        
        # Edit button with modern styling
        edit_btn = tk.Button(
            header,
            text="⚙ Edit Favorites",
            font=("Helvetica", 11),
            bg="#f3f4f6",
            fg="#111827",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._open_favorites_editor,
            activebackground="#e5e7eb",
            activeforeground="#111827",
            bd=0,
            highlightthickness=0
        )
        edit_btn.pack(side=tk.RIGHT)
        # Add hover effect
        def on_enter(e):
            edit_btn.config(bg="#e5e7eb")
        def on_leave(e):
            edit_btn.config(bg="#f3f4f6")
        edit_btn.bind("<Enter>", on_enter)
        edit_btn.bind("<Leave>", on_leave)
        
        # Grid for favorite cards
        self.favorites_grid = tk.Frame(parent, bg=self.bg)
        self.favorites_grid.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        self.favorites_grid.columnconfigure((0, 1), weight=1)
        
        self._refresh_favorites_display()
    
    def _refresh_favorites_display(self):
        """Refresh the favorites display with current user favorites"""
        # Clear existing cards
        for widget in self.favorites_grid.winfo_children():
            widget.destroy()
        self.favorite_cards.clear()
        
        # Create cards for current favorites
        row_index = 0
        col_index = 0
        for idx, symbol in enumerate(self.user_favorites):
            if symbol not in self.symbols:
                continue
            
            # Get color palette (cycle through available colors)
            palette = FAVORITE_COLORS[idx % len(FAVORITE_COLORS)]
            
            card = tk.Frame(self.favorites_grid, bg=self.surface, bd=0, relief="flat", padx=2, pady=2)
            card.grid(row=row_index, column=col_index, sticky="nsew", padx=8, pady=8)
            # Start with a neutral gray background, will be updated dynamically
            inner = tk.Frame(card, bg="#e5e7eb", padx=18, pady=16)
            inner.pack(fill=tk.BOTH, expand=True)
            inner.bind("<Button-1>", lambda _e, s=symbol: self._handle_symbol_select(s))

            price_label = tk.Label(inner, text="$ --", font=("Helvetica", 24, "bold"), bg="#e5e7eb", fg="#111827")
            price_label.pack(anchor="w", pady=(30, 0))
            price_label.bind("<Button-1>", lambda _e, s=symbol: self._handle_symbol_select(s))
            
            subtitle = tk.Label(inner, text=f"{symbol} / USDT", font=("Helvetica", 12), bg="#e5e7eb", fg="#111827")
            subtitle.pack(anchor="w")
            subtitle.bind("<Button-1>", lambda _e, s=symbol: self._handle_symbol_select(s))
            
            change_label = tk.Label(inner, text="--", font=("Helvetica", 11, "bold"), bg="#e5e7eb", fg="#6b7280")
            change_label.pack(anchor="ne")
            change_label.bind("<Button-1>", lambda _e, s=symbol: self._handle_symbol_select(s))

            self.favorite_cards[symbol] = {
                "frame": card,
                "inner": inner,
                "price": price_label,
                "subtitle": subtitle,
                "change": change_label,
                "palette": palette,
            }
            col_index = (col_index + 1) % 2
            if col_index == 0:
                row_index += 1
    
    def _open_favorites_editor(self):
        """Open dialog to edit favorites"""
        dialog = tk.Toplevel(self.frame)
        dialog.title("Edit Favorites")
        dialog.geometry("480x580")
        dialog.configure(bg=self.bg)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Main container with consistent padding
        main_container = tk.Frame(dialog, bg=self.bg, padx=28, pady=28)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Header section
        header_frame = tk.Frame(main_container, bg=self.bg)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(
            header_frame,
            text="Edit Favorites",
            font=("Helvetica", 20, "bold"),
            bg=self.bg,
            fg="#0f172a"
        ).pack(anchor="w")
        
        tk.Label(
            header_frame,
            text="Select up to 4 favorites",
            font=("Helvetica", 11),
            bg=self.bg,
            fg="#6b7280"
        ).pack(anchor="w", pady=(6, 0))
        
        # Available symbols section with card style matching the app
        list_card = tk.Frame(main_container, bg=self.surface, padx=20, pady=18, 
                            highlightthickness=1, highlightbackground="#e5e7eb",
                            relief="flat")
        list_card.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Section header
        section_header = tk.Frame(list_card, bg=self.surface)
        section_header.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(
            section_header,
            text="Available Cryptocurrencies",
            font=("Helvetica", 13, "bold"),
            bg=self.surface,
            fg="#111827"
        ).pack(side=tk.LEFT)
        
        # Selection counter in header
        info_label = tk.Label(
            section_header,
            text=f"{len(self.user_favorites)} / 4 selected",
            font=("Helvetica", 11),
            bg=self.surface,
            fg="#6b7280"
        )
        info_label.pack(side=tk.RIGHT)
        
        # Scrollable listbox frame
        listbox_frame = tk.Frame(list_card, bg=self.surface)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", bg="#e5e7eb",
                                 troughcolor="#f3f4f6", width=12)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        available_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.MULTIPLE,
            font=("Helvetica", 12),
            bg="#ffffff",
            fg="#111827",
            selectbackground="#3b82f6",
            selectforeground="white",
            relief="flat",
            bd=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
            height=12,
            activestyle="none"
        )
        available_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=available_listbox.yview)
        
        # Populate with all available symbols
        all_symbols = sorted(self.symbols.keys())
        for idx, symbol in enumerate(all_symbols):
            available_listbox.insert(tk.END, f"  {symbol} / USDT")
            if symbol in self.user_favorites:
                available_listbox.selection_set(idx)
        
        def update_selection_info():
            count = len(available_listbox.curselection())
            info_label.config(text=f"{count} / 4 selected")
            # Change color if limit reached
            if count >= 4:
                info_label.config(fg="#dc2626")
            else:
                info_label.config(fg="#6b7280")
        
        # Track previous selection to detect additions
        previous_selection = set(available_listbox.curselection())
        
        def limit_selection(event):
            """Prevent selecting more than 4 items"""
            nonlocal previous_selection
            current_selection = set(available_listbox.curselection())
            current_count = len(current_selection)
            
            # If we have more than 4, we need to fix it
            if current_count > 4:
                # Check if this is a new selection (count increased) or just a change
                if current_count > len(previous_selection):
                    # User tried to add a new item when already at 4
                    # Revert to previous selection
                    available_listbox.selection_clear(0, tk.END)
                    for idx in previous_selection:
                        available_listbox.selection_set(idx)
                    info_label.config(text="4 / 4 selected (maximum reached)", fg="#dc2626")
                    dialog.after(100, update_selection_info)
                else:
                    # Count is same or less, but somehow > 4 - shouldn't happen, but fix it
                    # Keep first 4
                    limited = list(current_selection)[:4]
                    available_listbox.selection_clear(0, tk.END)
                    for idx in limited:
                        available_listbox.selection_set(idx)
                    previous_selection = set(limited)
                    update_selection_info()
            else:
                # Valid selection (4 or fewer) - allow it
                previous_selection = current_selection
                update_selection_info()
        
        available_listbox.bind("<<ListboxSelect>>", limit_selection)
        
        # Buttons section with consistent styling
        btn_frame = tk.Frame(main_container, bg=self.bg)
        btn_frame.pack(fill=tk.X)
        
        def apply_favorites():
            selected = [all_symbols[i] for i in available_listbox.curselection()]
            if len(selected) > 4:
                messagebox.showwarning("Too Many Favorites", "Please select up to 4 favorites.")
                return
            if len(selected) == 0:
                messagebox.showwarning("No Selection", "Please select at least one favorite.")
                return
            
            self.user_favorites = selected
            save_favorites(selected)
            self._refresh_favorites_display()
            dialog.destroy()
        
        # Button container for proper spacing
        button_container = tk.Frame(btn_frame, bg=self.bg)
        button_container.pack(side=tk.RIGHT)
        
        # Cancel button - same font size as Save Changes
        cancel_btn = tk.Button(
            button_container,
            text="Cancel",
            font=("Helvetica", 13, "bold"),
            bg="#f3f4f6",
            fg="#111827",
            relief="flat",
            padx=20,
            pady=10,
            command=dialog.destroy,
            cursor="hand2",
            activebackground="#e5e7eb",
            activeforeground="#111827",
            bd=0,
            highlightthickness=0
        )
        cancel_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        def on_cancel_enter(e):
            cancel_btn.config(bg="#e5e7eb")
        def on_cancel_leave(e):
            cancel_btn.config(bg="#f3f4f6")
        cancel_btn.bind("<Enter>", on_cancel_enter)
        cancel_btn.bind("<Leave>", on_cancel_leave)
        
        # Save button with light background and dark text for better readability
        save_btn = tk.Button(
            button_container,
            text="Save Changes",
            font=("Helvetica", 13, "bold"),
            bg="#f3f4f6",
            fg="#111827",
            relief="flat",
            padx=24,
            pady=10,
            command=apply_favorites,
            cursor="hand2",
            activebackground="#e5e7eb",
            activeforeground="#111827",
            bd=0,
            highlightthickness=0,
            highlightbackground="#f3f4f6",
            highlightcolor="#f3f4f6"
        )
        save_btn.pack(side=tk.LEFT)
        
        def on_save_enter(e):
            save_btn.config(bg="#e5e7eb", fg="#111827")
        def on_save_leave(e):
            save_btn.config(bg="#f3f4f6", fg="#111827")
        save_btn.bind("<Enter>", on_save_enter)
        save_btn.bind("<Leave>", on_save_leave)

    def _build_chart_preview(self, parent):
        # Add a label to match the "Favorites" label spacing
        tk.Label(parent, text="Chart Preview", font=("Helvetica", 16, "bold"), bg=self.bg, fg="#111827").pack(anchor="w")
        holder = tk.Frame(parent, bg=self.surface, padx=18, pady=16, highlightthickness=2, highlightbackground="#93c5fd")
        holder.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
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
        card = tk.Frame(parent, bg=self.surface, padx=18, pady=10)
        card.pack(fill=tk.BOTH, expand=True)
        tk.Label(card, text="Live Market", font=("Helvetica", 16, "bold"), bg=self.surface, fg="#111827").pack(anchor="w", pady=(0, 6))
        
        # Create scrollable frame for market rows
        # Calculate height for exactly 5 rows: each row ~74px (50px canvas + 20px padding + 4px margin)
        row_height = 74  # Approximate height per row
        max_visible_rows = 5
        scrollable_height = row_height * max_visible_rows
        
        # Create canvas and scrollbar - make it expand to fill available space
        canvas_frame = tk.Frame(card, bg=self.surface)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        market_canvas = tk.Canvas(canvas_frame, bg=self.surface, highlightthickness=0, yscrollcommand=scrollbar.set)
        market_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Update canvas height dynamically when frame is resized
        def update_canvas_height(event=None):
            if event and event.widget == canvas_frame:
                frame_height = event.height
                if frame_height > 1:
                    market_canvas.configure(height=frame_height)
        
        canvas_frame.bind("<Configure>", update_canvas_height)
        scrollbar.config(command=market_canvas.yview)
        
        # Create frame inside canvas for rows
        rows_container = tk.Frame(market_canvas, bg=self.surface)
        canvas_window = market_canvas.create_window((0, 0), window=rows_container, anchor="nw")
        
        # Configure canvas scrolling
        def configure_scroll_region(event=None):
            market_canvas.configure(scrollregion=market_canvas.bbox("all"))
            # Limit canvas width to prevent horizontal scrolling
            canvas_width = market_canvas.winfo_width()
            if canvas_width > 1:
                market_canvas.itemconfig(canvas_window, width=canvas_width)
            
            # Update scrollbar visibility based on content
            rows_container.update_idletasks()
            bbox = market_canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                if content_height <= scrollable_height:
                    scrollbar.pack_forget()
                else:
                    if not scrollbar.winfo_ismapped():
                        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def on_canvas_configure(event):
            canvas_width = event.width
            market_canvas.itemconfig(canvas_window, width=canvas_width)
            configure_scroll_region()
        
        rows_container.bind("<Configure>", configure_scroll_region)
        market_canvas.bind("<Configure>", on_canvas_configure)
        
        # Track if mouse is over market section
        market_mouse_inside = [False]
        
        def on_enter(event):
            market_mouse_inside[0] = True
        
        def on_leave(event):
            market_mouse_inside[0] = False
        
        # Enable mousewheel scrolling and prevent event propagation
        # Use bind_all with add="+" to run BEFORE main window's handler
        def on_mousewheel_global(event):
            # Check if mouse is over market section
            if not market_mouse_inside[0]:
                return None
            
            try:
                widget = event.widget
                # Double-check widget hierarchy
                current = widget
                is_in_market = False
                
                while current:
                    if current == market_canvas or current == rows_container or current == canvas_frame:
                        is_in_market = True
                        break
                    try:
                        current = current.master
                    except:
                        break
                
                if is_in_market:
                    if hasattr(event, 'delta') and event.delta:
                        # Windows/Mac
                        market_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    elif hasattr(event, 'num'):
                        if event.num == 4:
                            # Linux scroll up
                            market_canvas.yview_scroll(-1, "units")
                        elif event.num == 5:
                            # Linux scroll down
                            market_canvas.yview_scroll(1, "units")
                    return "break"  # Stop event propagation to main window
            except Exception:
                pass
            return None
        
        # Bind enter/leave events to track mouse position
        canvas_frame.bind("<Enter>", on_enter)
        canvas_frame.bind("<Leave>", on_leave)
        market_canvas.bind("<Enter>", on_enter)
        market_canvas.bind("<Leave>", on_leave)
        rows_container.bind("<Enter>", on_enter)
        rows_container.bind("<Leave>", on_leave)
        
        # Bind directly to widgets WITHOUT add="+" to give our handlers priority
        # This ensures our handler runs first and can return "break" to stop propagation
        def bind_mousewheel(widget):
            # Use bind (not bind_all) without add="+" to replace any existing handlers
            # This gives our handler priority for these specific widgets
            widget.bind("<MouseWheel>", on_mousewheel_global)
            widget.bind("<Button-4>", on_mousewheel_global)
            widget.bind("<Button-5>", on_mousewheel_global)
        
        bind_mousewheel(market_canvas)
        bind_mousewheel(rows_container)
        bind_mousewheel(canvas_frame)
        bind_mousewheel(card)  # Also bind to the card itself
        
        # Store canvas reference for cleanup
        self.market_canvas = market_canvas
        
        # Create rows for each symbol
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
            
            # Bind mousewheel and enter/leave to row and all its children
            bind_mousewheel(row)
            bind_mousewheel(title)
            bind_mousewheel(change)
            bind_mousewheel(price)
            bind_mousewheel(canvas)
            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)
            
            self.market_rows[symbol] = {"frame": row, "change": change, "price": price}
            self.spark_canvases[symbol] = canvas

    def _build_exchange_card(self, parent):
        card = tk.Frame(parent, bg=self.surface, padx=18, pady=10, highlightthickness=1, highlightbackground="#e5e7eb")
        card.pack(fill=tk.BOTH, expand=True)
        
        # Exchange title
        tk.Label(card, text="Exchange", font=("Helvetica", 16, "bold"), bg=self.surface, fg="#111827").pack(anchor="w", pady=(0, 12))
        
        # Conversion display section with better layout
        conversion_frame = tk.Frame(card, bg=self.surface)
        conversion_frame.pack(fill=tk.X, pady=(0, 12))
        
        # Left side: description text
        desc_frame = tk.Frame(conversion_frame, bg=self.surface)
        desc_frame.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(desc_frame, text="1 unit converts to", font=("Helvetica", 11), bg=self.surface, fg="#6b7280").pack(anchor="w")
        
        # Right side: conversion value
        quote_frame = tk.Frame(conversion_frame, bg=self.surface)
        quote_frame.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(quote_frame, textvariable=self.exchange_quote_var, font=("Helvetica", 18, "bold"), bg=self.surface, fg="#111827").pack(anchor="e")

        # Input section with improved styling
        entry_frame = tk.Frame(card, bg="#f9fafb", highlightthickness=1, highlightbackground="#e5e7eb", padx=14, pady=12)
        entry_frame.pack(fill=tk.X, pady=(0, 16))
        
        # Amount input
        amount_frame = tk.Frame(entry_frame, bg="#f9fafb")
        amount_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(amount_frame, text="Amount", font=("Helvetica", 10, "bold"), bg="#f9fafb", fg="#6b7280").pack(anchor="w", pady=(0, 4))
        amount_entry = tk.Entry(amount_frame, textvariable=self.exchange_amount_var, bd=0, font=("Helvetica", 16, "bold"), 
                                bg="#ffffff", fg="#111827", relief="flat", highlightthickness=1, highlightbackground="#d1d5db",
                                highlightcolor="#3b82f6", insertbackground="#111827", justify="left")
        amount_entry.pack(fill=tk.X, ipady=8)
        
        # Asset selector
        asset_frame = tk.Frame(entry_frame, bg="#f9fafb")
        asset_frame.pack(side=tk.RIGHT, padx=(12, 0))
        tk.Label(asset_frame, text="Asset", font=("Helvetica", 10, "bold"), bg="#f9fafb", fg="#6b7280").pack(anchor="w", pady=(0, 4))
        asset_combo = ttk.Combobox(asset_frame, values=list(self.symbols.keys()), textvariable=self.exchange_asset_var, 
                                   state="readonly", width=10, font=("Helvetica", 14, "bold"))
        asset_combo.pack(fill=tk.X)

        # Bind events for real-time updates
        self.exchange_amount_var.trace_add("write", lambda *_: self._update_exchange_quote())
        asset_combo.bind("<<ComboboxSelected>>", lambda _e: self._handle_exchange_select())
        amount_entry.bind("<KeyRelease>", lambda _e: self._update_exchange_quote())
        amount_entry.bind("<FocusOut>", lambda _e: self._update_exchange_quote())

        # Balance section with improved styling
        balance_section = tk.Frame(card, bg=self.surface)
        balance_section.pack(fill=tk.X, pady=(8, 0))
        tk.Label(balance_section, text="Portfolio Balance", font=("Helvetica", 12, "bold"), bg=self.surface, fg="#6b7280").pack(anchor="w", pady=(0, 4))
        self.exchange_balance_var = tk.StringVar(value="$ -- USD")
        tk.Label(balance_section, textvariable=self.exchange_balance_var, font=("Helvetica", 20, "bold"), bg=self.surface, fg="#16a34a").pack(anchor="w")

    def _handle_symbol_select(self, symbol):
        self.chart_symbol = symbol
        self.exchange_asset_var.set(symbol)
        self.chart_selector_var.set(symbol)
        self._update_exchange_quote()
        self.on_select(symbol)
        self.set_active_symbol(symbol)

    def _handle_exchange_select(self):
        symbol = self.exchange_asset_var.get()
        if symbol and symbol in self.symbols:
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
        # Calculate portfolio balance (sum of all symbol prices for demo purposes)
        # In a real app, this would be based on actual holdings
        balance = 0.0
        for symbol_key, payload in data.items():
            price = payload["price"]
            change_percent = payload["change_percent"]
            self.latest_prices[symbol_key] = price
            history = self.price_history[symbol_key]
            history.append(price)
            self.price_history[symbol_key] = history[-120:]
            # For demo: sum all prices (in real app, multiply by holdings)
            balance += price

            favorite = self.favorite_cards.get(symbol_key)
            if favorite:
                # Determine colors based on price change
                if change_percent >= 0:
                    # Green shades for positive changes
                    bg_color = "#d1fae5"  # Light green background
                    text_color = "#065f46"  # Dark green text
                    change_color = "#059669"  # Medium green for change text
                else:
                    # Red shades for negative changes
                    bg_color = "#fee2e2"  # Light red background
                    text_color = "#7f1d1d"  # Dark red text
                    change_color = "#dc2626"  # Medium red for change text
                
                # Update background colors
                favorite["inner"].config(bg=bg_color)
                favorite["price"].config(text=f"$ {price:,.2f}", bg=bg_color, fg=text_color)
                favorite["subtitle"].config(bg=bg_color, fg=text_color)
                favorite["change"].config(bg=bg_color, fg=change_color)
                
                sign = "+" if change_percent >= 0 else ""
                favorite["change"].config(text=f"{sign}{change_percent:.2f}%")

            row = self.market_rows.get(symbol_key)
            if row:
                sign = "+" if change_percent >= 0 else ""
                fg = "#16a34a" if change_percent >= 0 else "#dc2626"
                row["change"].config(text=f"{sign}{change_percent:.2f}%", fg=fg)
                row["price"].config(text=f"{price:,.2f} USD")
                canvas = self.spark_canvases.get(symbol_key)
                if canvas:
                    self._draw_sparkline(canvas, self.price_history[symbol_key], symbol_key)

        # Update exchange balance
        if hasattr(self, "exchange_balance_var"):
            self.exchange_balance_var.set(f"$ {balance:,.2f} USD")
        # Update exchange quote when prices change
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
        # Use green gradient for upward trends, red gradient for downward trends
        fill_color = "#d1fae5" if actual_trend_up else "#fee2e2"  # Light green for up, light red for down

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
        if not symbol or symbol not in self.symbols:
            self.exchange_quote_var.set("$ -- USD")
            return
        
        try:
            amount_str = self.exchange_amount_var.get().strip()
            if not amount_str:
                amount = 0.0
            else:
                amount = float(amount_str)
        except (TypeError, ValueError):
            amount = 0.0
        
        price = self.latest_prices.get(symbol, 0.0)
        if price <= 0:
            self.exchange_quote_var.set("$ -- USD")
            return
        
        quote = amount * price
        if quote > 0:
            self.exchange_quote_var.set(f"$ {quote:,.2f} USD")
        else:
            self.exchange_quote_var.set("$ 0.00 USD")

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
        # Update exchange quote when symbol changes
        self._update_exchange_quote()
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
