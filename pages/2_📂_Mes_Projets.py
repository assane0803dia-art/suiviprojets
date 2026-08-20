import streamlit as st
from i18n import t
import os
import pandas as pd
from auth import require_login, logout_button
import auth
from ui_style import sidebar_brand, section_title, badge_html, tip, ai_text_field
import ui_style
import crud
import storage_service
import validators
import indicateurs_temporels
import ai_text_assist

require_login()
sidebar_brand()
logout_button()

st.title(t("my_projects_title"))
st.caption(t("my_projects_subtitle"))
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

# Mémorise le dernier projet consulté (redirection après connexion)
if st.session_state.get("hub_last_projet_id") != selected_projet_id:
    st.session_state["hub_last_projet_id"] = selected_projet_id
    auth.update_last_project(current_user["id"], selected_projet_id)


def responsable_options():
    df = crud.get_utilisateurs(selected_projet_id)
    options = {None: "— Aucun —"}
    for _, row in df.iterrows():
        options[row["id"]] = row["nom"]
    return options


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

# ----------------------------------------------------------------------------
# Navigation par onglets
# ----------------------------------------------------------------------------
objectifs_df = crud.get_objectifs(selected_projet_id)
resultats_df = crud.get_resultats_by_projet(selected_projet_id)
activites_df = crud.get_activites_by_projet(selected_projet_id)
taches_df = crud.get_taches_by_projet(selected_projet_id)
parties_prenantes_df = crud.get_parties_prenantes(selected_projet_id)
documents_df = crud.get_documents(selected_projet_id)

(tab_informations, tab_objectifs, tab_resultats, tab_activites, tab_taches,
 tab_budget, tab_indicateurs, tab_parties, tab_documents) = st.tabs([
    "🏠 Informations générales", "🎯 Objectifs", "📈 Résultats", "📅 Activités", "✅ Tâches",
    "💰 Budget", "📊 Indicateurs", "👥 Parties prenantes", "📄 Documents",
])

with tab_informations:
    if not is_lecteur:
        with st.expander("👥 Gérer les responsables (chefs de projet, gestionnaires, membres d'équipe)"):
            comptes_df = crud.get_comptes_utilisateurs()
            compte_options = {None: "— Aucun (ne recevra pas de notifications) —"}
            for _, c in comptes_df.iterrows():
                compte_options[c["id"]] = f"{c['username']}" + (f" ({c['nom_complet']})" if c["nom_complet"] else "")

            with st.form("form_new_utilisateur", clear_on_submit=True):
                st.markdown("**➕ Ajouter un responsable**")
                c1, c2, c3 = st.columns(3)
                nom_u = c1.text_input("Nom complet *")
                email_u = c2.text_input("Email")
                role_u = c3.text_input("Rôle (ex: Chef de projet)")
                compte_u = st.selectbox(
                    "Compte associé (facultatif)", options=list(compte_options.keys()),
                    format_func=lambda x: compte_options[x],
                    help="Si ce responsable a aussi un compte de connexion à l'application, associez-le ici pour qu'il puisse recevoir des notifications (ex: activité à venir).",
                )
                if st.form_submit_button("Ajouter"):
                    if not nom_u:
                        st.warning("Le nom est obligatoire.")
                    else:
                        try:
                            crud.create_utilisateur(nom_u, email_u, role_u, selected_projet_id, compte_u)
                            st.toast(f"✅ '{nom_u}' ajouté avec succès.")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

            st.divider()
            st.markdown(f"**📋 Responsables de « {projet_row['nom']} »**")
            st.caption("Chaque projet a sa propre liste de responsables, indépendante des autres projets.")
            tous_responsables_df = crud.get_utilisateurs(selected_projet_id)

            if tous_responsables_df.empty:
                st.caption("Aucun responsable enregistré pour ce projet pour l'instant.")
            else:
                for _, resp in tous_responsables_df.iterrows():
                    rc1, rc2, rc3 = st.columns([3, 2, 1])
                    with rc1:
                        lien_compte = " 🔔" if resp["user_id"] else ""
                        st.write(f"**{resp['nom']}**{lien_compte}")
                    with rc2:
                        st.caption(f"{resp['email'] or '—'} — {resp['role'] or '—'}")
                    with rc3:
                        if st.button("✏️", key=f"edit_resp_btn_{resp['id']}", use_container_width=True, help="Modifier / supprimer"):
                            st.session_state["editing_resp_id"] = None if st.session_state.get("editing_resp_id") == resp["id"] else resp["id"]
                            st.rerun()

                    if st.session_state.get("editing_resp_id") == resp["id"]:
                        with st.form(f"form_edit_resp_{resp['id']}"):
                            nom_edit_u = st.text_input("Nom complet *", value=resp["nom"])
                            ec1, ec2 = st.columns(2)
                            email_edit_u = ec1.text_input("Email", value=resp["email"] or "")
                            role_edit_u = ec2.text_input("Rôle", value=resp["role"] or "")
                            current_compte = resp["user_id"] if resp["user_id"] in compte_options else None
                            compte_edit_u = st.selectbox(
                                "Compte associé (facultatif)", options=list(compte_options.keys()),
                                format_func=lambda x: compte_options[x],
                                index=list(compte_options.keys()).index(current_compte),
                            )
                            col_save_u, col_del_u = st.columns(2)
                            if col_save_u.form_submit_button("💾 Enregistrer", use_container_width=True):
                                if not nom_edit_u:
                                    st.warning("Le nom est obligatoire.")
                                else:
                                    try:
                                        crud.update_utilisateur(resp["id"], nom_edit_u, email_edit_u, role_edit_u, compte_edit_u)
                                        st.toast("✅ Responsable mis à jour avec succès.")
                                        st.session_state["editing_resp_id"] = None
                                        st.rerun()
                                    except ValueError as e:
                                        st.error(str(e))
                            if col_del_u.form_submit_button("🗑️ Supprimer", use_container_width=True):
                                crud.delete_utilisateur(resp["id"])
                                st.warning("Responsable supprimé (les éléments qu'il gérait passent en 'Aucun responsable').")
                                st.session_state["editing_resp_id"] = None
                                st.rerun()

        with st.expander("✏️ Modifier les informations du projet"):
            utilisateurs_df_edit = crud.get_utilisateurs(selected_projet_id)
            resp_options_edit = {None: "— Aucun —"}
            for _, row in utilisateurs_df_edit.iterrows():
                resp_options_edit[row["id"]] = row["nom"]

            edit_projet_desc_key = f"edit_projet_description_{selected_projet_id}"
            if edit_projet_desc_key not in st.session_state:
                st.session_state[edit_projet_desc_key] = projet_row["description"] or ""

            nom_edit = st.text_input("Nom du projet *", value=projet_row["nom"], key=f"edit_projet_nom_{selected_projet_id}")
            description_edit = ai_text_field(
                "Description", key=edit_projet_desc_key,
                contexte=f"Nom du projet : {nom_edit}",
            )

            with st.form("form_edit_projet_info"):
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
                                selected_projet_id, nom_edit, st.session_state[edit_projet_desc_key], date_debut_edit, date_fin_edit,
                                float(projet_row["budget"] or 0), statut_edit, responsable_id_edit,
                            )
                            st.toast("✅ Projet mis à jour avec succès.")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))


