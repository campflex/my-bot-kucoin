from datetime import datetime
import argparse
import time
import random
import sys
import signal
import threading

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

# Initialize the MEXC spot client for HTTP requests
try:
    print("Initializing Kucoin Spot-HF client...")
    spot_client = Trade(api_key, api_secret, passphrase)
    market_client = Market(api_key, api_secret, passphrase)
    user_client = User(m_api_key, m_api_secret, m_passphrase)
    print("All clients initialized successfully.")
except Exception as e:
    print(f"Failed to initialize spot client: {e}")
    sys.exit(1)  # Exit if client initialization fails

# Console management
console_lock = threading.Lock()  # Lock to synchronize console output

# Spot trading operations
active_orders = []
active_orders_lock = threading.Lock()  # Lock to ensure thread-safe access to active_orders
stop_signal = threading.Event()  # Global stop signal for graceful shutdown

# Store initial prices and quantities
initial_prices = {}
initial_balances = {}

def get_current_price(trading_pair):
    """
    Retrieves the current market price for the given trading pair.
    """
    try:
        response = market_client.get_ticker(symbol=trading_pair)
        current_price = response['price']  # Adjusted to access 'price' directly
        return current_price
    except Exception as e:
        print(f"Error retrieving current price: {e}")
        return None

def place_order(trading_pair, side, price, random_quantity):
    """
    Places an order with a random quantity within the specified range and returns the order ID.
    """
    try:
        price_str = str(price)
        response = spot_client.create_limit_hf_order(
            symbol=trading_pair,
            side=side,
            size=random_quantity,
            price=price_str,
            # Add additional parameters as needed
        )
        order_id = response.get('orderId')
        if order_id:
            with active_orders_lock:
                active_orders.append(order_id)  # Add to active orders list in a thread-safe way
        return order_id
    except Exception as e:
        print(f"Error placing {side} order: {e}")
        return None

def cancel_order(symbol, order_id=None):
    """
    Cancels the specified order.
    """
    try:
        with active_orders_lock:
            response = spot_client.sync_cancel_hf_order_by_order_id(symbol=symbol, orderId=order_id)
            active_orders.remove(order_id)
        return response
    except Exception as e:
        print(f"Error cancelling order {order_id} for symbol {symbol}: {e}")
        return None

def query_order_status(symbol, order_id):
    """
    Queries the status of an order and returns its status.

    :param symbol: The trading pair symbol (e.g., 'BTC-USDT').
    :param order_id: The unique ID of the order.
    :return: Boolean indicating if the order is active, or None if the status cannot be determined.
    """
    try:
        # Query order details using the SDK
        response = spot_client.get_single_hf_order(symbol=symbol, orderId=order_id)
        
        # Extract the 'active' field
        status = response.get('active')
        
        if status is not None:
            return status
        else:
            print(f"Order {order_id} on symbol {symbol} returned an unexpected response: {response}")
            return None
    except Exception as e:
        print(f"Error querying order {order_id} for symbol {symbol}: {e}")
        return None


def calculate_num_book_orders(current_price, price_range_depth, spacing):
    """
    Calculate the number of buy/sell orders based on the price range depth and the spacing.
    """
    price_range_absolute = current_price * (price_range_depth / 100)  # Convert percentage to absolute
    num_orders = int(price_range_absolute / spacing)  # Calculate number of orders
    return num_orders

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

