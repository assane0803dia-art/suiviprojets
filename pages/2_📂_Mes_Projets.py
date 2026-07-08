import streamlit as st
import os
from auth import require_login, logout_button
import auth
from ui_style import sidebar_brand, section_title, badge_html, tip, ai_text_toolbar
import ui_style
import crud
import validators
import ai_text_assist

st.set_page_config(page_title="Mes projets - SuiviProjets", page_icon="📂", layout="wide")
require_login()
sidebar_brand()
logout_button()

st.title("📂 Mes projets")
st.caption("Votre espace de gestion : ouvrez n'importe quelle section, dans l'ordre que vous voulez.")
st.divider()

# ----------------------------------------------------------------------------
# Mode lecture seule (compte "lecteur")
# ----------------------------------------------------------------------------
current_user = st.session_state.get("user", {})
is_lecteur = current_user.get("role") == "lecteur"

# ----------------------------------------------------------------------------
# Sélection du projet
# ----------------------------------------------------------------------------
if is_lecteur:
    projets_df = crud.get_projets_accessibles(current_user["id"])
    if projets_df.empty:
        st.info("👋 Aucun projet ne vous a encore été partagé. Contactez un administrateur.")
        st.stop()
else:
    projets_df = crud.get_projets()
    if projets_df.empty:
        st.info("👋 Aucun projet pour l'instant. Rendez-vous dans **📁 Nouveau projet** pour en créer un.")
        st.stop()

if is_lecteur:
    st.info("🔒 **Mode lecture seule** — vous pouvez consulter ce projet mais pas le modifier.")

projet_options = {row["id"]: row["nom"] for _, row in projets_df.iterrows()}

default_index = 0
jump_id = st.session_state.pop("jump_to_projet_id", None)
if jump_id in projet_options:
    default_index = list(projet_options.keys()).index(jump_id)

selected_projet_id = st.selectbox(
    "📌 Projet ouvert",
    options=list(projet_options.keys()),
    format_func=lambda x: projet_options[x],
    index=default_index,
)

projet_row = projets_df[projets_df["id"] == selected_projet_id].iloc[0]

# Réinitialise la section active seulement si l'utilisateur change réellement de projet
# (ne pas écraser la section déjà ouverte par la redirection post-connexion)
if "hub_last_projet_id" in st.session_state and st.session_state["hub_last_projet_id"] != selected_projet_id:
    st.session_state["hub_active_section"] = None

if st.session_state.get("hub_last_projet_id") != selected_projet_id:
    st.session_state["hub_last_projet_id"] = selected_projet_id
    auth.update_last_project(current_user["id"], selected_projet_id)

if "hub_active_section" not in st.session_state:
    st.session_state["hub_active_section"] = None


def responsable_options():
    df = crud.get_utilisateurs()
    options = {None: "— Aucun —"}
    for _, row in df.iterrows():
        options[row["id"]] = row["nom"]
    return options


def open_section(key):
    st.session_state["hub_active_section"] = key
    st.rerun()


# ----------------------------------------------------------------------------
# En-tête du projet
# ----------------------------------------------------------------------------
col_header, col_del = st.columns([5, 1])
with col_header:
    st.markdown(f"## {projet_row['nom']}")
    st.caption(projet_row["description"] or "Aucune description")
    statut_badge_kind = {"En cours": "success", "Planifié": "muted", "Terminé": "success", "Suspendu": "warning"}.get(projet_row["statut"], "muted")
    st.markdown(badge_html(projet_row["statut"] or "Sans statut", statut_badge_kind), unsafe_allow_html=True)

with col_del:
    st.write("")
    if not is_lecteur and st.session_state.get("confirm_delete_projet_id") != selected_projet_id:
        if st.button("🗑️ Supprimer", use_container_width=True):
            st.session_state["confirm_delete_projet_id"] = selected_projet_id
            st.rerun()

if not is_lecteur and st.session_state.get("confirm_delete_projet_id") == selected_projet_id:
    st.warning(
        f"⚠️ Confirmez-vous la suppression définitive du projet **{projet_row['nom']}** "
        "ainsi que tous ses objectifs, résultats, activités et tâches ? Cette action est irréversible."
    )
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("🗑️ Oui, supprimer définitivement", type="primary", use_container_width=True):
            crud.delete_projet(selected_projet_id)
            st.session_state.pop("confirm_delete_projet_id", None)
            st.session_state.pop("hub_last_projet_id", None)
            st.success(f"✅ Projet « {projet_row['nom']} » supprimé avec succès.")
            st.rerun()
    with col_cancel:
        if st.button("Annuler", use_container_width=True):
            st.session_state.pop("confirm_delete_projet_id", None)
            st.rerun()
    st.stop()

st.write("")

