#!/bin/bash

python3 kucoin-bot.py --ask_spread_percent $3  --bid_spread_percent $3 --buy_above_market_price --num_trades 1 --q_min $1 --q_max $2 --interval 6