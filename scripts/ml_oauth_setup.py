"""
Autorización OAuth inicial (una sola vez) para poder llamar a la API de
Mercado Libre con un access_token real.

Uso:
    python scripts/ml_oauth_setup.py

Te va a pedir tu CLIENT_ID y CLIENT_SECRET (los que te da Mercado Libre al
crear tu aplicación en developers.mercadolibre.com.mx/apps), construye la URL
de autorización, tú la abres, inicias sesión, aceptas, y pegas aquí el "code"
que queda en la URL a la que te redirige. Al final imprime el
ACCESS_TOKEN/REFRESH_TOKEN para que los guardes como GitHub Secrets.
"""
import sys
import urllib.parse

from src.ml_auth import MLAuthError, exchange_code_for_token

AUTH_BASE = "https://auth.mercadolibre.com.mx/authorization"
# No necesita ser un servidor real: solo vamos a leer el "code" de la URL
# resultante en la barra de direcciones del navegador.
DEFAULT_REDIRECT_URI = "https://www.google.com.mx"


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
    )

    print(f"\n1. Abre esta URL en tu navegador (logueado con tu cuenta de Mercado Libre):\n\n{auth_url}\n")
    print("2. Acepta los permisos.")
    print(
        f"3. Te va a redirigir a algo como {redirect_uri}/?code=TG-XXXXXXXX...\n"
        "   Copia SOLO el valor después de 'code=' (y antes de cualquier '&' si hay más parámetros).\n"
    )

    code = input("Pega aquí el code: ").strip()

    try:
        tokens = exchange_code_for_token(client_id, client_secret, code, redirect_uri)
    except MLAuthError as e:
        print(f"\nERROR: {e}")
        return 1

    print("\n=== Listo. Guarda estos 3 valores como GitHub Secrets ===")
    print(f"ML_CLIENT_ID={client_id}")
    print(f"ML_CLIENT_SECRET={client_secret}")
    print(f"ML_REFRESH_TOKEN={tokens['refresh_token']}")
    print(
        "\n(El access_token no se guarda, el workflow lo obtiene solo con estos "
        "3 valores cada vez que corre.)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
