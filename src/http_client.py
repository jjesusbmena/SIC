"""
Cliente HTTP compartido para llamar a la API pública de Mercado Libre.

Se agrega un User-Agent de navegador real porque la API rechaza (403) el
User-Agent genérico por defecto de la librería requests
("python-requests/x.y.z"), típico de protecciones anti-bot.
"""
import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def get(url: str, params: dict | None = None, timeout: int = 15) -> requests.Response:
    resp = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp
