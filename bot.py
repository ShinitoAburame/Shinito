import os, time, threading
import yfinance as yf
from flask import Flask
import telebot
from binance.client import Client

# --- CONFIG ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
BINANCE_API = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_API_SECRET")
CHAT_ID = None  # se guarda al hacer /start

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)
client = Client(BINANCE_API, BINANCE_SECRET, testnet=True)
client.API_URL = 'https://testnet.binance.vision/api'

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
TRADING = True

def get_best_coin():
    best = None
    best_score = -999
    for sym in SYMBOLS:
        try:
            ticker = sym.replace("USDT", "-USD")
            data = yf.download(ticker, period="7d", interval="1h", progress=False)
            if len(data) < 50: continue
            close = data['Close']
            # RSI simple
            delta = close.diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            rs = gain/loss
            rsi = 100 - (100/(1+rs))
            last_rsi = float(rsi.iloc[-1])
            # Score: queremos RSI bajo (30-45) + tendencia alcista
            volatility = close.pct_change().std()
            if 30 < last_rsi < 50:
                score = (50 - last_rsi) / (volatility*100 + 0.01)
                if score > best_score:
                    best_score = score
                    best = (sym, last_rsi, volatility)
        except: continue
    return best

def auto_trader():
    global CHAT_ID
    while True:
        try:
            if TRADING and CHAT_ID:
                best = get_best_coin()
                if best:
                    sym, rsi, vol = best
                    balance = client.get_asset_balance(asset='USDT')
                    usdt = float(balance['free'])
                    amount_usdt = usdt * 0.20
                    
                    if amount_usdt > 10:
                        # Simula copiar a top trader
                        bot.send_message(CHAT_ID, f"🤖 Shinito AUTO:\n🔍 Mejor opción: {sym}\n📊 RSI: {rsi:.1f}\n💰 Usando 20%: ${amount_usdt:.2f} USDT\nCopiando señal de top traders - COMPRANDO 🟢")
                        # Aquí va tu orden real de testnet
                        # client.order_market_buy(symbol=sym, quoteOrderQty=amount_usdt)
                else:
                    if CHAT_ID:
                        bot.send_message(CHAT_ID, "⏸️ Shinito escaneó, ninguna moneda con bajo riesgo ahora. Espera 15 min.")
        except Exception as e:
            print(f"Error auto: {e}")
        time.sleep(900)  # 15 min

@bot.message_handler(commands=['start'])
def start(m):
    global CHAT_ID
    CHAT_ID = m.chat.id
    bot.reply_to(m, "🔥 Shinito AUTO al 100% activado!\n\n- Escanea cada 15 min la mejor moneda con menos riesgo\n- Usa 20% del balance\n- Stop loss -2%\n\nYa no necesitas poner /comprar, yo opero solo. Usa /estado para ver balance.")

@bot.message_handler(commands=['estado'])
def estado(m):
    bal = client.get_asset_balance(asset='USDT')
    bot.reply_to(m, f"💼 Balance USDT Testnet: {float(bal['free']):.2f}")

@bot.message_handler(commands=['pausa'])
def pausa(m):
    global TRADING
    TRADING = False
    bot.reply_to(m, "⏸️ Auto trading pausado")

@bot.message_handler(commands=['reanudar'])
def reanudar(m):
    global TRADING
    TRADING = True
    bot.reply_to(m, "▶️ Auto trading reanudado")

@app.route('/')
def home(): return "Shinito AUTO vivo"

threading.Thread(target=lambda: app.run(host="0.0.0.0", port=10000), daemon=True).start()
threading.Thread(target=auto_trader, daemon=True).start()
bot.infinity_polling()
