import pandas as pd
import streamlit as st
from db import get_connection


@st.cache_data(ttl=60)
def load_all_indicators() -> pd.DataFrame:
    """Charge toute la configuration (utilisé sur la page Paramètres)."""
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM Dashboard_Indicateurs ORDER BY type_element, ordre",
        conn,
    )
    conn.close()
    return df


def load_visible_indicators() -> pd.DataFrame:
    """Charge uniquement les indicateurs actifs, ordonnés (utilisé sur le dashboard)."""
    df = load_all_indicators()
    return df[df["visible"] == 1].sort_values("ordre")


def update_indicator(indicateur_id: int, visible: bool, ordre: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Dashboard_Indicateurs SET visible = %s, ordre = %s WHERE id = %s",
        (bool(visible), ordre, indicateur_id),
    )
    conn.commit()
    conn.close()


def compute_kpi_value(row: pd.Series, df: pd.DataFrame):
    """Calcule la valeur d'un KPI selon sa config (agrégation + colonne source)."""
    agregation = row["agregation"]
    colonne = row["colonne_source"]

    if agregation == "count":
        return len(df)

    if colonne not in df.columns:
        return None

    if agregation == "sum":
        return df[colonne].sum()
    elif agregation == "max":
        return df[colonne].max()
    elif agregation == "mean":
        return df[colonne].mean()

    return None


def format_kpi_value(value, format_affichage: str) -> str:
    if value is None:
        return "N/A"
    if format_affichage == "montant":
        return f"{value:,.0f} FCFA".replace(",", " ")
    elif format_affichage == "pourcentage":
        return f"{value:.0f}%"
    else:
        return f"{value:.0f}"