if not is_lecteur:
    with st.expander("👥 Ajouter un responsable (chef de projet, gestionnaire, membre d'équipe)"):
        with st.form("form_new_utilisateur", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            nom_u = c1.text_input("Nom complet *")
            email_u = c2.text_input("Email")
            role_u = c3.text_input("Rôle (ex: Chef de projet)")
            if st.form_submit_button("Ajouter"):
                if not nom_u:
                    st.warning("Le nom est obligatoire.")
                else:
                    try:
                        crud.create_utilisateur(nom_u, email_u, role_u)
                        st.success(f"✅ '{nom_u}' ajouté avec succès.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    with st.expander("✏️ Modifier les informations du projet"):
        utilisateurs_df_edit = crud.get_utilisateurs()
        resp_options_edit = {None: "— Aucun —"}
        for _, row in utilisateurs_df_edit.iterrows():
            resp_options_edit[row["id"]] = row["nom"]

        with st.form("form_edit_projet_info"):
            nom_edit = st.text_input("Nom du projet *", value=projet_row["nom"])
            description_edit = st.text_area("Description", value=projet_row["description"] or "")
            c1, c2 = st.columns(2)
            date_debut_edit = c1.date_input("Date de début", value=projet_row["date_debut"])
            date_fin_edit = c2.date_input("Date de fin", value=projet_row["date_fin"])
            c3, c4 = st.columns(2)
            statut_edit = c3.selectbox(
                "Statut", crud.STATUTS_PROJET,
                index=crud.STATUTS_PROJET.index(projet_row["statut"]) if projet_row["statut"] in crud.STATUTS_PROJET else 0,
            )
            current_resp_edit = projet_row["responsable_id"] if projet_row["responsable_id"] in resp_options_edit else None
            responsable_id_edit = c4.selectbox(
                "Responsable", options=list(resp_options_edit.keys()),
                format_func=lambda x: resp_options_edit[x],
                index=list(resp_options_edit.keys()).index(current_resp_edit),
            )

            if st.form_submit_button("💾 Enregistrer", use_container_width=True):
                if not nom_edit:
                    st.warning("Le nom du projet est obligatoire.")
                elif not validators.dates_valides(date_debut_edit, date_fin_edit):
                    st.warning("⚠️ La date de fin ne peut pas être antérieure à la date de début.")
                else:
                    try:
                        crud.update_projet(
                            selected_projet_id, nom_edit, description_edit, date_debut_edit, date_fin_edit,
                            float(projet_row["budget"] or 0), statut_edit, responsable_id_edit,
                        )
                        st.toast("✅ Projet mis à jour avec succès.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

st.write("")

# ----------------------------------------------------------------------------
# Grille de cartes — chaque section est indépendante
# ----------------------------------------------------------------------------
objectifs_df = crud.get_objectifs(selected_projet_id)
resultats_df = crud.get_resultats_by_projet(selected_projet_id)
activites_df = crud.get_activites_by_projet(selected_projet_id)
taches_df = crud.get_taches_by_projet(selected_projet_id)
parties_prenantes_df = crud.get_parties_prenantes(selected_projet_id)
documents_df = crud.get_documents(selected_projet_id)

cards = [
    ("objectifs", "🎯", "Objectifs spécifiques", len(objectifs_df)),
    ("resultats", "📈", "Résultats attendus", len(resultats_df)),
    ("activites", "📅", "Activités", len(activites_df)),
    ("taches", "✅", "Tâches", len(taches_df)),
    ("indicateurs", "📊", "Indicateurs", len(resultats_df[resultats_df["indicateur"].notna() & (resultats_df["indicateur"] != "")]) if not resultats_df.empty else 0),
    ("budget", "💰", "Budget", None),
    ("parties_prenantes", "👥", "Parties prenantes", len(parties_prenantes_df)),
    ("documents", "📄", "Documents", len(documents_df)),
]

grid_cols = st.columns(4)
for i, (key, icon, label, count) in enumerate(cards):
    with grid_cols[i % 4]:
        with st.container(border=True):
            if key in ui_style.SECTION_HELP:
                col_label, col_info = st.columns([5, 1])
                with col_label:
                    st.markdown(f"**{icon} {label}**")
                with col_info:
                    with st.popover("ℹ️", use_container_width=True):
                        st.write(ui_style.SECTION_HELP[key])
            else:
                st.markdown(f"**{icon} {label}**")
            if count is not None:
                st.caption(f"{count} élément(s) enregistré(s)")
            else:
                st.caption("Aperçu rapide")
            if st.button("Ouvrir", key=f"open_{key}", use_container_width=True):
                open_section(key)

st.divider()

active = st.session_state["hub_active_section"]

if active is None:
    st.info("👆 Cliquez sur **Ouvrir** dans une carte ci-dessus pour gérer cette section.")
    st.stop()

col_header, col_close = st.columns([6, 1])
with col_close:
    if st.button("✖️ Fermer", use_container_width=True):
        st.session_state["hub_active_section"] = None
        st.rerun()

# ==============================================================================
# SECTION : OBJECTIFS
# ==============================================================================
if is_lecteur:
    if active == "objectifs":
        section_title("🎯", "Objectifs spécifiques", ui_style.SECTION_HELP["objectifs"])
        tip("objectifs_smart", "Utilisez des objectifs SMART : Spécifiques, Mesurables, Atteignables, Réalistes, Temporellement définis.")
        if objectifs_df.empty:
            st.info("Aucun objectif pour ce projet.")
        else:
            st.dataframe(
                objectifs_df[["type_objectif", "titre", "responsable"]].rename(
                    columns={"type_objectif": "Type", "titre": "Titre", "responsable": "Responsable"}
                ),
                use_container_width=True, hide_index=True,
            )

    elif active == "resultats":
        section_title("📈", "Résultats attendus", ui_style.SECTION_HELP["resultats"])
        tip("resultats_indicateurs", "Les indicateurs doivent être mesurables — préférez un chiffre précis à une appréciation générale.")
        if resultats_df.empty:
            st.info("Aucun résultat attendu pour ce projet.")
        else:
            st.dataframe(
                resultats_df[["objectif_titre", "titre", "indicateur", "valeur_cible", "valeur_actuelle", "unite", "statut"]].rename(
                    columns={"objectif_titre": "Objectif", "titre": "Titre", "indicateur": "Indicateur",
                             "valeur_cible": "Cible", "valeur_actuelle": "Actuelle", "unite": "Unité", "statut": "Statut"}
                ),
                use_container_width=True, hide_index=True,
            )

    elif active == "activites":
        section_title("📅", "Activités", ui_style.SECTION_HELP["activites"])
        if activites_df.empty:
            st.info("Aucune activité pour ce projet.")
        else:
            st.dataframe(
                activites_df[["resultat_titre", "titre", "statut", "progression", "budget", "responsable"]].rename(
                    columns={"resultat_titre": "Résultat", "titre": "Titre", "statut": "Statut",
                             "progression": "Progression (%)", "budget": "Budget", "responsable": "Responsable"}
                ),
                use_container_width=True, hide_index=True,
            )

    elif active == "taches":
        section_title("✅", "Tâches", ui_style.SECTION_HELP["taches"])
        if taches_df.empty:
            st.info("Aucune tâche pour ce projet.")
        else:
            st.dataframe(
                taches_df[["activite_titre", "titre", "priorite", "statut", "progression", "responsable"]].rename(
                    columns={"activite_titre": "Activité", "titre": "Titre", "priorite": "Priorité",
                             "statut": "Statut", "progression": "Progression (%)", "responsable": "Responsable"}
                ),
                use_container_width=True, hide_index=True,
            )

    elif active == "indicateurs":
        section_title("📊", "Indicateurs de suivi")
        tip("indicateurs_mesurables", "Les indicateurs doivent être mesurables : donnez toujours une valeur cible et une unité claire.")
        indicateurs_df_ro = resultats_df[resultats_df["indicateur"].notna() & (resultats_df["indicateur"] != "")] if not resultats_df.empty else resultats_df
        if indicateurs_df_ro.empty:
            st.info("Aucun indicateur défini pour ce projet.")
        else:
            st.dataframe(
                indicateurs_df_ro[["objectif_titre", "titre", "indicateur", "valeur_cible", "valeur_actuelle", "unite"]].rename(
                    columns={"objectif_titre": "Objectif", "titre": "Résultat", "indicateur": "Indicateur",
                             "valeur_cible": "Cible", "valeur_actuelle": "Actuelle", "unite": "Unité"}
                ),
                use_container_width=True, hide_index=True,
            )

    elif active == "budget":
        section_title("💰", "Budget du projet")
        tip("budget_fixe_variable", "Pensez à distinguer les coûts fixes (équipements, infrastructure) et variables (consommables, main-d'œuvre).")
        budget_projet_ro = float(projet_row["budget"] or 0)
        budget_active_ro = float(activites_df["budget"].fillna(0).sum()) if not activites_df.empty else 0.0
        c1, c2 = st.columns(2)
        c1.metric("Budget global du projet", f"{budget_projet_ro:,.0f} FCFA".replace(",", " "))
        c2.metric("Somme des budgets d'activités", f"{budget_active_ro:,.0f} FCFA".replace(",", " "))
        if not activites_df.empty:
            st.write("")
            st.markdown("**Détail par activité**")
            st.dataframe(
                activites_df[["resultat_titre", "titre", "budget"]].rename(
                    columns={"resultat_titre": "Résultat", "titre": "Activité", "budget": "Budget (FCFA)"}
                ),
                use_container_width=True, hide_index=True,
            )

    elif active == "parties_prenantes":
        section_title("👥", "Parties prenantes")
        if parties_prenantes_df.empty:
            st.info("Aucune partie prenante enregistrée pour ce projet.")
        else:
            st.dataframe(
                parties_prenantes_df[["nom", "type_partie", "role_contribution", "contact"]].rename(
                    columns={"nom": "Nom", "type_partie": "Type", "role_contribution": "Rôle / contribution", "contact": "Contact"}
                ),
                use_container_width=True, hide_index=True,
            )

    elif active == "documents":
        section_title("📄", "Documents")
        if documents_df.empty:
            st.info("Aucun document pour ce projet.")
        else:
            for _, doc in documents_df.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{doc['nom_fichier']}**")
                        st.caption(f"{doc['type_document'] or 'Autre'} — {doc['description'] or 'Sans description'}")
                    with col2:
                        if os.path.exists(doc["chemin_fichier"]):
                            with open(doc["chemin_fichier"], "rb") as f:
                                st.download_button(
                                    "⬇️ Télécharger", data=f.read(),
                                    file_name=doc["nom_fichier"], key=f"dl_ro_{doc['id']}",
                                    use_container_width=True,
                                )
                        else:
                            st.caption("⚠️ Fichier introuvable")

else:
    if active == "objectifs":
        section_title("🎯", "Objectifs spécifiques", ui_style.SECTION_HELP["objectifs"])
        tip("objectifs_smart_2", "Utilisez des objectifs SMART : Spécifiques, Mesurables, Atteignables, Réalistes, Temporellement définis.")

        with st.expander("➕ Ajouter un objectif"):
            type_objectif_new = st.selectbox("Type", crud.TYPES_OBJECTIF, key="type_new_obj")
            with st.form("form_new_objectif", clear_on_submit=True):
                titre = st.text_input("Titre *")
                responsable_id = None
                if type_objectif_new == "Spécifique":
                    resp_options = responsable_options()
                    responsable_id = st.selectbox(
                        "Responsable", options=list(resp_options.keys()),
                        format_func=lambda x: resp_options[x], key="resp_new_obj",
                    )
                if st.form_submit_button("Ajouter"):
                    if not titre:
                        st.warning("Le titre est obligatoire.")
                    else:
                        crud.create_objectif(selected_projet_id, type_objectif_new, titre, responsable_id)
                        st.toast("✅ Objectif ajouté avec succès.")
                        st.rerun()

        if objectifs_df.empty:
            st.info("Aucun objectif pour ce projet.")
        else:
            st.dataframe(
                objectifs_df[["type_objectif", "titre", "responsable"]].rename(
                    columns={"type_objectif": "Type", "titre": "Titre", "responsable": "Responsable"}
                ),
                use_container_width=True, hide_index=True,
            )

            obj_options = {row["id"]: f"[{row['type_objectif']}] {row['titre']}" for _, row in objectifs_df.iterrows()}
            selected_obj_id = st.selectbox("Modifier un objectif", options=list(obj_options.keys()), format_func=lambda x: obj_options[x])
            obj = objectifs_df[objectifs_df["id"] == selected_obj_id].iloc[0]

            type_objectif_edit = st.selectbox(
                "Type", crud.TYPES_OBJECTIF,
                index=crud.TYPES_OBJECTIF.index(obj["type_objectif"]) if obj["type_objectif"] in crud.TYPES_OBJECTIF else 0,
                key=f"type_edit_obj_{obj['id']}",
            )
            with st.form(f"form_edit_obj_{obj['id']}"):
                titre = st.text_input("Titre *", value=obj["titre"])
                responsable_id = None
                if type_objectif_edit == "Spécifique":
                    resp_options = responsable_options()
                    current_resp = obj["responsable_id"] if obj["responsable_id"] in resp_options else None
                    responsable_id = st.selectbox(
                        "Responsable", options=list(resp_options.keys()),
                        format_func=lambda x: resp_options[x],
                        index=list(resp_options.keys()).index(current_resp),
                    )
                col_save, col_delete = st.columns(2)
                if col_save.form_submit_button("💾 Enregistrer", use_container_width=True):
                    crud.update_objectif(obj["id"], type_objectif_edit, titre, responsable_id)
                    st.toast("✅ Objectif mis à jour avec succès.")
                    st.rerun()
                if col_delete.form_submit_button("🗑️ Supprimer", use_container_width=True):
                    crud.delete_objectif(obj["id"])
                    st.warning("Objectif supprimé (ainsi que ses résultats, activités et tâches liés).")
                    st.rerun()

    # ==============================================================================
    # SECTION : RÉSULTATS
    # ==============================================================================
    elif active == "resultats":
        section_title("📈", "Résultats attendus", ui_style.SECTION_HELP["resultats"])
        tip("resultats_indicateurs_2", "Les indicateurs doivent être mesurables — préférez un chiffre précis à une appréciation générale.")

        if objectifs_df.empty:
            st.warning("Créez d'abord un objectif pour pouvoir y attacher un résultat.")
            if st.button("🎯 Ouvrir la section Objectifs"):
                open_section("objectifs")
        else:
            with st.expander("➕ Ajouter un résultat attendu"):
                obj_options = {row["id"]: row["titre"] for _, row in objectifs_df.iterrows()}
                objectif_id = st.selectbox("Objectif concerné *", options=list(obj_options.keys()), format_func=lambda x: obj_options[x], key="new_res_objectif")

                titre_r = st.text_input("Titre *", key="new_res_titre")
                description_r = st.text_area("Description", key="new_res_description")
                ai_text_toolbar("new_res_description", contexte=f"Projet : {projet_row['description'] or ''} | Objectif : {obj_options.get(objectif_id, '')}")

                if st.button("✨ Suggérer des résultats avec l'IA", key="suggest_res_btn"):
                    try:
                        with st.spinner("L'IA réfléchit..."):
                            suggestions = ai_text_assist.suggest_items(
                                "resultats", projet_row["description"] or "", obj_options.get(objectif_id, ""),
                            )
                        st.session_state["res_suggestions"] = suggestions
                    except RuntimeError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Erreur IA : {e}")

                if st.session_state.get("res_suggestions"):
                    st.caption("Suggestions de l'IA — cliquez sur ➕ pour ajouter directement :")
                    for i, sugg in enumerate(st.session_state["res_suggestions"]):
                        c1, c2 = st.columns([5, 1])
                        with c1:
                            st.write(f"**{sugg.get('titre', '')}** — {sugg.get('indicateur', '')} ({sugg.get('unite', '')})")
                            st.caption(sugg.get("description", ""))
                        with c2:
                            if st.button("➕ Ajouter", key=f"add_suggestion_res_{i}", use_container_width=True):
                                crud.create_resultat(
                                    objectif_id, sugg.get("titre", ""), sugg.get("description", ""),
                                    sugg.get("indicateur", ""), 0, 0, sugg.get("unite", ""), "À faire",
                                )
                                st.toast("✅ Résultat ajouté avec succès.")
                                st.rerun()

                c1, c2, c3 = st.columns(3)
                indicateur = c1.text_input("Indicateur", key="new_res_indicateur")
                valeur_cible = c2.number_input("Valeur cible", key="new_res_cible")
                valeur_actuelle = c3.number_input("Valeur actuelle", key="new_res_actuelle")
                c4, c5 = st.columns(2)
                unite = c4.text_input("Unité", key="new_res_unite")
                statut_r = c5.selectbox("Statut", crud.STATUTS_GENERIQUE, key="new_res_statut")
                if st.button("Ajouter", key="submit_new_resultat"):
                    if not titre_r:
                        st.warning("Le titre est obligatoire.")
                    else:
                        crud.create_resultat(objectif_id, titre_r, description_r, indicateur, valeur_cible, valeur_actuelle, unite, statut_r)
                        for k in ["new_res_titre", "new_res_description", "new_res_indicateur", "new_res_unite", "res_suggestions"]:
                            st.session_state.pop(k, None)
                        st.toast("✅ Résultat ajouté avec succès.")
                        st.rerun()

            if resultats_df.empty:
                st.info("Aucun résultat attendu pour ce projet.")
            else:
                st.dataframe(
                    resultats_df[["objectif_titre", "titre", "indicateur", "valeur_cible", "valeur_actuelle", "unite", "statut"]].rename(
                        columns={"objectif_titre": "Objectif", "titre": "Titre", "indicateur": "Indicateur",
                                 "valeur_cible": "Cible", "valeur_actuelle": "Actuelle", "unite": "Unité", "statut": "Statut"}
                    ),
                    use_container_width=True, hide_index=True,
                )

                res_options = {row["id"]: f"{row['titre']} ({row['objectif_titre']})" for _, row in resultats_df.iterrows()}
                selected_res_id = st.selectbox("Modifier un résultat", options=list(res_options.keys()), format_func=lambda x: res_options[x])
                res = resultats_df[resultats_df["id"] == selected_res_id].iloc[0]

                edit_key = f"edit_res_description_{res['id']}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = res["description"] or ""

                titre_r = st.text_input("Titre *", value=res["titre"], key=f"edit_res_titre_{res['id']}")
                description_r = st.text_area("Description", key=edit_key)
                ai_text_toolbar(edit_key, contexte=f"Résultat : {res['titre']} | Indicateur : {res['indicateur'] or ''}")

                with st.form(f"form_edit_res_{res['id']}"):
                    c1, c2, c3 = st.columns(3)
                    indicateur = c1.text_input("Indicateur", value=res["indicateur"] or "")
                    valeur_cible = c2.number_input("Valeur cible", value=float(res["valeur_cible"] or 0))
                    valeur_actuelle = c3.number_input("Valeur actuelle", value=float(res["valeur_actuelle"] or 0))
                    c4, c5 = st.columns(2)
                    unite = c4.text_input("Unité", value=res["unite"] or "")
                    statut_r = c5.selectbox(
                        "Statut", crud.STATUTS_GENERIQUE,
                        index=crud.STATUTS_GENERIQUE.index(res["statut"]) if res["statut"] in crud.STATUTS_GENERIQUE else 0,
                    )
                    col_save, col_delete = st.columns(2)
                    if col_save.form_submit_button("💾 Enregistrer", use_container_width=True):
                        crud.update_resultat(res["id"], titre_r, st.session_state[edit_key], indicateur, valeur_cible, valeur_actuelle, unite, statut_r)
                        st.toast("✅ Résultat mis à jour avec succès.")
                        st.rerun()
                    if col_delete.form_submit_button("🗑️ Supprimer", use_container_width=True):
                        crud.delete_resultat(res["id"])
                        st.warning("Résultat supprimé (ainsi que ses activités et tâches liées).")
                        st.rerun()

    # ==============================================================================
    # SECTION : ACTIVITÉS
    # ==============================================================================
    elif active == "activites":
        section_title("📅", "Activités", ui_style.SECTION_HELP["activites"])

        if resultats_df.empty:
            st.warning("Créez d'abord un résultat attendu pour pouvoir y attacher une activité.")
            if st.button("📈 Ouvrir la section Résultats"):
                open_section("resultats")
        else:
            with st.expander("➕ Ajouter une activité"):
                res_options = {row["id"]: f"{row['titre']} ({row['objectif_titre']})" for _, row in resultats_df.iterrows()}
                resultat_id = st.selectbox("Résultat concerné *", options=list(res_options.keys()), format_func=lambda x: res_options[x], key="new_act_resultat")

                if st.button("✨ Suggérer des activités avec l'IA", key="suggest_act_btn"):
                    try:
                        with st.spinner("L'IA réfléchit..."):
                            suggestions = ai_text_assist.suggest_items(
                                "activites", projet_row["description"] or "", res_options.get(resultat_id, ""),
                            )
                        st.session_state["act_suggestions"] = suggestions
                    except RuntimeError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Erreur IA : {e}")

                if st.session_state.get("act_suggestions"):
                    st.caption("Suggestions de l'IA — cliquez sur ➕ pour ajouter directement :")
                    for i, sugg in enumerate(st.session_state["act_suggestions"]):
                        c1, c2 = st.columns([5, 1])
                        with c1:
                            st.write(f"**{sugg.get('titre', '')}**")
                            st.caption(sugg.get("description", ""))
                        with c2:
                            if st.button("➕ Ajouter", key=f"add_suggestion_act_{i}", use_container_width=True):
                                crud.create_activite(
                                    resultat_id, sugg.get("titre", ""), sugg.get("description", ""),
                                    None, None, None, "À faire", 0, 0,
                                )
                                st.toast("✅ Activité ajoutée avec succès.")
                                st.rerun()

                with st.form("form_new_activite", clear_on_submit=True):
                    titre_a = st.text_input("Titre *")
                    description_a = st.text_area("Description")
                    c1, c2 = st.columns(2)
                    date_debut_a = c1.date_input("Date de début", value=None)
                    date_fin_a = c2.date_input("Date de fin", value=None)
                    c3, c4 = st.columns(2)
                    budget_a = c3.number_input("Budget (FCFA)", min_value=0.0)
                    progression_a = c4.slider("Progression (%)", 0, 100, 0)
                    statut_a = st.selectbox("Statut", crud.STATUTS_GENERIQUE)
                    resp_options = responsable_options()
                    responsable_id_a = st.selectbox("Responsable", options=list(resp_options.keys()), format_func=lambda x: resp_options[x])
                    if st.form_submit_button("Ajouter"):
                        if not titre_a:
                            st.warning("Le titre est obligatoire.")
                        elif not validators.dates_valides(date_debut_a, date_fin_a):
                            st.warning("⚠️ La date de fin ne peut pas être antérieure à la date de début.")
                        else:
                            crud.create_activite(resultat_id, titre_a, description_a, responsable_id_a, date_debut_a, date_fin_a, statut_a, budget_a, progression_a)
                            st.session_state.pop("act_suggestions", None)
                            st.toast("✅ Activité ajoutée avec succès.")
                            st.rerun()

            if activites_df.empty:
                st.info("Aucune activité pour ce projet.")
            else:
                st.dataframe(
                    activites_df[["resultat_titre", "titre", "statut", "progression", "budget", "responsable"]].rename(
                        columns={"resultat_titre": "Résultat", "titre": "Titre", "statut": "Statut",
                                 "progression": "Progression (%)", "budget": "Budget", "responsable": "Responsable"}
                    ),
                    use_container_width=True, hide_index=True,
                )

                act_options = {row["id"]: f"{row['titre']} ({row['resultat_titre']})" for _, row in activites_df.iterrows()}
                selected_act_id = st.selectbox("Modifier une activité", options=list(act_options.keys()), format_func=lambda x: act_options[x])
                act = activites_df[activites_df["id"] == selected_act_id].iloc[0]

                with st.form(f"form_edit_act_{act['id']}"):
                    titre_a = st.text_input("Titre *", value=act["titre"])
                    description_a = st.text_area("Description", value=act["description"] or "")
                    c1, c2 = st.columns(2)
                    date_debut_a = c1.date_input("Date de début", value=act["date_debut"])
                    date_fin_a = c2.date_input("Date de fin", value=act["date_fin"])
                    c3, c4 = st.columns(2)
                    budget_a = c3.number_input("Budget (FCFA)", min_value=0.0, value=float(act["budget"] or 0))
                    progression_a = c4.slider("Progression (%)", 0, 100, int(act["progression"] or 0))
                    statut_a = st.selectbox(
                        "Statut", crud.STATUTS_GENERIQUE,
                        index=crud.STATUTS_GENERIQUE.index(act["statut"]) if act["statut"] in crud.STATUTS_GENERIQUE else 0,
                    )
                    resp_options = responsable_options()
                    current_resp = act["responsable_id"] if act["responsable_id"] in resp_options else None
                    responsable_id_a = st.selectbox(
                        "Responsable", options=list(resp_options.keys()), format_func=lambda x: resp_options[x],
                        index=list(resp_options.keys()).index(current_resp),
                    )
                    col_save, col_delete = st.columns(2)
                    if col_save.form_submit_button("💾 Enregistrer", use_container_width=True):
                        if not validators.dates_valides(date_debut_a, date_fin_a):
                            st.warning("⚠️ La date de fin ne peut pas être antérieure à la date de début.")
                        else:
                            crud.update_activite(act["id"], titre_a, description_a, responsable_id_a, date_debut_a, date_fin_a, statut_a, budget_a, progression_a)
                            st.toast("✅ Activité mise à jour avec succès.")
                            st.rerun()
                    if col_delete.form_submit_button("🗑️ Supprimer", use_container_width=True):
                        crud.delete_activite(act["id"])
                        st.warning("Activité supprimée (ainsi que ses tâches liées).")
                        st.rerun()

    # ==============================================================================
    # SECTION : TÂCHES
    # ==============================================================================
    elif active == "taches":
        section_title("✅", "Tâches", ui_style.SECTION_HELP["taches"])

        if activites_df.empty:
            st.warning("Créez d'abord une activité pour pouvoir y attacher une tâche.")
            if st.button("📅 Ouvrir la section Activités"):
                open_section("activites")
        else:
            with st.expander("➕ Ajouter une tâche"):
                act_options = {row["id"]: f"{row['titre']} ({row['resultat_titre']})" for _, row in activites_df.iterrows()}
                with st.form("form_new_tache", clear_on_submit=True):
                    activite_id = st.selectbox("Activité concernée *", options=list(act_options.keys()), format_func=lambda x: act_options[x])
                    titre_t = st.text_input("Titre *")
                    description_t = st.text_area("Description")
                    c1, c2 = st.columns(2)
                    priorite_t = c1.selectbox("Priorité", crud.PRIORITES_TACHE)
                    statut_t = c2.selectbox("Statut", crud.STATUTS_GENERIQUE)
                    c3, c4 = st.columns(2)
                    date_debut_t = c3.date_input("Date de début", value=None)
                    date_fin_t = c4.date_input("Date de fin", value=None)
                    progression_t = st.slider("Progression (%)", 0, 100, 0)
                    resp_options = responsable_options()
                    responsable_id_t = st.selectbox("Responsable", options=list(resp_options.keys()), format_func=lambda x: resp_options[x])
                    if st.form_submit_button("Ajouter"):
                        act_row = activites_df[activites_df["id"] == activite_id].iloc[0]
                        if not titre_t:
                            st.warning("Le titre est obligatoire.")
                        elif not validators.dates_valides(date_debut_t, date_fin_t):
                            st.warning("⚠️ La date de fin ne peut pas être antérieure à la date de début.")
                        elif not validators.tache_dans_intervalle_activite(date_debut_t, date_fin_t, act_row["date_debut"], act_row["date_fin"]):
                            st.warning(
                                f"⚠️ Les dates de la tâche doivent rester dans la période de l'activité "
                                f"« {act_row['titre']} » ({act_row['date_debut']} → {act_row['date_fin']})."
                            )
                        else:
                            crud.create_tache(activite_id, titre_t, description_t, responsable_id_t, priorite_t, statut_t, date_debut_t, date_fin_t, progression_t)
                            st.toast("✅ Tâche ajoutée avec succès.")
                            st.rerun()

            if taches_df.empty:
                st.info("Aucune tâche pour ce projet.")
            else:
                st.dataframe(
                    taches_df[["activite_titre", "titre", "priorite", "statut", "progression", "responsable"]].rename(
                        columns={"activite_titre": "Activité", "titre": "Titre", "priorite": "Priorité",
                                 "statut": "Statut", "progression": "Progression (%)", "responsable": "Responsable"}
                    ),
                    use_container_width=True, hide_index=True,
                )

                tache_options = {row["id"]: f"{row['titre']} ({row['activite_titre']})" for _, row in taches_df.iterrows()}
                selected_tache_id = st.selectbox("Modifier une tâche", options=list(tache_options.keys()), format_func=lambda x: tache_options[x])
                tache = taches_df[taches_df["id"] == selected_tache_id].iloc[0]

                with st.form(f"form_edit_tache_{tache['id']}"):
                    titre_t = st.text_input("Titre *", value=tache["titre"])
                    description_t = st.text_area("Description", value=tache["description"] or "")
                    c1, c2 = st.columns(2)
                    priorite_t = c1.selectbox(
                        "Priorité", crud.PRIORITES_TACHE,
                        index=crud.PRIORITES_TACHE.index(tache["priorite"]) if tache["priorite"] in crud.PRIORITES_TACHE else 0,
                    )
                    statut_t = c2.selectbox(
                        "Statut", crud.STATUTS_GENERIQUE,
                        index=crud.STATUTS_GENERIQUE.index(tache["statut"]) if tache["statut"] in crud.STATUTS_GENERIQUE else 0,
                    )
                    c3, c4 = st.columns(2)
                    date_debut_t = c3.date_input("Date de début", value=tache["date_debut"])
                    date_fin_t = c4.date_input("Date de fin", value=tache["date_fin"])
                    progression_t = st.slider("Progression (%)", 0, 100, int(tache["progression"] or 0))
                    resp_options = responsable_options()
                    current_resp = tache["responsable_id"] if tache["responsable_id"] in resp_options else None
                    responsable_id_t = st.selectbox(
                        "Responsable", options=list(resp_options.keys()), format_func=lambda x: resp_options[x],
                        index=list(resp_options.keys()).index(current_resp),
                    )
                    col_save, col_delete = st.columns(2)
                    if col_save.form_submit_button("💾 Enregistrer", use_container_width=True):
                        act_row = activites_df[activites_df["id"] == tache["activite_id"]].iloc[0]
                        if not validators.dates_valides(date_debut_t, date_fin_t):
                            st.warning("⚠️ La date de fin ne peut pas être antérieure à la date de début.")
                        elif not validators.tache_dans_intervalle_activite(date_debut_t, date_fin_t, act_row["date_debut"], act_row["date_fin"]):
                            st.warning(
                                f"⚠️ Les dates de la tâche doivent rester dans la période de l'activité "
                                f"« {act_row['titre']} » ({act_row['date_debut']} → {act_row['date_fin']})."
                            )
                        else:
                            crud.update_tache(tache["id"], titre_t, description_t, responsable_id_t, priorite_t, statut_t, date_debut_t, date_fin_t, progression_t)
                            st.toast("✅ Tâche mise à jour avec succès.")
                            st.rerun()
                    if col_delete.form_submit_button("🗑️ Supprimer", use_container_width=True):
                        crud.delete_tache(tache["id"])
                        st.warning("Tâche supprimée.")
                        st.rerun()

    # ==============================================================================
    # SECTION : INDICATEURS (vue transversale sur tous les résultats du projet)
    # ==============================================================================
    elif active == "indicateurs":
        section_title("📊", "Indicateurs de suivi")
        tip("indicateurs_mesurables_2", "Les indicateurs doivent être mesurables : donnez toujours une valeur cible et une unité claire.")
        st.caption("Mettez à jour rapidement la valeur actuelle de chaque indicateur, sans naviguer dans la hiérarchie.")

        indicateurs_df = resultats_df[resultats_df["indicateur"].notna() & (resultats_df["indicateur"] != "")] if not resultats_df.empty else resultats_df

        if indicateurs_df.empty:
            st.info(
                "Aucun indicateur défini. Les indicateurs se définissent au niveau des résultats attendus "
                "(champ « Indicateur » du formulaire)."
            )
            if st.button("📈 Ouvrir la section Résultats"):
                open_section("resultats")
        else:
            for _, row in indicateurs_df.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**{row['indicateur']}**")
                        st.caption(f"{row['titre']} — {row['objectif_titre']}")
                    with c2:
                        st.metric("Cible", f"{row['valeur_cible']:.0f} {row['unite'] or ''}")
                    with c3:
                        new_val = st.number_input(
                            "Valeur actuelle", value=float(row["valeur_actuelle"] or 0),
                            key=f"indic_val_{row['id']}", label_visibility="visible",
                        )
                        if st.button("Mettre à jour", key=f"indic_update_{row['id']}", use_container_width=True):
                            crud.update_resultat_valeur_actuelle(row["id"], new_val)
                            st.toast("✅ Indicateur mis à jour avec succès.")
                            st.rerun()

    # ==============================================================================
    # SECTION : BUDGET
    # ==============================================================================
    elif active == "budget":
        section_title("💰", "Budget du projet")
        tip("budget_fixe_variable_2", "Pensez à distinguer les coûts fixes (équipements, infrastructure) et variables (consommables, main-d'œuvre).")

        budget_projet = float(projet_row["budget"] or 0)
        budget_active = float(activites_df["budget"].fillna(0).sum()) if not activites_df.empty else 0.0

        c1, c2 = st.columns(2)
        c1.metric("Budget global du projet", f"{budget_projet:,.0f} FCFA".replace(",", " "))
        c2.metric("Somme des budgets d'activités", f"{budget_active:,.0f} FCFA".replace(",", " "))

        if budget_active > budget_projet and budget_projet > 0:
            st.warning("⚠️ La somme des budgets d'activités dépasse le budget global du projet.")

        with st.expander("✏️ Modifier le budget global du projet"):
            with st.form("form_edit_budget"):
                nouveau_budget = st.number_input("Budget global (FCFA)", min_value=0.0, step=100000.0, value=budget_projet)
                if st.form_submit_button("💾 Enregistrer", use_container_width=True):
                    crud.update_projet(
                        selected_projet_id, projet_row["nom"], projet_row["description"],
                        projet_row["date_debut"], projet_row["date_fin"], nouveau_budget,
                        projet_row["statut"], projet_row["responsable_id"],
                    )
                    st.toast("✅ Budget mis à jour avec succès.")
                    st.rerun()

        if not activites_df.empty:
            st.write("")
            st.markdown("**Détail par activité**")
            st.dataframe(
                activites_df[["resultat_titre", "titre", "budget"]].rename(
                    columns={"resultat_titre": "Résultat", "titre": "Activité", "budget": "Budget (FCFA)"}
                ),
                use_container_width=True, hide_index=True,
            )

    # ==============================================================================
    # SECTION : PARTIES PRENANTES
    # ==============================================================================
    elif active == "parties_prenantes":
        section_title("👥", "Parties prenantes")
        st.caption("Partenaires, bailleurs, bénéficiaires ou communautés associés à ce projet.")

        with st.expander("➕ Ajouter une partie prenante"):
            with st.form("form_new_partie", clear_on_submit=True):
                nom_p = st.text_input("Nom *")
                c1, c2 = st.columns(2)
                type_p = c1.selectbox("Type", crud.TYPES_PARTIE_PRENANTE)
                contact_p = c2.text_input("Contact (email / téléphone)")
                role_p = st.text_area("Rôle / contribution au projet")
                if st.form_submit_button("Ajouter"):
                    if not nom_p:
                        st.warning("Le nom est obligatoire.")
                    else:
                        crud.create_partie_prenante(selected_projet_id, nom_p, type_p, role_p, contact_p)
                        st.toast("✅ Partie prenante ajoutée avec succès.")
                        st.rerun()

        if parties_prenantes_df.empty:
            st.info("Aucune partie prenante enregistrée pour ce projet.")
        else:
            st.dataframe(
                parties_prenantes_df[["nom", "type_partie", "role_contribution", "contact"]].rename(
                    columns={"nom": "Nom", "type_partie": "Type", "role_contribution": "Rôle / contribution", "contact": "Contact"}
                ),
                use_container_width=True, hide_index=True,
            )

            partie_options = {row["id"]: row["nom"] for _, row in parties_prenantes_df.iterrows()}
            selected_partie_id = st.selectbox("Modifier une partie prenante", options=list(partie_options.keys()), format_func=lambda x: partie_options[x])
            partie = parties_prenantes_df[parties_prenantes_df["id"] == selected_partie_id].iloc[0]

            with st.form(f"form_edit_partie_{partie['id']}"):
                nom_p = st.text_input("Nom *", value=partie["nom"])
                c1, c2 = st.columns(2)
                type_p = c1.selectbox(
                    "Type", crud.TYPES_PARTIE_PRENANTE,
                    index=crud.TYPES_PARTIE_PRENANTE.index(partie["type_partie"]) if partie["type_partie"] in crud.TYPES_PARTIE_PRENANTE else 0,
                )
                contact_p = c2.text_input("Contact", value=partie["contact"] or "")
                role_p = st.text_area("Rôle / contribution", value=partie["role_contribution"] or "")
                col_save, col_delete = st.columns(2)
                if col_save.form_submit_button("💾 Enregistrer", use_container_width=True):
                    crud.update_partie_prenante(partie["id"], nom_p, type_p, role_p, contact_p)
                    st.toast("✅ Partie prenante mise à jour avec succès.")
                    st.rerun()
                if col_delete.form_submit_button("🗑️ Supprimer", use_container_width=True):
                    crud.delete_partie_prenante(partie["id"])
                    st.warning("Partie prenante supprimée.")
                    st.rerun()

    # ==============================================================================
    # SECTION : DOCUMENTS
    # ==============================================================================
    elif active == "documents":
        section_title("📄", "Documents")
        st.caption("Rapports, contrats, fiches projet ou photos liés à ce projet.")

        with st.expander("➕ Ajouter un document"):
            with st.form("form_new_document", clear_on_submit=True):
                fichier = st.file_uploader("Fichier *", type=None)
                c1, c2 = st.columns(2)
                type_doc = c1.selectbox("Type", crud.TYPES_DOCUMENT)
                description_doc = c2.text_input("Description (facultatif)")
                if st.form_submit_button("Ajouter"):
                    if fichier is None:
                        st.warning("Veuillez sélectionner un fichier.")
                    else:
                        dossier = os.path.join("documents", str(selected_projet_id))
                        os.makedirs(dossier, exist_ok=True)
                        chemin = os.path.join(dossier, fichier.name)
                        with open(chemin, "wb") as f:
                            f.write(fichier.getbuffer())
                        crud.create_document(selected_projet_id, fichier.name, chemin, type_doc, description_doc)
                        st.toast("✅ Document ajouté avec succès.")
                        st.rerun()

        if documents_df.empty:
            st.info("Aucun document pour ce projet.")
        else:
            for _, doc in documents_df.iterrows():
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{doc['nom_fichier']}**")
                        st.caption(f"{doc['type_document'] or 'Autre'} — {doc['description'] or 'Sans description'}")
                    with col2:
                        if os.path.exists(doc["chemin_fichier"]):
                            with open(doc["chemin_fichier"], "rb") as f:
                                st.download_button(
                                    "⬇️ Télécharger", data=f.read(),
                                    file_name=doc["nom_fichier"], key=f"dl_{doc['id']}",
                                    use_container_width=True,
                                )
                        else:
                            st.caption("⚠️ Fichier introuvable sur le disque")
                    with col3:
                        if st.button("🗑️ Supprimer", key=f"del_doc_{doc['id']}", use_container_width=True):
                            crud.delete_document(doc["id"])
                            st.warning("Document supprimé.")
                            st.rerun()

