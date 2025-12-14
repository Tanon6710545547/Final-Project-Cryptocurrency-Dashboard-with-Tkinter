# Crypto Dashboard

A real-time cryptocurrency trading dashboard built with Python and Tkinter, featuring live market data, trading simulation, and portfolio management.

## Features

- **Overview Panel**: Favorite cryptocurrencies, live market data, charts, and exchange section
- **Wallet Panel**: Portfolio management, buy/sell functionality, deposit/withdraw
- **Transactions Panel**: Trading history with buy/sell records
- **Real-time Data**: Live price updates from Binance API

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python crypto_dashboard/main.py
```

## Requirements

- Python 3.7+
- matplotlib, numpy, requests, websocket-client

## Usage

### Overview & Wallet Panels
- Select asset from dropdown
- Enter amount to buy/sell
- Click "Buy" or "Sell"
- View holdings and balance updates

### Transactions
- All trades are automatically recorded
- View history in Transactions panel
- Color-coded: Green (BUY), Red (SELL)

## Configuration

Supported cryptocurrencies: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, MATIC, LTC, AVAX

Default balance: 2,500 USDT

## Notes

- Mock trading application (no real money)
- Requires internet connection for Binance API
- Data refreshes every 8-15 seconds
