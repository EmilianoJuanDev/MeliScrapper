from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import psycopg2
import os

app = Flask(__name__)
app.secret_key = 'meli_tracker_2026_emi'

# ─────────────────────────────────────────
# CONEXIÓN A BASE DE DATOS
# ─────────────────────────────────────────

def get_conn():
    """Retorna una conexión a Supabase usando la variable de entorno DATABASE_URL."""
    return psycopg2.connect(os.environ['DATABASE_URL'])


def init_db():
    """Crea las tablas si no existen. Se llama una vez al iniciar la app."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS monitoreados (
            id              SERIAL PRIMARY KEY,
            query           TEXT,
            email           TEXT,
            precio_minimo   REAL,
            fecha_agregado  TEXT
        )
    ''')
    conn.commit()
    conn.close()


# ─────────────────────────────────────────
# SCRAPING
# ─────────────────────────────────────────

def clean_price(price_str):
    try:
        return float(price_str.replace('.', '').replace(',', '.'))
    except:
        return None


def get_search_results(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-AR,es;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
    }
    url = f"https://listado.mercadolibre.com.ar/{query}"
    response = requests.get(url, headers=headers, timeout=10)
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

    try:
        img_tag = soup.find('img', class_='ui-pdp-image')
        image_url = img_tag.get('src') or img_tag.get('data-src')
    except:
        image_url = None

    return title, price, image_url


# ─────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/buscar', methods=['POST'])
def buscar():
    query = request.form.get('busqueda', '').strip()
    email = request.form.get('email', '').strip()

    if not query:
        flash('Por favor ingresá un producto para buscar.')
        return redirect(url_for('index'))

    product_urls = get_search_results(query)

    if not product_urls:
        flash('No se encontraron resultados para tu búsqueda.')
        return redirect(url_for('index'))

    productos = []
    for url in product_urls[:9]:
        title, price, image_url = get_product_info(url)
        if title and price:
            productos.append({
                'titulo': title,
                'precio': clean_price(price),
                'imagen': image_url,
                'url':    url,
            })

    if not productos:
        flash('No se pudieron extraer datos de los productos encontrados.')
        return redirect(url_for('index'))

    return render_template('resultados.html', productos=productos, query=query, email=email)


@app.route('/guardar-busqueda', methods=['POST'])
def guardar_busqueda():
    query         = request.form.get('query')
    email         = request.form.get('email')
    precio_minimo = request.form.get('precio_minimo')

    if not email:
        flash('Ingresá un email para poder enviarte alertas.')
        return redirect(url_for('index'))

    conn = get_conn()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO monitoreados (query, email, precio_minimo, fecha_agregado)
        VALUES (%s, %s, %s, %s)''',
        (query, email, float(precio_minimo), datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()

    flash(f'✅ Búsqueda "{query}" guardada. Te avisaremos a {email} cuando el precio baje.')
    return redirect(url_for('index'))


@app.route('/monitoreados', methods=['GET', 'POST'])
def ver_monitoreados():
    email_filtro = None
    monitoreados = []

    if request.method == 'POST':
        email_filtro = request.form.get('email', '').strip()
        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT * FROM monitoreados WHERE email = %s', (email_filtro,))
        monitoreados = c.fetchall()
        conn.close()

    return render_template('monitoreados.html', monitoreados=monitoreados, email_filtro=email_filtro)



@app.route('/eliminar/<int:id>')
def eliminar(id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM monitoreados WHERE id = %s', (id,))
    conn.commit()
    conn.close()
    flash('Búsqueda eliminada del monitoreo.')
    return redirect(url_for('ver_monitoreados'))


# ─────────────────────────────────────────
# INICIO
# ─────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
