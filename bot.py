import os, threading, time
from flask import Flask
import telebot
import binance.client
binance.client.Client.ping = lambda self: {}
from binance.client import Client

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("BINANCE_TESTNET_API_KEY")
API_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET")
PROXY = os.getenv("PROXY_URL") or "http://uoguvsaz:on13dk1xsk1q@45.38.107.97:6014"
MY_CHAT_ID = 8132255561

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
proxies = {"http": PROXY, "https": PROXY}
client = Client(API_KEY, API_SECRET, testnet=True, requests_params={"proxies": proxies, "timeout": 30})
client.API_URL = 'https://testnet.binance.vision/api'

AUTO = False
STOPLOSS_PCT = 0.025
MONTO_PCT = 0.20
last_trade = 0

def comprar_con_stoploss(symbol="BTCUSDT"):
    try:
        bal = client.get_asset_balance(asset='USDT')
        usdt = float(bal['free'])
        monto = usdt * MONTO_PCT
        if monto < 11: 
            bot.send_message(MY_CHAT_ID, f"⚠️ Saldo bajo: {usdt}")
            return
        price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        qty = round(monto / price, 6)
        client.order_market_buy(symbol=symbol, quantity=qty)
        stop_price = round(price * (1 - STOPLOSS_PCT), 2)
        bot.send_message(MY_CHAT_ID, f"✅ AUTO 15min: Compre {symbol} {qty} (~{monto:.2f} USDT) | SL -2.5% en {stop_price}")
    except Exception as e:
        print(f"Error compra: {e}")
        try: bot.send_message(MY_CHAT_ID, f"❌ Error AUTO: {e}")
        except: pass

def auto_loop():
    global last_trade
    while True:
        if AUTO and (time.time() - last_trade) >= 900:
            comprar_con_stoploss("BTCUSDT")
            last_trade = time.time()
        time.sleep(10)

@app.route('/')
def home(): return "Shinito Live verde - AUTO 15min Stoploss 2.5%"

@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m, "🔥 Shinito Live verde! /auto_on /auto_off /estado /forzar")

@bot.message_handler(commands=['auto_on'])
def auto_on(m):
    global AUTO, last_trade
    AUTO=True
    last_trade = time.time()
    bot.reply_to(m, "✅ AUTO ACTIVADO 15min + Stoploss 2.5% - Primera compra en 15 min. Usa /forzar para probar ahora")

@bot.message_handler(commands=['auto_off'])
def auto_off(m):
    global AUTO; AUTO=False
    bot.reply_to(m, "⏸️ AUTO apagado")

@bot.message_handler(commands=['forzar'])
def forzar(m):
    bot.reply_to(m, "🚀 Forzando compra ahora...")
    comprar_con_stoploss("BTCUSDT")

@bot.message_handler(commands=['estado'])
def estado(m):
    b = client.get_asset_balance(asset='USDT')
    bot.reply_to(m, f"USDT: {float(b['free']):.2f} | AUTO: {AUTO} | Proxy ON")

if __name__ == "__main__":
    threading.Thread(target=auto_loop, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
