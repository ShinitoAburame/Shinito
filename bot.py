import math
import os, threading, time, json
from datetime import datetime
from flask import Flask
import telebot
from telebot.types import BotCommand
import binance.client
binance.client.Client.ping = lambda self: {}
from binance.client import Client

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("BINANCE_TESTNET_API_KEY")
API_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET")
PROXY = os.getenv("PROXY_URL") or "http://uoguvsaz:on13dk1xsk1q@45.38.107.97:6014"
MY_CHAT_ID = 8132255561

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
proxies = {"http": PROXY, "https": PROXY}
client = Client(API_KEY, API_SECRET, testnet=True, requests_params={"proxies": proxies, "timeout": 30})
client.API_URL = 'https://testnet.binance.vision/api'

AUTO = False
MONTO_PCT = 0.20
STOPLOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.05
last_trade = 0
positions = {}
historial_trades = []

ESTADO_FILE = "estado.json"
HISTORIAL_FILE = "historial.json"

def guardar_todo():
    try:
        with open(ESTADO_FILE, "w") as f:
            json.dump({"positions": positions, "AUTO": AUTO, "last_trade": last_trade}, f)
        with open(HISTORIAL_FILE, "w") as f:
            json.dump(historial_trades, f)
    except Exception as e:
        print(f"Error guardando: {e}")

def cargar_todo():
    global positions, AUTO, last_trade, historial_trades
    try:
        if os.path.exists(ESTADO_FILE):
            with open(ESTADO_FILE, "r") as f:
                data = json.load(f)
                positions = data.get("positions", {})
                AUTO = data.get("AUTO", False)
                last_trade = data.get("last_trade", 0)
        if os.path.exists(HISTORIAL_FILE):
            with open(HISTORIAL_FILE, "r") as f:
                historial_trades = json.load(f)
        print(f"Cargado: {len(positions)} posiciones, {len(historial_trades)} trades en historial")
    except Exception as e:
        print(f"Error cargando: {e}")
        positions = {}
        historial_trades = []

# --- NUEVO V3.2: Configura menu desde Github ---
def configurar_menu():
    try:
        print("Configurando menu desde Github...")
        bot.delete_my_commands()
        time.sleep(1)
        comandos = [
            BotCommand("start", "🔥 Menu principal"),
            BotCommand("auto_on", "Activa modo automatico 15min"),
            BotCommand("auto_off", "Pausa modo automatico"),
            BotCommand("estado", "Ver saldo y posiciones"),
            BotCommand("forzar", "Fuerza 1 compra ahora"),
            BotCommand("retirar", "Vende todo manual"),
            BotCommand("dejar", "Deja correr ganancia"),
            BotCommand("historial", "Ver ultimas operaciones"),
            BotCommand("ganancias", "Resumen de profit"),
            BotCommand("recuperar", "Sincroniza con Binance"),
        ]
        bot.set_my_commands(comandos)
        # Intenta borrar el boton de Menu web feo si existe
        try:
            bot.delete_my_commands(scope=None)
            bot.set_my_commands(comandos)
        except: pass
        print("✅ Menu configurado correctamente")
    except Exception as e:
        print(f"Error configurando menu: {e}")

# --- FIX V3.1: Sincroniza posiciones fantasma con Binance real ---
def limpiar_fantasmas():
    global positions
    try:
        account = client.get_account()
        balances_reales = {b['asset']: float(b['free']) for b in account['balances'] if float(b['free']) > 0.00001}
        fantasmas = []
        for sym in list(positions.keys()):
            asset = sym.replace('USDT','')
            if asset not in balances_reales and sym[:-4] not in balances_reales:
                if balances_reales.get(asset, 0) == 0:
                    fantasmas.append(sym)
        for f in fantasmas:
            print(f"Limpiando fantasma: {f}")
            del positions[f]
        if fantasmas:
            guardar_todo()
            return True
    except Exception as e:
        print(f"Error limpiando fantasmas: {e}")
    return False

