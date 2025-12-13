import requests

BASE_URL = "https://api.binance.com"


def safe_api_call(path, params=None, retries=3, timeout=10):
    url = BASE_URL + path
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            print(f"Timeout calling {path} (attempt {attempt + 1}/{retries})")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error calling {path}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error calling {path}: {e}")
            return None
    print(f"All retries failed for {path}")
    return None


def get_order_book(symbol, limit=10):
    return safe_api_call("/api/v3/depth", {"symbol": symbol.upper(), "limit": limit})


def get_recent_trades(symbol, limit=20):
    return safe_api_call("/api/v3/trades", {"symbol": symbol.upper(), "limit": limit})


def get_klines(symbol, interval="1h", limit=50):
    return safe_api_call("/api/v3/klines", {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    })


def get_24hr_ticker(symbol):
    return safe_api_call(
        "/api/v3/ticker/24hr",
        {
            "symbol": symbol.upper(),
        },
    )
