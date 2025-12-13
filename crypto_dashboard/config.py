DEFAULT_SYMBOLS = {
    "BTC": "btcusdt",
    "ETH": "ethusdt",
    "SOL": "solusdt",
    "BNB": "bnbusdt",
    "XRP": "xrpusdt",
    "ADA": "adausdt",
    "DOGE": "dogeusdt",
    "MATIC": "maticusdt",
    "LTC": "ltcusdt",
    "AVAX": "avaxusdt",
}

# UI settings
TICKER_REFRESH_INTERVAL = 0.1      # seconds between ticker WebSocket updates
ORDERBOOK_REFRESH_MS = 3000       # ms, REST depth refresh interval
TECHNICAL_REFRESH_MS = 30000      # ms, fetch new klines every 30 seconds
MAX_TRADES_DISPLAY = 50           # number of trade rows to display
WALLET_REFRESH_MS = 15000
TRANSACTIONS_REFRESH_MS = 8000

ORDERBOOK_DEFAULT_LEVELS = 10
ORDERBOOK_ALL_LEVELS = 20
DEFAULT_TECH_INTERVAL = "1h"
OVERVIEW_REFRESH_MS = 8000

THEME = {
    "bg": "#0d1117",
    "panel": "#161b22",
    "panel_border": "#242c37",
    "header": "#111827",
    "text_primary": "#f3f4f6",
    "text_muted": "#9ca3af",
    "accent_green": "#10b981",
    "accent_red": "#ef4444",
    "accent_orange": "#f59e0b",
    "divider": "#1f2933",
    "sidebar_bg": "#f5f5f5",
    "sidebar_text": "#6b7280",
    "sidebar_active": "#2563eb",
    "sidebar_active_bg": "#e0edff",
}

CHART_THEME = {
    **THEME,
    "bg": "#f5f7fb",
    "panel": "#ffffff",
    "panel_border": "#d1d5db",
    "header": "#e5e7eb",
    "text_primary": "#0f172a",
    "text_muted": "#6b7280",
    "divider": "#e5e7eb",
}

WALLET_CASH_BALANCE = 2500.0
WALLET_HOLDINGS = {
    "BTC": 0.005,
    "ETH": 0.15,
    "SOL": 3.2,
    "MATIC": 50,
}
