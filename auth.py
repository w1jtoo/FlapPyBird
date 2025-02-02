import logging
import json
import requests
import jwt
from threading import Thread


AUTH_URL = "https://identity.testkontur.ru/connect/deviceauthorization"
TOCKEN_URL = "https://identity.testkontur.ru/connect/token"
API_KEY = "e8b2d06f-51d4-2b46-2af9-ac096ae67d96"
CLIENT_NAME = "portal_flappy_bird"

DEVICE_CODE = None
AUTH_META = None
IS_AUTHORIZED = False

def init_logging() -> None:
    logging.basicConfig(level=logging.DEBUG)

def build_auth_url() -> str:
    global DEVICE_CODE

    req = requests.post(
        AUTH_URL,
        data={
            "client_id": CLIENT_NAME,
            "client_secret": API_KEY,
            "scope": "openid profile email",
        },
        timeout=10
    )

    if req.status_code != 200:
        raise Exception(f"OIDC is unavailable, got {req.status_code} status code")

    json_content = json.loads(req.text)
    DEVICE_CODE = json_content["device_code"]

    return json_content["verification_uri_complete"]


def check_auth() -> None:
    if DEVICE_CODE is None:
        return
    thread = Thread(target = _check_auth)
    thread.start()

def _check_auth() -> None:
    global AUTH_META, IS_AUTHORIZED

    if DEVICE_CODE is None:
        raise Exception("DEVICE_CODE is None")

    req = requests.post(
        TOCKEN_URL,
        data={
            "client_id": CLIENT_NAME,
            "client_secret": API_KEY,
            "scope": "openid profile email",
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": DEVICE_CODE,
        },
        timeout=10
    )

    json_content = json.loads(req.text)

    if req.status_code == 200:
        encoded = json_content["id_token"]
        decoded = jwt.decode(encoded, options={"verify_signature": False})

        AUTH_META = decoded
        IS_AUTHORIZED = True
        return

    if req.status_code == 400:
        return

    raise Exception(f"OIDC is unavailable, got {req.status_code} status code")


def is_authorized() -> None:
    return IS_AUTHORIZED

def logout() -> None:
    global AUTH_META, IS_AUTHORIZED
    IS_AUTHORIZED = False

def get_auth_meta() -> dict:
    return (AUTH_META["name"], AUTH_META["picture"])
