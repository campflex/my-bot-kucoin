from datetime import datetime
import argparse
import time
import random
import sys
import signal

from kucoin.client import Trade
from kucoin.client import Market
from kucoin.client import User

# Your Sub account API keys
api_key = '67444c37c35dcd000134bcb0'
api_secret = 'ab3ce0ba-d61b-4ac1-b9d3-b2625bbdd5c1'
passphrase = 'MioSub2024@!'
#Your Master account API Keys
# Your API keys
m_api_key = '6730ff6bf6b7900001147c8e'
m_api_secret = '88faffd6-a817-4e21-8d97-ea5b8fe6ed9c'
m_passphrase = 'Mm@trading!2024'

# Store initial prices and quantities
initial_prices = {}
initial_balances = {}

# Initialize the Kucoin spot hf trading client for HTTP requests
try:
    print("Initializing Kucoin Spot-HF client...")
    spot_client = Trade(api_key, api_secret, passphrase)
    market_client = Market(api_key, api_secret, passphrase)
    user_client = User(m_api_key, m_api_secret, m_passphrase)    
    print("Spot client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize spot client: {e}")
    sys.exit(1)  # Exit if client initialization fails

def get_current_price(trading_pair):
    """
    Retrieves the current market price for the given trading pair.
    """
    try:
        #print(f"Retrieving current price for {trading_pair}...")
        response = market_client.get_ticker(symbol=trading_pair)
        #print(f"Raw response: {response}")  # Log the raw response
        current_price = response['price']  # Adjusted to access 'price' directly
        return current_price
    except Exception as e:
        print(f"Error retrieving current price: {e}")
        return None

active_orders = []

def place_order(trading_pair, side, price, random_quantity):
    """
    Places an order with a random quantity within the specified range and returns the order ID.
    
    Note: This function assumes that 'quantity' and 'price' can be decimal values and converts them to string
    to maintain precision, which might need adjustment based on the API's actual requirements.
    """
    try:
        
        # Convert price to string to maintain precision
        price_str = str(price)
        
        print(f"Placing {side} order for {trading_pair} at price {price_str} with quantity ~{random_quantity}...")
        response = spot_client.create_limit_hf_order(
            symbol=trading_pair,
            side=side,
            size=random_quantity,
            price=price_str,
            # Add additional parameters as needed
        )
        #print (f"Raw response {response}")
        # Assuming the response structure includes an order ID directly or within a nested structure
        order_id = response.get('orderId')  # Adjust based on the actual response structure
        if order_id:
            active_orders.append(order_id)  # Track the active order
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{current_time} - {side} order placed with ID: {order_id}")
        return order_id
    except Exception as e:
        print(f"Error placing {side} order: {e}")
        return None

def cancel_all_active_orders():
    print("Cancelling all active orders...")
    for order_id in list(active_orders):
        try:
            order_status = query_order_status(trading_pair, order_id)
            if order_status == True:
                cancel_order(trading_pair, order_id=order_id)
        except Exception as e:
            print(f"Failed to cancel order {order_id}: {e}")
        finally:
            active_orders.remove(order_id)


def cancel_order(symbol, order_id=None):
    """
    Cancels the specified order.

    :param symbol: The trading pair symbol (e.g., 'BTC_USDT').
    :param order_id: (optional) The exchange's order ID to cancel.
    """
    try:
        print(f"Cancelling order {order_id} for symbol {symbol}...")
        response = spot_client.sync_cancel_hf_order_by_order_id(
            symbol=symbol,
            orderId=order_id
        )
        print(f"Order {order_id} for symbol {symbol} cancelled successfully.")
        return response
    except Exception as e:
        print(f"Error cancelling order {order_id} for symbol {symbol}: {e}")

def query_order_status(symbol, order_id):
    """
    Queries the status of an order and returns its status.
    """
    try:
        response = spot_client.get_single_hf_order(symbol=symbol, orderId=order_id)
        status = response.get('active', None)
        #print(f"Order stauus of {order_id} is: {status}")
        return status
    except Exception as e:
        print(f"Error querying order {order_id} status: {e}")
        return None

