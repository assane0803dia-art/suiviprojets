import streamlit as st
from datetime import datetime
from auth import require_login, logout_button, get_profile
from ui_style import sidebar_brand, section_title, tip
import crud
import ai_report_generator as ai
import report_export

require_login()
sidebar_brand()
logout_button()

user = st.session_state.get("user", {})
profile = get_profile(user["id"])

st.title("📊 Rapports")
st.caption("Génération automatique de rapports d'exécution par IA (Claude), à partir des données déjà saisies dans le projet.")
st.divider()

projets_df = crud.get_projets()

if projets_df.empty:
    st.info("Aucun projet pour l'instant.")
    st.stop()

projet_options = {row["id"]: row["nom"] for _, row in projets_df.iterrows()}
selected_projet_id = st.selectbox(
    "📌 Sélectionner un projet",
    options=list(projet_options.keys()),
    format_func=lambda x: projet_options[x],
)
projet_row = projets_df[projets_df["id"] == selected_projet_id].iloc[0]

# Réinitialise le brouillon affiché si on change de projet
if st.session_state.get("rapport_last_projet_id") != selected_projet_id:
    st.session_state.pop("rapport_draft", None)
    st.session_state["rapport_last_projet_id"] = selected_projet_id

section_title("📋", "Aperçu des données disponibles")

objectifs_df = crud.get_objectifs(selected_projet_id)
resultats_df = crud.get_resultats_by_projet(selected_projet_id)
activites_df = crud.get_activites_by_projet(selected_projet_id)
taches_df = crud.get_taches_by_projet(selected_projet_id)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Objectifs", len(objectifs_df))
c2.metric("Résultats", len(resultats_df))
c3.metric("Activités", len(activites_df))
c4.metric("Tâches", len(taches_df))

st.divider()

# ==============================================================================
# Génération / régénération / édition
# ==============================================================================
section_title("🤖", "Rapport d'exécution")
tip("rapport_ia", "Vérifiez le rapport avant export — le contenu ci-dessous est entièrement modifiable. Sections couvertes : résumé, contexte, problématique, objectifs, résultats, activités, indicateurs, risques, budget, calendrier, conclusion et recommandations.")

modele_prefere = (profile or {}).get("ia_modele") or "claude-sonnet-5"

col_gen, col_regen = st.columns(2)
with col_gen:
    generer = st.button("🤖 Générer le rapport", type="primary", use_container_width=True)
with col_regen:
    regenerer = st.button("🔄 Régénérer", use_container_width=True, disabled="rapport_draft" not in st.session_state)

if generer or regenerer:
    if objectifs_df.empty and taches_df.empty:
        st.warning("Ce projet n'a pas encore assez de données (objectifs, activités, tâches) pour générer un rapport utile.")
    else:
        with st.spinner("Analyse du projet et rédaction du rapport en cours..."):
            try:
                snapshot = ai.build_project_snapshot(selected_projet_id, projet_row, crud)
                report_text = ai.generate_execution_report(snapshot, model=modele_prefere)
                st.session_state["rapport_draft"] = report_text
                st.toast("✅ Rapport généré avec succès. Vous pouvez le modifier ci-dessous avant de l'enregistrer.")
            except RuntimeError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Erreur lors de la génération du rapport : {e}")

if "rapport_draft" in st.session_state:
    st.write("")
    rapport_edite = st.text_area(
        "✏️ Contenu du rapport (modifiable avant sauvegarde)",
        value=st.session_state["rapport_draft"],
        height=500,
        key="rapport_textarea",
    )
    st.session_state["rapport_draft"] = rapport_edite

    st.write("")
    col1, col2, col3 = st.columns(3)

    with col1:
        titre_rapport = st.text_input("Titre du rapport à sauvegarder", value=f"Rapport — {projet_row['nom']} — {datetime.now().strftime('%d/%m/%Y')}")
        if st.button("💾 Sauvegarder dans le projet", use_container_width=True):
            crud.create_rapport(selected_projet_id, titre_rapport, rapport_edite, user["id"])
            st.toast("✅ Rapport sauvegardé avec succès.")
            st.rerun()

    with col2:
        docx_bytes = report_export.export_to_docx(rapport_edite, projet_row["nom"])
        st.download_button(
            "⬇️ Télécharger en Word (.docx)", data=docx_bytes,
            file_name=f"rapport_{projet_row['nom']}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with col3:
        pdf_bytes = report_export.export_to_pdf(rapport_edite, projet_row["nom"])
        st.download_button(
            "⬇️ Télécharger en PDF", data=pdf_bytes,
            file_name=f"rapport_{projet_row['nom']}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

st.divider()

# ==============================================================================
# Rapports déjà sauvegardés pour ce projet
# ==============================================================================
section_title("🗂️", "Rapports sauvegardés")

rapports_df = crud.get_rapports(selected_projet_id)

if rapports_df.empty:
    st.info("Aucun rapport sauvegardé pour ce projet.")
else:
    for _, rap in rapports_df.iterrows():
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
            with col1:
                st.markdown(f"**{rap['titre']}**")
                date_str = rap["date_creation"].strftime("%d/%m/%Y à %H:%M") if rap["date_creation"] else ""
                st.caption(f"Créé par {rap['cree_par'] or 'inconnu'} — {date_str}")
            with col2:
                if st.button("👁️ Voir", key=f"view_rap_{rap['id']}", use_container_width=True):
                    st.session_state[f"show_rap_{rap['id']}"] = not st.session_state.get(f"show_rap_{rap['id']}", False)
                    st.rerun()
            with col3:
                docx_bytes_saved = report_export.export_to_docx(rap["contenu"], projet_row["nom"])
                st.download_button(
                    "⬇️ Word", data=docx_bytes_saved, file_name=f"{rap['titre']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_docx_{rap['id']}", use_container_width=True,
                )
            with col4:
                if st.button("🗑️ Supprimer", key=f"del_rap_{rap['id']}", use_container_width=True):
                    crud.delete_rapport(rap["id"])
                    st.warning("Rapport supprimé.")
                    st.rerun()

            if st.session_state.get(f"show_rap_{rap['id']}"):
                st.markdown(report_export.to_display_markdown(rap["contenu"]))
