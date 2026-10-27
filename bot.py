import os
from flask import Flask
import threading
import telebot
from binance.spot import Spot as BinanceClient
import yfinance as yf

app = Flask(__name__)

@app.route('/')
def home():
    return "Shinito Testnet FIX is alive! 🔥"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("BINANCE_TESTNET_API_KEY")
API_SECRET = os.environ.get("BINANCE_TESTNET_API_SECRET")

bot = telebot.TeleBot(TOKEN)

# Cliente TESTNET - no toca binance.com
client = BinanceClient(
    api_key=API_KEY,
    api_secret=API_SECRET,
    base_url='https://testnet.binance.vision'
)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 Shinito TESTNET FIX jalando!\n/balance\n/comprar\n/vender")

@bot.message_handler(commands=['balance'])
def balance(message):
    try:
        info = client.account()
        balances = [f"{b['asset']}: {b['free']}" for b in info['balances'] if float(b['free']) > 0]
        bot.reply_to(message, "💰 Balance Testnet:\n" + "\n".join(balances))
    except Exception as e:
        bot.reply_to(message, f"Error balance: {e}")

@bot.message_handler(commands=['comprar'])
def comprar(message):
    try:
        order = client.new_order(symbol='BTCUSDT', side='BUY', type='MARKET', quoteOrderQty=100)
        bot.reply_to(message, f"✅ Compra testnet $100 OK! ID {order['orderId']}")
    except Exception as e:
        bot.reply_to(message, f"Error comprando: {e}")

@bot.message_handler(commands=['vender'])
def vender(message):
    try:
        bal = client.account()
        btc = 0
        for b in bal['balances']:
            if b['asset'] == 'BTC':
                btc = float(b['free'])
        if btc < 0.0001:
            bot.reply_to(message, "No tienes BTC")
            return
        order = client.new_order(symbol='BTCUSDT', side='SELL', type='MARKET', quantity=btc)
        bot.reply_to(message, f"✅ Venta {btc} BTC OK")
    except Exception as e:
        bot.reply_to(message, f"Error vendiendo: {e}")

bot.infinity_polling()
