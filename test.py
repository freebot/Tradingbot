import psycopg2
conn = psycopg2.connect(
    dbname="trading_bot",
    user="flask_user",
    password="Bigfoot1",
    host="74.249.193.139",
    port="5432",
    sslmode="require"
)
print("Conexión exitosa")
