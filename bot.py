import os, time, threading
import yfinance as yf
from flask import Flask
import telebot
from binance.client import Client

TOKEN = os.getenv("TELEGRAM_TOKEN")
BINANCE_API = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_API_SECRET")

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)
client = Client(BINANCE_API, BINANCE_SECRET, testnet=True)
client.API_URL = 'https://testnet.binance.vision/api'

SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"]
CHAT_ID = None
TRADING = True

@app.route('/')
def home():
    return "Shinito AUTO vivo - 20% balance"

def get_best_coin():
    best = None
    best_score = -999
    for sym in SYMBOLS:
        try:
            data = yf.download(sym, period="7d", interval="1h", progress=False)
            if len(data) < 50: continue
            close = data['Close']
            delta = close.diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            rs = gain/loss
            rsi = 100 - (100/(1+rs))
            last_rsi = float(rsi.iloc[-1])
            vol = float(close.pct_change().std())
            if 30 < last_rsi < 50:
                score = (50 - last_rsi) / (vol*100 + 0.01)
                if score > best_score:
                    best_score = score
                    best = (sym, last_rsi, vol)
        except: continue
    return best

def auto_loop():
    global CHAT_ID
    while True:
        try:
            if TRADING and CHAT_ID:
                best = get_best_coin()
                if best:
                    sym, rsi, vol = best
                    bal = client.get_asset_balance(asset='USDT')
                    usdt = float(bal['free'])
                    use = usdt * 0.20
                    if use > 10:
                        bot.send_message(CHAT_ID, f"🤖 Shinito AUTO\n🔍 Mejor: {sym}\nRSI: {rsi:.1f}\nUsando 20%: ${use:.2f}\nCopiando top traders 🟢")
        except Exception as e:
            print(f"Error loop: {e}")
        time.sleep(900)

@bot.message_handler(commands=['start'])
def start(m):
    global CHAT_ID
    CHAT_ID = m.chat.id
    bot.reply_to(m, "🔥 Shinito AUTO 100% ON\nEscaneo cada 15 min\n20% balance\nMejor moneda menor riesgo")

@bot.message_handler(commands=['estado'])
def estado(m):
    bal = client.get_asset_balance(asset='USDT')
    bot.reply_to(m, f"USDT: {float(bal['free']):.2f}")

# Inicia hilos
threading.Thread(target=auto_loop, daemon=True).start()

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
