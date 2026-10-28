import os, threading
from flask import Flask
import telebot
# PARCHE para que no falle por IP de USA
import binance.client
binance.client.Client.ping = lambda self: {}
from binance.client import Client

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("BINANCE_TESTNET_API_KEY")
API_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET")
PROXY = os.getenv("PROXY_URL") or "http://uoguvsaz:on13dk1xsk1q@45.38.107.97:6014"

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

proxies = {"http": PROXY, "https": PROXY}
client = None
try:
    client = Client(API_KEY, API_SECRET, testnet=True, requests_params={"proxies": proxies, "timeout": 30})
    client.API_URL = 'https://testnet.binance.vision/api'
    print(f"Binance con proxy OK: {PROXY}")
except Exception as e:
    print(f"Error con proxy: {e}")

@app.route('/')
def home():
    return "Shinito vivo con proxy - Live"

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "🔥 Shinito vivo! Con proxy ya estoy en Live verde otra vez. Listo para el AUTO 15 min del 20%")

@bot.message_handler(commands=['estado'])
def estado(m):
    try:
        b = client.get_asset_balance(asset='USDT')
        bot.reply_to(m, f"💰 USDT Testnet: {float(b['free']):.2f} con proxy")
    except Exception as e:
        bot.reply_to(m, f"Error binance: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
