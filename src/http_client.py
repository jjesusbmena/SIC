"""
Cliente HTTP compartido para llamar a la API de Mercado Libre con el
access_token OAuth (ver src/ml_auth.py) — Mercado Libre exige Authorization
Bearer real en estos endpoints, ya no acepta llamadas anónimas.
"""
from typing import Optional

import requests


def get(url: str, access_token: str, params: Optional[dict] = None, timeout: int = 15) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    if not resp.ok:
        print(f"--- Respuesta de error de {url} ---")
        print(f"Status: {resp.status_code}")
        print(f"Body (primeros 2000 chars): {resp.text[:2000]}")
        print("--- fin respuesta de error ---")
    resp.raise_for_status()
    return resp
