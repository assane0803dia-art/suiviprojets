"""
Module de connexion centralisé — utilise psycopg2 pour se connecter à Supabase
(PostgreSQL), compatible Streamlit Community Cloud.

Configuration via .streamlit/secrets.toml (en local) ou les Secrets du
tableau de bord Streamlit Cloud (en production). Récupérez ces informations
depuis Supabase : Project Settings > Database > Connection parameters.

    DB_HOST     = "db.xxxxxxxxxxxx.supabase.co"
    DB_PORT     = 5432
    DB_DATABASE = "postgres"
    DB_USERNAME = "postgres"
    DB_PASSWORD = "votre_mot_de_passe"
"""

import psycopg2
import streamlit as st


def get_connection():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        port=st.secrets.get("DB_PORT", 5432),
        dbname=st.secrets["DB_DATABASE"],
        user=st.secrets["DB_USERNAME"],
        password=st.secrets["DB_PASSWORD"],
    )
