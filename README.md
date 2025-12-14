<img width="1710" height="1107" alt="Screenshot 2568-12-14 at 22 14 24" src="https://github.com/user-attachments/assets/278a5930-1550-403f-8aa8-158e82b6aa33" />
<img width="1710" height="1107" alt="Screenshot 2568-12-14 at 22 14 27" src="https://github.com/user-attachments/assets/83e4d0c6-2425-47ae-a1a8-a7a9e98a0792" />
<img width="1710" height="1107" alt="Screenshot 2568-12-14 at 22 14 30" src="https://github.com/user-attachments/assets/dda6f118-41a1-4832-aa83-d70883a0e2fb" />
<img width="1710" height="1107" alt="Screenshot 2568-12-14 at 22 14 33" src="https://github.com/user-attachments/assets/d748ffbf-81de-4f2c-9d78-0295aed3837b" />
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
