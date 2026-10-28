import os, threading
from flask import Flask
import telebot
from binance.client import Client

TOKEN = os.getenv("BOT_TOKEN")
API = os.getenv("BINANCE_TESTNET_API_KEY")
SECRET = os.getenv("BINANCE_TESTNET_API_SECRET")

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)
client = Client(API, SECRET, testnet=True)
client.API_URL = 'https://testnet.binance.vision/api'

CHAT_ID = None

@app.route('/')
def home():
    return "Shinito AUTO vivo - esperando"

@bot.message_handler(commands=['start'])
def start(m):
    global CHAT_ID
    CHAT_ID = m.chat.id
    bot.reply_to(m, "🔥 Shinito AUTO 100% ON - Ya estoy vivo en Render. En 15 min escaneo mejor moneda.")

@bot.message_handler(commands=['estado'])
def estado(m):
    try:
        b = client.get_asset_balance(asset='USDT')
        bot.reply_to(m, f"USDT: {float(b['free']):.2f}")
    except Exception as e:
        bot.reply_to(m, f"Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
