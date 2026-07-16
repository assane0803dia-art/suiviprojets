import streamlit as st
import pandas as pd
import plotly.express as px
from auth import require_login, logout_button, get_last_project
from ui_style import sidebar_brand, kpi_card_html, section_title, badge_html
from indicators_config import (
    load_all_indicators,
    load_visible_indicators,
    update_indicator,
    compute_kpi_value,
    format_kpi_value,
)
import db
import crud

require_login()
sidebar_brand()
logout_button()

user = st.session_state.get("user", {})
is_admin = user.get("role") == "admin"


@st.cache_data(ttl=300)
def load_vue_dashboard():
    return db.run_query("SELECT * FROM V_Dashboard_Projets")


col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.title("🏠 Tableau de bord")
    st.caption("Suivi en temps réel, projet par projet")
with col_refresh:
    st.write("")
    if st.button("🔄 Actualiser", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

projets_df = crud.get_projets()

if projets_df.empty:
    st.info("👋 Aucun projet pour l'instant. Rendez-vous dans **📁 Nouveau projet** pour créer votre premier projet.")
    st.stop()

# ----------------------------------------------------------------------------
# Sélection du projet
# ----------------------------------------------------------------------------
projet_options = {row["id"]: row["nom"] for _, row in projets_df.iterrows()}
dernier_projet_id = get_last_project(user.get("id"))
default_index = list(projet_options.keys()).index(dernier_projet_id) if dernier_projet_id in projet_options else 0

selected_projet_id = st.selectbox(
    "📌 Projet à afficher",
    options=list(projet_options.keys()),
    format_func=lambda x: projet_options[x],
    index=default_index,
)

projet_row = projets_df[projets_df["id"] == selected_projet_id].iloc[0]

# ----------------------------------------------------------------------------
# Détails du projet — en haut, lisible, un seul projet à la fois
# ----------------------------------------------------------------------------
statut_kind = {"En cours": "success", "Planifié": "muted", "Terminé": "success", "Suspendu": "warning"}.get(projet_row["statut"], "muted")

st.markdown(f"## {projet_row['nom']}")
st.markdown(badge_html(projet_row["statut"] or "Sans statut", statut_kind), unsafe_allow_html=True)
st.caption(projet_row["description"] or "Aucune description")

activites_df = crud.get_activites_by_projet(selected_projet_id)
taches_df = crud.get_taches_by_projet(selected_projet_id)
depenses_projet_dash = crud.get_depenses_by_projet(selected_projet_id)
depense_reelle_dash = float(depenses_projet_dash["montant"].sum()) if not depenses_projet_dash.empty else 0.0
budget_active_dash = float(activites_df["budget"].fillna(0).sum()) if not activites_df.empty else 0.0
taux_execution_dash = (depense_reelle_dash / budget_active_dash * 100) if budget_active_dash else 0.0

detail_cols = st.columns(5)
detail_cols[0].metric("Budget", f"{(projet_row['budget'] or 0):,.0f} FCFA".replace(",", " "))
detail_cols[1].metric("Dépensé réellement", f"{depense_reelle_dash:,.0f} FCFA".replace(",", " "), delta=f"{taux_execution_dash:.0f}% exécuté")
detail_cols[2].metric("Début", str(projet_row["date_debut"] or "—"))
detail_cols[3].metric("Fin prévue", str(projet_row["date_fin"] or "—"))
detail_cols[4].metric("Responsable", projet_row["responsable"] or "—")

st.divider()

# ----------------------------------------------------------------------------
# Données du projet sélectionné
# ----------------------------------------------------------------------------
try:
    df_all = load_vue_dashboard()
except Exception as e:
    st.error(f"Impossible de se connecter à la base de données : {e}")
    st.stop()

df_projet = df_all[df_all["projet"] == projet_row["nom"]]
NOM_COLONNE_PROGRESSION = "progression_projet"

# ----------------------------------------------------------------------------
# Indicateurs — affichés ici, configurables directement sur cette page (admin)
# ----------------------------------------------------------------------------
indicateurs_config = load_visible_indicators()
kpis = indicateurs_config[indicateurs_config["type_element"] == "kpi"]
graphiques = indicateurs_config[indicateurs_config["type_element"] == "graphique"]

if not df_projet.empty and not kpis.empty:
    kpis_pertinents = kpis[kpis["agregation"] != "count"]  # "nombre de projets" n'a plus de sens par projet
    if not kpis_pertinents.empty:
        kpi_cols = st.columns(len(kpis_pertinents))
        for col, (_, row) in zip(kpi_cols, kpis_pertinents.iterrows()):
            value = compute_kpi_value(row, df_projet)
            display_value = format_kpi_value(value, row["format_affichage"])
            with col:
                st.markdown(kpi_card_html(row["icone"] or "", row["libelle"], display_value), unsafe_allow_html=True)

st.write("")

if is_admin:
    with st.expander("⚙️ Choisir les indicateurs affichés (visible par toute l'équipe)"):
        st.caption("Ces réglages s'appliquent à tous les utilisateurs, sur tous les projets.")
        df_indic_all = load_all_indicators()

        for type_element, (icon, label) in [("kpi", ("📊", "Indicateurs clés (KPI)")), ("graphique", ("📈", "Graphiques"))]:
            subset = df_indic_all[df_indic_all["type_element"] == type_element]
            st.markdown(f"**{icon} {label}**")
            if subset.empty:
                st.caption("Aucun indicateur de ce type.")
                continue

            with st.form(f"form_dashboard_{type_element}"):
                updated_rows = []
                for _, row in subset.iterrows():
                    cols = st.columns([0.6, 3.4, 1.2, 1.8])
                    visible = cols[0].checkbox("Actif", value=bool(row["visible"]), key=f"dash_visible_{row['id']}", label_visibility="collapsed")
                    cols[1].write(f"{row['icone'] or ''} {row['libelle']}")
                    ordre = cols[2].number_input("Ordre", value=int(row["ordre"]), min_value=0, max_value=100, step=1, key=f"dash_ordre_{row['id']}", label_visibility="collapsed")
                    badge_kind = "success" if row["visible"] else "muted"
                    cols[3].markdown(badge_html("Actif" if row["visible"] else "Masqué", badge_kind), unsafe_allow_html=True)
                    updated_rows.append((row["id"], visible, ordre))

                if st.form_submit_button(f"💾 Enregistrer", use_container_width=True):
                    for indicateur_id, visible, ordre in updated_rows:
                        update_indicator(indicateur_id, visible, ordre)
                    st.cache_data.clear()
                    st.toast("✅ Configuration enregistrée avec succès.")
                    st.rerun()
            st.write("")

st.divider()

# ----------------------------------------------------------------------------
# Graphiques du projet sélectionné
# ----------------------------------------------------------------------------
if not graphiques.empty:
    for _, row in graphiques.iterrows():
        section_title(row["icone"] or "", row["libelle"])

        if row["cle"] == "graph_budget_projet":
            if not activites_df.empty and "budget" in activites_df.columns:
                fig = px.bar(
                    activites_df.sort_values("budget", ascending=True),
                    x="budget", y="titre", orientation="h",
                    text_auto=",.0f", color_discrete_sequence=["#4F46E5"],
                )
                fig.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white",
                    xaxis_title="Budget (FCFA)", yaxis_title="",
                    margin=dict(l=10, r=10, t=10, b=10), height=320,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune activité avec budget pour ce projet.")

        elif row["cle"] == "graph_progression_projet":
            if not activites_df.empty and "progression" in activites_df.columns:
                fig = px.bar(
                    activites_df.sort_values("progression", ascending=True),
                    x="progression", y="titre", orientation="h",
                    text_auto=".0f", color="progression",
                    color_continuous_scale=["#F59E0B", "#16A34A"], range_color=[0, 100],
                )
                fig.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white",
                    xaxis_title="Progression (%)", yaxis_title="",
                    margin=dict(l=10, r=10, t=10, b=10), height=320,
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune activité pour ce projet.")

        st.write("")

# ----------------------------------------------------------------------------
# Diagramme de Gantt — planification des activités
# ----------------------------------------------------------------------------
section_title("📅", "Planification (Gantt)")

gantt_df = activites_df.dropna(subset=["date_debut", "date_fin"]) if not activites_df.empty else activites_df

if gantt_df.empty:
    st.info("Ajoutez des dates de début/fin à vos activités pour voir apparaître la planification ici.")
else:
    gantt_df = gantt_df.copy()
    gantt_df["date_debut"] = pd.to_datetime(gantt_df["date_debut"])
    gantt_df["date_fin"] = pd.to_datetime(gantt_df["date_fin"])

    fig_gantt = px.timeline(
        gantt_df, x_start="date_debut", x_end="date_fin", y="titre",
        color="statut", color_discrete_map={
            "À faire": "#94A3B8", "En cours": "#F59E0B", "Terminé": "#16A34A", "Bloqué": "#DC2626",
        },
    )
    fig_gantt.update_yaxes(autorange="reversed", title="")
    fig_gantt.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10), height=max(200, 40 * len(gantt_df)),
        legend_title="Statut",
    )
    st.plotly_chart(fig_gantt, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------------
# Détail lisible du projet sélectionné (activités)
# ----------------------------------------------------------------------------
section_title("📋", f"Détail des activités — {projet_row['nom']}")

if activites_df.empty:
    st.info("Aucune activité pour ce projet.")
else:
    st.dataframe(
        activites_df[["titre", "statut", "progression", "budget", "date_debut", "date_fin", "responsable"]].rename(
            columns={"titre": "Activité", "statut": "Statut", "progression": "Progression (%)",
                     "budget": "Budget (FCFA)", "date_debut": "Début", "date_fin": "Fin", "responsable": "Responsable"}
        ),
        use_container_width=True, hide_index=True,
        column_config={
            "Budget (FCFA)": st.column_config.NumberColumn(format="%,.0f"),
            "Progression (%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
        },
    )

st.divider()

# ----------------------------------------------------------------------------
# Export pour Power BI / analyse externe (toujours sur l'ensemble des projets)
# ----------------------------------------------------------------------------
section_title("📥", "Exporter pour Power BI")
st.caption(
    "Téléchargez les données de tous vos projets sous forme de tables reliées (par identifiants), "
    "prêtes à être importées dans Power BI, Excel ou tout autre outil d'analyse."
)

if st.button("📥 Générer l'export (ZIP de fichiers CSV)", type="primary"):
    import io
    import zipfile

    tables = {
        "projets.csv": crud.export_projets(),
        "objectifs.csv": crud.export_objectifs(),
        "resultats.csv": crud.export_resultats(),
        "activites.csv": crud.export_activites(),
        "taches.csv": crud.export_taches(),
        "indicateurs.csv": crud.export_indicateurs(),
        "depenses.csv": crud.export_depenses(),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, table_df in tables.items():
            zf.writestr(filename, table_df.to_csv(index=False))
    st.session_state["powerbi_export"] = buffer.getvalue()

if "powerbi_export" in st.session_state:
    st.download_button(
        "⬇️ Télécharger l'export (.zip)",
        data=st.session_state["powerbi_export"],
        file_name="suiviprojets_export_powerbi.zip",
        mime="application/zip",
    )

with st.expander("ℹ️ Comment importer ça dans Power BI"):
    st.markdown("""
1. Décompressez le fichier `.zip` téléchargé.
2. Dans Power BI Desktop : **Accueil → Obtenir les données → Texte/CSV**, importez les 6 fichiers un par un.
3. Dans **Gérer les relations**, reliez les tables par leurs colonnes d'identifiants.
4. Construisez vos visuels normalement — toutes les tables sont désormais reliées.
    """)
