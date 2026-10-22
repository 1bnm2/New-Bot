import asyncio
import os
import threading
import pandas as pd
import ta
import yfinance as yf
from flask import Flask
from telegram import Bot

# ==========================================
# ⚙️ CONFIGURATION (কনফিগারেশন)
# ==========================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN","8974738929:AAHYJHOM5HNAUtl2zQpM0B061bdmdHhbK-U")
CHAT_ID = os.environ.get("CHAT_ID", "8825945512")

# ট্রেডিং সেটিংস (লাইভ ও ওটিসি পেয়ারের জন্য)
SYMBOL = "EURUSD=X"      # কারেন্সি পেয়ার (যেমন: EURUSD=X, GBPUSD=X, NZDCAD=X)
TIMEFRAME = "5m"         # ক্যান্ডেল টাইমফ্রেম (1m, 5m, 15m)
CHECK_INTERVAL = 30      # কত সেকেন্ড পর পর মার্কেট চেক করবে

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# ==========================================
# 🌐 FLASK WEB SERVER (Render 24/7 Keeping)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Active and Running 24/7 on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 📊 MARKET DATA & INDICATORS
# ==========================================
def get_market_data(symbol, timeframe="5m"):
    """মার্কেট ডাটা ফেচ করা এবং ইন্ডিকেটর প্রসেস করা"""
    try:
        df = yf.download(tickers=symbol, period="1d", interval=timeframe, progress=False)
        if df.empty:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # ১. RSI (Relative Strength Index - 14)
        df['RSI'] = ta.momentum.rsi(close=df['Close'], window=14)
        
        # ২. EMA (Exponential Moving Average - 9 & 21)
        df['EMA_9'] = ta.trend.ema_indicator(close=df['Close'], window=9)
        df['EMA_21'] = ta.trend.ema_indicator(close=df['Close'], window=21)
        
        # ৩. MACD (Moving Average Convergence Divergence)
        df['MACD'] = ta.trend.macd(close=df['Close'])
        df['MACD_Signal'] = ta.trend.macd_signal(close=df['Close'])

        return df
    except Exception as e:
        print(f"Data Fetching Error: {e}")
        return None

# ==========================================
# 🎯 STRATEGY ANALYSIS (কৌশল ও ফিল্টার)
# ==========================================
def analyze_strategy(df):
    latest = df.iloc[-1]
    previous = df.iloc[-2]

    close_price = round(float(latest['Close']), 5)
    rsi_val = round(float(latest['RSI']), 2)
    signal = None

    # --- CALL (BUY) SIGNAL CONDITION ---
    is_ema_bullish = (previous['EMA_9'] < previous['EMA_21']) and (latest['EMA_9'] > latest['EMA_21'])
    is_macd_bullish = latest['MACD'] > latest['MACD_Signal']

    if is_ema_bullish and (rsi_val > 50) and is_macd_bullish:
        signal = "CALL 🟢 (BUY)"

    # --- PUT (SELL) SIGNAL CONDITION ---
    is_ema_bearish = (previous['EMA_9'] > previous['EMA_21']) and (latest['EMA_9'] < latest['EMA_21'])
    is_macd_bearish = latest['MACD'] < latest['MACD_Signal']

    if is_ema_bearish and (rsi_val < 50) and is_macd_bearish:
        signal = "PUT 🔴 (SELL)"

    return signal, close_price, rsi_val

# ==========================================
# 🚀 MAIN LOOP (বট এক্সিকিউশন)
# ==========================================
async def bot_loop():
    print("Signal Engine Started...")
    last_signal = None

    while True:
        df = get_market_data(SYMBOL, TIMEFRAME)
        if df is not None and len(df) >= 26:
            signal, price, rsi = analyze_strategy(df)

            if signal and signal != last_signal:
                message = (
                    f"🚨 **HIGH ACCURACY SIGNAL** 🚨\n\n"
                    f"📊 **Asset:** `{SYMBOL}`\n"
                    f"⏱️ **Timeframe:** `{TIMEFRAME}`\n"
                    f"📈 **Direction:** {signal}\n"
                    f"💰 **Entry Price:** `{price}`\n"
                    f"📉 **RSI Filter:** `{rsi}`\n\n"
                    f"💡 *Tip: মানি ম্যানেজমেন্ট মেনে ট্রেড করুন।*"
                )
                try:
                    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
                    print(f"Sent Signal: {signal} at {price}")
                    last_signal = signal
                except Exception as e:
                    print(f"Telegram Delivery Error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(bot_loop())
  
