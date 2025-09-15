#!/usr/bin/env bash
python3 kucoin-bot.py --ask_spread_percent 0  --bid_spread_percent 0 --block_order_price --buy_above_market_price --num_trades 100000000 --q_min 2100 --q_max 2110 --interval 6

