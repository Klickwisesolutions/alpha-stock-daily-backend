import os
import pandas as pd
import yfinance as yf
import time
import logging
import shutil
from datetime import datetime, timedelta
from emailer import stuur_email_dashboard
from dotenv import load_dotenv
import psycopg2

# .env laden (voor SMTP en DATABASE_URL)
load_dotenv()

# Setup
basepad = os.path.dirname(os.path.abspath(__file__))
bestand_input = os.path.join(basepad, "lijst_adr_nasdaq.csv")
bestand_output = os.path.join(basepad, "adr_debug_results.csv")
vandaag = datetime.today().strftime("%Y-%m-%d")
gisteren = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
bestand_gisteren = os.path.join(basepad, f"adr_debug_results_{gisteren}.csv")

# Logging
logfile = os.path.join(basepad, f"log_adr_{vandaag}.txt")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(logfile, encoding='utf-8'), logging.StreamHandler()]
)

# Backup
if os.path.exists(bestand_output):
    backuppad = os.path.join(basepad, f"adr_debug_results_{vandaag}.csv")
    shutil.copyfile(bestand_output, backuppad)
    logging.info(f"📂 Vorige resultaten opgeslagen als: {backuppad}")

# Inlezen input
try:
    df = pd.read_csv(bestand_input)
except Exception as e:
    logging.error(f"❌ Fout bij inlezen CSV: {e}", exc_info=True)
    exit()

if 'ticker' not in df.columns:
    logging.error("❌ Kolom 'ticker' niet gevonden in het CSV-bestand.")
    exit()

tickers = df['ticker'].dropna().unique().tolist()
logging.info(f"📊 Aantal tickers gevonden: {len(tickers)}")

# Analyse
results = []
for ticker in tickers:
    ticker = str(ticker).strip().upper()
    if not ticker:
        logging.warning("⚠️ Lege of ongeldige ticker overgeslagen.")
        continue

    logging.info(f"🔄 Verwerk ticker: {ticker}")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        recommendation = info.get("recommendationKey")
        mean_target = info.get("targetMeanPrice")
        current_price = info.get("currentPrice")
        opinions = info.get("numberOfAnalystOpinions")

        if recommendation in ["buy", "strong_buy"] and mean_target and current_price:
            upside = round((mean_target - current_price) / current_price * 100, 2)
            if upside >= 20:
                results.append({
                    "Ticker": ticker,
                    "Name": info.get("longName", "n/a"),
                    "Recommendation": recommendation,
                    "Current Price": current_price,
                    "Target Price": mean_target,
                    "Upside (%)": upside,
                    "Analyst Opinions": opinions
                })
    except Exception as e:
        logging.error(f"❌ Fout bij ophalen {ticker}: {e}", exc_info=True)

    time.sleep(1.5)

# Opslaan resultaten
df_result = pd.DataFrame(results)
if not df_result.empty:
    df_result.to_csv(bestand_output, index=False)
    logging.info(f"✅ Analyse voltooid. CSV opgeslagen op: {bestand_output}")
else:
    logging.warning("⚠️ Geen resultaten die aan de criteria voldeden.")
    if os.path.exists(bestand_output):
        try:
            os.remove(bestand_output)
            logging.info("🗑️ Oud CSV-bestand verwijderd omdat geen nieuwe resultaten beschikbaar waren.")
        except Exception as e:
            logging.error(f"❌ Fout bij verwijderen oud CSV-bestand: {e}", exc_info=True)

# Vergelijk met gisteren
if os.path.exists(bestand_gisteren):
    df_yesterday = pd.read_csv(bestand_gisteren)
    nieuw = df_result[~df_result['Ticker'].isin(df_yesterday['Ticker'])]
    verdwenen = df_yesterday[~df_yesterday['Ticker'].isin(df_result['Ticker'])]
    gewijzigd = pd.merge(df_result, df_yesterday, on='Ticker', suffixes=('_nieuw', '_oud'))
    gewijzigd = gewijzigd[
        (gewijzigd['Target Price_nieuw'] != gewijzigd['Target Price_oud']) |
        (gewijzigd['Recommendation_nieuw'] != gewijzigd['Recommendation_oud'])
    ]
    nieuw.to_csv(os.path.join(basepad, f"adr_{vandaag}_nieuw.csv"), index=False)
    verdwenen.to_csv(os.path.join(basepad, f"adr_{vandaag}_verdwenen.csv"), index=False)
    gewijzigd.to_csv(os.path.join(basepad, f"adr_{vandaag}_gewijzigd.csv"), index=False)
else:
    logging.warning("⚠️ Geen bestand van gisteren gevonden voor vergelijking.")

# Ophalen e-mails
alle_emails = []
try:
    conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
    cur = conn.cursor()
    cur.execute('"SELECT email FROM "user"')
    rows = cur.fetchall()
    alle_emails = [row[0] for row in rows if row[0]]
    cur.close()
    conn.close()
    logging.info(f"📧 Aantal gebruikers gevonden: {len(alle_emails)}")
except Exception as e:
    logging.error("❌ Fout bij ophalen van e-mailadressen uit de database.", exc_info=True)

# E-mail versturen
try:
    stuur_email_dashboard(
        df=df_result,
        dashboard_url="https://dashboardstocks-2.onrender.com",
        ontvanger_emails=alle_emails,
        afzender_email=os.getenv("SENDER_EMAIL"),
        smtp_server=os.getenv("SMTP_SERVER"),
        smtp_port=int(os.getenv("SMTP_PORT")),
        smtp_user=os.getenv("SMTP_USER"),
        smtp_pass=os.getenv("SMTP_PASS")
    )
    logging.info("📩 E-mail verzonden.")
except Exception as e:
    logging.error(f"❌ Fout bij verzenden e-mail: {e}", exc_info=True)
