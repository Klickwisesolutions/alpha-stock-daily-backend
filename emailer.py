# emailer.py

import smtplib
from email.message import EmailMessage
from datetime import datetime
import pandas as pd

# emailer.py

import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from datetime import datetime
import pandas as pd

def stuur_email_dashboard(df, dashboard_url, ontvanger_emails, afzender_email, smtp_server, smtp_port, smtp_user, smtp_pass):
    datum = datetime.today().strftime("%Y-%m-%d")
    onderwerp = f"📈 ADR Dashboard – Samenvatting {datum}"

    # ➕ Filter en sorteer topresultaten
    df_filtered = df.copy()
    df_filtered['Recommendation'] = df_filtered['Recommendation'].str.lower().fillna("")
    df_filtered['Analyst Opinions'] = pd.to_numeric(df_filtered['Analyst Opinions'], errors='coerce').fillna(0)
    df_filtered['Upside (%)'] = pd.to_numeric(df_filtered['Upside (%)'], errors='coerce').fillna(0)

    df_top = df_filtered[
        (df_filtered['Recommendation'].isin(['strong_buy', 'buy'])) &
        (df_filtered['Analyst Opinions'] >= 3) &
        (df_filtered['Upside (%)'] >= 20)
    ]

    df_top = df_top.sort_values(by=['Analyst Opinions', 'Upside (%)'], ascending=[False, False])
    kolommen = ['Ticker', 'Name', 'Recommendation', 'Upside (%)', 'Analyst Opinions']
    df_kort = df_top[kolommen].head(10).fillna("-")

    if df_kort.empty:
        tabel_html = "<p><em>Geen aanbevelingen vandaag die aan de criteria voldoen.</em></p>"
    else:
        tabel_html = df_kort.to_html(index=False, border=0, classes="adr-table")

    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .adr-table {{
                border-collapse: collapse;
                width: 100%;
            }}
            .adr-table th, .adr-table td {{
                border: 1px solid #dddddd;
                text-align: left;
                padding: 8px;
            }}
            .adr-table th {{
                background-color: #4CAF50;
                color: white;
            }}
            .adr-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h2>📈 ADR Samenvatting – {datum}</h2>
        {tabel_html}
        <p>🔗 <a href="{dashboard_url}" target="_blank">Bekijk het volledige dashboard</a></p>
        <br>
        <p style="font-size: small; color: gray;">Automatisch verzonden door ADR Bot – geen actie vereist.</p>
    </body>
    </html>
    """

    # Verstuur naar elke ontvanger afzonderlijk
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(smtp_user, smtp_pass)
        for ontvanger in ontvanger_emails:
            msg = EmailMessage()
            msg['Subject'] = onderwerp
            msg['From'] = formataddr(("ADR Bot", afzender_email))
            msg['To'] = ontvanger
            msg.set_content("Bekijk deze e-mail in HTML.")
            msg.add_alternative(html_body, subtype='html')
            server.send_message(msg)
            print(f"✅ HTML-mail verzonden naar {ontvanger}")
