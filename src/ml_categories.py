"""
Resuelve nombres de categoría configurados en settings.yaml contra los IDs reales
que expone la API pública de Mercado Libre: GET /sites/{site_id}/categories

No se hardcodean category_id porque cambian por sitio y no están documentados
de forma estable; se resuelven por nombre en cada corrida.
"""
import unicodedata

from src.http_client import get as http_get

API_BASE = "https://api.mercadolibre.com"


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return text


def fetch_categories(site_id: str) -> list[dict]:
    resp = http_get(f"{API_BASE}/sites/{site_id}/categories")
    return resp.json()


def resolve_category_ids(site_id: str, names: list[str]) -> dict[str, str]:
    """Devuelve {nombre_configurado: category_id}. Lanza si algún nombre no matchea."""
    categories = fetch_categories(site_id)
    by_norm_name = {_normalize(c["name"]): c["id"] for c in categories}

    resolved = {}
    unmatched = []
    for name in names:
        norm = _normalize(name)
        if norm in by_norm_name:
            resolved[name] = by_norm_name[norm]
        else:
            unmatched.append(name)

    if unmatched:
        available = ", ".join(sorted(c["name"] for c in categories))
        raise ValueError(
            f"No se encontraron estas categorías en /sites/{site_id}/categories: "
            f"{unmatched}. Categorías disponibles: {available}"
        )
    return resolved