def get_order_book(trading_pair, pieces=20):
    """
    Retrieves the order book for the given trading pair.
    :param trading_pair: The trading pair (e.g., 'BTC-USDT').
    :param depth: The number of levels to fetch from the order book.
    :return: A tuple of (bids, asks), where each is a list of [price, size].
    """
    try:
        order_book = market_client.get_part_order(pieces=pieces, symbol=trading_pair)
        bids = order_book.get('bids', [])
        asks = order_book.get('asks', [])
        return bids, asks
    except Exception as e:
        print(f"Error retrieving order book for {trading_pair}: {e}")
        return [], []

def calculate_order_price(trading_pair, current_price, avoid_sell_on_bid_order_match, avoid_buy_on_ask_order_match):
    """
    Determines the price at which to place both buy and sell orders based on the current order book.
    :param trading_pair: The trading pair (e.g., 'BTC-USDT').
    :param current_price: The current market price.
    :param avoid_sell_on_bid_order_match: Skip placing a sell order if chosen price matches the closest bid price.
    :param avoid_buy_on_ask_order_match: Skip placing a buy order if chosen price matches the closest ask price.
    :return: A single price to use for both buy and sell orders, or None if no valid price can be determined.
    """
    bids, asks = get_order_book(trading_pair)

    if not asks or not bids:
        print("Order book is empty or could not be retrieved.")
        return None

    # Closest sell price (ask)
    closest_ask_price = float(asks[0][0])
    # Closest buy price (bid)
    closest_bid_price = float(bids[0][0])

    # Check if there's enough gap to place orders
    if closest_ask_price - closest_bid_price <= 0:
        print("No valid gap between closest bid and ask prices.")
        return None

    # Randomly select a single price within the gap
    chosen_price = round(random.uniform(closest_bid_price, closest_ask_price), 6)
    print(f"\033[93mChosen price is {chosen_price} in between closest bid price {closest_bid_price} and closest ask price {closest_ask_price}\033[0m")

    # Conditions for avoiding matches on closest bid and ask prices
    if avoid_sell_on_bid_order_match and chosen_price == closest_bid_price:
        print("Avoiding sell order as chosen price matches the closest bid price!")
        return None

    if avoid_buy_on_ask_order_match and chosen_price == closest_ask_price:
        print("Avoiding buy order as chosen price matches the closest ask price!")
        return None

    return chosen_price

def get_account_information():
    """
    Retrieves accounts information and prints asset balances (free and locked).
    Tracks initial prices and quantities for PNL calculation.
    """
    try:
        account_info = user_client.get_sub_accounts()  # This returns a list of dictionaries
        print("\033[93mAccount Report:\033[0m")
        print("\033[93mAsset, Free, Locked\033[0m")
        
        for account in account_info:
            # Iterate over tradeAccounts in each sub-account
            trade_accounts = account.get('tradeAccounts', [])
            
            for balance in trade_accounts:
                asset = balance['currency']
                free = float(balance['available'])
                locked = float(balance['holds'])
                
                # Store initial quantities and prices if not already done
                if asset not in initial_balances:
                    initial_balances[asset] = free + locked  # Initial quantity
                    
                    if asset == "USDT":
                        initial_prices[asset] = 1.0  # USDT is a stablecoin, price is always 1
                    else:
                        # Assume the asset is traded against USDT
                        initial_prices[asset] = float(get_current_price(f"{asset}-USDT") or 0)  # Initial price
                
                print(f"\033[93m{asset}, {free}, {locked}\033[0m")
    except Exception as e:
        print(f"Error retrieving account information: {e}")

