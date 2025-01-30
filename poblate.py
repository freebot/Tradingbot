import ccxt
import psycopg2
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuración de PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT', 5432)
    )

# Crear instancia de ccxt para Binance
exchange = ccxt.kraken()


# Función para obtener precios
def get_prices():
    try:
        # Obtener el precio de MATIC/USDT y USDC/USDT desde Binance
        matic_price = exchange.fetch_ticker('MATIC/USDT')['last']
        usdc_price = exchange.fetch_ticker('USDC/USDT')['last']

        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insertar precios en la base de datos
        cursor.execute("""
            INSERT INTO prices (token1, token2, price1, price2)
            VALUES (%s, %s, %s, %s)
        """, ('MATIC', 'USDC', matic_price, usdc_price))
        conn.commit()

        print(f"Datos insertados: MATIC={matic_price}, USDC={usdc_price}")
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error al obtener o insertar datos: {e}")

# Llamar a la función para poblar la base de datos
get_prices()
