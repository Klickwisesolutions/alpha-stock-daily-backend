import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Laad omgevingsvariabelen
load_dotenv()

# Laad CSV-resultaten
bestand_output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adr_debug_results.csv")

try:
    df = pd.read_csv(bestand_output)
except Exception as e:
    print(f"❌ Fout bij inlezen CSV: {e}")
    exit()

# Maak verbinding met de PostgreSQL database
try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )
    cur = conn.cursor()

    # Verwijder eerst alle oude rijen uit de tabel
    cur.execute("DELETE FROM adr_results")
    conn.commit()

    # Voeg nieuwe rijen toe
    for _, row in df.iterrows():
        cur.execute(
            """
            INSERT INTO adr_results 
            (ticker, name, recommendation, current_price, target_price, upside_percent, analyst_opinions)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                row["Ticker"],
                row["Name"],
                row["Recommendation"],
                row["Current Price"],
                row["Target Price"],
                row["Upside (%)"],
                row["Analyst Opinions"],
            )
        )
    
    conn.commit()
    print("✅ Data succesvol geüpload naar PostgreSQL.")

except Exception as e:
    print(f"❌ Fout bij verbinden of uploaden naar database: {e}")

finally:
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals():
        conn.close()
