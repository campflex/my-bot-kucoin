from datetime import datetime
import argparse
import time
import random
import sys
import signal

from kucoin.client import Trade
from kucoin.client import Market
# Your Sub account API keys
api_key = '67444c37c35dcd000134bcb0'
api_secret = 'ab3ce0ba-d61b-4ac1-b9d3-b2625bbdd5c1'
passphrase = 'MioSub2024@!'

# Initialize the Kucoin spot hf trading client for HTTP requests
try:
    print("Initializing Kucoin Spot-HF client...")
    spot_client = Trade(api_key, api_secret, passphrase)
    market_client = Market(api_key, api_secret, passphrase)
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
        print(f"Current price for {trading_pair} is {current_price}")
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


def trade_loop(trading_pair, quantity_min, quantity_max, interval, num_trades):
    """
    Main trading loop. Places sell and buy orders, checks for their fulfillment, and cancels if not filled.
    """
    
    # Check if need to take the current market price and block it for the orders
    if block_order_price == True:
        blocked_price = get_current_price(trading_pair)
    # Generate a random quantity within the specified range and format it as a string
    #random_quantity = str(round(random.uniform(quantity_min, quantity_max), 8))

    for i in range(num_trades):
        random_quantity = int(random.uniform(quantity_min, quantity_max))
        print(f"Trade cycle {i+1}/{num_trades}...")
        if block_order_price != True:
            current_price = get_current_price(trading_pair)
        else:
            current_price = blocked_price

        if current_price is None:
            print("Failed to retrieve current price. Skipping this cycle.")
            continue

        # Convert current_price to float for calculation
        current_price = float(current_price)
        # Calculate the price spread for sell
        sell_price_spread = current_price * (SELL_PRICE_SPREAD_PERCENT / 100)
        sell_price = current_price + sell_price_spread
        # Format sell_price to match the required precision
        sell_price = round(sell_price, 6)
        
        #Execute the sell order
        sell_order_id = place_order(trading_pair, 'sell', sell_price, random_quantity)
        
        # Re-fetch the current price to verify before placing a buy order
        if block_order_price != True:
            new_current_price_str = get_current_price(trading_pair)
        else:
            new_current_price_str = blocked_price
        if new_current_price_str is None:
            print("Failed to retrieve current price again. Skipping buy order for this cycle.")
            continue
        
        new_current_price = float(new_current_price_str)
        # Calculate the price spread for buy
        buy_price_spread = new_current_price * (BUY_PRICE_SPREAD_PERCENT / 100)
        if buy_above_market_price == False:
            random_quantity = int(random.uniform(quantity_min, quantity_max))
            buy_price = new_current_price - buy_price_spread
            # Format buy_price to match the required precision
            buy_price = round(buy_price,6)
            buy_order_id = place_order(trading_pair, 'buy', buy_price, random_quantity)
        else:
            buy_price = new_current_price + buy_price_spread
            # Format buy_price to match the required precision
            buy_price = round(buy_price,6)      
            # Verify if the new current price conditions
            if buy_price == sell_price:
                buy_order_id = place_order(trading_pair, 'buy', buy_price, random_quantity)
            else:
                print("Current price has changed from sell price. Skipping buy order for this cycle.")
                # If needed, handle any additional logic here for the situation where the buy order is skipped
                # Check and log the status of the sell order and cancell it
                sell_order_status = query_order_status(trading_pair, sell_order_id)
                if sell_order_status == False:
                    print(f"Sell Order {sell_order_id} is FILLED.")
                    if sell_order_id in active_orders:
                        active_orders.remove(sell_order_id)  # Remove from tracking list after cancellation
                elif sell_order_status == True:
                    cancel_order(trading_pair, order_id=sell_order_id)
                    if sell_order_id in active_orders:
                        active_orders.remove(sell_order_id)  # Remove from tracking list after cancellation
                else:
                    print(f"Sell Order {sell_order_id} is FILLED.")
                    if sell_order_id in active_orders:
                        active_orders.remove(sell_order_id)  # Remove from tracking list after cancellation
                continue

        # Sleep for the interval minus a small buffer to check order statuses just before the interval ends
        print(f"Waiting for {interval - 5} seconds before checking order statuses...")
        time.sleep(interval - 5)  # Adjust buffer time as necessary

        # Check and log the status of the sell order
        sell_order_status = query_order_status(trading_pair, sell_order_id)
        if sell_order_status == False:
            print(f"Sell Order {sell_order_id} is FILLED.")
            if sell_order_id in active_orders:
                active_orders.remove(sell_order_id)  # Remove from tracking list after cancellation
        elif sell_order_status == True:
            cancel_order(trading_pair, order_id=sell_order_id)
            if sell_order_id in active_orders:
                active_orders.remove(sell_order_id)  # Remove from tracking list after cancellation
        else:
            print(f"Sell Order {sell_order_id} is FILLED.")
            if sell_order_id in active_orders:
                active_orders.remove(sell_order_id)  # Remove from tracking list after cancellation

        # Check and log the status of the buy ordercle
        buy_order_status = query_order_status(trading_pair, buy_order_id)
        if buy_order_status == False:
            print(f"Buy Order {buy_order_id} is FILLED.")
            if buy_order_id in active_orders:
                active_orders.remove(buy_order_id)  # Remove from tracking list after cancellation
        elif buy_order_status == True:
            cancel_order(trading_pair, order_id=buy_order_id)
            if buy_order_id in active_orders:
                active_orders.remove(buy_order_id)  # Remove from tracking list after cancellation
        else:
            print(f"Buy Order {buy_order_id} is FILLED.")
            if buy_order_id in active_orders:
                active_orders.remove(buy_order_id)  # Remove from tracking list after cancellation
        active_orders.clear()