def calculate_pnl():
    """
    Calculates the PNL (Profit and Loss) for the tracked assets, assuming all assets are traded against USDT.
    Special handling for USDT as its price is always 1.
    Takes into account changing total quantity during trading.
    """
    # Ensure account information is updated
    get_account_information()
    
    try:
        # Retrieve account info
        account_info = user_client.get_sub_accounts()
        print("\033[94mPNL Report:\033[0m")
        print("\033[94mAsset, Initial Price, Current Price, Initial Quantity, Current Quantity, Unrealized PNL\033[0m")
        
        for account in account_info:
            # Corrected key for tradeAccounts
            trade_accounts = account.get('tradeAccounts', [])
            for balance in trade_accounts:
                asset = balance['currency']
                free = float(balance['available'])
                locked = float(balance['holds'])
                current_quantity = free + locked  # Current quantity held

                if asset not in initial_prices or asset not in initial_balances:
                    # Skip assets not initialized
                    print(f"\033[93mSkipping {asset} - Missing initial data.\033[0m")
                    continue

                # Handle USDT separately
                if asset == "USDT":
                    initial_price = initial_prices[asset]
                    current_price = 1.0  # USDT is a stablecoin, price is always 1
                else:
                    # Assume the asset is traded against USDT
                    initial_price = initial_prices[asset]
                    current_price = float(get_current_price(f"{asset}-USDT") or 0)

                initial_quantity = initial_balances[asset]
                
                # Unrealized PNL = (current price - initial price) * current quantity
                unrealized_pnl = (current_price - initial_price) * current_quantity
                
                # Print PNL information, showing both initial and current quantities
                print(f"\033[94m{asset}, {initial_price}, {current_price}, {initial_quantity}, {current_quantity}, {unrealized_pnl:.2f}\033[0m")
        print(f"------------------------------------------------------------")
    except Exception as e:
        print(f"Error calculating PNL: {e}")


class TradeThread(threading.Thread):
    """
    Thread class to handle individual buy/sell operations, repeated for num_trades cycles.
    """
    def __init__(self, trading_pair, quantity_min, quantity_max, spacing, interval, n, num_trades):
        threading.Thread.__init__(self)
        self.trading_pair = trading_pair
        self.quantity_min = quantity_min
        self.quantity_max = quantity_max
        self.spacing = spacing
        self.interval = interval
        self.n = n
        self.num_trades = num_trades

    def run(self):

        for i in range(self.num_trades):
            if stop_signal.is_set():
                print(f"Thread {self.n} stopping gracefully.")
                return  # Exit the thread if stop signal is set

            current_price = get_current_price(self.trading_pair)

            if current_price is None:
                print(f"Failed to retrieve current price. Skipping.")
                return

            current_price = float(current_price)
            random_quantity_sell = int(random.uniform(self.quantity_min, self.quantity_max))
            random_quantity_buy = int(random.uniform(self.quantity_min, self.quantity_max))

            # Adjust pricing
            if self.n == 0:
                adjusted_sell_price = round(current_price + (self.spacing / 2), 6)
                adjusted_buy_price = round(current_price - (self.spacing / 2), 6)
            else:
                adjusted_sell_price = round(current_price + (self.n * self.spacing), 6)
                adjusted_buy_price = round(current_price - (self.n * self.spacing), 6)

            # Place buy and sell orders
            sell_order_id = place_order(self.trading_pair, 'sell', adjusted_sell_price, random_quantity_sell)
            buy_order_id = place_order(self.trading_pair, 'buy', adjusted_buy_price, random_quantity_buy)
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with console_lock:
                # Write placed order logs
                print(f"\n------------------------------------------------------------")
                if sell_order_id:
                    print(f"\033[91m{current_time} Thread {self.n} Cycle {i + 1}/{self.num_trades}) - SELL qty. {random_quantity_sell} placed (ID: {sell_order_id}) at {adjusted_sell_price}\033[0m")
                if buy_order_id:
                    print(f"\033[92m{current_time} Thread {self.n} Cycle {i + 1}/{self.num_trades}) - BUY qty. {random_quantity_buy} placed (ID: {buy_order_id}) at {adjusted_buy_price}\033[0m")
                calculate_pnl()

            # Wait for a random interval based on range (interval-interval/2, interval + interval/2) before checking and cancelling orders
            random_interval = int(random.uniform(self.interval - (self.interval)/2, self.interval + (self.interval)/2))

            stop_signal.wait(timeout=random_interval)

            # Check and cancel all orders statuses
            sell_order_status = query_order_status(self.trading_pair, sell_order_id)
            buy_order_status = query_order_status(self.trading_pair, buy_order_id)
            if sell_order_id: 
                if sell_order_status == True:
                    cancel_order(self.trading_pair, order_id=sell_order_id)
                    print(f"\033[90m{current_time} Thread {self.n} Cycle {i + 1}/{self.num_trades}) - SELL order: {sell_order_id} cancelled\033[0m")
                else:
                    print(f"\033[95m{current_time} Thread {self.n} Cycle {i + 1}/{self.num_trades}) - SELL order: {sell_order_id} was FILLED\033[9m")
                

            if buy_order_id:
                if buy_order_status == True:
                    cancel_order(self.trading_pair, order_id=buy_order_id)
                    print(f"\033[90m{current_time} Thread {self.n} Cycle {i + 1}/{self.num_trades}) - BUY order: {buy_order_id} cancelled\033[0m")
                else:
                    print(f"\033[95m{current_time} Thread {self.n} Cycle {i + 1}/{self.num_trades}) - BUY order: {buy_order_id} was FILLED\033[0m")


