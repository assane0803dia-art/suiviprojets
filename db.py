"""
Module de connexion centralisé — utilise psycopg2 avec un POOL de connexions
réutilisables (plutôt qu'une nouvelle connexion à chaque requête), ce qui évite
la latence d'une poignée de main réseau/TLS avec Supabase à chaque appel.

Configuration via .streamlit/secrets.toml (en local) ou les Secrets du
tableau de bord Streamlit Cloud (en production) :

    DB_HOST     = "aws-0-eu-west-3.pooler.supabase.com"
    DB_PORT     = 5432
    DB_DATABASE = "postgres"
    DB_USERNAME = "postgres.xxxxxxxxxxxx"
    DB_PASSWORD = "votre_mot_de_passe"
"""

import psycopg2
from psycopg2 import pool
import pandas as pd
import streamlit as st


@st.cache_resource
def _get_pool():
    """Un seul pool de connexions, partagé et réutilisé entre tous les reruns
    et toutes les sessions de l'application (grâce à st.cache_resource)."""
    return psycopg2.pool.ThreadedConnectionPool(
        1, 10,  # 1 connexion minimum, 10 maximum en simultané
        host=st.secrets["DB_HOST"],
        port=st.secrets.get("DB_PORT", 5432),
        dbname=st.secrets["DB_DATABASE"],
        user=st.secrets["DB_USERNAME"],
        password=st.secrets["DB_PASSWORD"],
    )


def get_connection():
    """Emprunte une connexion au pool. Doit être rendue avec release_connection()."""
    conn = _get_pool().getconn()
    if conn.get_transaction_status() != psycopg2.extensions.TRANSACTION_STATUS_IDLE:
        # Connexion laissée dans un état incertain par un appel précédent — on la nettoie.
        conn.rollback()
    return conn


def release_connection(conn, discard=False):
    """Rend une connexion au pool. discard=True si la connexion est dans un état
    incertain (ex: après une erreur non gérée) — elle sera alors fermée et remplacée
    plutôt que réutilisée telle quelle."""
    _get_pool().putconn(conn, close=discard)


def run_query(query, params=None):
    """Exécute une requête SELECT et retourne un DataFrame pandas."""
    conn = get_connection()
    try:
        return pd.read_sql(query, conn, params=params)
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def run_execute(query, params=None):
    """
    Exécute une requête d'écriture. Si elle se termine par "RETURNING ...",
    retourne cette valeur (motif standard PostgreSQL pour récupérer un ID inséré).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        result = None
        if cursor.description:
            row = cursor.fetchone()
            if row:
                result = row[0]

        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)