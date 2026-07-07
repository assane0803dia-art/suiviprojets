import streamlit as st
import pandas as pd
import plotly.express as px
from auth import require_login, logout_button
from ui_style import sidebar_brand, kpi_card_html, section_title
from indicators_config import (
    load_visible_indicators,
    compute_kpi_value,
    format_kpi_value,
)
from db import get_connection

st.set_page_config(page_title="Tableau de bord - SuiviProjets", page_icon="📊", layout="wide")

require_login()
sidebar_brand()
logout_button()


@st.cache_data(ttl=300)
def load_data():
    conn = get_connection()
    return pd.read_sql("SELECT * FROM V_Dashboard_Projets", conn)


try:
    df = load_data()
except Exception as e:
    st.error(f"Impossible de se connecter à la base de données : {e}")
    st.stop()

NOM_COLONNE_PROJET = "Projet"

col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.title("🏠 Tableau de bord")
    st.caption("Vue d'ensemble en temps réel de l'avancement de vos projets")
with col_refresh:
    st.write("")
    if st.button("🔄 Actualiser", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

if df.empty:
    st.info(
        "👋 Aucun projet pour l'instant. Rendez-vous dans **📁 Nouveau projet** "
        "pour créer votre premier projet."
    )
    st.stop()

indicateurs = load_visible_indicators()
kpis = indicateurs[indicateurs["type_element"] == "kpi"]
graphiques = indicateurs[indicateurs["type_element"] == "graphique"]

if not kpis.empty:
    kpi_cols = st.columns(len(kpis))
    for col, (_, row) in zip(kpi_cols, kpis.iterrows()):
        value = compute_kpi_value(row, df)
        display_value = format_kpi_value(value, row["format_affichage"])
        with col:
            st.markdown(kpi_card_html(row["icone"] or "", row["libelle"], display_value), unsafe_allow_html=True)

st.write("")

if not graphiques.empty:
    chart_cols = st.columns(len(graphiques))
    for col, (_, row) in zip(chart_cols, graphiques.iterrows()):
        with col:
            section_title(row["icone"] or "", row["libelle"])

            if row["cle"] == "graph_budget_projet" and "budget" in df.columns:
                fig = px.bar(
                    df.sort_values("budget", ascending=True),
                    x="budget", y=NOM_COLONNE_PROJET, orientation="h",
                    text_auto=",.0f", color_discrete_sequence=["#4F46E5"],
                )
                fig.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white",
                    xaxis_title="Budget (FCFA)", yaxis_title="",
                    margin=dict(l=10, r=10, t=10, b=10), height=320,
                )
                st.plotly_chart(fig, use_container_width=True)

            elif row["cle"] == "graph_progression_projet" and "Progression_Projet" in df.columns:
                fig = px.bar(
                    df.sort_values("Progression_Projet", ascending=True),
                    x="Progression_Projet", y=NOM_COLONNE_PROJET, orientation="h",
                    text_auto=".0f", color="Progression_Projet",
                    color_continuous_scale=["#F59E0B", "#16A34A"], range_color=[0, 100],
                )
                fig.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white",
                    xaxis_title="Progression (%)", yaxis_title="",
                    margin=dict(l=10, r=10, t=10, b=10), height=320,
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig, use_container_width=True)

st.write("")
section_title("📋", "Détail des projets")

column_config = {}
if "budget" in df.columns:
    column_config["budget"] = st.column_config.NumberColumn("Budget (FCFA)", format="%,.0f")
if "Progression_Projet" in df.columns:
    column_config["Progression_Projet"] = st.column_config.ProgressColumn(
        "Progression", min_value=0, max_value=100, format="%.0f%%"
    )

st.dataframe(df, use_container_width=True, hide_index=True, column_config=column_config)

st.divider()
st.caption(
    "🤖 La génération automatique de rapports d'exécution par IA sera bientôt disponible "
    "depuis la page **📂 Mes projets**."
)