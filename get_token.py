import requests

response = requests.post('https://api.mercadolibre.com/oauth/token', data={
    'grant_type': 'authorization_code',
    'client_id': '4000900854667787',
    'client_secret': 'uafeEgd9k69pX7jsgMjAuahdy9LArdun',
    'code': 'TG-69eaaa08d244e0000137a14f-1056371703',
    'redirect_uri': 'https://meli-tracker.onrender.com'
})

print(response.json())