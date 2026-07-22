"""
OAuth 2.0 de Mercado Libre: intercambio de refresh_token por access_token.
Fuente: https://developers.mercadolibre.com.mx/en_us/authentication-and-authorization

Detalle importante: el refresh_token es de un solo uso. Cada llamada a este
endpoint devuelve un access_token nuevo (válido 6 horas) Y un refresh_token
nuevo; el anterior queda invalidado. Quien use esta función es responsable de
persistir el refresh_token nuevo (ver src/github_secrets.py).
"""
import requests

TOKEN_URL = "https://api.mercadolibre.com/oauth/token"


class MLAuthError(RuntimeError):
    pass


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if not resp.ok:
        raise MLAuthError(
            f"No se pudo refrescar el access_token ({resp.status_code}): {resp.text[:500]}"
        )
    data = resp.json()
    if "refresh_token" not in data:
        raise MLAuthError(
            "La respuesta no incluyó refresh_token. Revisa que el flujo 'Refresh Token' "
            f"esté habilitado en tu app de Mercado Libre. Respuesta completa: {data}"
        )
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_in": data.get("expires_in"),
    }


def exchange_code_for_token(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    """Solo se usa una vez, en scripts/ml_oauth_setup.py, para la autorización inicial."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if not resp.ok:
        raise MLAuthError(
            f"No se pudo intercambiar el code por un token ({resp.status_code}): {resp.text[:500]}"
        )
    data = resp.json()
    if "refresh_token" not in data:
        raise MLAuthError(
            "La respuesta no incluyó refresh_token. Revisa que el flujo 'Refresh Token' "
            f"esté habilitado en tu app de Mercado Libre. Respuesta completa: {data}"
        )
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_in": data.get("expires_in"),
    }
