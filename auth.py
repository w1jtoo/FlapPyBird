import requests
import json

authorize_url = "https://identity.testkontur.ru/connect/deviceauthorization"
api_key = "e8b2d06f-51d4-2b46-2af9-ac096ae67d96"
client_name = "portal_flappy_bird"


def build_auth_url():
    req = requests.post(
        authorize_url,
        data={
            "client_id": client_name,
            "client_secret": api_key,
            "scope": "openid profile email",
        },
    )
    return json.loads(req.text)["verification_uri_complete"]
