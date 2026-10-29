import math
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
MONTO_PCT = 0.20
STOPLOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.05
last_trade = 0
positions = {}

def buscar_mejor_moneda():
    try:
        tickers = client.get_ticker()
        blacklist = ['USDCUSDT','BUSDUSDT','DAIUSDT','TUSDUSDT','FDUSDUSDT']
        candidatos = []
        for t in tickers:
            sym = t['symbol']
            if not sym.endswith('USDT'): continue
            if sym in blacklist: continue
            if sym in positions: continue  # <-- FIX 1: No comprar repetidas
            try:
                vol = float(t['quoteVolume'])
                change = float(t['priceChangePercent'])
                if vol > 5000000 and change > 0 and change < 15:
                    candidatos.append(t)
            except: continue
        candidatos = sorted(candidatos, key=lambda x: float(x['priceChangePercent']), reverse=True)
        if candidatos:
            return candidatos[0]['symbol'], float(candidatos[0]['priceChangePercent'])
        return None, 0
    except Exception as e:
        print(f"Error buscando moneda: {e}")
        return None, 0

def ejecutar_compra_autonoma(symbol):
    try:
        balance = client.get_account()
        usdt_balance = float([b for b in balance['balances'] if b['asset']=='USDT'][0]['free'])
        monto_usdt = usdt_balance * MONTO_PCT
        if monto_usdt < 12: 
            bot.send_message(MY_CHAT_ID, f"⚠️ Saldo muy bajo: {usdt_balance:.2f} USDT")
            return False

        info = client.get_symbol_info(symbol)
        lot_filter = [f for f in info['filters'] if f['filterType']=='LOT_SIZE'][0]
        step_size = float(lot_filter['stepSize'])
        
        ticker = client.get_symbol_ticker(symbol=symbol)
        precio = float(ticker['price'])
        cantidad_bruta = monto_usdt / precio
        
        precision = int(round(-math.log(step_size, 10), 0)) if step_size < 1 else 0
        if precision < 0: precision = 0
        cantidad = math.floor(cantidad_bruta * (10**precision)) / (10**precision)
        if cantidad == 0:
            cantidad = step_size
        
        client.order_market_buy(symbol=symbol, quantity=cantidad)

        # FIX 2: Acumular en lugar de sobreescribir
        if symbol in positions:
            old = positions[symbol]
            total_qty = old['qty'] + cantidad
            avg_price = (old['price']*old['qty'] + precio*cantidad) / total_qty
            positions[symbol] = {'price': avg_price, 'qty': total_qty}
        else:
            positions[symbol] = {'price': precio, 'qty': cantidad}
        
        bot.send_message(MY_CHAT_ID, f"🤖 AUTO COMPRÉ: {symbol} x{cantidad} @ {precio}")
        return True
        
    except Exception as e:
        bot.send_message(MY_CHAT_ID, f"❌ Error AUTO comprando {symbol}: {e}")
        return False

def check_ganancias():
    while True:
        try:
            for symbol in list(positions.keys()):
                info = positions[symbol]
                curr_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
                ganancia_pct = (curr_price - info['price']) / info['price']
                if ganancia_pct <= -STOPLOSS_PCT:
                    try:
                        client.order_market_sell(symbol=symbol, quantity=info['qty'])
                        bot.send_message(MY_CHAT_ID, f"🛑 STOPLOSS -2% en {symbol}\nVendido en {curr_price}")
                        del positions[symbol]
                    except Exception as e:
                        print(f"Error SL {symbol}: {e}")
                elif ganancia_pct >= TAKE_PROFIT_PCT:
                    bot.send_message(MY_CHAT_ID, f"💰 ¡+{ganancia_pct*100:.2f}% en {symbol}!\nEntrada: {info['price']} -> Ahora: {curr_price}\n/retirar - Vendo\n/dejar - Dejo correr")
        except Exception as e:
            print(f"Check error: {e}")
        time.sleep(60)

def comprar_autonomo():
    try:
        symbol, change = buscar_mejor_moneda()
        if symbol:
            ejecutar_compra_autonoma(symbol)
        else:
            bot.send_message(MY_CHAT_ID, "ℹ️ No hay monedas nuevas para comprar, todas ya están en posiciones")
    except Exception as e:
        print(f"Error en comprar_autonomo: {e}")

def auto_loop():
    global last_trade
    while True:
        try:
            if AUTO and (time.time() - last_trade) >= 900:
                comprar_autonomo()
                last_trade = time.time()
        except Exception as e:
            print(f"Error en auto_loop: {e}")
        time.sleep(10)

@app.route('/')
def home(): return "Shinito Autonomo Live - 20% SL 2% TP 5%+ FIXED"

@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m, "🔥 Shinito Autonomo Live!\n/auto_on - Activa 15min\n/auto_off\n/estado\n/forzar - Fuerza 1 compra\n/retirar\n/dejar")

@bot.message_handler(commands=['auto_on'])
def auto_on(m):
    global AUTO, last_trade
    AUTO=True
    last_trade = time.time()
    bot.reply_to(m, "✅ AUTO ACTIVADO\nBusca moneda cada 15min\n20% balance | SL 2% | TP 5%+")

@bot.message_handler(commands=['auto_off'])
def auto_off(m):
    global AUTO; AUTO=False
    bot.reply_to(m, "⏸️ AUTO apagado")
    
@bot.message_handler(commands=['forzar'])
def forzar(m):
    try:
        bot.reply_to(m, "🔎 Forzando búsqueda...")
        symbol, change = buscar_mejor_moneda()
        if not symbol:
            bot.reply_to(m, "Ya tienes todas las mejores monedas o no hay candidatas")
            return
        ok = ejecutar_compra_autonoma(symbol)
        if ok:
            bot.reply_to(m, f"✅ Compra forzada: {symbol} (+{change:.2f}%)")
    except Exception as e:
        bot.reply_to(m, f"Error en forzar: {e}")
        
@bot.message_handler(commands=['retirar'])
def retirar(m):
    try:
        if not positions:
            bot.reply_to(m, "No hay posiciones abiertas")
            return
        for symbol in list(positions.keys()):
            info = positions[symbol]
            client.order_market_sell(symbol=symbol, quantity=info['qty'])
            curr = float(client.get_symbol_ticker(symbol=symbol)['price'])
            gan = (curr - info['price'])/info['price']*100
            bot.reply_to(m, f"✅ Vendido {symbol} con {gan:.2f}%")
            del positions[symbol]
    except Exception as e:
        bot.reply_to(m, f"Error retirar: {e}")

@bot.message_handler(commands=['dejar'])
def dejar(m):
    bot.reply_to(m, "👌 Dejando correr la ganancia")

@bot.message_handler(commands=['estado'])
def estado(m):
    b = client.get_asset_balance(asset='USDT')
    msg = f"USDT: {float(b['free']):.2f} | AUTO: {AUTO}\n"
    if positions:
        for s,i in positions.items():
            curr = float(client.get_symbol_ticker(symbol=s)['price'])
            pct = (curr-i['price'])/i['price']*100
            msg += f"{s}: {pct:.2f}% ({i['qty']})\n"
    else:
        msg += "Sin posiciones"
    bot.reply_to(m, msg)

if __name__ == "__main__":
    threading.Thread(target=auto_loop, daemon=True).start()
    threading.Thread(target=check_ganancias, daemon=True).start()
    try:
        bot.remove_webhook()
    except:
        pass
    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True), daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
