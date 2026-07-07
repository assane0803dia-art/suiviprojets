import streamlit as st
from auth import require_login, logout_button
from ui_style import sidebar_brand, section_title
import crud
import ai_report_generator as ai
import report_export

st.set_page_config(page_title="Rapports - SuiviProjets", page_icon="📊", layout="wide")
require_login()
sidebar_brand()
logout_button()

st.title("📊 Rapports")
st.caption("Génération automatique de rapports d'exécution par IA (Claude).")
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
section_title("🤖", "Rapport d'exécution automatique")

if "generated_report" not in st.session_state:
    st.session_state["generated_report"] = None
if "generated_report_projet_id" not in st.session_state:
    st.session_state["generated_report_projet_id"] = None

if st.button("🤖 Générer le rapport", type="primary"):
    if objectifs_df.empty and taches_df.empty:
        st.warning("Ce projet n'a pas encore assez de données (objectifs, activités, tâches) pour générer un rapport utile.")
    else:
        with st.spinner("Analyse du projet et rédaction du rapport en cours..."):
            try:
                snapshot = ai.build_project_snapshot(selected_projet_id, projet_row, crud)
                report_text = ai.generate_execution_report(snapshot)
                st.session_state["generated_report"] = report_text
                st.session_state["generated_report_projet_id"] = selected_projet_id
            except RuntimeError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Erreur lors de la génération du rapport : {e}")

if (
    st.session_state["generated_report"]
    and st.session_state["generated_report_projet_id"] == selected_projet_id
):
    st.write("")
    with st.container(border=True):
        st.markdown(st.session_state["generated_report"])

    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        docx_bytes = report_export.export_to_docx(st.session_state["generated_report"], projet_row["nom"])
        st.download_button(
            "⬇️ Télécharger en Word (.docx)", data=docx_bytes,
            file_name=f"rapport_{projet_row['nom']}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with col2:
        pdf_bytes = report_export.export_to_pdf(st.session_state["generated_report"], projet_row["nom"])
        st.download_button(
            "⬇️ Télécharger en PDF", data=pdf_bytes,
            file_name=f"rapport_{projet_row['nom']}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
