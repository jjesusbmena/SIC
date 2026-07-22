"""
Actualiza un GitHub Actions repository secret vía la API REST oficial.
Fuente: https://docs.github.com/en/rest/guides/encrypting-secrets-for-the-rest-api

Necesario porque el refresh_token de Mercado Libre es de un solo uso: cada
corrida del workflow debe guardar el refresh_token nuevo que le entregó ML,
y no se puede escribir en el código de un repo público.
"""
import base64

import requests
from nacl import encoding, public

GITHUB_API_BASE = "https://api.github.com"


class GitHubSecretsError(RuntimeError):
    pass


def _encrypt(public_key_b64: str, secret_value: str) -> str:
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def update_repo_secret(pat: str, owner: str, repo: str, secret_name: str, secret_value: str) -> None:
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
    }

    key_resp = requests.get(
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/secrets/public-key",
        headers=headers,
        timeout=15,
    )
    if not key_resp.ok:
        raise GitHubSecretsError(
            f"No se pudo obtener la public key de secrets ({key_resp.status_code}): {key_resp.text[:300]}"
        )
    key_data = key_resp.json()

    encrypted_value = _encrypt(key_data["key"], secret_value)

    put_resp = requests.put(
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/secrets/{secret_name}",
        headers=headers,
        json={"encrypted_value": encrypted_value, "key_id": key_data["key_id"]},
        timeout=15,
    )
    if not put_resp.ok:
        raise GitHubSecretsError(
            f"No se pudo actualizar el secret {secret_name} ({put_resp.status_code}): {put_resp.text[:300]}"
        )
