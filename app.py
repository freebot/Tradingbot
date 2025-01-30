import os
import time
import threading
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool
from pycoingecko import CoinGeckoAPI
from web3 import Web3
import plotly.graph_objs as go
import requests
import numpy as np
import tensorflow as tf

# Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# Configuración de PostgreSQL
postgresql_pool = psycopg2.pool.SimpleConnectionPool(
    1, 20,
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    port=os.getenv('DB_PORT', 5432),
    sslmode=os.getenv('DB_SSLMODE', 'require')
)

# Configurar Web3 con Alchemy
alchemy_url = os.getenv('ALCHEMY_URL')
web3 = Web3(Web3.HTTPProvider(alchemy_url))

# Conexión a CoinGecko
cg = CoinGeckoAPI()

# Función para obtener una conexión a la base de datos
def get_db_connection():
    return postgresql_pool.getconn()

# Función para cerrar una conexión a la base de datos
def close_db_connection(conn):
    postgresql_pool.putconn(conn)

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
                VALUES (NOW(), 'MATIC', %s, 'USDC', %s)
            """, (matic_price, usdc_price))
            conn.commit()
            close_db_connection(conn)

            print(f"Precios guardados: MATIC={matic_price}, USDC={usdc_price}")

            # Esperar el intervalo
            time.sleep(interval)
        except Exception as e:
            print(f"Error fetching or storing prices: {e}")
            time.sleep(30)  # Reintentar después de 30 segundos

# Función para entrenar un modelo de TensorFlow y guardar métricas
def train_model():
    while True:
        try:
            # Simular datos de entrenamiento
            x_train = np.random.rand(100, 2)
            y_train = (x_train[:, 0] + x_train[:, 1] > 1).astype(int)

            # Crear y entrenar el modelo
            model = tf.keras.Sequential([
                tf.keras.layers.Dense(16, activation='relu', input_shape=(2,)),
                tf.keras.layers.Dense(16, activation='relu'),
                tf.keras.layers.Dense(1, activation='sigmoid')
            ])
            model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
            history = model.fit(x_train, y_train, epochs=1, verbose=0)

            # Guardar métricas en la base de datos
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO training_metrics (loss, accuracy, training_time)
                VALUES (%s, %s, NOW())
            """, (history.history['loss'][0], history.history['accuracy'][0]))
            conn.commit()
            close_db_connection(conn)

            print(f"Métricas guardadas: Loss={history.history['loss'][0]}, Accuracy={history.history['accuracy'][0]}")

            # Esperar el intervalo
            time.sleep(60)  # Entrenar cada 60 segundos
        except Exception as e:
            print(f"Error en entrenamiento: {e}")
            time.sleep(30)  # Reintentar después de 30 segundos

# Iniciar hilos para obtener precios y entrenar el modelo
threading.Thread(target=fetch_and_store_prices, daemon=True).start()
threading.Thread(target=train_model, daemon=True).start()

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

        # Obtener métricas de entrenamiento
        cursor.execute("""
            SELECT loss, accuracy 
            FROM training_metrics 
            ORDER BY training_time DESC 
            LIMIT 10
        """)
        training_metrics = cursor.fetchall()

        close_db_connection(conn)

        return render_template("index.html", 
                            total_records=total_records,
                            last_records=last_records,
                            matic_stats=matic_stats,
                            usdc_stats=usdc_stats,
                            training_metrics=training_metrics)

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
        latest_block = web3.eth.block_number

        return render_template("strategy.html", 
                            bitcoin_price=bitcoin_price,
                            latest_block=latest_block)

    except Exception as e:
        return render_template("error.html", error_message=str(e))

# Iniciar el servidor
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
