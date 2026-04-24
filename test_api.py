import requests

# Paso 1: obtener token nuevo con client credentials
response = requests.post('https://api.mercadolibre.com/oauth/token', data={
    'grant_type': 'client_credentials',
    'client_id': '4000900854667787',
    'client_secret': 'uafeEgd9k69pX7jsgMjAuahdy9LArdun',
})

print("Token response:", response.json())
token = response.json().get('access_token')

# Paso 2: buscar con ese token
if token:
    r = requests.get(
        'https://api.mercadolibre.com/sites/MLA/search',
        params={'q': 'samsung galaxy s24', 'limit': 3},
        headers={'Authorization': f'Bearer {token}'}
    )
    print("Search status:", r.status_code)
    print("Search response:", r.json())