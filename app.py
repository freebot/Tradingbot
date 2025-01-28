import os  # Importa el módulo os
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
import sqlite3
import threading
import time
from pycoingecko import CoinGeckoAPI
from web3 import Web3
import plotly.graph_objs as go

# Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# Conexión a la API de CoinGecko
cg = CoinGeckoAPI()

# URL de Infura para Polygon
# Cargar la URL de Infura desde el archivo .env
infura_url = os.getenv('INFURA_URL')  # Aquí es donde se usa os
web3 = Web3(Web3.HTTPProvider(infura_url))

# Ruta para la página principal
@app.route("/")
def home():
    # Obtener los últimos 10 logs de la base de datos
    conn = sqlite3.connect("trading_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT message FROM logs ORDER BY timestamp DESC LIMIT 10")
    logs = cursor.fetchall()
    conn.close()

    # Obtener los datos del gráfico
    conn = sqlite3.connect("trading_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, price1, price2 FROM prices ORDER BY timestamp DESC LIMIT 100")
    data = cursor.fetchall()
    conn.close()

    # Preparar los datos para el gráfico
    timestamps = [row[0] for row in data]
    matic_prices = [row[1] for row in data]
    usdc_prices = [row[2] for row in data]

    # Crear el gráfico con Plotly
    trace1 = go.Scatter(x=timestamps, y=matic_prices, mode='lines', name='MATIC')
    trace2 = go.Scatter(x=timestamps, y=usdc_prices, mode='lines', name='USDC')

    layout = go.Layout(title="Precios de MATIC y USDC", xaxis={'title': 'Tiempo'}, yaxis={'title': 'Precio'})
    fig = go.Figure(data=[trace1, trace2], layout=layout)

    # Convertir el gráfico a HTML
    graph_html = fig.to_html(full_html=False)

    return render_template("index.html", logs=logs, graph_html=graph_html)

# Ruta para la estrategia de trading
@app.route("/strategy")
def strategy():
    # Detalles sobre la estrategia de trading
    strategy_info = {
        "title": "Estrategia de Trading Pairs",
        "description": """
            Esta estrategia de trading utiliza dos tokens (por ejemplo, MATIC y USDC) para identificar
            oportunidades de compra o venta en función de la relación de precios entre ambos tokens.
            El bot compara los precios de MATIC y USDC en tiempo real y, basándose en reglas predefinidas,
            decide cuándo ejecutar una operación de compra o venta.
        """,
        "steps": [
            "Paso 1: Obtener precios de MATIC y USDC desde CoinGecko.",
            "Paso 2: Evaluar la relación de precios entre MATIC y USDC.",
            "Paso 3: Tomar decisiones de compra o venta en función de las condiciones del mercado.",
            "Paso 4: Ejecutar la operación de acuerdo con los resultados del análisis."
        ]
    }
    return render_template("strategy.html", strategy=strategy_info)

# Ruta para obtener datos de la base de datos
@app.route("/data")
def get_data():
    conn = sqlite3.connect("trading_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, token1, price1, token2, price2 FROM prices ORDER BY timestamp DESC LIMIT 100")
    data = cursor.fetchall()
    conn.close()
    return jsonify(data)


# Función para actualizar los datos
def update_data():
    conn = sqlite3.connect("trading_bot.db")
    cursor = conn.cursor()

    while True:
        try:
            # Obtener precios de CoinGecko para MATIC y USDC
            precios_matic = cg.get_price(ids='matic-network', vs_currencies='usd')
            precios_usdc = cg.get_price(ids='usd-coin', vs_currencies='usd')

            # Extraer los precios de las respuestas
            precio_matic = precios_matic['matic-network']['usd']
            precio_usdc = precios_usdc['usd-coin']['usd']

            # Actualizar la base de datos con los precios obtenidos
            cursor.execute("""
                INSERT INTO prices (token1, token2, price1, price2)
                VALUES ('MATIC', 'USDC', ?, ?)
            """, (precio_matic, precio_usdc))
            conn.commit()

            print(f"Datos actualizados: MATIC={precio_matic} USDC={precio_usdc}")

        except Exception as e:
            print(f"Error al actualizar datos: {e}")

        time.sleep(60)  # Esperar 1 minuto antes de la siguiente actualización


def log_message(message):
    # Insertar mensaje de log en la base de datos
    conn = sqlite3.connect("trading_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (message) VALUES (?)", (message,))
    conn.commit()
    conn.close()

# Iniciar el hilo para actualizar los datos en segundo plano
if __name__ == "__main__":
    threading.Thread(target=update_data, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True)
