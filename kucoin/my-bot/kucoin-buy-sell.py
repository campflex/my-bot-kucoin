from kucoin.client import Trade, Market, User
from datetime import datetime
import argparse
import sys

# KuCoin API credentials
api_key = '682309c7c1dfd90001056247'
api_secret = '68748ee9-ad00-4f9e-bd5e-5fd7f8316b3c'
passphrase = '13May2025'

# Initialize clients
try:
    print("Initializing KuCoin clients...")
    spot_client = Trade(api_key, api_secret, passphrase)
    market_client = Market(api_key, api_secret, passphrase)
    user_client = User(api_key, api_secret, passphrase)
    print("Initialization successful.")
except Exception as e:
    print(f"Failed to initialize KuCoin client: {e}")
    sys.exit(1)

def place_order(trading_pair, side, price, amount):
    """
    Place a LIMIT buy or sell order.
    """
    try:
        response = spot_client.create_limit_hf_order(
            symbol=trading_pair,
            side=side,
            size=amount,
            price=str(price)
        )
        order_id = response.get('orderId')
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{current_time} - {side.upper()} order placed at {price} for amount {amount} (Order ID: {order_id})")
    except Exception as e:
        print(f"Error placing {side} order: {e}")

def get_main_account_info():
    """
    Show 'trade' balances for the main account.
    """
    try:
        balances = user_client.get_account_list(account_type='trade')
        print("\n\033[93mMain Account (Trade) Balances:\033[0m")
        print("Asset\tAvailable\tHolds")
        for b in balances:
            print(f"{b['currency']}\t{b['available']}\t{b['holds']}")
    except Exception as e:
        print(f"Error retrieving main account info: {e}")

def get_sub_account_info():
    """
    Show balances for the subaccount.
    """
    try:
        subaccounts = user_client.get_sub_accounts()
        print("\n\033[93mSub Account Balances:\033[0m")
        print("Asset\tAvailable\tHolds")
        for account in subaccounts:
            for bal in account.get('tradeAccounts', []):
                print(f"{bal['currency']}\t{bal['available']}\t{bal['holds']}")
    except Exception as e:
        print(f"Error retrieving subaccount info: {e}")

# ---- Argument Parsing ----
parser = argparse.ArgumentParser(description="Place a KuCoin spot limit order.")

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--buy', action='store_true', help='Execute a BUY order')
group.add_argument('--sell', action='store_true', help='Execute a SELL order')

parser.add_argument('--amount', type=float, required=True, help='Amount to trade')
parser.add_argument('--price', type=float, required=True, help='Limit price to place the order at')
parser.add_argument('--symbol', type=str, required=True, help='Trading pair symbol (e.g., MIND-USDT)')
parser.add_argument('--use_subaccount', action='store_true', default=False, help='Use subaccount instead of main')

args = parser.parse_args()

# ---- Execute Trade ----
side = 'buy' if args.buy else 'sell'
place_order(args.symbol, side, args.price, args.amount)

# ---- Display Balances ----
if args.use_subaccount:
    get_sub_account_info()
else:
    get_main_account_info()
