from kucoin.client import Trade, User
from datetime import datetime
import argparse
import sys

# KuCoin API credentials (replace with your actual keys)
api_key = '682309c7c1dfd90001056247'
api_secret = '68748ee9-ad00-4f9e-bd5e-5fd7f8316b3c'
passphrase = '13May2025'

# Initialize clients
try:
    print("Initializing KuCoin client...")
    trade_client = Trade(key=api_key, secret=api_secret, passphrase=passphrase)
    user_client = User(key=api_key, secret=api_secret, passphrase=passphrase)
    print("Client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize KuCoin client: {e}")
    sys.exit(1)

def cancel_all_open_orders(symbol):
    try:
        print(f"Cancelling all HF orders for {symbol}...")
        result = trade_client._request('DELETE', '/api/v1/hf/orders', params={'symbol': symbol})
        print(f"Cancel result: {result}")
    except Exception as e:
        print(f"Error cancelling HF orders: {e}")

def display_account_balances():
    try:
        print("\n\033[92mMain Account Balances:\033[0m")
        print(f"{'Asset':<10}{'Free':<15}{'Holds':<15}")
        accounts = user_client.get_account_list(account_type='trade')
        for acc in accounts:
            currency = acc['currency']
            available = float(acc['available'])
            holds = float(acc['holds'])
            if available > 0 or holds > 0:
                print(f"{currency:<10}{available:<15}{holds:<15}")
    except Exception as e:
        print(f"Error fetching account balances: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Cancel all open orders for a given symbol on KuCoin.')
    parser.add_argument('--symbol', type=str, required=True, help='Trading pair symbol (e.g., MIND-USDT)')

    args = parser.parse_args()
    symbol = args.symbol.upper()

    cancel_all_open_orders(symbol)
    display_account_balances()