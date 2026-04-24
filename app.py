from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import psycopg2
import os

app = Flask(__name__)
app.secret_key = 'meli_tracker_2026_emi'


# ─────────────────────────────────────────
# CONEXIÓN A BASE DE DATOS
# ─────────────────────────────────────────

def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def init_db():
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS resultados (
            id              SERIAL PRIMARY KEY,
            query           TEXT,
            titulo          TEXT,
            precio          REAL,
            url             TEXT,
            fecha_escaneo   TEXT
        )
    ''')
    conn.commit()
    conn.close()


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

    # Verificar si ya hay resultados guardados para esta búsqueda
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        'SELECT * FROM resultados WHERE query = %s ORDER BY fecha_escaneo DESC LIMIT 9',
        (query,)
    )
    productos = c.fetchall()
    conn.close()

    if productos:
        # Hay resultados guardados — mostrarlos directamente
        productos_dict = [{
            'titulo': p[2],
            'precio': p[3],
            'url':    p[4],
            'imagen': None,
        } for p in productos]
        return render_template('resultados.html', productos=productos_dict, query=query, email=email)
    else:
        # No hay resultados aún — guardar búsqueda y avisar al usuario
        if email:
            conn = get_conn()
            c = conn.cursor()
            # Verificar que no esté ya guardada
            c.execute('SELECT id FROM monitoreados WHERE query = %s AND email = %s', (query, email))
            existe = c.fetchone()
            if not existe:
                c.execute(
                    'INSERT INTO monitoreados (query, email, precio_minimo, fecha_agregado) VALUES (%s, %s, %s, %s)',
                    (query, email, 0, datetime.now().strftime("%Y-%m-%d %H:%M"))
                )
                conn.commit()
            conn.close()
            flash(f'✅ Búsqueda "{query}" guardada. Los resultados estarán disponibles mañana cuando se ejecute el escaneo automático.')
        else:
            flash(f'No hay resultados para "{query}" todavía. Ingresá tu email para que te avisemos cuando estén disponibles.')

        return redirect(url_for('index'))


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
    c.execute('SELECT id FROM monitoreados WHERE query = %s AND email = %s', (query, email))
    existe = c.fetchone()
    if not existe:
        c.execute(
            'INSERT INTO monitoreados (query, email, precio_minimo, fecha_agregado) VALUES (%s, %s, %s, %s)',
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