def buscar_mejor_moneda():
    try:
        limpiar_fantasmas()
        tickers = client.get_ticker()
        blacklist = ['USDCUSDT','BUSDUSDT','DAIUSDT','TUSDUSDT','FDUSDUSDT','USDEUSDT']
        candidatos = []
        for t in tickers:
            sym = t['symbol']
            if not sym.endswith('USDT'): continue
            if sym in blacklist: continue
            if sym in positions: continue
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

def ajustar_cantidad(symbol, cantidad_bruta):
    try:
        info = client.get_symbol_info(symbol)
        lot_filter = [f for f in info['filters'] if f['filterType']=='LOT_SIZE'][0]
        step_size = float(lot_filter['stepSize'])
        precision = int(round(-math.log(step_size, 10), 0)) if step_size < 1 else 0
        if precision < 0: precision = 0
        cantidad = math.floor(cantidad_bruta * (10**precision)) / (10**precision)
        if cantidad == 0:
            cantidad = step_size
        return cantidad
    except:
        return cantidad_bruta

def ejecutar_compra_autonoma(symbol):
    try:
        balance = client.get_account()
        usdt_balance = float([b for b in balance['balances'] if b['asset']=='USDT'][0]['free'])
        monto_usdt = usdt_balance * MONTO_PCT
        if monto_usdt < 12: 
            bot.send_message(MY_CHAT_ID, f"⚠️ Saldo muy bajo: {usdt_balance:.2f} USDT")
            return False
        ticker = client.get_symbol_ticker(symbol=symbol)
        precio = float(ticker['price'])
        cantidad_bruta = monto_usdt / precio
        cantidad = ajustar_cantidad(symbol, cantidad_bruta)
        client.order_market_buy(symbol=symbol, quantity=cantidad)
        if symbol in positions:
            old = positions[symbol]
            total_qty = old['qty'] + cantidad
            avg_price = (old['price']*old['qty'] + precio*cantidad) / total_qty
            positions[symbol] = {'price': avg_price, 'qty': total_qty}
        else:
            positions[symbol] = {'price': precio, 'qty': cantidad}
        guardar_todo()
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
                        qty_ajustada = ajustar_cantidad(symbol, info['qty'])
                        client.order_market_sell(symbol=symbol, quantity=qty_ajustada)
                        bot.send_message(MY_CHAT_ID, f"🛑 STOPLOSS -2% en {symbol}\nVendido en {curr_price}")
                        historial_trades.append({
                            "par": symbol,
                            "tipo": "SL",
                            "ganancia_pct": round(ganancia_pct*100,2),
                            "ganancia_usdt": round((curr_price - info['price'])*info['qty'],4),
                            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        del positions[symbol]
                        guardar_todo()
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
            if len(positions) == 0:
                print("No hay candidatas ahora, intento en proximo ciclo")
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
                guardar_todo()
        except Exception as e:
            print(f"Error en auto_loop: {e}")
        time.sleep(10)

@app.route('/')
def home(): return "Shinito V3.2 - Menu desde Github - 20% SL 2% TP 5%+"

@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m, "🔥 Shinito V3.2 FIX!\n/auto_on - Activa 15min\n/auto_off - Pausa auto\n/estado - Ver saldo\n/forzar - Fuerza 1 compra\n/retirar - Vende todo\n/dejar - Deja correr\n/historial - Ver operaciones\n/ganancias - Resumen profit\n/recuperar - Sincroniza Binance")

@bot.message_handler(commands=['auto_on'])
def auto_on(m):
    global AUTO, last_trade
    AUTO=True
    last_trade = time.time()
    guardar_todo()
    bot.reply_to(m, "✅ AUTO ACTIVADO\nBusca moneda cada 15min\n20% balance | SL 2% | TP 5%+")

@bot.message_handler(commands=['auto_off'])
def auto_off(m):
    global AUTO; AUTO=False
    guardar_todo()
    bot.reply_to(m, "⏸️ AUTO apagado")
    
@bot.message_handler(commands=['forzar'])
def forzar(m):
    try:
        bot.reply_to(m, "🔎 Forzando búsqueda...")
        symbol, change = buscar_mejor_moneda()
        if not symbol:
            bot.reply_to(m, "Ya tienes todas las mejores monedas o no hay candidatas con volumen, espera 15 min")
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
            qty_ajustada = ajustar_cantidad(symbol, info['qty'])
            client.order_market_sell(symbol=symbol, quantity=qty_ajustada)
            curr = float(client.get_symbol_ticker(symbol=symbol)['price'])
            gan = (curr - info['price'])/info['price']*100
            gan_usdt = (curr - info['price'])*info['qty']
            historial_trades.append({
                "par": symbol,
                "tipo": "MANUAL",
                "ganancia_pct": round(gan,2),
                "ganancia_usdt": round(gan_usdt,4),
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            bot.reply_to(m, f"✅ Vendido {symbol} con {gan:.2f}% (+{gan_usdt:.4f} USDT)")
            del positions[symbol]
        guardar_todo()
    except Exception as e:
        bot.reply_to(m, f"Error retirar: {e}")

@bot.message_handler(commands=['dejar'])
def dejar(m):
    bot.reply_to(m, "👌 Dejando correr la ganancia")

@bot.message_handler(commands=['estado'])
def estado(m):
    try:
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
    except Exception as e:
        bot.reply_to(m, f"Error estado: {e}")

@bot.message_handler(commands=['historial'])
def historial(m):
    try:
        if not historial_trades:
            bot.reply_to(m, "📊 Sin trades aún. Usa /forzar para el primero.")
            return
        total_usdt = sum([t.get('ganancia_usdt',0) for t in historial_trades])
        msg = f"📊 HISTORIAL ({len(historial_trades)} trades)\nGanancia total: {total_usdt:.4f} USDT\n\n"
        for t in historial_trades[-10:]:
            msg += f"{t['fecha']} | {t['par']} {t['tipo']} {t['ganancia_pct']}% (+{t['ganancia_usdt']} USDT)\n"
        bot.reply_to(m, msg)
    except Exception as e:
        bot.reply_to(m, f"Error historial: {e}")

@bot.message_handler(commands=['ganancias'])
def ganancias(m):
    try:
        if not historial_trades:
            bot.reply_to(m, "Sin ganancias aún")
            return
        total = sum([t.get('ganancia_usdt',0) for t in historial_trades])
        b = client.get_asset_balance(asset='USDT')
        actual = float(b['free'])
        msg = f"💰 GANANCIAS\nHoy: {total:.4f} USDT\nBalance actual: {actual:.2f} USDT\nTrades: {len(historial_trades)}"
        bot.reply_to(m, msg)
    except Exception as e:
        bot.reply_to(m, f"Error ganancias: {e}")

@bot.message_handler(commands=['recuperar'])
def recuperar(m):
    try:
        account = client.get_account()
        balances = [b for b in account['balances'] if float(b['free']) > 0 and b['asset'] != 'USDT']
        msg = "🔄 Sincronizando con Binance...\n"
        for bal in balances:
            asset = bal['asset']
            symbol = asset + "USDT"
            try:
                free = float(bal['free'])
                if free == 0: continue
                if symbol not in positions:
                    curr = float(client.get_symbol_ticker(symbol=symbol)['price'])
                    positions[symbol] = {'price': curr, 'qty': free}
                    msg += f"Recuperado: {symbol} x{free}\n"
            except: continue
        guardar_todo()
        bot.reply_to(m, msg + "\n✅ Recuperación completa. Usa /estado")
    except Exception as e:
        bot.reply_to(m, f"Error recuperar: {e}")

def run_bot():
    while True:
        try:
            print("Iniciando bot polling...")
            bot.remove_webhook()
            time.sleep(3)
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"Polling crash: {e} - reintentando en 10s")
            time.sleep(10)

if __name__ == "__main__":
    cargar_todo()
    configurar_menu() # <-- NUEVO: configura menu desde Github
    threading.Thread(target=auto_loop, daemon=True).start()
    threading.Thread(target=check_ganancias, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
