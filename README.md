<img width="1710" height="1107" alt="Screenshot 2568-12-14 at 22 14 24" src="https://github.com/user-attachments/assets/278a5930-1550-403f-8aa8-158e82b6aa33" />
<img width="1710" height="1107" alt="Screenshot 2568-12-14 at 22 14 27" src="https://github.com/user-attachments/assets/83e4d0c6-2425-47ae-a1a8-a7a9e98a0792" />
<img width="1710" height="1107" alt="Screenshot 2568-12-14 at 22 14 30" src="https://github.com/user-attachments/assets/dda6f118-41a1-4832-aa83-d70883a0e2fb" />
<img width="1710" height="1107" alt="Screenshot 2568-12-14 at 22 14 33" src="https://github.com/user-attachments/assets/d748ffbf-81de-4f2c-9d78-0295aed3837b" />
# Crypto Dashboard

Real-time cryptocurrency trading dashboard built with Python and Tkinter. Shows live market data from Binance with charts, order book, and mock trading features.

## Features

- **Overview**: Market overview with favorite coins, live prices, and quick buy/sell
- **Chart**: Candlestick charts with technical indicators (1h, 4h, 1d intervals)
- **Wallet**: Portfolio management with mock trading (buy/sell cryptocurrencies)
- **Transactions**: View market trades and your transaction history

## Supported Coins

BTC, ETH, SOL, BNB, XRP, ADA, DOGE, MATIC, LTC, AVAX

## Requirements

- Python 3.7+
- Tkinter (usually comes with Python)
- Dependencies: matplotlib, numpy, requests, websocket-client

## Installation

```bash
pip install -r requirements.txt
```

Optional: Install Pillow for better image support
```bash
pip install pillow
```

## Usage

Run the app:
```bash
python -m crypto_dashboard
```

Or:
```bash
python crypto_dashboard/main.py
```

### Navigation

- Click on sidebar items to switch between sections
- Overview: View all coins, add favorites, quick trade
- Chart: Select coin and timeframe to view detailed charts
- Transactions: See market trades and your transaction history
- Wallet: Manage portfolio and execute trades

## Mock Trading

The app includes a mock trading system. You start with 2,500 USDT and some initial holdings. All trades are simulated - no real money involved.

Initial balance and holdings can be changed in `config.py`.

## Configuration

Edit `config.py` to:
- Add/remove cryptocurrencies
- Change theme colors
- Adjust refresh intervals
- Set initial wallet balance and holdings

## Project Structure

```
crypto_dashboard/
├── main.py
├── config.py
├── components/
│   ├── overview.py
│   ├── ticker.py
│   ├── orderbook.py
│   ├── technical.py
│   ├── wallet.py
│   └── transactions.py
└── utils/
    ├── binance_rest.py
    └── indicators.py
```

## Troubleshooting

If you get `ModuleNotFoundError`, make sure you're running from the project root directory and all dependencies are installed.

On Linux, if Tkinter doesn't work, install it:
```bash
sudo apt-get install python3-tk
```

## Notes

- Mock trading only - no real funds
- Requires internet connection for Binance API
- Data updates in real-time via WebSocket
- All prices are in USDT
