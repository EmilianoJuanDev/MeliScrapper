from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_cambiar_luego'  # necesario para usar flash()

# ─────────────────────────────────────────
# BASE DE DATOS
# ─────────────────────────────────────────

def init_db():
    """Crea las tablas si no existen. Se llama una vez al iniciar la app."""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Historial de todas las búsquedas realizadas
    c.execute('''
        CREATE TABLE IF NOT EXISTS busquedas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            titulo TEXT,
            precio REAL,
            url TEXT
        )
    ''')

    # Productos que el usuario quiere monitorear
    c.execute('''
        CREATE TABLE IF NOT EXISTS monitoreados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            precio_original REAL,
            precio_actual REAL,
            url TEXT,
            email TEXT,
            umbral REAL,          -- % de descuento que dispara el mail
            fecha_agregado TEXT
        )
    ''')

    conn.commit()
    conn.close()


# ─────────────────────────────────────────
# SCRAPING (misma lógica de tu código original)
# ─────────────────────────────────────────

def clean_price(price_str):
    try:
        price_clean = price_str.replace('.', '').replace(',', '.')
        return float(price_clean)
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
# RUTAS
# ─────────────────────────────────────────

@app.route('/')
def index():
    """Página principal con el buscador."""
    return render_template('index.html')


@app.route('/buscar', methods=['POST'])
def buscar():
    """Recibe el formulario, hace el scraping y muestra resultados."""
    query = request.form.get('busqueda', '').strip()

    if not query:
        flash('Por favor ingresá un producto para buscar.')
        return redirect(url_for('index'))

    product_urls = get_search_results(query)

    if not product_urls:
        flash('No se encontraron resultados para tu búsqueda.')
        return redirect(url_for('index'))

    productos = []
    for url in product_urls[:10]:
        title, price = get_product_info(url)

        if title and price:
            precio_limpio = clean_price(price)
            producto = {
                'titulo': title,
                'precio': precio_limpio,
                'url': url,
                'fecha': datetime.now().strftime("%Y-%m-%d"),
            }
            productos.append(producto)

            # Guardar en historial
            conn = sqlite3.connect('database.db')
            conn.execute(
                'INSERT INTO busquedas (fecha, titulo, precio, url) VALUES (?, ?, ?, ?)',
                (producto['fecha'], title, precio_limpio, url)
            )
            conn.commit()
            conn.close()

    if not productos:
        flash('No se pudieron extraer datos de los productos encontrados.')
        return redirect(url_for('index'))

    return render_template('resultados.html', productos=productos, query=query)


@app.route('/monitorear', methods=['POST'])
def monitorear():
    """Guarda un producto para monitorear su precio."""
    titulo = request.form.get('titulo')
    precio = request.form.get('precio')
    url = request.form.get('url')
    email = request.form.get('email')
    umbral = request.form.get('umbral', 10)  # 10% de descuento por defecto

    conn = sqlite3.connect('database.db')
    conn.execute(
        '''INSERT INTO monitoreados 
        (titulo, precio_original, precio_actual, url, email, umbral, fecha_agregado)
        VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (titulo, float(precio), float(precio), url, email, float(umbral),
        datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()

    flash(f'✅ "{titulo[:40]}..." agregado al monitoreo. Te avisaremos a {email}.')
    return redirect(url_for('index'))


@app.route('/monitoreados')
def ver_monitoreados():
    """Muestra todos los productos que se están monitoreando."""
    conn = sqlite3.connect('database.db')
    productos = conn.execute('SELECT * FROM monitoreados').fetchall()
    conn.close()
    return render_template('monitoreados.html', productos=productos)


@app.route('/eliminar/<int:id>')
def eliminar(id):
    """Elimina un producto del monitoreo."""
    conn = sqlite3.connect('database.db')
    conn.execute('DELETE FROM monitoreados WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Producto eliminado del monitoreo.')
    return redirect(url_for('ver_monitoreados'))


# ─────────────────────────────────────────
# INICIO
# ─────────────────────────────────────────

if __name__ == '__main__':
    init_db()           # crea las tablas al iniciar
    app.run(debug=True) # debug=True → recarga automática al guardar cambios
                        # IMPORTANTE: cambiar a debug=False antes de subir a PythonAnywhere



#streamlit run MeLi_webscrapy.py

#python -m streamlit run MeLi_webscrapy.py si no se reconoce streamlit

#.venv\Scripts\activate si no sale .venv