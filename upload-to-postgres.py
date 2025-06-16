import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Laad lokale .env-variabelen (alleen nuttig bij lokaal testen)
load_dotenv()

# 📄 CSV-bestand pad
csv_path = "adr_nasdaq_debug_results.csv"  # Zorg dat dit bestand in dezelfde map staat

# CSV inlezen
df = pd.read_csv(csv_path)

# Kolommen mappen
df.columns = [
    "ticker", "name", "recommendation", "current_price",
    "target_price", "upside_percent", "analyst_opinions"
]
df["rec_order"] = df["recommendation"].map({
    "strong_buy": 1,
    "buy": 2
}).fillna(3).astype(int)

# PostgreSQL-verbinding
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME", "mydata_qhtb"),
    user=os.getenv("DB_USER", "mydata_qhtb_user"),
    password=os.getenv("DB_PASS"),
    host=os.getenv("DB_HOST"),
    port="5432"
)

# Gegevens uploaden
cur = conn.cursor()
cur.execute("DELETE FROM adr_results;")
for _, row in df.iterrows():
    cur.execute("""
        INSERT INTO adr_results 
        (ticker, name, recommendation, current_price, target_price, 
         upside_percent, analyst_opinions, rec_order)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, tuple(row))
conn.commit()
cur.close()
conn.close()

print("✅ Data succesvol geüpload naar PostgreSQL.")
