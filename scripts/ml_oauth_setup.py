"""
Autorización OAuth inicial (una sola vez) para poder llamar a la API de
Mercado Libre con un access_token real.

Uso:
    python scripts/ml_oauth_setup.py

Te va a pedir tu CLIENT_ID y CLIENT_SECRET (los que te da Mercado Libre al
crear tu aplicación en developers.mercadolibre.com.mx/apps), construye la URL
de autorización, tú la abres, inicias sesión, aceptas, y pegas aquí el "code"
que queda en la URL a la que te redirige. Al final guarda ML_CLIENT_ID/
ML_CLIENT_SECRET/ML_REFRESH_TOKEN directo en tu archivo .env local (no los
imprime en pantalla, solo una versión enmascarada) para que copies esos 3
valores a GitHub Secrets sin riesgo de compartirlos por accidente.
"""
import re
import sys
import urllib.parse
from pathlib import Path

from src.ml_auth import MLAuthError, exchange_code_for_token
from src.ml_categories import fetch_categories

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

AUTH_BASE = "https://auth.mercadolibre.com.mx/authorization"
# No necesita ser un servidor real: httpbin.org/get simplemente muestra en
# pantalla los parámetros que recibió (a diferencia de google.com, que
# redirige y descarta el "code" antes de que lo puedas copiar).
DEFAULT_REDIRECT_URI = "https://httpbin.org/get"


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def _write_env(values: dict) -> None:
    """Escribe/actualiza claves en .env sin imprimir los valores en pantalla."""
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    keys_left = dict(values)

    for i, line in enumerate(lines):
        match = re.match(r"^([A-Z_][A-Z0-9_]*)=", line)
        if match and match.group(1) in keys_left:
            key = match.group(1)
            lines[i] = f"{key}={keys_left.pop(key)}"

    for key, value in keys_left.items():
        lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    print("=== Autorización OAuth de Mercado Libre ===\n")
    client_id = input("CLIENT_ID de tu aplicación: ").strip()
    client_secret = input("CLIENT_SECRET de tu aplicación: ").strip()
    redirect_uri = input(
        f"redirect_uri configurado en tu app [ENTER para usar {DEFAULT_REDIRECT_URI}]: "
    ).strip() or DEFAULT_REDIRECT_URI

    auth_url = (
        f"{AUTH_BASE}?response_type=code&client_id={urllib.parse.quote(client_id)}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
        # offline_access es obligatorio para que la respuesta incluya refresh_token
        f"&scope={urllib.parse.quote('offline_access read write')}"
    )

    print(f"\n1. Abre esta URL en tu navegador (logueado con tu cuenta de Mercado Libre):\n\n{auth_url}\n")
    print("2. Acepta los permisos.")
    print(
        f"3. Te va a redirigir a {redirect_uri} mostrando un JSON en pantalla.\n"
        "   Busca dentro de ese JSON la clave \"args\" -> \"code\" y copia SOLO ese valor.\n"
    )

    code = input("Pega aquí el code: ").strip()

    try:
        tokens = exchange_code_for_token(client_id, client_secret, code, redirect_uri)
    except MLAuthError as e:
        print(f"\nERROR: {e}")
        return 1

    print("\n=== Probando el access_token contra /sites/MLM/categories desde esta máquina ===")
    try:
        categories = fetch_categories("MLM", tokens["access_token"])
        print(f"OK: la API respondió {len(categories)} categorías. El token funciona desde aquí.")
    except Exception as e:
        print(f"FALLÓ la prueba: {e}")

    _write_env(
        {
            "ML_CLIENT_ID": client_id,
            "ML_CLIENT_SECRET": client_secret,
            "ML_REFRESH_TOKEN": tokens["refresh_token"],
        }
    )

    print(f"\n=== Listo. Guardado en {ENV_PATH} (no se imprime en pantalla) ===")
    print(f"ML_CLIENT_ID={_mask(client_id)}")
    print(f"ML_CLIENT_SECRET={_mask(client_secret)}")
    print(f"ML_REFRESH_TOKEN={_mask(tokens['refresh_token'])}")
    print(
        "\nAhora copia esos 3 valores de tu archivo .env a GitHub Secrets. Para verlos "
        "completos sin arriesgarte a compartirlos por accidente, ábrelos con un editor "
        "de texto local (nano .env / open -e .env), NO los imprimas en la Terminal con "
        "cat/echo ni los mandes por chat a nadie."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
