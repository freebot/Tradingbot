import sqlite3

def create_logs_table():
    conn = sqlite3.connect("trading_bot.db")
    cursor = conn.cursor()

    # Crear la tabla 'logs'
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

# Llamar a la función para crear la tabla
create_logs_table()
