import streamlit as st
from auth import require_login, logout_button
from ui_style import sidebar_brand, section_title, tip, ai_text_toolbar
import crud
import validators

st.set_page_config(page_title="Nouveau projet - SuiviProjets", page_icon="📁", layout="wide")
require_login()
sidebar_brand()
logout_button()

st.title("📁 Nouveau projet")
st.caption("Créez votre projet en quelques secondes. Vous compléterez objectifs, résultats, activités, tâches et indicateurs ensuite, dans l'ordre que vous voulez, depuis son espace de gestion.")
st.divider()

section_title("📌", "Informations de base")
tip("nouveau_projet_contexte", "Décrivez brièvement le problème auquel votre projet répond — cette description sert de base au Contexte du rapport IA.")

# En dehors du formulaire pour permettre les boutons d'assistance IA
nom = st.text_input("Nom du projet *", key="new_projet_nom")
description = st.text_area("Description", key="new_projet_description")
ai_text_toolbar("new_projet_description", contexte=f"Nom du projet : {nom}" if nom else "")

with st.form("form_new_projet_quick"):
    with st.expander("➕ Informations complémentaires (facultatif — modifiable plus tard)"):
        c1, c2 = st.columns(2)
        date_debut = c1.date_input("Date de début", value=None)
        date_fin = c2.date_input("Date de fin", value=None)
        c3, c4 = st.columns(2)
        budget = c3.number_input("Budget (FCFA)", min_value=0.0, step=100000.0)
        statut = c4.selectbox("Statut", crud.STATUTS_PROJET)
        utilisateurs_df = crud.get_utilisateurs()
        resp_options = {None: "— Aucun —"}
        for _, row in utilisateurs_df.iterrows():
            resp_options[row["id"]] = row["nom"]
        responsable_id = st.selectbox(
            "Responsable du projet", options=list(resp_options.keys()),
            format_func=lambda x: resp_options[x],
        )

    if st.form_submit_button("✅ Créer le projet", use_container_width=True, type="primary"):
        if not nom:
            st.warning("Le nom du projet est obligatoire.")
        elif not validators.dates_valides(date_debut, date_fin):
            st.warning("⚠️ La date de fin ne peut pas être antérieure à la date de début.")
        else:
            try:
                new_id = crud.create_projet(nom, description, date_debut, date_fin, budget, statut, responsable_id)
                st.session_state["jump_to_projet_id"] = new_id
                st.session_state.pop("new_projet_nom", None)
                st.session_state.pop("new_projet_description", None)
                st.success(f"✅ Projet « {nom} » créé avec succès.")
                st.switch_page("pages/2_📂_Mes_Projets.py")
            except ValueError as e:
                st.error(str(e))
