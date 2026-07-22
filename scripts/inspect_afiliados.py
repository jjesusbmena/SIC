"""
Abre el portal de Afiliados con la sesión ya guardada y se queda esperando
para que puedas inspeccionar la página real (dónde está el campo de URL, el
botón de generar link, etc.) antes de ajustar los localizadores en
src/affiliate.py.

Uso:
    python scripts/inspect_afiliados.py "https://articulo.mercadolibre.com.mx/..."
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
STORAGE_STATE_PATH = ROOT_DIR / "storage_state.json"
GENERATOR_URL = "https://www.mercadolibre.com.mx/l/afiliados-central-de-afiliados"


def main():
    product_url = sys.argv[1] if len(sys.argv) > 1 else None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context(storage_state=str(STORAGE_STATE_PATH), permissions=["camera"])
        page = context.new_page()
        page.goto(GENERATOR_URL, wait_until="networkidle")

        print("\nPágina cargada. Mira el navegador e inspecciona dónde está:")
        print("  1. El campo para pegar la URL del producto a convertir.")
        print("  2. El botón para generar el link.")
        if product_url:
            print(f"\nURL de producto para probar manualmente: {product_url}")
        print(
            "\nSi quieres ver el HTML exacto de un elemento: clic derecho -> Inspeccionar."
        )
        input("\nPresiona ENTER aquí cuando ya hayas visto todo lo que necesitas... ")

        browser.close()


if __name__ == "__main__":
    sys.exit(main())