def graceful_shutdown(signum, frame):
    print("Received SIGINT. Cancelling all active orders and shutting down.")
    cancel_all_active_orders()
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_shutdown)
            
# Trading parameters
# Set up argument parsing
parser = argparse.ArgumentParser(description='Trading script parameters.')
parser.add_argument('--ask_spread_percent', type=float, required=True,
                    help='Price spread percentage, e.g., 0.07 for 0.07%')
parser.add_argument('--bid_spread_percent', type=float, required=True,
                    help='Price spread percentage, e.g., 0.07 for 0.07%')
parser.add_argument('--buy_above_market_price', action='store_true',
                    help='Flag to indicate if buy orders should be placed above market price. Default is False.')
parser.add_argument('--num_trades', type=int, required=True,
                    help='Total number of trades to execute.')
parser.add_argument('--q_min', type=int, required=True,
                    help='Minimum quantity for each trade.')
parser.add_argument('--q_max', type=int, required=True,
                    help='Maximum quantity for each trade.')
parser.add_argument('--interval', type=int, required=True,
                    help='Number of seconds betweeb orders.')
parser.add_argument('--block_order_price', action='store_true',
                    help='Flag to indicate if to block the price for the orders. Default is False.')

# Parse arguments
args = parser.parse_args()
# Validate ask_spread_percent and bid_spread_percent if buy_above_market_price is True
if args.buy_above_market_price and args.ask_spread_percent != args.bid_spread_percent:
    print("Error: When buy_above_market_price is True, ask_spread_percent and bid_spread_percent must be equal.")
    sys.exit(1)  # Terminate the script to prevent execution under these settings

trading_pair = 'MIND-USDT'
quantity_min = args.q_min  # Set based on the argument
quantity_max = args.q_max  # Set based on the argument
interval = args.interval  # Seconds between orders
num_trades = args.num_trades  # Set based on the argument
buy_above_market_price = args.buy_above_market_price  # Set based on the argument; defaults to False if not provided
block_order_price = args.block_order_price  # Set based on the argument; defaults to False if not provided
SELL_PRICE_SPREAD_PERCENT = args.ask_spread_percent  # Use the argument value
BUY_PRICE_SPREAD_PERCENT = args.bid_spread_percent  # Use the argument value


print("Starting trading script...")
trade_loop(trading_pair, quantity_min, quantity_max, interval, num_trades)
