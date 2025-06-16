import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Laad omgevingsvariabelen uit .env
load_dotenv()

# Pad naar CSV
bestand_output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adr_debug_results.csv")

# Probeer CSV in te lezen
try:
    df = pd.read_csv(bestand_output)
    print(f"✅ CSV geladen met {len(df)} rijen.")
except Exception as e:
    print(f"⚠️ Fout bij inlezen CSV: {e}")
    df = pd.DataFrame()  # lege DataFrame

# Verbind met database en werk bij
try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )
    cur = conn.cursor()

    # Verwijder altijd eerst oude rijen
    cur.execute("DELETE FROM adr_results")
    conn.commit()
    print("🗑️ Oude rijen verwijderd uit adr_results.")

    # Voeg nieuwe rijen toe als beschikbaar
    if not df.empty:
        for _, row in df.iterrows():
            cur.execute(
                """
                INSERT INTO adr_results 
                (ticker, name, recommendation, current_price, target_price, upside_percent, analyst_opinions)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row.get("Ticker"),
                    row.get("Name"),
                    row.get("Recommendation"),
                    row.get("Current Price"),
                    row.get("Target Price"),
                    row.get("Upside (%)"),
                    row.get("Analyst Opinions"),
                )
            )
        conn.commit()
        print("✅ Nieuwe data toegevoegd aan adr_results.")
    else:
        print("⚠️ Geen nieuwe data om toe te voegen.")

except Exception as e:
    print(f"❌ Fout bij verbinden of uploaden naar database: {e}")

finally:
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals():
        conn.close()
