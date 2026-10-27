import os
from flask import Flask
import threading
import yfinance as yf
import telebot
from binance.client import Client

app = Flask(__name__)

@app.route('/')
def home():
    return "Shinito Bot Testnet is alive! 🔥"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# Tokens
TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("BINANCE_TESTNET_API_KEY")
API_SECRET = os.environ.get("BINANCE_TESTNET_API_SECRET")

bot = telebot.TeleBot(TOKEN)
client = Client(API_KEY, API_SECRET, testnet=True)
client.API_URL = 'https://testnet.binance.vision/api'

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 Shinito en TESTNET jalando!\n\nComandos:\n/balance - ver saldo falso\n/senales - analizar BTC\n/comprar - compra $100 de BTC de prueba\n/vender - vende todo")

@bot.message_handler(commands=['balance'])
def balance(message):
    try:
        info = client.get_account()
        balances = [f"{b['asset']}: {b['free']}" for b in info['balances'] if float(b['free']) > 0]
        texto = "\n".join(balances)
        bot.reply_to(message, f"💰 Balance Testnet:\n{texto}")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=['senales'])
def senales(message):
    try:
        btc = yf.download("BTC-USD", period="1d", interval="15m", progress=False)
        precio = float(btc["Close"].iloc[-1])
        bot.reply_to(message, f"₿ BTC real: ${precio:.2f}\nIA dice: Si baja, compramos en testnet. Usa /comprar")
    except Exception as e:
        bot.reply_to(message, f"Error senales: {e}")

@bot.message_handler(commands=['comprar'])
def comprar(message):
    try:
        order = client.order_market_buy(symbol='BTCUSDT', quoteOrderQty=100)
        bot.reply_to(message, f"✅ Compra de $100 en testnet ejecutada!\nID: {order['orderId']}")
    except Exception as e:
        bot.reply_to(message, f"Error comprando: {e}")

@bot.message_handler(commands=['vender'])
def vender(message):
    try:
        btc_balance = float(client.get_asset_balance(asset='BTC')['free'])
        if btc_balance < 0.0001:
            bot.reply_to(message, "No tienes BTC para vender")
            return
        order = client.order_market_sell(symbol='BTCUSDT', quantity=btc_balance)
        bot.reply_to(message, f"✅ Venta ejecutada: {btc_balance} BTC")
    except Exception as e:
        bot.reply_to(message, f"Error vendiendo: {e}")

bot.infinity_polling()