def trade_loop(trading_pair, quantity_min, quantity_max, interval, num_trades, spacing, price_range_depth):
    """
    Manages multiple threads for buy/sell operations.
    """
    current_price = get_current_price(trading_pair)
    
    if current_price is None:
        print("Failed to retrieve current price. Exiting.")
        return

    current_price = float(current_price)
    # Calculate the number of orders (num_book_orders) dynamically based on price_range_depth and spacing
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"Bot is started at {current_time} - market price for {trading_pair} is {current_price}")
    num_book_orders = calculate_num_book_orders(current_price, price_range_depth, spacing)
    print(f"Number of buy/sell orders to be placed: {num_book_orders}")

    threads = []
    for n in range(num_book_orders):
        trade_thread = TradeThread(trading_pair, quantity_min, quantity_max, spacing, interval, n, num_trades)
        threads.append(trade_thread)
        trade_thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print(f"Process completed...")

def graceful_shutdown(signum, frame):
    print("Received (SIGINT). Stopping all threads and cancelling all active orders.")
    stop_signal.set()  # Set the stop signal to stop all threads

    # Wait for all threads to complete with a timeout to avoid infinite blocking
    for thread in threading.enumerate():
        if thread is not threading.current_thread():
            thread.join()  # Add a timeout to avoid hanging indefinitely

    # Cancel all active orders
    for order_id in active_orders:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        order_status = query_order_status(trading_pair, order_id)
        if order_status == True:
            cancel_order(trading_pair, order_id=order_id)
            print(f"\033[90m{current_time} Order: {order_id} cancelled\033[0m")
        else:
            print(f"\033[95m{current_time} order: {order_id} was {order_status}\033[0m")
    
    print("All active orders cancelled and threads stopped. Exiting.")
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_shutdown)


# Trading parameters
parser = argparse.ArgumentParser(description='Trading script parameters.')
parser.add_argument('--num_trades', type=int, required=True,
                    help='Total number of times each order thread should repeat its buy/sell operation.')
parser.add_argument('--q_min', type=int, required=True,
                    help='Minimum quantity for each trade.')
parser.add_argument('--q_max', type=int, required=True,
                    help='Maximum quantity for each trade.')
parser.add_argument('--interval', type=int, required=True,
                    help='Number of seconds between orders.')
parser.add_argument('--spacing', type=float, default=0.000002,
                    help='Spacing between orders when strategy is multiple.')
parser.add_argument('--price_range_depth', type=float, required=False, default=1.0,
                    help='The price range depth in percentage for placing multiple orders (default: 1%).')

args = parser.parse_args()

trading_pair = 'MIND-USDT'
quantity_min = args.q_min
quantity_max = args.q_max
interval = args.interval
num_trades = args.num_trades
spacing = args.spacing
price_range_depth = args.price_range_depth

print("Starting trading script with multithreading...")
trade_loop(trading_pair, quantity_min, quantity_max, interval, num_trades, spacing, price_range_depth)