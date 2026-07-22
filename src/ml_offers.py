"""
Busca ofertas por categoría en la API pública de Mercado Libre:
GET /sites/{site_id}/search?category={id}

Fuente de datos: endpoint público de Items & Searches de Mercado Libre.
Nota importante: los campos "original_price" (precio de referencia) y
"sold_quantity" son los que expone hoy el buscador público; si un item no
trae "original_price" simplemente no se lo considera oferta (no se inventa
un descuento). Este script no usa el endpoint /trends (requiere OAuth con
autorización de usuario); en su lugar aproxima "tendencia" combinando
% de descuento real con sold_quantity, ambos datos reales devueltos por la API.
"""
from dataclasses import dataclass
from typing import Optional

from src.http_client import get as http_get

API_BASE = "https://api.mercadolibre.com"


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
        # Ranking simple y explicable: descuento real + peso por popularidad (ventas).
        return self.discount_pct + min(self.sold_quantity, 5000) / 100.0


def _search_category(site_id: str, access_token: str, category_id: str, limit: int) -> list[dict]:
    params = {"category": category_id, "limit": min(limit, 50)}
    resp = http_get(f"{API_BASE}/sites/{site_id}/search", access_token, params=params)
    return resp.json().get("results", [])


def get_top_offers_for_category(
    site_id: str,
    access_token: str,
    category_name: str,
    category_id: str,
    items_to_scan: int,
    min_discount_pct: float,
    top_n: int,
) -> list[Offer]:
    raw_items = _search_category(site_id, access_token, category_id, items_to_scan)

    offers = []
    for item in raw_items:
        price = item.get("price")
        original_price = item.get("original_price")
        if not price or not original_price or original_price <= price:
            continue  # sin descuento real verificable, se descarta

        discount_pct = round((original_price - price) / original_price * 100, 1)
        if discount_pct < min_discount_pct:
            continue

        offers.append(
            Offer(
                item_id=item.get("id", ""),
                title=item.get("title", ""),
                price=price,
                original_price=original_price,
                discount_pct=discount_pct,
                sold_quantity=item.get("sold_quantity") or 0,
                permalink=item.get("permalink", ""),
                thumbnail=item.get("thumbnail", ""),
                category_name=category_name,
            )
        )

    offers.sort(key=lambda o: o.score, reverse=True)
    return offers[:top_n]
