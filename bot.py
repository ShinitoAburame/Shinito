import os, threading
from flask import Flask
import telebot
from binance.client import Client

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("BINANCE_TESTNET_API_KEY")
API_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET")

print("Iniciando Shinito...")

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
client = Client(API_KEY, API_SECRET, testnet=True)
client.API_URL = 'https://testnet.binance.vision/api'

@app.route('/')
def home():
    return "Shinito AUTO vivo - Live"

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "🔥 Shinito vivo! Ya estoy en Live de nuevo como antes. Listo para el AUTO 15 min")

@bot.message_handler(commands=['estado'])
def estado(m):
    try:
        b = client.get_asset_balance(asset='USDT')
        bot.reply_to(m, f"USDT Testnet: {float(b['free']):.2f}")
    except Exception as e:
        bot.reply_to(m, f"Error balance: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
