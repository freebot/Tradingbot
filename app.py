import os
import time
import threading
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
import sqlite3
from transformers import pipeline
from pycoingecko import CoinGeckoAPI
from web3 import Web3
import plotly.graph_objs as go
import requests
import numpy as np

# Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# Configuración de PostgreSQL
# Configuración de SQLite
DB_NAME = "trading_bot.db"

# Inicializar modelo de Hugging Face (Análisis de sentimiento)
# Usamos un modelo específico para finanzas si es posible, o uno general
print("Cargando modelo de Hugging Face...")
sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
print("Modelo cargado.")

# Configurar Web3 con Alchemy
alchemy_url = os.getenv('ALCHEMY_URL')
if alchemy_url:
    web3 = Web3(Web3.HTTPProvider(alchemy_url))
else:
    print("Advertencia: ALCHEMY_URL no configurado. La funcionalidad Web3 estará desactivada.")
    web3 = None

# Conexión a CoinGecko
cg = CoinGeckoAPI()

# Función para obtener una conexión a la base de datos
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Para acceder a columnas por nombre
    return conn

# Función para cerrar una conexión a la base de datos
def close_db_connection(conn):
    conn.close()

# Función para obtener precios de CoinGecko y guardarlos en la base de datos
def fetch_and_store_prices(interval=60):
    while True:
        try:
            # Obtener precios de CoinGecko
            prices = cg.get_price(ids='matic-network,usd-coin', vs_currencies='usd')
            matic_price = prices['matic-network']['usd']
            usdc_price = prices['usd-coin']['usd']

            # Guardar en la base de datos
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prices (timestamp, token1, price1, token2, price2)
                VALUES (datetime('now'), 'MATIC', ?, 'USDC', ?)
            """, (matic_price, usdc_price))
            conn.commit()
            close_db_connection(conn)

            print(f"Precios guardados: MATIC={matic_price}, USDC={usdc_price}")

            # Esperar el intervalo
            time.sleep(interval)
        except Exception as e:
            print(f"Error fetching or storing prices: {e}")
            time.sleep(30)  # Reintentar después de 30 segundos

# Iniciar el hilo para obtener y guardar precios
threading.Thread(target=fetch_and_store_prices, daemon=True).start()

# Ruta para la página principal
@app.route("/")
def home():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener el número total de registros en la tabla prices
        cursor.execute("SELECT COUNT(*) FROM prices")
        total_records = cursor.fetchone()[0]

        # Obtener los últimos 10 registros de la tabla prices
        cursor.execute("""
            SELECT timestamp, token1, price1, token2, price2 
            FROM prices 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        last_records = cursor.fetchall()

        # Obtener estadísticas de precios
        cursor.execute("SELECT MIN(price1), MAX(price1), AVG(price1) FROM prices")
        matic_stats = cursor.fetchone()

        cursor.execute("SELECT MIN(price2), MAX(price2), AVG(price2) FROM prices")
        usdc_stats = cursor.fetchone()

        close_db_connection(conn)

        return render_template("index.html", 
                            total_records=total_records,
                            last_records=last_records,
                            matic_stats=matic_stats,
                            usdc_stats=usdc_stats)

    except Exception as e:
        return render_template("error.html", error_message=str(e))

# Ruta para mostrar gráficos
@app.route("/chart")
def chart():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener datos para el gráfico de precios
        cursor.execute("""
            SELECT timestamp, price1, price2 
            FROM prices 
            ORDER BY timestamp DESC 
            LIMIT 100
        """)
        chart_data = cursor.fetchall()
        timestamps = [row[0] for row in chart_data]
        price1 = [row[1] for row in chart_data]
        price2 = [row[2] for row in chart_data]

        close_db_connection(conn)

        # Crear gráficos con Plotly
        price1_trace = go.Scatter(x=timestamps, y=price1, mode='lines', name='Precio MATIC')
        price2_trace = go.Scatter(x=timestamps, y=price2, mode='lines', name='Precio USDC')
        layout = go.Layout(title='Gráfico de Precios', xaxis={'title': 'Fecha'}, yaxis={'title': 'Precio'})
        chart_fig = go.Figure(data=[price1_trace, price2_trace], layout=layout)
        chart_html = chart_fig.to_html(full_html=False)

        return render_template("chart.html", chart_html=chart_html)

    except Exception as e:
        return render_template("error.html", error_message=str(e))

# Ruta para mostrar estrategias
@app.route("/strategy")
def strategy():
    try:
        # Obtener datos de CoinGecko (ejemplo: precio de Bitcoin)
        bitcoin_price = cg.get_price(ids='bitcoin', vs_currencies='usd')['bitcoin']['usd']

        # Obtener el último bloque de Polygon Amoy desde Alchemy
        if web3 and web3.is_connected():
            latest_block = web3.eth.block_number
        else:
            latest_block = "No disponible (configura ALCHEMY_URL)"

        return render_template("strategy.html", 
                            bitcoin_price=bitcoin_price,
                            latest_block=latest_block)

    except Exception as e:
        return render_template("error.html", error_message=str(e))

# Ruta para mostrar noticias y sentimiento
@app.route("/news")
def news():
    try:
        # Obtener noticias de CryptoPanic
        api_key = os.getenv('CRYPTOPANIC_API_KEY', 'TU_API_KEY')
        news_url = f"https://cryptopanic.com/api/v1/posts/?auth_token={api_key}"
        response = requests.get(news_url)
        if response.status_code == 200:
            news_data = response.json()
        else:
            news_data = {"error": "No se pudieron obtener noticias (Verifica tu API KEY)"}

        return render_template("news.html", news_data=news_data)

    except Exception as e:
        return render_template("error.html", error_message=str(e))

# Ruta para mostrar métricas de machine learning
@app.route("/ml")
def ml():
    try:
        # Simular métricas de un modelo de machine learning
        # Usar Hugging Face para analizar sentimiento de textos de ejemplo (o noticias reales si se implementa)
        examples = [
            "Bitcoin is soaring to new heights!",
            "Regulation concerns cause market drop.",
            "Polygon network sees massive adoption."
        ]
        
        predictions = sentiment_analyzer(examples)
        
        ml_metrics = {
            "model_name": "distilbert-base-uncased-finetuned-sst-2-english",
            "examples": list(zip(examples, predictions))
        }

        # ml_metrics formateado para el template
        # predictions es una lista de diccionarios [{'label': 'POSITIVE', 'score': 0.99}, ...]

        return render_template("ml.html", ml_metrics=ml_metrics)

    except Exception as e:
        return render_template("error.html", error_message=str(e))

# Ruta para mostrar información de liquidez en DEXs
@app.route("/liquidity")
def liquidity():
    try:
        # Simular datos de pools de liquidez
        liquidity_data = {
            "pool1": {"token1": "MATIC", "token2": "USDC", "volume": 1000000},
            "pool2": {"token1": "ETH", "token2": "USDC", "volume": 500000}
        }

        return render_template("liquidity.html", liquidity_data=liquidity_data)

    except Exception as e:
        return render_template("error.html", error_message=str(e))

# Iniciar el servidor
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
