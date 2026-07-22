"""
Orquestador: categorías configuradas -> ofertas reales de Mercado Libre ->
link de afiliado -> publicación en Telegram.

Uso:
    python -m src.main            # busca, genera links y publica
    python -m src.main --dry-run  # solo muestra qué publicaría, no llama a Telegram/Playwright
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import Env, ROOT_DIR, load_settings
from src.ml_auth import MLAuthError, refresh_access_token
from src.ml_categories import resolve_category_ids
from src.ml_offers import get_top_offers_for_category


def _load_posted_items(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_posted_items(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _prune_old(posted: dict, window_days: int) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    return {
        item_id: ts
        for item_id, ts in posted.items()
        if datetime.fromisoformat(ts) > cutoff
    }


def get_ml_access_token() -> str:
    """Refresca el access_token de ML y rota el refresh_token (de un solo uso)."""
    try:
        tokens = refresh_access_token(
            Env.ML_CLIENT_ID, Env.ML_CLIENT_SECRET, Env.ML_REFRESH_TOKEN
        )
    except MLAuthError as e:
        raise RuntimeError(
            f"No se pudo obtener un access_token de Mercado Libre: {e}\n"
            "Si el error menciona un refresh_token inválido/usado, corre de nuevo "
            "scripts/ml_oauth_setup.py para generar uno nuevo."
        ) from e

    new_refresh_token = tokens["refresh_token"]
    if new_refresh_token != Env.ML_REFRESH_TOKEN:
        if Env.GH_PAT_SECRETS and Env.GITHUB_REPOSITORY:
            from src.github_secrets import GitHubSecretsError, update_repo_secret

            owner, repo = Env.GITHUB_REPOSITORY.split("/", 1)
            try:
                update_repo_secret(
                    Env.GH_PAT_SECRETS, owner, repo, "ML_REFRESH_TOKEN", new_refresh_token
                )
                print("ML_REFRESH_TOKEN rotado y actualizado en GitHub Secrets.")
            except GitHubSecretsError as e:
                print(
                    f"AVISO: no se pudo rotar ML_REFRESH_TOKEN en GitHub Secrets ({e}). "
                    "La próxima corrida puede fallar por refresh_token inválido."
                )
        else:
            print(
                "AVISO: el refresh_token cambió pero no hay GH_PAT_SECRETS/GITHUB_REPOSITORY "
                f"configurados para rotarlo solo. Actualiza manualmente tu .env con:\n"
                f"ML_REFRESH_TOKEN={new_refresh_token}"
            )

    return tokens["access_token"]


def collect_offers(settings: dict, access_token: str):
    ml_cfg = settings["mercado_libre"]
    site_id = ml_cfg["site_id"]
    category_ids = resolve_category_ids(site_id, access_token, ml_cfg["categories"])

    all_offers = []
    for name, category_id in category_ids.items():
        offers = get_top_offers_for_category(
            site_id=site_id,
            access_token=access_token,
            category_name=name,
            category_id=category_id,
            items_to_scan=ml_cfg["items_per_category"],
            min_discount_pct=ml_cfg["min_discount_pct"],
            top_n=ml_cfg["top_per_category"],
        )
        all_offers.extend(offers)

    all_offers.sort(key=lambda o: o.score, reverse=True)
    return all_offers[: ml_cfg["top_total"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    if not args.dry_run:
        Env.validate_for_publishing()

    access_token = get_ml_access_token()

    posted_path = ROOT_DIR / settings["publishing"]["posted_items_file"]
    posted = _prune_old(_load_posted_items(posted_path), settings["publishing"]["dedupe_window_days"])

    print("Buscando ofertas por categoría...")
    offers = collect_offers(settings, access_token)
    new_offers = [o for o in offers if o.item_id not in posted]

    if not new_offers:
        print("No hay ofertas nuevas que superen el umbral de descuento configurado.")
        return

    for offer in new_offers:
        print(f"\n[{offer.category_name}] {offer.title} -{offer.discount_pct:.0f}% (${offer.price})")

        if args.dry_run:
            print(f"  producto: {offer.permalink}")
            continue

        from src.affiliate import AffiliateLinkError, generate_affiliate_link
        from src.telegram_bot import send_offer

        try:
            affiliate_link = generate_affiliate_link(offer.permalink)
        except AffiliateLinkError as e:
            print(f"  ERROR generando link de afiliado, se omite este item: {e}")
            continue

        send_offer(
            bot_token=Env.TELEGRAM_BOT_TOKEN,
            chat_id=Env.TELEGRAM_CHAT_ID,
            offer=offer,
            affiliate_link=affiliate_link,
            parse_mode=settings["telegram"]["parse_mode"],
        )
        print(f"  publicado -> {affiliate_link}")

        posted[offer.item_id] = datetime.now(timezone.utc).isoformat()
        _save_posted_items(posted_path, posted)
        time.sleep(2)  # evita rate limiting de Telegram/ML


if __name__ == "__main__":
    sys.exit(main())
