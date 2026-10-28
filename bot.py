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
STOPLOSS_PCT = 0.02  # 2%
TAKE_PROFIT_PCT = 0.05 # 5%
last_trade = 0
positions = {} # guarda compras {symbol: {price, qty}}

def buscar_mejor_moneda():
    try:
        tickers = client.get_ticker()
        # Filtro: solo USDT, volumen > 5M, no stablecoins
        blacklist = ['USDCUSDT','BUSDUSDT','DAIUSDT','TUSDUSDT','FDUSDUSDT']
        candidatos = []
        for t in tickers:
            sym = t['symbol']
            if not sym.endswith('USDT'): continue
            if sym in blacklist: continue
            try:
                vol = float(t['quoteVolume'])
                change = float(t['priceChangePercent'])
                if vol > 5000000 and change > 0 and change < 15: # sube pero no pump raro de 50%
                    candidatos.append(t)
            except: continue
        
        # Ordena por % de ganancia 24h
        candidatos = sorted(candidatos, key=lambda x: float(x['priceChangePercent']), reverse=True)
        if candidatos:
            return candidatos[0]['symbol'], float(candidatos[0]['priceChangePercent'])
        return "BTCUSDT", 0
    except Exception as e:
        print(f"Error buscando moneda: {e}")
        return "BTCUSDT", 0

def ejecutar_compra_autonoma(symbol):
    try:
        # 1. Sacar balance
        balance = client.get_account()
        usdt_balance = float([b for b in balance['balances'] if b['asset']=='USDT'][0]['free'])
        monto_usdt = usdt_balance * 0.20
        if monto_usdt < 12: 
            return

        # 2. Sacar LOT_SIZE y PRICE_FILTER de Binance
        info = client.get_symbol_info(symbol)
        lot_filter = [f for f in info['filters'] if f['filterType']=='LOT_SIZE'][0]
        step_size = float(lot_filter['stepSize'])
        
        # 3. Calcular cantidad y AJUSTARLA al stepSize
        ticker = client.get_symbol_ticker(symbol=symbol)
        precio = float(ticker['price'])
        cantidad_bruta = monto_usdt / precio
        
        # Esta magia lo redondea al lote que quiere Binance
        precision = int(round(-math.log(step_size, 10), 0))
        cantidad = math.floor(cantidad_bruta * (10**precision)) / (10**precision)
        
        # 4. Comprar
        client.order_market_buy(symbol=symbol, quantity=cantidad)
        
        bot.send_message(MY_CHAT_ID, f"🤖 AUTO COMPRÉ: {symbol} x{cantidad}")
        
    except Exception as e:
        bot.send_message(MY_CHAT_ID, f"❌ Error AUTO: {e}")

def check_ganancias():
    # Revisa posiciones cada 1 min
    while True:
        try:
            for symbol in list(positions.keys()):
                info = positions[symbol]
                curr_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
                ganancia_pct = (curr_price - info['price']) / info['price']

                # Si cae -2% vende solo con stoploss
                if ganancia_pct <= -STOPLOSS_PCT:
                    try:
                        client.order_market_sell(symbol=symbol, quantity=info['qty'])
                        bot.send_message(MY_CHAT_ID, f"🛑 STOPLOSS -2% ejecutado en {symbol}\nVendido en {curr_price}")
                        del positions[symbol]
                    except: pass
                
                # Si sube 5% o más, te pregunta
                elif ganancia_pct >= TAKE_PROFIT_PCT:
                    bot.send_message(MY_CHAT_ID, f"💰 ¡GOLPE DE SUERTE! +{ganancia_pct*100:.2f}% en {symbol}\nEntrada: {info['price']} -> Ahora: {curr_price}\nGanancia rebasa 5%\n\n¿Quieres retirar? Responde:\n/retirar - Vendo todo y guardo ganancia\n/dejar - Dejo que siga corriendo")
        except Exception as e:
            print(f"Check error: {e}")
        time.sleep(60)

def comprar_autonomo():
    try:
        # Aquí pon tu lógica real de compra, te dejo la plantilla con el fix de LOT_SIZE
        from binance_logic import buscar_moneda_mas_rentable, comprar_con_lote_correcto
        symbol = buscar_moneda_mas_rentable()
        if symbol:
            comprar_con_lote_correcto(symbol)
    except Exception as e:
        print(f"Error en comprar_autonomo: {e}")
        raise e

def auto_loop():
    global last_trade
    while True:
        try:
            if AUTO and (time.time() - last_trade) >= 900:
                comprar_autonomo()
                last_trade = time.time()
        except Exception as e:
            print(f"Error en auto_loop pero sigo vivo: {e}")
            try:
                bot.send_message(MY_CHAT_ID, f"⚠️ AUTO falló pero sigo vivo: {e}")
            except:
                pass
        time.sleep(10)

@app.route('/')
def home(): return "Shinito Autonomo Live - 20% SL 2% TP 5%+"

@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m, "🔥 Shinito Autonomo Live verde!\n/ auto_on - Activa modo autonomo 15min\n/ auto_off\n/ estado\n/ retirar - Vende si hay +5%\n/ dejar")

@bot.message_handler(commands=['auto_on'])
def auto_on(m):
    global AUTO, last_trade
    AUTO=True
    last_trade = time.time()
    bot.reply_to(m, "✅ AUTO AUTONOMO ACTIVADO\nBusca moneda más rentable cada 15min\n20% balance | SL 2% | TP 5%+\nTe aviso solo cuando haya +5%")

@bot.message_handler(commands=['auto_off'])
def auto_off(m):
    global AUTO; AUTO=False
    bot.reply_to(m, "⏸️ AUTO apagado")

@bot.message_handler(commands=['retirar'])
def retirar(m):
    try:
        for symbol in list(positions.keys()):
            info = positions[symbol]
            client.order_market_sell(symbol=symbol, quantity=info['qty'])
            curr = float(client.get_symbol_ticker(symbol=symbol)['price'])
            gan = (curr - info['price'])/info['price']*100
            bot.reply_to(m, f"✅ Retiro ejecutado {symbol} con +{gan:.2f}%")
            del positions[symbol]
        if not positions:
            bot.reply_to(m, "No hay posiciones abiertas")
    except Exception as e:
        bot.reply_to(m, f"Error retirar: {e}")

@bot.message_handler(commands=['dejar'])
def dejar(m):
    bot.reply_to(m, "👌 Dejando correr la ganancia, te vuelvo a avisar si sube más")

@bot.message_handler(commands=['estado'])
def estado(m):
    b = client.get_asset_balance(asset='USDT')
    msg = f"USDT: {float(b['free']):.2f} | AUTO: {AUTO} | SL 2% | TP 5%+\n"
    if positions:
        for s,i in positions.items():
            curr = float(client.get_symbol_ticker(symbol=s)['price'])
            pct = (curr-i['price'])/i['price']*100
            msg += f"{s}: {pct:.2f}%\n"
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
