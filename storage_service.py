"""
Stockage des documents dans Supabase Storage — au lieu du disque local du serveur,
qui est ÉPHÉMÈRE sur Streamlit Cloud (effacé à chaque redémarrage ou redéploiement).

Configuration requise dans .streamlit/secrets.toml (Streamlit Cloud : Settings → Secrets) :

    SUPABASE_URL         = "https://VOTRE_PROJET.supabase.co"
    SUPABASE_SERVICE_KEY = "..."   (clé "service_role", PAS la clé "anon" publique)

Ces deux valeurs se trouvent dans Supabase : Project Settings → API.

Un bucket nommé "documents" doit exister dans Supabase Storage (Storage → New bucket,
type "Private" recommandé puisque l'accès passe déjà par l'authentification de l'app).
"""

import requests
import streamlit as st
from urllib.parse import quote

BUCKET = "documents"


def is_configured() -> bool:
    return "SUPABASE_URL" in st.secrets and "SUPABASE_SERVICE_KEY" in st.secrets


def _base_url() -> str:
    return st.secrets["SUPABASE_URL"].rstrip("/")


def _headers() -> dict:
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return {"Authorization": f"Bearer {key}", "apikey": key}


def _object_url(chemin: str) -> str:
    """Construit l'URL de l'objet en encodant le chemin (espaces, accents...) —
    sans quoi Supabase rejette la requête avec 'Invalid path specified'."""
    chemin_encode = quote(chemin, safe="/")
    return f"{_base_url()}/storage/v1/object/{BUCKET}/{chemin_encode}"


def upload_file(chemin: str, contenu: bytes, content_type: str = "application/octet-stream") -> None:
    """Envoie un fichier dans le bucket. `chemin` est le chemin interne au bucket
    (ex: "12/rapport.pdf"), pas un chemin sur le disque local."""
    headers = _headers()
    headers["Content-Type"] = content_type
    headers["x-upsert"] = "true"  # écrase si un fichier existe déjà au même chemin
    resp = requests.post(_object_url(chemin), headers=headers, data=contenu, timeout=30)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Échec de l'envoi du fichier vers Supabase Storage : {resp.text}")


def download_file(chemin: str) -> bytes:
    resp = requests.get(_object_url(chemin), headers=_headers(), timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Fichier introuvable dans le stockage : {chemin}")
    return resp.content


def delete_file(chemin: str) -> None:
    try:
        requests.delete(_object_url(chemin), headers=_headers(), timeout=30)
    except Exception:
        pass  # La suppression du fichier ne doit jamais faire échouer la suppression en base