if is_lecteur:
    with tab_objectifs:
        section_title("🎯", "Objectifs (Général et Spécifiques)", ui_style.SECTION_HELP["objectifs"])
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

    with tab_resultats:
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

    with tab_activites:
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

    with tab_taches:
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

    with tab_indicateurs:
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

    with tab_budget:
        section_title("💰", "Budget du projet")
        tip("budget_fixe_variable", "Pensez à distinguer les coûts fixes (équipements, infrastructure) et variables (consommables, main-d'œuvre).")

        devise_p_ro = projet_row["devise_principale"] or "XOF"
        lignes_budget_ro = crud.get_budget_lignes_by_projet(selected_projet_id)
        total_hierarchique_ro = float(lignes_budget_ro["cout_total"].sum()) if not lignes_budget_ro.empty else 0.0

        budget_projet_ro = float(projet_row["budget"] or 0)
        budget_active_ro = float(activites_df["budget"].fillna(0).sum()) if not activites_df.empty else 0.0
        depenses_projet_ro = crud.get_depenses_by_projet(selected_projet_id)
        depense_reelle_ro = float(depenses_projet_ro["montant"].sum()) if not depenses_projet_ro.empty else 0.0
        reference_ro = total_hierarchique_ro if total_hierarchique_ro > 0 else budget_active_ro
        taux_execution_ro = (depense_reelle_ro / reference_ro * 100) if reference_ro else 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("Budget global du projet", f"{budget_projet_ro:,.0f} {devise_p_ro}".replace(",", " "))
        c2.metric("Budget prévisionnel", f"{reference_ro:,.0f} {devise_p_ro}".replace(",", " "))
        c3.metric("Dépensé réellement", f"{depense_reelle_ro:,.0f} {devise_p_ro}".replace(",", " "), delta=f"{taux_execution_ro:.0f}% exécuté")

        if not lignes_budget_ro.empty:
            st.write("")
            st.markdown("**Budget prévisionnel détaillé par rubrique**")
            recap_rubriques = lignes_budget_ro.groupby("rubrique_nom")["cout_total"].sum().reset_index()
            recap_rubriques.columns = ["Rubrique", f"Total ({devise_p_ro})"]
            st.dataframe(recap_rubriques, use_container_width=True, hide_index=True)

        if not activites_df.empty:
            st.write("")
            st.markdown("**Détail par activité**")
            st.dataframe(
                activites_df[["resultat_titre", "titre", "budget"]].rename(
                    columns={"resultat_titre": "Résultat", "titre": "Activité", "budget": f"Budget ({devise_p_ro})"}
                ),
                use_container_width=True, hide_index=True,
            )
        if not depenses_projet_ro.empty:
            st.write("")
            st.markdown("**Dépenses enregistrées**")
            st.dataframe(
                depenses_projet_ro[["activite_titre", "date_depense", "montant", "description"]].rename(
                    columns={"activite_titre": "Activité", "date_depense": "Date", "montant": "Montant (FCFA)", "description": "Description"}
                ),
                use_container_width=True, hide_index=True,
            )

    with tab_parties:
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

    with tab_documents:
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
                        if storage_service.is_configured():
                            try:
                                contenu_dl_ro = storage_service.download_file(doc["chemin_fichier"])
                                st.download_button(
                                    "⬇️ Télécharger", data=contenu_dl_ro,
                                    file_name=doc["nom_fichier"], key=f"dl_ro_{doc['id']}",
                                    use_container_width=True,
                                )
                            except RuntimeError:
                                st.caption("⚠️ Fichier introuvable dans le stockage")
                        elif os.path.exists(doc["chemin_fichier"]):
                            with open(doc["chemin_fichier"], "rb") as f:
                                st.download_button(
                                    "⬇️ Télécharger", data=f.read(),
                                    file_name=doc["nom_fichier"], key=f"dl_ro_{doc['id']}",
                                    use_container_width=True,
                                )
                        else:
                            st.caption("⚠️ Fichier introuvable")

