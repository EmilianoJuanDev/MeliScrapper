import os
import re
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st


# 🔧 limpiar precio
def clean_price(price_str):
    try:
        price_clean = price_str.replace('.', '').replace(',', '.')
        return float(price_clean)
    except:
        return None


def get_product_info(url):
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept-Language': 'es-ES,es;q=0.9',
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # título
    try:
        title = soup.find('h1', class_='ui-pdp-title').get_text(strip=True)
    except:
        title = 'No se encontró el título'

    # imagen
    try:
        img_tag = soup.find('img', class_='ui-pdp-image')
        image_url = img_tag.get('src') or img_tag.get('data-src')
    except:
        image_url = None

    # precio
    try:
        price = soup.find('span', class_='andes-money-amount__fraction').get_text(strip=True)
    except:
        price = None

    return title, image_url, price


def save_image(image_url, product_name):
    folder = "imagenes"
    os.makedirs(folder, exist_ok=True)

    valid_filename = re.sub(r'[<>:"/\\|?*]', '', product_name)[:10]
    filepath = os.path.join(folder, valid_filename + '.jpg')

    base, ext = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(filepath):
        filepath = f"{base}_{counter}{ext}"
        counter += 1

    response = requests.get(image_url, stream=True)
    if response.status_code == 200:
        with open(filepath, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        return filepath

    return None


def save_to_excel(data):
    df = pd.DataFrame(data)
    filename = "busquedas.xlsx"

    if os.path.exists(filename):
        existing_df = pd.read_excel(filename)
        df = pd.concat([existing_df, df], ignore_index=True)

    df.to_excel(filename, index=False)
    return filename


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


# 🚀 STREAMLIT
st.title("Producto Scraper de MercadoLibre")

search_query = st.text_input("Ingrese el nombre del producto:")

if search_query:
    st.write(f"Buscando productos para: {search_query}")
    product_urls = get_search_results(search_query)

    if product_urls:
        st.write(f"Encontrados {len(product_urls)} productos. Extrayendo información...")

        all_data = []

        for url in product_urls[:10]:
            title, image_url, price = get_product_info(url)

            if title != 'No se encontró el título' and price:
                data = {
                    'Fecha': datetime.now().strftime("%Y-%m-%d"),
                    'Titulo': title,
                    'Precio': clean_price(price),
                    'URL Imagen': image_url,
                    'URL Producto': url,
                }
                all_data.append(data)

                if image_url:
                    save_image(image_url, title)

        if all_data:
            df = pd.DataFrame(all_data)
            st.write("### Información de los Productos")
            st.dataframe(df)

            file_name = save_to_excel(all_data)
            st.success(f"Datos guardados en {file_name}")
        else:
            st.error("No se encontraron productos válidos.")
    else:
        st.error("No se encontraron resultados para tu búsqueda.")


#streamlit run MeLi_webscrapy.py

#python -m streamlit run MeLi_webscrapy.py si no se reconoce streamlit

#.venv\Scripts\activate si no sale .venv