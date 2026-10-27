import os
from flask import Flask
import threading, telebot, requests, hmac, hashlib, time, json
from urllib.parse import urlencode

app = Flask(__name__)
@app.route('/')
def home(): return "Shinito Testnet DEBUG alive! 🔥"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("BINANCE_TESTNET_API_KEY", "").strip()
API_SECRET = os.environ.get("BINANCE_TESTNET_API_SECRET", "").strip()

bot = telebot.TeleBot(TOKEN)
BASE_URL = "https://testnet.binance.vision"

def signed_request(method, path, params={}):
    params = {**params, "timestamp": int(time.time() * 1000), "recvWindow": 5000}
    query = urlencode(params)
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    headers = {"X-MBX-APIKEY": API_KEY}
    url = f"{BASE_URL}{path}?{query}&signature={signature}"
    r = requests.request(method, url, headers=headers, timeout=10)
    try:
        return r.json()
    except:
        return {"raw": r.text, "status": r.status_code}

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, f"🔥 Shinito DEBUG\nAPI Key cargada: {API_KEY[:5]}...{API_KEY[-3:]}\nPrueba /balance")

@bot.message_handler(commands=['balance'])
def balance(m):
    try:
        data = signed_request("GET", "/api/v3/account")
        if "balances" not in data:
            bot.reply_to(m, f"❌ Binance dice:\n{json.dumps(data, indent=2)[:1000]}")
            return
        bals = [f"{b['asset']}: {b['free']}" for b in data['balances'] if float(b['free']) > 0]
        bot.reply_to(m, "💰 Balance Testnet:\n" + "\n".join(bals[:15]))
    except Exception as e:
        bot.reply_to(m, f"Error balance: {e}")

@bot.message_handler(commands=['comprar'])
def comprar(m):
    try:
        order = signed_request("POST", "/api/v3/order", {"symbol":"BTCUSDT","side":"BUY","type":"MARKET","quoteOrderQty":100})
        bot.reply_to(m, f"Orden:\n{json.dumps(order, indent=2)[:1000]}")
    except Exception as e:
        bot.reply_to(m, f"Error: {e}")

bot.infinity_polling()
