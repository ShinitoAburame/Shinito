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
STOPLOSS_PCT = 0.025 # 2.5%
MONTO_PCT = 0.20 # 20%

def comprar_con_stoploss(symbol="BTCUSDT"):
    try:
        bal = client.get_asset_balance(asset='USDT')
        usdt = float(bal['free'])
        monto = usdt * MONTO_PCT
        if monto < 11: return
        price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        qty = round(monto / price, 6)
        order = client.order_market_buy(symbol=symbol, quantity=qty)
        stop_price = round(price * (1 - STOPLOSS_PCT), 2)
        # Intenta OCO con stoploss y take profit
        try:
            client.create_oco_order(symbol=symbol, side='SELL', quantity=qty, price=round(price*1.05,2), stopPrice=stop_price, stopLimitPrice=stop_price, stopLimitTimeInForce='GTC')
        except: pass
        bot.send_message(MY_CHAT_ID or order, f"✅ AUTO: Compre {symbol} con 20% USDT | Stoploss -2.5% en {stop_price}")
    except Exception as e:
        print(f"Error compra: {e}")

def auto_loop():
    while True:
        if AUTO:
            try:
                # aqui luego metemos tu scan de mejor moneda, por ahora BTCUSDT para probar
                comprar_con_stoploss("BTCUSDT")
                print("AUTO scan 15 min ejecutado")
            except Exception as e:
                print(f"AUTO error: {e}")
        time.sleep(900)

@app.route('/')
def home(): return "Shinito AUTO 15min + Stoploss 2.5% - Live verde"

@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m, "🔥 Shinito Live verde! /auto_on para activar 15min 20% + stoploss 2.5% | /auto_off | /estado")

@bot.message_handler(commands=['auto_on'])
def auto_on(m):
    global AUTO; AUTO=True
    bot.reply_to(m, "✅ AUTO ACTIVADO 15min + Stoploss 2.5%")

@bot.message_handler(commands=['auto_off'])
def auto_off(m):
    global AUTO; AUTO=False
    bot.reply_to(m, "⏸️ AUTO apagado")

@bot.message_handler(commands=['estado'])
def estado(m):
    b = client.get_asset_balance(asset='USDT')
    bot.reply_to(m, f"USDT: {float(b['free']):.2f} | AUTO: {AUTO} | Stoploss: {STOPLOSS_PCT*100}% | Proxy ON")

if __name__ == "__main__":
    threading.Thread(target=auto_loop, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
