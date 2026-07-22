"""
Orquestador: ofertas reales de mercadolibre.com.mx/ofertas (scraping) ->
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
from src.ml_scraper import scrape_top_offers


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


def collect_offers(settings: dict):
    ml_cfg = settings["mercado_libre"]
    return scrape_top_offers(
        min_discount_pct=ml_cfg["min_discount_pct"],
        top_n=ml_cfg["top_total"],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    if not args.dry_run:
        Env.validate_for_publishing()

    posted_path = ROOT_DIR / settings["publishing"]["posted_items_file"]
    posted = _prune_old(_load_posted_items(posted_path), settings["publishing"]["dedupe_window_days"])

    print("Buscando ofertas en mercadolibre.com.mx/ofertas...")
    offers = collect_offers(settings)
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
