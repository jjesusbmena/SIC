"""
Login manual, de una sola vez, al portal de Afiliados de Mercado Libre.

Por qué es manual: el login de Mercado Libre puede pedir verificación en dos
pasos o captcha, y no hay una API pública documentada para el generador de
links del portal de afiliados (es una funcionalidad web, no un endpoint de
developers.mercadolibre.com). Este script abre un navegador real para que
tú inicies sesión con tus ojos y tus manos; luego guarda la sesión
(cookies) en storage_state.json para que el resto de la automatización
(src/affiliate.py) la reutilice sin volver a pedirte credenciales cada vez.

Uso:
    python scripts/login_afiliados.py

La sesión guardada expira eventualmente (Mercado Libre la invalida por
tiempo o cambio de contraseña); si src/affiliate.py falla con un login
inválido, vuelve a correr este script.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
STORAGE_STATE_PATH = ROOT_DIR / "storage_state.json"
LOGIN_URL = "https://www.mercadolibre.com.mx/l/afiliados-central-de-afiliados"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(LOGIN_URL)

        print(
            "\nSe abrió el navegador. Inicia sesión con tu cuenta de Mercado Libre "
            "(incluyendo cualquier verificación en dos pasos) hasta que veas la "
            "Central de Afiliados cargada.\n"
        )
        input("Cuando ya estés dentro, regresa aquí y presiona ENTER para guardar la sesión... ")

        context.storage_state(path=str(STORAGE_STATE_PATH))
        print(f"Sesión guardada en {STORAGE_STATE_PATH}")

        browser.close()


if __name__ == "__main__":
    sys.exit(main())
