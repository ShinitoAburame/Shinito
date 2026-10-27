import telebot
import yfinance as yf

import os
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home():
    return "Shinto Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🦈 ¡Shinito Trader en tu lap jalando!\n\nUsa /senales para ver el BTC")

@bot.message_handler(commands=['senales'])
def senales(message):
    try:
        btc = yf.download("BTC-USD", period="1d", interval="15m", progress=False)
        precio = float(btc['Close'].iloc[-1])
        bot.reply_to(message, f"📈 BTC: ${precio:.2f} USD")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

print("BOT INICIADO - Déjame abierto")
bot.infinity_polling()
