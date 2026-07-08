import pandas as pd
import streamlit as st
import db


@st.cache_data(ttl=60)
def load_all_indicators() -> pd.DataFrame:
    """Charge toute la configuration (utilisé sur la page Paramètres)."""
    return db.run_query("SELECT * FROM Dashboard_Indicateurs ORDER BY type_element, ordre")


def load_visible_indicators() -> pd.DataFrame:
    """Charge uniquement les indicateurs actifs, ordonnés (utilisé sur le dashboard)."""
    df = load_all_indicators()
    return df[df["visible"] == 1].sort_values("ordre")


def update_indicator(indicateur_id: int, visible: bool, ordre: int):
    db.run_execute(
        "UPDATE Dashboard_Indicateurs SET visible = %s, ordre = %s WHERE id = %s",
        (bool(visible), ordre, indicateur_id),
    )


def compute_kpi_value(row: pd.Series, df: pd.DataFrame):
    """Calcule la valeur d'un KPI selon sa config (agrégation + colonne source)."""
    agregation = row["agregation"]
    colonne = row["colonne_source"]

    if agregation == "count":
        return len(df)

    if colonne is None:
        return None

    # PostgreSQL renvoie les noms de colonnes non cités en minuscules, même si
    # colonne_source a été enregistré avec une autre casse (ex: "Progression_Projet").
    if colonne not in df.columns:
        colonnes_par_minuscule = {c.lower(): c for c in df.columns}
        colonne = colonnes_par_minuscule.get(colonne.lower())
        if colonne is None:
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