else:
    with tab_objectifs:
        section_title("🎯", "Objectifs (Général et Spécifiques)", ui_style.SECTION_HELP["objectifs"])
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
            for _, obj in objectifs_df.iterrows():
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1.2])
                    with col1:
                        badge_kind = "muted" if obj["type_objectif"] == "Général" else "success"
                        st.markdown(
                            f"{badge_html(obj['type_objectif'], badge_kind)} <b>{obj['titre'].strip()}</b>",
                            unsafe_allow_html=True,
                        )
                    with col2:
                        st.caption(obj["responsable"] or "Sans responsable")
                    with col3:
                        if st.button("✏️ Modifier", key=f"editbtn_obj_{obj['id']}", use_container_width=True):
                            st.session_state["editing_obj_id"] = None if st.session_state.get("editing_obj_id") == obj["id"] else obj["id"]
                            st.rerun()

                    if st.session_state.get("editing_obj_id") == obj["id"]:
                        type_objectif_edit = st.selectbox(
                            "Type", crud.TYPES_OBJECTIF,
                            index=crud.TYPES_OBJECTIF.index(obj["type_objectif"]) if obj["type_objectif"] in crud.TYPES_OBJECTIF else 0,
                            key=f"type_edit_obj_{obj['id']}",
                        )

                        edit_obj_titre_key = f"edit_obj_titre_{obj['id']}"
                        if edit_obj_titre_key not in st.session_state:
                            st.session_state[edit_obj_titre_key] = obj["titre"]

                        if type_objectif_edit == "Spécifique":
                            boutons_ia_obj = [("🎯 Rendre SMART", "smart")]
                        else:
                            boutons_ia_obj = [("🧭 Rendre plus pertinent", "pertinent")]

                        titre = ai_text_field(
                            "Titre *", key=edit_obj_titre_key, is_area=False,
                            contexte=f"Projet : {projet_row['description'] or ''}",
                            boutons=boutons_ia_obj,
                        )

                        with st.form(f"form_edit_obj_{obj['id']}"):
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
                                st.session_state.pop(edit_obj_titre_key, None)
                                st.toast("✅ Objectif mis à jour avec succès.")
                                st.session_state["editing_obj_id"] = None
                                st.rerun()
                            if col_delete.form_submit_button("🗑️ Supprimer", use_container_width=True):
                                crud.delete_objectif(obj["id"])
                                st.session_state.pop(edit_obj_titre_key, None)
                                st.warning("Objectif supprimé (ainsi que ses résultats, activités et tâches liés).")
                                st.session_state["editing_obj_id"] = None
                                st.rerun()

    # ==============================================================================
    # SECTION : RÉSULTATS
    # ==============================================================================
    with tab_resultats:
        section_title("📈", "Résultats attendus", ui_style.SECTION_HELP["resultats"])
        tip("resultats_indicateurs_2", "Les indicateurs doivent être mesurables — préférez un chiffre précis à une appréciation générale.")

        if objectifs_df.empty:
            st.warning("Créez d'abord un objectif pour pouvoir y attacher un résultat.")
            st.caption("👉 Rendez-vous dans l'onglet **🎯 Objectifs** ci-dessus pour en créer un.")
        else:
            with st.expander("➕ Ajouter un résultat attendu"):
                obj_options = {row["id"]: row["titre"] for _, row in objectifs_df.iterrows()}
                objectif_id = st.selectbox("Objectif concerné *", options=list(obj_options.keys()), format_func=lambda x: obj_options[x], key="new_res_objectif")

                titre_r = st.text_input("Titre *", key="new_res_titre")
                description_r = ai_text_field(
                    "Description", key="new_res_description",
                    contexte=f"Projet : {projet_row['description'] or ''} | Objectif : {obj_options.get(objectif_id, '')}",
                )

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
                c6, c7 = st.columns(2)
                baseline = c6.number_input("Baseline (valeur de départ)", key="new_res_baseline")
                source_verification = c7.text_input("Source de vérification", key="new_res_source", placeholder="ex: rapport de terrain, enquête...")
                if st.button("Ajouter", key="submit_new_resultat"):
                    if not titre_r:
                        st.warning("Le titre est obligatoire.")
                    else:
                        crud.create_resultat(objectif_id, titre_r, description_r, indicateur, valeur_cible, valeur_actuelle, unite, statut_r, source_verification, baseline)
                        for k in ["new_res_titre", "new_res_description", "new_res_indicateur", "new_res_unite", "res_suggestions"]:
                            st.session_state.pop(k, None)
                        st.toast("✅ Résultat ajouté avec succès.")
                        st.rerun()

            if resultats_df.empty:
                st.info("Aucun résultat attendu pour ce projet.")
            else:
                for _, res in resultats_df.iterrows():
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 2, 1.2])
                        with col1:
                            st.markdown(f"**{res['titre']}**")
                            st.caption(f"Objectif : {res['objectif_titre']}")
                        with col2:
                            st.caption(f"{res['indicateur'] or 'Sans indicateur'} — {res['valeur_actuelle']}/{res['valeur_cible']} {res['unite'] or ''}")
                        with col3:
                            if st.button("✏️ Modifier", key=f"editbtn_res_{res['id']}", use_container_width=True):
                                st.session_state["editing_res_id"] = None if st.session_state.get("editing_res_id") == res["id"] else res["id"]
                                st.rerun()

                        indicateurs_suppl = crud.get_indicateurs_supplementaires(res["id"])
                        with st.expander(f"📊 Indicateurs ({1 + len(indicateurs_suppl)})"):
                            st.caption(f"**Principal** — {res['indicateur'] or 'Sans nom'} : {res['valeur_actuelle']}/{res['valeur_cible']} {res['unite'] or ''} *(modifiable via « ✏️ Modifier » ci-dessus)*")
                            if res["baseline"] or res["source_verification"]:
                                st.caption(f"　　Baseline : {res['baseline'] if res['baseline'] is not None else '—'} · Source de vérification : {res['source_verification'] or '—'}")

                            st.write("")
                            st.markdown("**📅 Ventilation temporelle (indicateur principal)**")
                            freq_options = crud.FREQUENCES_VENTILATION
                            freq_actuelle = res["frequence_ventilation"] if res["frequence_ventilation"] in freq_options else "aucune"
                            nouvelle_freq = st.selectbox(
                                "Fréquence", freq_options, index=freq_options.index(freq_actuelle),
                                key=f"freq_res_{res['id']}",
                                help="Planifie une cible par période, pour détecter un retard avant la fin du projet plutôt qu'à la toute fin.",
                            )
                            vc1, vc2 = st.columns(2)
                            date_debut_vent = vc1.date_input(
                                "Début de la ventilation", value=projet_row["date_debut"], key=f"vent_debut_res_{res['id']}",
                                help="Par défaut la date de début du projet — à ajuster si cet indicateur ne démarre réellement que plus tard.",
                            )
                            date_fin_vent = vc2.date_input(
                                "Fin de la ventilation", value=projet_row["date_fin"], key=f"vent_fin_res_{res['id']}",
                            )
                            if st.button("🔄 Générer / régénérer les périodes", key=f"gen_periodes_res_{res['id']}"):
                                if nouvelle_freq != freq_actuelle:
                                    crud.set_frequence_ventilation_resultat(res["id"], nouvelle_freq)
                                if nouvelle_freq == "aucune":
                                    crud.regenerer_periodes_resultat(res["id"], [])
                                elif not validators.dates_valides(date_debut_vent, date_fin_vent):
                                    st.warning("⚠️ La date de fin de ventilation ne peut pas être antérieure à la date de début.")
                                else:
                                    nouvelles_periodes = indicateurs_temporels.generer_periodes(
                                        date_debut_vent, date_fin_vent, nouvelle_freq, cible_finale=res["valeur_cible"] or 0, baseline=res["baseline"] or 0,
                                    )
                                    if not nouvelles_periodes:
                                        st.warning("Impossible de générer des périodes — vérifiez les dates de ventilation.")
                                    else:
                                        crud.regenerer_periodes_resultat(res["id"], nouvelles_periodes)
                                        st.toast(f"✅ {len(nouvelles_periodes)} période(s) générée(s).")
                                        st.rerun()

                            periodes_res = crud.get_periodes_resultat(res["id"])
                            if not periodes_res.empty:
                                periodes_liste = periodes_res.to_dict("records")
                                for p in periodes_liste:
                                    p["label"] = p.pop("periode_label")
                                periodes_calc = indicateurs_temporels.calculer_statuts_cumules(
                                    sorted(periodes_liste, key=lambda p: p["date_debut"])
                                )
                                badge_par_statut = {"Conforme": "success", "En avance": "success", "En retard": "warning", "Critique": "danger", "À venir": "muted"}
                                with st.form(f"form_periodes_res_{res['id']}"):
                                    for pc in periodes_calc:
                                        pcol1, pcol2, pcol3, pcol4 = st.columns([2, 1.3, 1.3, 1.6])
                                        pcol1.write(f"**{pc['label']}**")
                                        pcol2.caption(f"Cible : {pc['cible_periode']:.1f}")
                                        pc["realise_edit"] = pcol3.number_input(
                                            "Réalisé", value=float(pc["realise_periode"] or 0), key=f"realise_{pc['id']}", label_visibility="collapsed",
                                        )
                                        pcol4.markdown(badge_html(pc["statut"], badge_par_statut.get(pc["statut"], "muted")), unsafe_allow_html=True)
                                    if st.form_submit_button("💾 Enregistrer les réalisations", use_container_width=True):
                                        for pc in periodes_calc:
                                            crud.update_periode(pc["id"], pc["cible_periode"], pc["realise_edit"], est_resultat=True)
                                        st.toast("✅ Réalisations enregistrées avec succès.")
                                        st.rerun()

                            for _, ind in indicateurs_suppl.iterrows():
                                ic1, ic2, ic3 = st.columns([3, 1.5, 1])
                                with ic1:
                                    st.write(f"**{ind['nom']}**")
                                with ic2:
                                    st.caption(f"{ind['valeur_actuelle']}/{ind['valeur_cible']} {ind['unite'] or ''}")
                                with ic3:
                                    if st.button("✏️", key=f"editbtn_ind_{ind['id']}", use_container_width=True, help="Modifier"):
                                        st.session_state["editing_ind_id"] = None if st.session_state.get("editing_ind_id") == ind["id"] else ind["id"]
                                        st.rerun()

                                if st.session_state.get("editing_ind_id") == ind["id"]:
                                    with st.form(f"form_edit_ind_{ind['id']}"):
                                        nom_ind = st.text_input("Nom de l'indicateur *", value=ind["nom"])
                                        jc1, jc2, jc3 = st.columns(3)
                                        cible_ind = jc1.number_input("Valeur cible", value=float(ind["valeur_cible"] or 0), key=f"cible_ind_{ind['id']}")
                                        actuelle_ind = jc2.number_input("Valeur actuelle", value=float(ind["valeur_actuelle"] or 0), key=f"actuelle_ind_{ind['id']}")
                                        unite_ind = jc3.text_input("Unité", value=ind["unite"] or "", key=f"unite_ind_{ind['id']}")
                                        jc4, jc5 = st.columns(2)
                                        baseline_ind = jc4.number_input("Baseline", value=float(ind["baseline"] or 0), key=f"baseline_ind_{ind['id']}")
                                        source_ind = jc5.text_input("Source de vérification", value=ind["source_verification"] or "", key=f"source_ind_{ind['id']}")
                                        col_save_ind, col_del_ind = st.columns(2)
                                        if col_save_ind.form_submit_button("💾 Enregistrer", use_container_width=True):
                                            if not nom_ind:
                                                st.warning("Le nom est obligatoire.")
                                            else:
                                                crud.update_indicateur_supplementaire(ind["id"], nom_ind, cible_ind, actuelle_ind, unite_ind, baseline_ind, source_ind)
                                                st.toast("✅ Indicateur mis à jour avec succès.")
                                                st.session_state["editing_ind_id"] = None
                                                st.rerun()
                                        if col_del_ind.form_submit_button("🗑️ Supprimer", use_container_width=True):
                                            crud.delete_indicateur_supplementaire(ind["id"])
                                            st.warning("Indicateur supprimé.")
                                            st.session_state["editing_ind_id"] = None
                                            st.rerun()

                                    st.markdown("**📅 Ventilation temporelle**")
                                    freq_options_ind = crud.FREQUENCES_VENTILATION
                                    freq_actuelle_ind = ind["frequence_ventilation"] if ind["frequence_ventilation"] in freq_options_ind else "aucune"
                                    nouvelle_freq_ind = st.selectbox(
                                        "Fréquence", freq_options_ind, index=freq_options_ind.index(freq_actuelle_ind),
                                        key=f"freq_ind_{ind['id']}",
                                        help="Planifie une cible par période, pour détecter un retard avant la fin du projet plutôt qu'à la toute fin.",
                                    )
                                    vc1_ind, vc2_ind = st.columns(2)
                                    date_debut_vent_ind = vc1_ind.date_input(
                                        "Début de la ventilation", value=projet_row["date_debut"], key=f"vent_debut_ind_{ind['id']}",
                                        help="Par défaut la date de début du projet — à ajuster si cet indicateur ne démarre réellement que plus tard.",
                                    )
                                    date_fin_vent_ind = vc2_ind.date_input(
                                        "Fin de la ventilation", value=projet_row["date_fin"], key=f"vent_fin_ind_{ind['id']}",
                                    )
                                    if st.button("🔄 Générer / régénérer les périodes", key=f"gen_periodes_ind_{ind['id']}"):
                                        if nouvelle_freq_ind != freq_actuelle_ind:
                                            crud.set_frequence_ventilation_indicateur_suppl(ind["id"], nouvelle_freq_ind)
                                        if nouvelle_freq_ind == "aucune":
                                            crud.regenerer_periodes_indicateur_suppl(ind["id"], [])
                                        elif not validators.dates_valides(date_debut_vent_ind, date_fin_vent_ind):
                                            st.warning("⚠️ La date de fin de ventilation ne peut pas être antérieure à la date de début.")
                                        else:
                                            nouvelles_periodes_ind = indicateurs_temporels.generer_periodes(
                                                date_debut_vent_ind, date_fin_vent_ind, nouvelle_freq_ind, cible_finale=ind["valeur_cible"] or 0, baseline=ind["baseline"] or 0,
                                            )
                                            if not nouvelles_periodes_ind:
                                                st.warning("Impossible de générer des périodes — vérifiez les dates de ventilation.")
                                            else:
                                                crud.regenerer_periodes_indicateur_suppl(ind["id"], nouvelles_periodes_ind)
                                                st.toast(f"✅ {len(nouvelles_periodes_ind)} période(s) générée(s).")
                                                st.rerun()

                                    periodes_ind_df = crud.get_periodes_indicateur_supplementaire(ind["id"])
                                    if not periodes_ind_df.empty:
                                        periodes_ind_liste = periodes_ind_df.to_dict("records")
                                        for p in periodes_ind_liste:
                                            p["label"] = p.pop("periode_label")
                                        periodes_ind_calc = indicateurs_temporels.calculer_statuts_cumules(
                                            sorted(periodes_ind_liste, key=lambda p: p["date_debut"])
                                        )
                                        badge_par_statut_ind = {"Conforme": "success", "En avance": "success", "En retard": "warning", "Critique": "danger", "À venir": "muted"}
                                        with st.form(f"form_periodes_ind_{ind['id']}"):
                                            for pc in periodes_ind_calc:
                                                pcol1, pcol2, pcol3, pcol4 = st.columns([2, 1.3, 1.3, 1.6])
                                                pcol1.write(f"**{pc['label']}**")
                                                pcol2.caption(f"Cible : {pc['cible_periode']:.1f}")
                                                pc["realise_edit"] = pcol3.number_input(
                                                    "Réalisé", value=float(pc["realise_periode"] or 0), key=f"realise_ind_{pc['id']}", label_visibility="collapsed",
                                                )
                                                pcol4.markdown(badge_html(pc["statut"], badge_par_statut_ind.get(pc["statut"], "muted")), unsafe_allow_html=True)
                                            if st.form_submit_button("💾 Enregistrer les réalisations", use_container_width=True):
                                                for pc in periodes_ind_calc:
                                                    crud.update_periode(pc["id"], pc["cible_periode"], pc["realise_edit"], est_resultat=False)
                                                st.toast("✅ Réalisations enregistrées avec succès.")
                                                st.rerun()

                            st.divider()
                            st.caption("➕ Ajouter un indicateur")
                            with st.form(f"form_new_ind_{res['id']}", clear_on_submit=True):
                                nom_new_ind = st.text_input("Nom de l'indicateur *")
                                kc1, kc2, kc3 = st.columns(3)
                                cible_new_ind = kc1.number_input("Valeur cible", key=f"new_ind_cible_{res['id']}")
                                actuelle_new_ind = kc2.number_input("Valeur actuelle", key=f"new_ind_actuelle_{res['id']}")
                                unite_new_ind = kc3.text_input("Unité", key=f"new_ind_unite_{res['id']}")
                                kc4, kc5 = st.columns(2)
                                baseline_new_ind = kc4.number_input("Baseline", key=f"new_ind_baseline_{res['id']}")
                                source_new_ind = kc5.text_input("Source de vérification", key=f"new_ind_source_{res['id']}")
                                if st.form_submit_button("Ajouter un indicateur", use_container_width=True):
                                    if not nom_new_ind:
                                        st.warning("Le nom est obligatoire.")
                                    else:
                                        crud.create_indicateur_supplementaire(res["id"], nom_new_ind, cible_new_ind, actuelle_new_ind, unite_new_ind, baseline_new_ind, source_new_ind)
                                        st.toast("✅ Indicateur ajouté avec succès.")
                                        st.rerun()

                        if st.session_state.get("editing_res_id") == res["id"]:
                            edit_key = f"edit_res_description_{res['id']}"
                            if edit_key not in st.session_state:
                                st.session_state[edit_key] = res["description"] or ""

                            titre_r = st.text_input("Titre *", value=res["titre"], key=f"edit_res_titre_{res['id']}")
                            description_r = ai_text_field(
                                "Description", key=edit_key,
                                contexte=f"Résultat : {res['titre']} | Indicateur : {res['indicateur'] or ''}",
                            )

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
                                c6, c7 = st.columns(2)
                                baseline = c6.number_input("Baseline (valeur de départ)", value=float(res["baseline"] or 0))
                                source_verification = c7.text_input("Source de vérification", value=res["source_verification"] or "")
                                col_save, col_delete = st.columns(2)
                                if col_save.form_submit_button("💾 Enregistrer", use_container_width=True):
                                    crud.update_resultat(res["id"], titre_r, st.session_state[edit_key], indicateur, valeur_cible, valeur_actuelle, unite, statut_r, source_verification, baseline)
                                    st.toast("✅ Résultat mis à jour avec succès.")
                                    st.session_state["editing_res_id"] = None
                                    st.rerun()
                                if col_delete.form_submit_button("🗑️ Supprimer", use_container_width=True):
                                    crud.delete_resultat(res["id"])
                                    st.warning("Résultat supprimé (ainsi que ses activités et tâches liées).")
                                    st.session_state["editing_res_id"] = None
                                    st.rerun()

    # ==============================================================================
    # SECTION : ACTIVITÉS
    # ==============================================================================
    with tab_activites:
        section_title("📅", "Activités", ui_style.SECTION_HELP["activites"])

        if resultats_df.empty:
            st.warning("Créez d'abord un résultat attendu pour pouvoir y attacher une activité.")
            st.caption("👉 Rendez-vous dans l'onglet **📈 Résultats** ci-dessus pour en créer un.")
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
                    depend_options = {None: "— Aucune (activité de départ) —"}
                    for _, a in activites_df.iterrows():
                        if not validators.depend_coherent(date_debut_a, a["date_fin"]):
                            depend_options[a["id"]] = f"⚠️ {a['titre']} (se termine après le début de cette activité)"
                        else:
                            depend_options[a["id"]] = f"✅ {a['titre']}"
                    depend_de_a = st.selectbox(
                        "Dépend de (doit démarrer après cette activité)",
                        options=list(depend_options.keys()), format_func=lambda x: depend_options[x],
                        help="Nécessaire pour calculer le chemin critique dans le diagramme de Gantt. Les options marquées ⚠️ seront refusées à l'enregistrement.",
                    )
                    observation_a = st.text_area(
                        "Observation (facultatif)", placeholder="Difficultés, contraintes ou événements particuliers rencontrés...",
                        help="Utilisée par l'IA pour expliquer un taux de réalisation dans les rapports générés, pas seulement le constater.",
                    )
                    if st.form_submit_button("Ajouter"):
                        date_fin_predecesseur_a = (
                            activites_df[activites_df["id"] == depend_de_a].iloc[0]["date_fin"]
                            if depend_de_a is not None and not activites_df.empty else None
                        )
                        if not titre_a:
                            st.warning("Le titre est obligatoire.")
                        elif not validators.dates_valides(date_debut_a, date_fin_a):
                            st.warning("⚠️ La date de fin ne peut pas être antérieure à la date de début.")
                        elif not validators.depend_coherent(date_debut_a, date_fin_predecesseur_a):
                            titre_predecesseur_a = activites_df[activites_df["id"] == depend_de_a].iloc[0]["titre"]
                            st.warning(
                                f"⚠️ Cette activité ne peut pas dépendre de « {titre_predecesseur_a} », "
                                f"qui se termine après sa propre date de début. Corrigez les dates ou changez la dépendance."
                            )
                        else:
                            crud.create_activite(resultat_id, titre_a, description_a, responsable_id_a, date_debut_a, date_fin_a, statut_a, budget_a, progression_a, depend_de_a, observation_a)
                            st.session_state.pop("act_suggestions", None)
                            st.toast("✅ Activité ajoutée avec succès.")
                            st.rerun()

            if activites_df.empty:
                st.info("Aucune activité pour ce projet.")
            else:
                for _, act in activites_df.iterrows():
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 2, 1.2])
                        with col1:
                            st.markdown(f"**{act['titre']}**")
                            st.caption(f"Résultat : {act['resultat_titre']}")
                        with col2:
                            st.caption(f"{act['statut']} — {act['progression'] or 0}% — {act['responsable'] or 'Sans responsable'}")
                        with col3:
                            if st.button("✏️ Modifier", key=f"editbtn_act_{act['id']}", use_container_width=True):
                                st.session_state["editing_act_id"] = None if st.session_state.get("editing_act_id") == act["id"] else act["id"]
                                st.rerun()

                        if st.session_state.get("editing_act_id") == act["id"]:
                            with st.form(f"form_edit_act_{act['id']}"):
                                titre_a = st.text_input("Titre *", value=act["titre"])
                                description_a = st.text_area("Description", value=act["description"] or "")
                                c1, c2 = st.columns(2)
                                date_debut_a = c1.date_input("Date de début", value=act["date_debut"])
                                date_fin_a = c2.date_input("Date de fin", value=act["date_fin"])
                                c3, c4 = st.columns(2)
                                budget_a = c3.number_input("Budget (FCFA)", min_value=0.0, value=float(act["budget"] or 0))

                                a_des_taches = not taches_df[taches_df["activite_id"] == act["id"]].empty if not taches_df.empty else False
                                progression_a = c4.slider(
                                    "Progression (%)", 0, 100, int(act["progression"] or 0),
                                    disabled=a_des_taches,
                                    help="Calculée automatiquement à partir des tâches de cette activité." if a_des_taches else None,
                                )
                                if a_des_taches:
                                    st.caption("🔒 Cette activité a des tâches — sa progression est calculée automatiquement à partir d'elles (moyenne de leur avancement, « Terminé » seulement si toutes le sont).")

                                statut_a = st.selectbox(
                                    "Statut", crud.STATUTS_GENERIQUE,
                                    index=crud.STATUTS_GENERIQUE.index(act["statut"]) if act["statut"] in crud.STATUTS_GENERIQUE else 0,
                                    disabled=a_des_taches,
                                )
                                resp_options = responsable_options()
                                current_resp = act["responsable_id"] if act["responsable_id"] in resp_options else None
                                responsable_id_a = st.selectbox(
                                    "Responsable", options=list(resp_options.keys()), format_func=lambda x: resp_options[x],
                                    index=list(resp_options.keys()).index(current_resp),
                                )

                                autres_activites = activites_df[activites_df["id"] != act["id"]] if not activites_df.empty else activites_df
                                depend_options = {None: "— Aucune (activité de départ) —"}
                                for _, a2 in autres_activites.iterrows():
                                    if validators.cree_une_boucle(act["id"], a2["id"], activites_df):
                                        depend_options[a2["id"]] = f"⚠️ {a2['titre']} (créerait une boucle)"
                                    elif not validators.depend_coherent(act["date_debut"], a2["date_fin"]):
                                        depend_options[a2["id"]] = f"⚠️ {a2['titre']} (se termine après le début de cette activité)"
                                    else:
                                        depend_options[a2["id"]] = f"✅ {a2['titre']}"
                                current_depend = act["depend_de_activite_id"] if act["depend_de_activite_id"] in depend_options else None
                                depend_de_a = st.selectbox(
                                    "Dépend de (doit démarrer après cette activité)",
                                    options=list(depend_options.keys()), format_func=lambda x: depend_options[x],
                                    index=list(depend_options.keys()).index(current_depend),
                                    help="Nécessaire pour calculer le chemin critique dans le diagramme de Gantt. Les options marquées ⚠️ seront refusées à l'enregistrement.",
                                )
                                st.caption("💡 Basé sur la date de début actuellement enregistrée — si vous modifiez cette date dans le formulaire, les repères ✅/⚠️ ne se mettront à jour qu'après l'enregistrement.")

                                observation_edit_a = st.text_area(
                                    "Observation (facultatif)", value=act["observation"] or "",
                                    placeholder="Difficultés, contraintes ou événements particuliers rencontrés...",
                                    help="Utilisée par l'IA pour expliquer un taux de réalisation dans les rapports générés, pas seulement le constater.",
                                )

                                col_save, col_delete = st.columns(2)
                                if col_save.form_submit_button("💾 Enregistrer", use_container_width=True):
                                    date_fin_predecesseur_edit = (
                                        activites_df[activites_df["id"] == depend_de_a].iloc[0]["date_fin"]
                                        if depend_de_a is not None else None
                                    )
                                    if not validators.dates_valides(date_debut_a, date_fin_a):
                                        st.warning("⚠️ La date de fin ne peut pas être antérieure à la date de début.")
                                    elif validators.cree_une_boucle(act["id"], depend_de_a, activites_df):
                                        st.warning("⚠️ Cette dépendance créerait une boucle (une activité ne peut pas dépendre, même indirectement, d'elle-même).")
                                    elif not validators.depend_coherent(date_debut_a, date_fin_predecesseur_edit):
                                        titre_predecesseur = activites_df[activites_df["id"] == depend_de_a].iloc[0]["titre"]
                                        st.warning(
                                            f"⚠️ Cette activité ne peut pas dépendre de « {titre_predecesseur} », "
                                            f"qui se termine après sa propre date de début. Corrigez les dates ou changez la dépendance."
                                        )
                                    else:
                                        # Si l'activité a des tâches, on garde la progression/le statut déjà
                                        # calculés automatiquement plutôt que d'écraser avec les champs désactivés.
                                        progression_finale = float(act["progression"] or 0) if a_des_taches else progression_a
                                        statut_final = act["statut"] if a_des_taches else statut_a
                                        crud.update_activite(act["id"], titre_a, description_a, responsable_id_a, date_debut_a, date_fin_a, statut_final, budget_a, progression_finale, depend_de_a, observation_edit_a)
                                        st.toast("✅ Activité mise à jour avec succès.")
                                        st.session_state["editing_act_id"] = None
                                        st.rerun()
                                if col_delete.form_submit_button("🗑️ Supprimer", use_container_width=True):
                                    crud.delete_activite(act["id"])
                                    st.warning("Activité supprimée (ainsi que ses tâches liées).")
                                    st.session_state["editing_act_id"] = None
                                    st.rerun()

    # ==============================================================================
    # SECTION : TÂCHES
    # ==============================================================================
    with tab_taches:
        section_title("✅", "Tâches", ui_style.SECTION_HELP["taches"])

        if activites_df.empty:
            st.warning("Créez d'abord une activité pour pouvoir y attacher une tâche.")
            st.caption("👉 Rendez-vous dans l'onglet **📅 Activités** ci-dessus pour en créer une.")
        else:
            with st.expander("➕ Ajouter une tâche"):
                act_options = {row["id"]: f"{row['titre']} ({row['resultat_titre']})" for _, row in activites_df.iterrows()}
                activite_id = st.selectbox("Activité concernée *", options=list(act_options.keys()), format_func=lambda x: act_options[x], key="new_tache_activite")
                act_row = activites_df[activites_df["id"] == activite_id].iloc[0]

                if st.button("✨ Suggérer des tâches avec l'IA", key="suggest_tache_btn"):
                    try:
                        with st.spinner("L'IA réfléchit..."):
                            suggestions = ai_text_assist.suggest_items(
                                "taches", projet_row["description"] or "", act_row["titre"],
                            )
                        st.session_state["tache_suggestions"] = suggestions
                    except RuntimeError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Erreur IA : {e}")

                if st.session_state.get("tache_suggestions"):
                    st.caption("Suggestions de l'IA — cliquez sur ➕ pour ajouter directement :")
                    for i, sugg in enumerate(st.session_state["tache_suggestions"]):
                        c1, c2 = st.columns([5, 1])
                        with c1:
                            st.write(f"**{sugg.get('titre', '')}**")
                            st.caption(sugg.get("description", ""))
                        with c2:
                            if st.button("➕ Ajouter", key=f"add_suggestion_tache_{i}", use_container_width=True):
                                crud.create_tache(
                                    activite_id, sugg.get("titre", ""), sugg.get("description", ""),
                                    None, "Moyenne", "À faire", None, None, 0,
                                )
                                crud.recalculate_activite_progression(activite_id)
                                st.toast("✅ Tâche ajoutée avec succès.")
                                st.rerun()

                titre_t = st.text_input("Titre *", key="new_tache_titre")
                description_t = st.text_area("Description", key="new_tache_description")
                c1, c2 = st.columns(2)
                priorite_t = c1.selectbox("Priorité", crud.PRIORITES_TACHE, key="new_tache_priorite")
                statut_t = c2.selectbox("Statut", crud.STATUTS_GENERIQUE, key="new_tache_statut")
                c3, c4 = st.columns(2)
                date_debut_t = c3.date_input("Date de début", value=None, key="new_tache_debut")
                date_fin_t = c4.date_input("Date de fin", value=None, key="new_tache_fin")
                st.caption(f"📅 Période de l'activité « {act_row['titre']} » : {act_row['date_debut'] or 'non définie'} → {act_row['date_fin'] or 'non définie'}")
                progression_t = st.slider("Progression (%)", 0, 100, 0, key="new_tache_progression")
                resp_options = responsable_options()
                responsable_id_t = st.selectbox("Responsable", options=list(resp_options.keys()), format_func=lambda x: resp_options[x], key="new_tache_responsable")

                if st.button("Ajouter", key="submit_new_tache"):
                    if not titre_t:
                        st.warning("Le titre est obligatoire.")
                    elif not validators.dates_valides(date_debut_t, date_fin_t):
                        st.warning("⚠️ La date de fin ne peut pas être antérieure à la date de début. Corrigez les dates ci-dessus et réessayez.")
                    elif not validators.tache_dans_intervalle_activite(date_debut_t, date_fin_t, act_row["date_debut"], act_row["date_fin"]):
                        st.warning(
                            f"⚠️ Les dates de la tâche doivent rester dans la période de l'activité "
                            f"« {act_row['titre']} » ({act_row['date_debut']} → {act_row['date_fin']}). "
                            "Corrigez les dates ci-dessus et réessayez — le reste de vos informations est conservé."
                        )
                    else:
                        crud.create_tache(activite_id, titre_t, description_t, responsable_id_t, priorite_t, statut_t, date_debut_t, date_fin_t, progression_t)
                        crud.recalculate_activite_progression(activite_id)
                        for k in ["new_tache_titre", "new_tache_description", "new_tache_debut", "new_tache_fin", "new_tache_progression", "tache_suggestions"]:
                            st.session_state.pop(k, None)
                        st.toast("✅ Tâche ajoutée avec succès.")
                        st.rerun()

            if taches_df.empty:
                st.info("Aucune tâche pour ce projet.")
            else:
                for _, tache in taches_df.iterrows():
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 2, 1.2])
                        with col1:
                            st.markdown(f"**{tache['titre']}**")
                            st.caption(f"Activité : {tache['activite_titre']}")
                        with col2:
                            st.caption(f"{tache['priorite']} — {tache['statut']} — {tache['progression'] or 0}%")
                        with col3:
                            if st.button("✏️ Modifier", key=f"editbtn_tache_{tache['id']}", use_container_width=True):
                                st.session_state["editing_tache_id"] = None if st.session_state.get("editing_tache_id") == tache["id"] else tache["id"]
                                st.rerun()

                        if st.session_state.get("editing_tache_id") == tache["id"]:
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
                                _act_row_for_caption = activites_df[activites_df["id"] == tache["activite_id"]].iloc[0]
                                st.caption(f"📅 Période de l'activité « {_act_row_for_caption['titre']} » : {_act_row_for_caption['date_debut'] or 'non définie'} → {_act_row_for_caption['date_fin'] or 'non définie'}")
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
                                            f"« {act_row['titre']} » ({act_row['date_debut']} → {act_row['date_fin']}). "
                                            "Corrigez les dates ci-dessus et réessayez — le reste de vos informations est conservé."
                                        )
                                    else:
                                        crud.update_tache(tache["id"], titre_t, description_t, responsable_id_t, priorite_t, statut_t, date_debut_t, date_fin_t, progression_t)
                                        crud.recalculate_activite_progression(tache["activite_id"])
                                        st.toast("✅ Tâche mise à jour avec succès.")
                                        st.session_state["editing_tache_id"] = None
                                        st.rerun()
                                if col_delete.form_submit_button("🗑️ Supprimer", use_container_width=True):
                                    crud.delete_tache(tache["id"])
                                    crud.recalculate_activite_progression(tache["activite_id"])
                                    st.warning("Tâche supprimée.")
                                    st.session_state["editing_tache_id"] = None
                                    st.rerun()

    # ==============================================================================
    # SECTION : INDICATEURS (vue transversale sur tous les résultats du projet)
    # ==============================================================================
    with tab_indicateurs:
        section_title("📊", "Indicateurs de suivi")
        tip("indicateurs_mesurables_2", "Les indicateurs doivent être mesurables : donnez toujours une valeur cible et une unité claire.")
        st.caption("Mettez à jour rapidement la valeur actuelle de chaque indicateur, sans naviguer dans la hiérarchie.")

        indicateurs_df = resultats_df[resultats_df["indicateur"].notna() & (resultats_df["indicateur"] != "")] if not resultats_df.empty else resultats_df
        indicateurs_suppl_df = crud.get_indicateurs_supplementaires_by_projet(selected_projet_id)

        if indicateurs_df.empty and indicateurs_suppl_df.empty:
            st.info(
                "Aucun indicateur défini. Les indicateurs se définissent au niveau des résultats attendus "
                "(champ « Indicateur » du formulaire, ou bouton « ➕ Ajouter un indicateur »)."
            )
            st.caption("👉 Rendez-vous dans l'onglet **📈 Résultats** ci-dessus pour en créer un.")
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

            for _, row in indicateurs_suppl_df.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**{row['nom']}**")
                        st.caption(f"{row['resultat_titre']} — {row['objectif_titre']}")
                    with c2:
                        st.metric("Cible", f"{row['valeur_cible']:.0f} {row['unite'] or ''}")
                    with c3:
                        new_val = st.number_input(
                            "Valeur actuelle", value=float(row["valeur_actuelle"] or 0),
                            key=f"indic_suppl_val_{row['id']}", label_visibility="visible",
                        )
                        if st.button("Mettre à jour", key=f"indic_suppl_update_{row['id']}", use_container_width=True):
                            crud.update_indicateur_supplementaire(row["id"], row["nom"], row["valeur_cible"], new_val, row["unite"])
                            st.toast("✅ Indicateur mis à jour avec succès.")
                            st.rerun()

    # ==============================================================================
    # SECTION : BUDGET
    # ==============================================================================
    with tab_budget:
        section_title("💰", "Budget du projet")
        tip("budget_fixe_variable_2", "Pensez à distinguer les coûts fixes (équipements, infrastructure) et variables (consommables, main-d'œuvre).")

        devise_p = projet_row["devise_principale"] or "XOF"
        devise_s = projet_row["devise_secondaire"] or "EUR"
        taux_conv = float(projet_row["taux_conversion"] or 1)

        with st.expander(f"💱 Devise du projet ({devise_p} → {devise_s}, taux actuel : 1 {devise_s} = {taux_conv:,.2f} {devise_p})".replace(",", " ")):
            with st.form("form_devise_projet"):
                dc1, dc2, dc3 = st.columns(3)
                nouvelle_devise_p = dc1.text_input("Devise principale", value=devise_p, help="Ex: XOF, GMD, USD...")
                nouvelle_devise_s = dc2.text_input("Devise secondaire", value=devise_s, help="Ex: EUR, USD...")
                nouveau_taux = dc3.number_input(f"1 {nouvelle_devise_s} = combien de {nouvelle_devise_p} ?", min_value=0.000001, value=taux_conv, step=0.01, format="%.4f")
                st.caption("Modifier le taux ne change aucun montant déjà enregistré dans la devise principale — seule la conversion affichée change.")
                if st.form_submit_button("💾 Enregistrer", use_container_width=True):
                    crud.update_devise_projet(selected_projet_id, nouvelle_devise_p.upper(), nouvelle_devise_s.upper(), nouveau_taux)
                    st.toast("✅ Configuration devise mise à jour avec succès.")
                    st.rerun()

        # ------------------------------------------------------------------------
        # Budget prévisionnel détaillé (Rubriques → Sous-rubriques → Lignes)
        # ------------------------------------------------------------------------
        st.write("")
        st.markdown("**📊 Budget prévisionnel détaillé**")

        lignes_budget_df = crud.get_budget_lignes_by_projet(selected_projet_id)
        rubriques_df = crud.get_budget_rubriques(selected_projet_id)

        total_hierarchique = float(lignes_budget_df["cout_total"].sum()) if not lignes_budget_df.empty else 0.0
        total_hierarchique_secondaire = (total_hierarchique / taux_conv) if taux_conv else 0.0

        tc1, tc2 = st.columns(2)
        tc1.metric(f"Budget prévisionnel total ({devise_p})", f"{total_hierarchique:,.0f}".replace(",", " "))
        tc2.metric(f"Équivalent ({devise_s})", f"{total_hierarchique_secondaire:,.2f}".replace(",", " "))

        with st.expander("➕ Ajouter une rubrique"):
            with st.form("form_new_rubrique", clear_on_submit=True):
                nom_rub = st.text_input("Nom de la rubrique *", placeholder="ex: RH, Équipements, Transport...")
                rc1, rc2 = st.columns(2)
                desc_rub = rc1.text_input("Description (facultatif)")
                code_rub = rc2.text_input("Code budgétaire (facultatif)")
                if st.form_submit_button("Ajouter", use_container_width=True):
                    if not nom_rub:
                        st.warning("Le nom de la rubrique est obligatoire.")
                    else:
                        crud.create_budget_rubrique(selected_projet_id, nom_rub, desc_rub, code_rub)
                        st.toast(f"✅ Rubrique « {nom_rub} » ajoutée avec succès.")
                        st.rerun()

        if rubriques_df.empty:
            st.info("Aucune rubrique budgétaire pour l'instant. Commencez par en ajouter une ci-dessus (ex: RH, Équipements, Transport).")
        else:
            for _, rubrique in rubriques_df.iterrows():
                lignes_rubrique = lignes_budget_df[lignes_budget_df["rubrique_id"] == rubrique["id"]] if not lignes_budget_df.empty else lignes_budget_df
                total_rubrique = float(lignes_rubrique["cout_total"].sum()) if not lignes_rubrique.empty else 0.0

                with st.expander(f"📁 {rubrique['nom']} — {total_rubrique:,.0f} {devise_p}".replace(",", " ")):
                    if rubrique["description"] or rubrique["code_budgetaire"]:
                        st.caption(f"{rubrique['description'] or ''} {'· Code : ' + rubrique['code_budgetaire'] if rubrique['code_budgetaire'] else ''}")

                    rbc1, rbc2 = st.columns(2)
                    if rbc1.button("✏️ Modifier / Supprimer la rubrique", key=f"toggle_edit_rub_{rubrique['id']}", use_container_width=True):
                        st.session_state["editing_rubrique_id"] = None if st.session_state.get("editing_rubrique_id") == rubrique["id"] else rubrique["id"]
                        st.rerun()

                    if st.session_state.get("editing_rubrique_id") == rubrique["id"]:
                        with st.form(f"form_edit_rub_{rubrique['id']}"):
                            nom_rub_edit = st.text_input("Nom", value=rubrique["nom"])
                            erc1, erc2 = st.columns(2)
                            desc_rub_edit = erc1.text_input("Description", value=rubrique["description"] or "")
                            code_rub_edit = erc2.text_input("Code budgétaire", value=rubrique["code_budgetaire"] or "")
                            esave, edel = st.columns(2)
                            if esave.form_submit_button("💾 Enregistrer", use_container_width=True):
                                crud.update_budget_rubrique(rubrique["id"], nom_rub_edit, desc_rub_edit, code_rub_edit)
                                st.toast("✅ Rubrique mise à jour avec succès.")
                                st.session_state["editing_rubrique_id"] = None
                                st.rerun()
                            if edel.form_submit_button("🗑️ Supprimer la rubrique", use_container_width=True):
                                crud.delete_budget_rubrique(rubrique["id"])
                                st.warning("Rubrique supprimée (ainsi que ses sous-rubriques et lignes).")
                                st.session_state["editing_rubrique_id"] = None
                                st.rerun()

                    st.divider()

                    sous_rubriques_df = crud.get_budget_sous_rubriques(rubrique["id"])

                    if sous_rubriques_df.empty:
                        st.caption("Aucune sous-rubrique pour l'instant.")
                    else:
                        for _, sr in sous_rubriques_df.iterrows():
                            lignes_sr = lignes_rubrique[lignes_rubrique["sous_rubrique_id"] == sr["id"]] if not lignes_rubrique.empty else lignes_rubrique
                            total_sr = float(lignes_sr["cout_total"].sum()) if not lignes_sr.empty else 0.0

                            with st.container(border=True):
                                st.markdown(f"**📂 {sr['nom']} — {total_sr:,.0f} {devise_p}**".replace(",", " "))

                                if not lignes_sr.empty:
                                    for _, ligne in lignes_sr.iterrows():
                                        lc1, lc2 = st.columns([5, 1])
                                        with lc1:
                                            rattachement = f" · rattachée à « {ligne['activite_titre']} »" if ligne["activite_titre"] else ""
                                            st.write(f"• {ligne['description']} — {ligne['quantite']:.0f} {ligne['unite']} × {ligne['cout_unitaire']:,.0f} = **{ligne['cout_total']:,.0f} {devise_p}**{rattachement}".replace(",", " "))
                                        with lc2:
                                            if st.button("✏️", key=f"edit_ligne_btn_{ligne['id']}", use_container_width=True, help="Modifier / supprimer"):
                                                st.session_state["editing_ligne_id"] = None if st.session_state.get("editing_ligne_id") == ligne["id"] else ligne["id"]
                                                st.rerun()

                                        if st.session_state.get("editing_ligne_id") == ligne["id"]:
                                            with st.form(f"form_edit_ligne_{ligne['id']}"):
                                                desc_ligne_e = st.text_input("Description *", value=ligne["description"])
                                                lec1, lec2, lec3 = st.columns(3)
                                                unite_options = crud.UNITES_BUDGET
                                                unite_idx = unite_options.index(ligne["unite"]) if ligne["unite"] in unite_options else len(unite_options) - 1
                                                unite_e = lec1.selectbox("Unité", unite_options, index=unite_idx, key=f"unite_e_{ligne['id']}")
                                                if unite_e == "autre":
                                                    unite_e = lec1.text_input("Préciser l'unité", value=ligne["unite"], key=f"unite_e_libre_{ligne['id']}")
                                                quantite_e = lec2.number_input("Quantité", min_value=0.0, value=float(ligne["quantite"]), key=f"qte_e_{ligne['id']}")
                                                cout_e = lec3.number_input(f"Coût unitaire ({devise_p})", min_value=0.0, value=float(ligne["cout_unitaire"]), key=f"cout_e_{ligne['id']}")
                                                act_options_ligne = {None: "— Aucune —"}
                                                for _, a in activites_df.iterrows():
                                                    act_options_ligne[a["id"]] = a["titre"]
                                                current_act = ligne["activite_id"] if ligne["activite_id"] in act_options_ligne else None
                                                activite_liee_e = st.selectbox(
                                                    "Activité associée (facultatif)", options=list(act_options_ligne.keys()),
                                                    format_func=lambda x: act_options_ligne[x],
                                                    index=list(act_options_ligne.keys()).index(current_act),
                                                    key=f"act_e_{ligne['id']}",
                                                )
                                                lsave, ldel = st.columns(2)
                                                if lsave.form_submit_button("💾 Enregistrer", use_container_width=True):
                                                    if not desc_ligne_e or not unite_e:
                                                        st.warning("La description et l'unité sont obligatoires.")
                                                    else:
                                                        crud.update_budget_ligne(ligne["id"], desc_ligne_e, unite_e, quantite_e, cout_e, activite_liee_e)
                                                        st.toast("✅ Ligne mise à jour avec succès.")
                                                        st.session_state["editing_ligne_id"] = None
                                                        st.rerun()
                                                if ldel.form_submit_button("🗑️ Supprimer", use_container_width=True):
                                                    crud.delete_budget_ligne(ligne["id"])
                                                    st.warning("Ligne budgétaire supprimée.")
                                                    st.session_state["editing_ligne_id"] = None
                                                    st.rerun()
                                else:
                                    st.caption("Aucune ligne pour l'instant.")

                                with st.form(f"form_new_ligne_{sr['id']}", clear_on_submit=True):
                                    st.caption("➕ Ajouter une ligne")
                                    desc_ligne = st.text_input("Description *", key=f"desc_new_ligne_{sr['id']}")
                                    nlc1, nlc2, nlc3 = st.columns(3)
                                    unite_ligne = nlc1.selectbox("Unité *", crud.UNITES_BUDGET, key=f"unite_new_{sr['id']}")
                                    if unite_ligne == "autre":
                                        unite_ligne = nlc1.text_input("Préciser l'unité", key=f"unite_new_libre_{sr['id']}")
                                    quantite_ligne = nlc2.number_input("Quantité *", min_value=0.0, value=1.0, key=f"qte_new_{sr['id']}")
                                    cout_ligne = nlc3.number_input(f"Coût unitaire ({devise_p}) *", min_value=0.0, key=f"cout_new_{sr['id']}")
                                    act_options_new = {None: "— Aucune —"}
                                    for _, a in activites_df.iterrows():
                                        act_options_new[a["id"]] = a["titre"]
                                    activite_liee_new = st.selectbox(
                                        "Activité associée (facultatif)", options=list(act_options_new.keys()),
                                        format_func=lambda x: act_options_new[x], key=f"act_new_{sr['id']}",
                                    )
                                    if st.form_submit_button("Ajouter la ligne", use_container_width=True):
                                        if not desc_ligne or not unite_ligne:
                                            st.warning("La description et l'unité sont obligatoires.")
                                        else:
                                            crud.create_budget_ligne(sr["id"], desc_ligne, unite_ligne, quantite_ligne, cout_ligne, activite_liee_new)
                                            st.toast("✅ Ligne budgétaire ajoutée avec succès.")
                                            st.rerun()

                    with st.form(f"form_new_sous_rubrique_{rubrique['id']}", clear_on_submit=True):
                        st.caption("➕ Ajouter une sous-rubrique")
                        nom_sr = st.text_input("Nom de la sous-rubrique *", key=f"nom_new_sr_{rubrique['id']}")
                        if st.form_submit_button("Ajouter", use_container_width=True):
                            if not nom_sr:
                                st.warning("Le nom est obligatoire.")
                            else:
                                crud.create_budget_sous_rubrique(rubrique["id"], nom_sr)
                                st.toast(f"✅ Sous-rubrique « {nom_sr} » ajoutée avec succès.")
                                st.rerun()

        st.divider()

        # ------------------------------------------------------------------------
        # Exécution financière (dépenses réelles) — système existant, inchangé
        # ------------------------------------------------------------------------
        budget_projet = float(projet_row["budget"] or 0)
        budget_active = float(activites_df["budget"].fillna(0).sum()) if not activites_df.empty else 0.0
        depenses_projet_df = crud.get_depenses_by_projet(selected_projet_id)
        depense_reelle_totale = float(depenses_projet_df["montant"].sum()) if not depenses_projet_df.empty else 0.0

        # Solde et taux d'exécution calculés sur le budget prévisionnel hiérarchique
        # (référence la plus précise), pas sur l'ancien total par activité.
        reference_budget = total_hierarchique if total_hierarchique > 0 else budget_active
        ecart_total = reference_budget - depense_reelle_totale
        taux_execution_total = (depense_reelle_totale / reference_budget * 100) if reference_budget else 0.0

        st.markdown("**💳 Exécution financière (dépenses réelles vs budget prévisionnel)**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Budget global du projet", f"{budget_projet:,.0f} {devise_p}".replace(",", " "))
        c2.metric("Budget prévisionnel", f"{reference_budget:,.0f} {devise_p}".replace(",", " "))
        c3.metric("Dépensé réellement", f"{depense_reelle_totale:,.0f} {devise_p}".replace(",", " "))
        c4.metric("Solde disponible", f"{ecart_total:,.0f} {devise_p}".replace(",", " "), delta=f"{taux_execution_total:.0f}% exécuté", delta_color="inverse" if ecart_total < 0 else "normal")
        st.caption("💡 Le budget prévisionnel de référence utilise le total des rubriques détaillées ci-dessus si renseigné, sinon la somme des budgets par activité (ancien système). Toutes les dépenses sont supposées dans la même devise que le budget global.")

        if budget_active > budget_projet and budget_projet > 0:
            st.warning("⚠️ La somme des budgets d'activités dépasse le budget global du projet.")
        if depense_reelle_totale > reference_budget and reference_budget > 0:
            st.warning("⚠️ Les dépenses réelles dépassent le budget prévisionnel — dépassement à surveiller.")

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

        st.write("")
        st.markdown("**📊 Exécution financière par activité**")

        if activites_df.empty:
            st.info("Aucune activité pour ce projet.")
        else:
            for _, act_budget in activites_df.iterrows():
                depenses_act = depenses_projet_df[depenses_projet_df["activite_id"] == act_budget["id"]] if not depenses_projet_df.empty else pd.DataFrame()
                budget_prevu_act = float(act_budget["budget"] or 0)
                depense_act = float(depenses_act["montant"].sum()) if not depenses_act.empty else 0.0
                ecart_act = budget_prevu_act - depense_act
                taux_act = (depense_act / budget_prevu_act * 100) if budget_prevu_act else 0.0

                with st.expander(f"{act_budget['titre']} — {taux_act:.0f}% exécuté"):
                    fc1, fc2, fc3 = st.columns(3)
                    fc1.metric("Prévu", f"{budget_prevu_act:,.0f} {devise_p}".replace(",", " "))
                    fc2.metric("Dépensé", f"{depense_act:,.0f} {devise_p}".replace(",", " "))
                    fc3.metric("Écart", f"{ecart_act:,.0f} {devise_p}".replace(",", " "))

                    if not depenses_act.empty:
                        st.dataframe(
                            depenses_act[["date_depense", "montant", "description"]].rename(
                                columns={"date_depense": "Date", "montant": "Montant (FCFA)", "description": "Description"}
                            ),
                            use_container_width=True, hide_index=True,
                        )
                        for _, dep in depenses_act.iterrows():
                            if st.button("🗑️ Supprimer cette dépense", key=f"del_dep_{dep['id']}"):
                                crud.delete_depense(dep["id"])
                                st.toast("✅ Dépense supprimée avec succès.")
                                st.rerun()
                    else:
                        st.caption("Aucune dépense enregistrée pour cette activité.")

                    with st.form(f"form_new_depense_{act_budget['id']}", clear_on_submit=True):
                        st.caption("➕ Enregistrer une dépense")
                        dc1, dc2 = st.columns(2)
                        montant_dep = dc1.number_input("Montant (FCFA)", min_value=0.0, step=1000.0)
                        date_dep = dc2.date_input("Date de la dépense", value=None)
                        desc_dep = st.text_input("Description")
                        if st.form_submit_button("Ajouter la dépense", use_container_width=True):
                            if montant_dep <= 0:
                                st.warning("Le montant doit être supérieur à 0.")
                            else:
                                crud.create_depense(act_budget["id"], montant_dep, date_dep, desc_dep)
                                st.toast("✅ Dépense enregistrée avec succès.")
                                st.rerun()

    # ==============================================================================
    # SECTION : PARTIES PRENANTES
    # ==============================================================================
    with tab_parties:
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
            for _, partie in parties_prenantes_df.iterrows():
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1.2])
                    with col1:
                        st.markdown(f"**{partie['nom']}**")
                        st.caption(partie["type_partie"] or "")
                    with col2:
                        st.caption(partie["contact"] or "Sans contact")
                    with col3:
                        if st.button("✏️ Modifier", key=f"editbtn_partie_{partie['id']}", use_container_width=True):
                            st.session_state["editing_partie_id"] = None if st.session_state.get("editing_partie_id") == partie["id"] else partie["id"]
                            st.rerun()

                    if st.session_state.get("editing_partie_id") == partie["id"]:
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
                                st.session_state["editing_partie_id"] = None
                                st.rerun()
                            if col_delete.form_submit_button("🗑️ Supprimer", use_container_width=True):
                                crud.delete_partie_prenante(partie["id"])
                                st.warning("Partie prenante supprimée.")
                                st.session_state["editing_partie_id"] = None
                                st.rerun()

    # ==============================================================================
    # SECTION : DOCUMENTS
    # ==============================================================================
    with tab_documents:
        section_title("📄", "Documents")
        st.caption("Rapports, contrats, fiches projet ou photos liés à ce projet.")

        if not storage_service.is_configured():
            st.warning(
                "⚠️ Le stockage durable n'est pas configuré (SUPABASE_URL / SUPABASE_SERVICE_KEY manquants "
                "dans les secrets) — les fichiers ajoutés maintenant seront perdus au prochain redémarrage "
                "de l'application. Voir la documentation de `storage_service.py` pour l'activer."
            )

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
                        contenu = fichier.getbuffer().tobytes()
                        if storage_service.is_configured():
                            chemin = f"{selected_projet_id}/{fichier.name}"
                            try:
                                storage_service.upload_file(chemin, contenu, fichier.type or "application/octet-stream")
                            except RuntimeError as e:
                                st.error(str(e))
                                st.stop()
                        else:
                            dossier = os.path.join("documents", str(selected_projet_id))
                            os.makedirs(dossier, exist_ok=True)
                            chemin = os.path.join(dossier, fichier.name)
                            with open(chemin, "wb") as f:
                                f.write(contenu)
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
                        if storage_service.is_configured():
                            try:
                                contenu_dl = storage_service.download_file(doc["chemin_fichier"])
                                st.download_button(
                                    "⬇️ Télécharger", data=contenu_dl,
                                    file_name=doc["nom_fichier"], key=f"dl_{doc['id']}",
                                    use_container_width=True,
                                )
                            except RuntimeError:
                                st.caption("⚠️ Fichier introuvable dans le stockage")
                        elif os.path.exists(doc["chemin_fichier"]):
                            with open(doc["chemin_fichier"], "rb") as f:
                                st.download_button(
                                    "⬇️ Télécharger", data=f.read(),
                                    file_name=doc["nom_fichier"], key=f"dl_{doc['id']}",
                                    use_container_width=True,
                                )
                        else:
                            st.caption("⚠️ Fichier introuvable sur le disque (stockage non durable — voir le message ci-dessus)")
                    with col3:
                        if st.button("🗑️ Supprimer", key=f"del_doc_{doc['id']}", use_container_width=True):
                            crud.delete_document(doc["id"])
                            st.warning("Document supprimé.")
                            st.rerun()

