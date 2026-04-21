import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────
# CONFIGURACIÓN — completá estos datos
# ─────────────────────────────────────────

GMAIL_USUARIO  = "emijuxxx@gmail.com"       # tu cuenta de Gmail
GMAIL_PASSWORD = "rqkb otaf scbr xuqd"      # contraseña de aplicación (16 caracteres)


# ─────────────────────────────────────────
# SCRAPING (igual que en app.py)
# ─────────────────────────────────────────

def clean_price(price_str):
    try:
        return float(price_str.replace('.', '').replace(',', '.'))
    except:
        return None


def get_search_results(query):
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept-Language': 'es-ES,es;q=0.9',
    }
    url = f"https://listado.mercadolibre.com.ar/{query}"
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    product_links = []
    for link in soup.find_all('a', class_='poly-component__title', href=True):
        product_links.append(link['href'])

    return product_links


def get_product_info(url):
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept-Language': 'es-ES,es;q=0.9',
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    try:
        title = soup.find('h1', class_='ui-pdp-title').get_text(strip=True)
    except:
        title = None

    try:
        price = soup.find('span', class_='andes-money-amount__fraction').get_text(strip=True)
    except:
        price = None

    return title, price


# ─────────────────────────────────────────
# MAIL
# ─────────────────────────────────────────

def enviar_mail(destinatario, query, productos_bajaron):
    """
    Manda un mail con la lista de productos que bajaron de precio.
    productos_bajaron: lista de dicts con titulo, precio_anterior, precio_nuevo, url
    """

    asunto = f"📉 Bajaron precios para: {query}"

    # Armar el cuerpo del mail en HTML
    filas = ""
    for p in productos_bajaron:
        diferencia  = p['precio_anterior'] - p['precio_nuevo']
        porcentaje  = (diferencia / p['precio_anterior']) * 100
        filas += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #2a2a2a;">
                <a href="{p['url']}" style="color: #f0c040; text-decoration: none;">
                    {p['titulo'][:70]}
                </a>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2a2a2a; color: #888; text-decoration: line-through;">
                ${p['precio_anterior']:,.0f}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2a2a2a; color: #4caf7d; font-weight: bold;">
                ${p['precio_nuevo']:,.0f}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #2a2a2a; color: #4caf7d;">
                -{porcentaje:.1f}%
            </td>
        </tr>
        """

    cuerpo_html = f"""
    <html>
    <body style="background: #0e0e0e; color: #f0ede6; font-family: sans-serif; padding: 32px;">

        <h2 style="color: #f0c040; margin-bottom: 8px;">📉 Bajaron precios</h2>
        <p style="color: #888; margin-bottom: 24px;">
            Búsqueda: <strong style="color: #f0ede6;">{query}</strong><br>
            Escaneo: {datetime.now().strftime("%d/%m/%Y %H:%M")}
        </p>

        <table style="width: 100%; border-collapse: collapse; background: #161616; border-radius: 8px; overflow: hidden;">
            <thead>
                <tr style="background: #1d1d1d;">
                    <th style="padding: 12px; text-align: left; color: #888; font-size: 12px; text-transform: uppercase;">Producto</th>
                    <th style="padding: 12px; text-align: left; color: #888; font-size: 12px; text-transform: uppercase;">Antes</th>
                    <th style="padding: 12px; text-align: left; color: #888; font-size: 12px; text-transform: uppercase;">Ahora</th>
                    <th style="padding: 12px; text-align: left; color: #888; font-size: 12px; text-transform: uppercase;">Baja</th>
                </tr>
            </thead>
            <tbody>
                {filas}
            </tbody>
        </table>

        <p style="color: #888; font-size: 12px; margin-top: 24px;">
            Este mail fue enviado automáticamente por MeLi Tracker.
        </p>

    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg['Subject'] = asunto
    msg['From']    = GMAIL_USUARIO
    msg['To']      = destinatario
    msg.attach(MIMEText(cuerpo_html, "html"))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USUARIO, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USUARIO, destinatario, msg.as_string())
        print(f"  ✅ Mail enviado a {destinatario}")
    except Exception as e:
        print(f"  ❌ Error al enviar mail a {destinatario}: {e}")


# ─────────────────────────────────────────
# ESCANEO PRINCIPAL
# ─────────────────────────────────────────

def escanear():
    print(f"\n{'='*50}")
    print(f"Escaneo iniciado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}")

    conn = sqlite3.connect('database.db')
    monitoreados = conn.execute('SELECT * FROM monitoreados').fetchall()
    conn.close()

    if not monitoreados:
        print("No hay búsquedas monitoreadas.")
        return

    for registro in monitoreados:
        id_registro    = registro[0]
        query          = registro[1]
        email          = registro[2]
        precio_minimo  = registro[3]   # el precio mínimo del último escaneo

        print(f"\n🔍 Buscando: '{query}' (mínimo guardado: ${precio_minimo:,.0f})")

        # Buscar los productos actuales
        urls = get_search_results(query)
        if not urls:
            print("  Sin resultados.")
            continue

        productos_bajaron = []
        nuevo_minimo      = precio_minimo   # vamos a actualizar si hay cambios

        for url in urls[:9]:
            title, price = get_product_info(url)
            if not title or not price:
                continue

            precio_actual = clean_price(price)
            if not precio_actual:
                continue

            # ¿Este producto bajó respecto al mínimo guardado?
            if precio_actual < precio_minimo:
                print(f"  📉 Bajó: {title[:50]} → ${precio_actual:,.0f} (antes ${precio_minimo:,.0f})")
                productos_bajaron.append({
                    'titulo':          title,
                    'precio_anterior': precio_minimo,
                    'precio_nuevo':    precio_actual,
                    'url':             url,
                })
                # Actualizamos el nuevo mínimo si encontramos uno menor
                if precio_actual < nuevo_minimo:
                    nuevo_minimo = precio_actual

        # Si hubo bajadas → mandar mail
        if productos_bajaron:
            enviar_mail(email, query, productos_bajaron)

            # Actualizar el precio mínimo en la base de datos
            conn = sqlite3.connect('database.db')
            conn.execute(
                'UPDATE monitoreados SET precio_minimo = ? WHERE id = ?',
                (nuevo_minimo, id_registro)
            )
            conn.commit()
            conn.close()
            print(f"  💾 Precio mínimo actualizado a ${nuevo_minimo:,.0f}")
        else:
            print(f"  ✔ Sin cambios de precio.")

    print(f"\nEscaneo finalizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")


# ─────────────────────────────────────────
# EJECUCIÓN
# ─────────────────────────────────────────

if __name__ == '__main__':
    escanear()
