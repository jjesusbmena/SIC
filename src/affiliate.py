"""
Genera links de afiliado usando el generador de links del portal de
Mercado Libre Afiliados, reutilizando la sesión guardada por
scripts/login_afiliados.py (storage_state.json).

AVISO IMPORTANTE: el portal de afiliados es una interfaz web, no una API
documentada públicamente, así que no existen "selectores oficiales" que se
puedan citar con una fuente. Los localizadores de abajo usan texto/roles
(más resistentes a cambios de diseño que clases CSS), pero Mercado Libre
puede modificar su UI en cualquier momento. Si algo falla:

    python -m src.affiliate --debug "https://articulo.mercadolibre.com.mx/..."

corre en modo visible (headed) y detiene la ejecución con pdb-like pausa
para que inspecciones la página real y ajustes los localizadores.
"""
import argparse
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

ROOT_DIR = Path(__file__).resolve().parent.parent
STORAGE_STATE_PATH = ROOT_DIR / "storage_state.json"
GENERATOR_URL = "https://www.mercadolibre.com.mx/l/afiliados-central-de-afiliados"


class AffiliateLinkError(RuntimeError):
    pass


def generate_affiliate_link(product_url: str, headless: bool = True) -> str:
    if not STORAGE_STATE_PATH.exists():
        raise AffiliateLinkError(
            "No existe storage_state.json. Corre primero: python scripts/login_afiliados.py"
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=str(STORAGE_STATE_PATH))
        page = context.new_page()

        try:
            page.goto(GENERATOR_URL, wait_until="networkidle")

            # Campo donde se pega la URL del producto a convertir.
            url_input = page.get_by_placeholder(re.compile("link|url", re.I)).first
            url_input.wait_for(timeout=10000)
            url_input.fill(product_url)

            generate_button = page.get_by_role(
                "button", name=re.compile("generar", re.I)
            ).first
            generate_button.click()

            result_field = page.get_by_text(
                re.compile(r"mercadolibre\.com/sec/|mercadolibre\.com\.mx/social/")
            ).first
            result_field.wait_for(timeout=15000)
            affiliate_link = result_field.inner_text().strip()

            if not affiliate_link:
                raise AffiliateLinkError("El portal no devolvió un link de afiliado.")

            return affiliate_link

        except PWTimeoutError as e:
            raise AffiliateLinkError(
                "No se encontró el generador de links con los localizadores actuales. "
                "Es probable que Mercado Libre haya cambiado la UI del portal. "
                "Vuelve a correr esto con --debug para inspeccionar la página y "
                "ajustar los localizadores en src/affiliate.py."
            ) from e
        finally:
            context.storage_state(path=str(STORAGE_STATE_PATH))
            browser.close()


def main():
    parser = argparse.ArgumentParser(description="Genera un link de afiliado de Mercado Libre")
    parser.add_argument("product_url")
    parser.add_argument("--debug", action="store_true", help="corre con navegador visible")
    args = parser.parse_args()

    link = generate_affiliate_link(args.product_url, headless=not args.debug)
    print(link)


if __name__ == "__main__":
    sys.exit(main())
