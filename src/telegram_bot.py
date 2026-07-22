"""
Publica mensajes en un canal/grupo de Telegram usando la Bot API oficial:
https://core.telegram.org/bots/api#sendphoto
"""
import requests

TELEGRAM_API_BASE = "https://api.telegram.org"


def send_offer(bot_token: str, chat_id: str, offer, affiliate_link: str, parse_mode: str = "HTML") -> dict:
    caption = (
        f"🔥 <b>{offer.title}</b>\n\n"
        f"💰 <b>${offer.price:,.2f}</b> "
        f"<s>${offer.original_price:,.2f}</s> "
        f"(-{offer.discount_pct:.0f}%)\n"
        f"📦 {offer.category_name}\n\n"
        f"👉 <a href=\"{affiliate_link}\">Ver oferta</a>"
    )

    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "caption": caption,
        "parse_mode": parse_mode,
        "photo": offer.thumbnail,
    }
    resp = requests.post(url, data=payload, timeout=15)
    if not resp.ok:
        raise RuntimeError(f"Telegram respondió {resp.status_code}: {resp.text}")
    return resp.json()
