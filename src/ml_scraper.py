"""
Scraper de la página pública de ofertas de Mercado Libre con Playwright.

Por qué scraping y no la API: desde abril de 2025 Mercado Libre bloquea las
búsquedas de catálogo de terceros vía API (/sites/{site}/search) incluso con
un access_token OAuth válido — solo deja ver los productos de la cuenta que
autorizó la app. La página pública de ofertas (mercadolibre.com.mx/ofertas)
sigue siendo visible para cualquier visitante normal, así que la leemos como
lo haría un navegador.

AVISO: esto es más frágil que una API — Mercado Libre puede cambiar el HTML
de esta página en cualquier momento, y en teoría podría bloquear scraping
agresivo. Los localizadores de abajo se basan en clases documentadas en
tutoriales públicos de scraping de Mercado Libre (ui-search-result,
andes-money-amount), pero no están garantizadas. Si dejan de funcionar, corre:

    python -m src.ml_scraper --debug

para abrir el navegador visible e inspeccionar la página real.
"""
import argparse
import re
from dataclasses import dataclass
from typing import Optional

from playwright.sync_api import sync_playwright

OFERTAS_URL = "https://www.mercadolibre.com.mx/ofertas"

CARD_SELECTORS = [
    "div.poly-card",
    "li.ui-search-layout__item",
    "div.ui-search-result__content-wrapper",
]


@dataclass
class Offer:
    item_id: str
    title: str
    price: float
    original_price: Optional[float]
    discount_pct: float
    sold_quantity: int
    permalink: str
    thumbnail: str
    category_name: str

    @property
    def score(self) -> float:
        return self.discount_pct


def _extract_item_id(url: str) -> str:
    match = re.search(r"(MLM-?\d{8,})", url)
    if match:
        return match.group(1).replace("-", "")
    return url


def _parse_money(text: str) -> Optional[float]:
    digits = re.sub(r"[^\d]", "", text or "")
    return float(digits) if digits else None


def _extract_offer_from_card(card, min_discount_pct: float) -> Optional[Offer]:
    link_el = card.query_selector("a[href]")
    if not link_el:
        return None
    permalink = link_el.get_attribute("href") or ""

    title_el = card.query_selector("h2, h3, [class*='title']")
    title = title_el.inner_text().strip() if title_el else ""

    money_els = card.query_selector_all(".andes-money-amount__fraction")
    if not money_els:
        return None

    prices = [_parse_money(el.inner_text()) for el in money_els]
    prices = [p for p in prices if p]
    if not prices:
        return None

    if len(prices) >= 2:
        price, original_price = min(prices), max(prices)
    else:
        price, original_price = prices[0], None

    if not original_price or original_price <= price:
        return None

    discount_pct = round((original_price - price) / original_price * 100, 1)
    if discount_pct < min_discount_pct:
        return None

    thumbnail_el = card.query_selector("img")
    thumbnail = (
        thumbnail_el.get_attribute("src") or thumbnail_el.get_attribute("data-src") or ""
    ) if thumbnail_el else ""

    return Offer(
        item_id=_extract_item_id(permalink),
        title=title,
        price=price,
        original_price=original_price,
        discount_pct=discount_pct,
        sold_quantity=0,
        permalink=permalink,
        thumbnail=thumbnail,
        category_name="Ofertas",
    )


def scrape_top_offers(min_discount_pct: float, top_n: int, headless: bool = True) -> list[Offer]:
    offers = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))
        page.goto(OFERTAS_URL, wait_until="networkidle", timeout=30000)

        cards = []
        for selector in CARD_SELECTORS:
            cards = page.query_selector_all(selector)
            if cards:
                break

        if not cards:
            browser.close()
            raise RuntimeError(
                "No se encontraron tarjetas de oferta con los selectores conocidos. "
                "Mercado Libre pudo haber cambiado el HTML de la página. Corre "
                "'python -m src.ml_scraper --debug' para inspeccionarla."
            )

        for card in cards:
            offer = _extract_offer_from_card(card, min_discount_pct)
            if offer:
                offers.append(offer)

        browser.close()

    offers.sort(key=lambda o: o.score, reverse=True)
    return offers[:top_n]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="corre con navegador visible")
    parser.add_argument("--min-discount", type=float, default=20)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    offers = scrape_top_offers(args.min_discount, args.top, headless=not args.debug)
    for o in offers:
        print(f"-{o.discount_pct:.0f}% ${o.price:.0f} (antes ${o.original_price:.0f}) - {o.title}")
        print(f"  {o.permalink}")


if __name__ == "__main__":
    main()
