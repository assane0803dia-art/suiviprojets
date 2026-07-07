import streamlit as st
from auth import require_login, logout_button
from ui_style import sidebar_brand, section_title, badge_html
import crud
import ai_report_generator as ai

st.set_page_config(page_title="IA - SuiviProjets", page_icon="🤖", layout="wide")
require_login()
sidebar_brand()
logout_button()

st.title("🤖 Assistant IA")
st.caption("Détection de risques en temps réel sur tous vos projets, et recommandations sur demande.")
st.divider()

projets_df = crud.get_projets()

if projets_df.empty:
    st.info("Aucun projet pour l'instant.")
    st.stop()

# ----------------------------------------------------------------------------
# Détection des risques — calcul instantané, sans appel IA
# ----------------------------------------------------------------------------
section_title("⚠️", "Risques détectés sur l'ensemble des projets")
st.caption("Calcul automatique et instantané (dates dépassées, statut non terminé) — aucun appel à l'IA n'est nécessaire pour cette partie.")

total_activites_retard = 0
total_taches_retard = 0
risques_par_projet = {}

for _, projet_row in projets_df.iterrows():
    snapshot = ai.build_project_snapshot(projet_row["id"], projet_row, crud)
    risques = ai.detect_delays_and_risks(snapshot)
    risques_par_projet[projet_row["id"]] = (snapshot, risques)
    total_activites_retard += len(risques["activites_en_retard"])
    total_taches_retard += len(risques["taches_en_retard"])

c1, c2, c3 = st.columns(3)
c1.metric("Projets suivis", len(projets_df))
c2.metric("Activités en retard", total_activites_retard)
c3.metric("Tâches en retard", total_taches_retard)

st.write("")

if total_activites_retard == 0 and total_taches_retard == 0:
    st.success("✅ Aucun retard détecté sur l'ensemble de vos projets.")
else:
    for _, projet_row in projets_df.iterrows():
        snapshot, risques = risques_par_projet[projet_row["id"]]
        nb_retards = len(risques["activites_en_retard"]) + len(risques["taches_en_retard"])
        if nb_retards == 0:
            continue

        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{projet_row['nom']}**")
            with col2:
                st.markdown(badge_html(f"{nb_retards} retard(s)", "warning"), unsafe_allow_html=True)

            for a in risques["activites_en_retard"]:
                st.caption(f"📅 Activité « {a.get('titre')} » — échéance dépassée le {a.get('date_fin')}")
            for t in risques["taches_en_retard"]:
                st.caption(f"✅ Tâche « {t.get('titre')} » — échéance dépassée le {t.get('date_fin')}")

st.divider()

# ----------------------------------------------------------------------------
# Recommandations IA à la demande
# ----------------------------------------------------------------------------
section_title("💡", "Recommandations IA")
st.caption("Génère de courtes recommandations basées sur les risques détectés ci-dessus pour un projet donné.")

projet_options = {row["id"]: row["nom"] for _, row in projets_df.iterrows()}
selected_projet_id = st.selectbox(
    "📌 Sélectionner un projet",
    options=list(projet_options.keys()),
    format_func=lambda x: projet_options[x],
)

if st.button("💡 Générer des recommandations", type="primary"):
    snapshot, risques = risques_par_projet[selected_projet_id]
    with st.spinner("Analyse en cours..."):
        try:
            recommandations = ai.generate_recommendations(snapshot, risques)
            st.session_state["ia_recommandations"] = recommandations
            st.session_state["ia_recommandations_projet_id"] = selected_projet_id
        except RuntimeError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Erreur lors de la génération : {e}")

if (
    st.session_state.get("ia_recommandations")
    and st.session_state.get("ia_recommandations_projet_id") == selected_projet_id
):
    with st.container(border=True):
        st.markdown(st.session_state["ia_recommandations"])

st.divider()
st.caption(
    "📝 Pour un rapport d'exécution complet et exportable (Word/PDF), rendez-vous sur la page **📊 Rapports**."
)
