import sqlite3

# Conectar a la base de datos (se crea si no existe)
conn = sqlite3.connect("trading_bot.db")
cursor = conn.cursor()

# Crear tablas si no existen
cursor.execute("""
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token1 TEXT NOT NULL,
    token2 TEXT NOT NULL,
    price1 REAL NOT NULL,
    price2 REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    side TEXT NOT NULL,
    token1 TEXT NOT NULL,
    token2 TEXT NOT NULL,
    price1 REAL NOT NULL,
    price2 REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