def trade_loop(trading_pair, quantity_min, quantity_max, interval, num_trades, avoid_sell_on_bid_order_match, avoid_buy_on_ask_order_match):
    """
    Main trading loop. Places sell and buy orders at the same price, checks for their fulfillment, and cancels if not filled.
    """
    previous_chosen_price = None  # Track the price used in the previous trade cycle

    for i in range(num_trades):
        random_quantity = int(random.uniform(quantity_min, quantity_max))
        print("")
        print("--------------------------------------------------------------------")
        print(f"\033[94mTrade cycle {i + 1}/{num_trades}...\033[0m")

        # Fetch the current price
        current_price = get_current_price(trading_pair)
        if current_price is None:
            print("Failed to retrieve current price. Skipping this cycle.")
            continue
        current_price = float(current_price)
        print(f"Current price for {trading_pair} is {current_price}")
        # Calculate a single price for both buy and sell orders
        chosen_price = calculate_order_price(trading_pair, current_price, avoid_sell_on_bid_order_match, avoid_buy_on_ask_order_match)
        if chosen_price is None:
            print("\033[91mSkipping trade cycle due to unmeet price condition.\033[0m")
            continue
 
        # Check if the chosen price is the same as the previous one
        if chosen_price == previous_chosen_price:
            print(f"\033[91mChosen price {chosen_price} is the same as the previous cycle. Skipping this trade cycle.\033[0m")
            continue

        # Update the previous chosen price
        previous_chosen_price = chosen_price
        # Place sell order
        sell_order_id = place_order(trading_pair, 'sell', chosen_price, random_quantity)
        if sell_order_id:
            print(f"Sell order placed at {chosen_price} with quantity {random_quantity}")

        # Place buy order
        buy_order_id = place_order(trading_pair, 'buy', chosen_price, random_quantity)
        if buy_order_id:
            print(f"Buy order placed at {chosen_price} with quantity {random_quantity}")

        # Wait for the specified interval
        print(f"Waiting for {interval} seconds before the next trade cycle...")
        time.sleep(interval)

        # Check and cancel unfilled orders
        if sell_order_id:
            sell_order_status = query_order_status(trading_pair, sell_order_id)
            if sell_order_status:
                cancel_order(trading_pair, sell_order_id)
                print(f"Cancelled sell order {sell_order_id}")
            else:
                print(f"Sell Order {sell_order_id} is FILLED.")
            if sell_order_id in active_orders:
                active_orders.remove(sell_order_id)  # Remove from tracking list after cancellation       

        if buy_order_id:
            buy_order_status = query_order_status(trading_pair, buy_order_id)
            if buy_order_status:
                cancel_order(trading_pair, buy_order_id)
                print(f"Cancelled buy order {buy_order_id}")
            else:
                print(f"Buy Order {buy_order_id} is FILLED.")
            if buy_order_id in active_orders:
                active_orders.remove(buy_order_id)  # Remove from tracking list after cancellation
        active_orders.clear()
        get_account_information()

def graceful_shutdown(signum, frame):
    print("Received SIGINT. Cancelling all active orders and shutting down.")
    cancel_all_active_orders()
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_shutdown)
            
# Trading parameters
# Set up argument parsing
parser = argparse.ArgumentParser(description='Trading script parameters.')
parser.add_argument('--num_trades', type=int, required=True,
                    help='Total number of trades to execute.')
parser.add_argument('--q_min', type=int, required=True,
                    help='Minimum quantity for each trade.')
parser.add_argument('--q_max', type=int, required=True,
                    help='Maximum quantity for each trade.')
parser.add_argument('--interval', type=int, required=True,
                    help='Number of seconds betweeb orders.')
parser.add_argument('--avoid_sell_on_bid_order_match', action='store_true', default=False,
                    help='Avoid placing sell orders if chosen price matches the closest bid price.')
parser.add_argument('--avoid_buy_on_ask_order_match', action='store_true', default=False,
                    help='Avoid placing buy orders if chosen price matches the closest ask price.')

# Parse arguments
args = parser.parse_args()

trading_pair = 'MIND-USDT'
quantity_min = args.q_min  # Set based on the argument
quantity_max = args.q_max  # Set based on the argument
interval = args.interval  # Seconds between orders
num_trades = args.num_trades  # Set based on the argument
avoid_sell_on_bid_order_match = args.avoid_sell_on_bid_order_match  # Set based on the argument
avoid_buy_on_ask_order_match = args.avoid_buy_on_ask_order_match  # Set based on the argument


print("Starting trading script...")
trade_loop(trading_pair, quantity_min, quantity_max, interval, num_trades, avoid_sell_on_bid_order_match, avoid_buy_on_ask_order_match)
