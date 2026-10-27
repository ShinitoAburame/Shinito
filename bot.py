import os
from flask import Flask
import threading
import telebot
import requests
import hmac, hashlib, time
from urllib.parse import urlencode

app = Flask(__name__)
@app.route('/')
def home():
    return "Shinito Testnet Direct FIX alive! 🔥"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("BINANCE_TESTNET_API_KEY")
API_SECRET = os.environ.get("BINANCE_TESTNET_API_SECRET")

bot = telebot.TeleBot(TOKEN)
BASE_URL = "https://testnet.binance.vision"

def signed_request(method, path, params={}):
    params['timestamp'] = int(time.time() * 1000)
    query = urlencode(params)
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    headers = {"X-MBX-APIKEY": API_KEY}
    url = f"{BASE_URL}{path}?{query}&signature={signature}"
    if method == "GET":
        return requests.get(url, headers=headers).json()
    else:
        return requests.post(url, headers=headers).json()

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "🔥 Shinito TESTNET DIRECT jalando!\n\n/balance - ver $10k falsos\n/comprar - compra $100 BTC prueba\n/vender - vende todo")

@bot.message_handler(commands=['balance'])
def balance(m):
    try:
        data = signed_request("GET", "/api/v3/account")
        bals = [f"{b['asset']}: {b['free']}" for b in data['balances'] if float(b['free']) > 0]
        bot.reply_to(m, "💰 Balance Testnet:\n" + "\n".join(bals[:15]))
    except Exception as e:
        bot.reply_to(m, f"Error balance: {e}")

@bot.message_handler(commands=['comprar'])
def comprar(m):
    try:
        order = signed_request("POST", "/api/v3/order", {"symbol":"BTCUSDT","side":"BUY","type":"MARKET","quoteOrderQty":100})
        bot.reply_to(m, f"✅ Compra testnet OK: {order}")
    except Exception as e:
        bot.reply_to(m, f"Error comprando: {e}")

@bot.message_handler(commands=['vender'])
def vender(m):
    try:
        acc = signed_request("GET", "/api/v3/account")
        btc = 0
        for b in acc['balances']:
            if b['asset'] == 'BTC': btc = float(b['free'])
        if btc < 0.0001:
            bot.reply_to(m, "No tienes BTC"); return
        order = signed_request("POST", "/api/v3/order", {"symbol":"BTCUSDT","side":"SELL","type":"MARKET","quantity":round(btc,6)})
        bot.reply_to(m, f"✅ Venta OK: {order}")
    except Exception as e:
        bot.reply_to(m, f"Error vendiendo: {e}")

bot.infinity_polling()
