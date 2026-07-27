import streamlit as st
from i18n import t
import os
from datetime import datetime
from auth import (
    require_login, logout_button, get_profile, update_profile,
    update_preferences_projet, update_preferences_ia, update_notifications,
    change_password, delete_own_account, get_recent_sessions,
)
from ui_style import sidebar_brand, section_title, badge_html, tip
import crud

require_login()
sidebar_brand()
logout_button()

user = st.session_state.get("user", {})
is_admin = user.get("role") == "admin"

st.title(t("settings_title"))
st.caption("Votre compte, vos préférences, et la configuration de l'application.")
st.divider()

profile = get_profile(user["id"])
if profile is None:
    st.error("Impossible de charger votre profil.")
    st.stop()

tab_labels = ["👤 Compte", "📁 Projet", "🤖 IA", "🔔 Notifications", "🔒 Sécurité"]
if is_admin:
    tab_labels += ["🛡️ Administration"]

tabs = st.tabs(tab_labels)

# ==============================================================================
# COMPTE
# ==============================================================================
with tabs[0]:
    tip("compte", "Votre nom et votre photo apparaissent dans les rapports générés et l'en-tête de l'application.")

    col_photo, col_form = st.columns([1, 3])
    with col_photo:
        if profile["photo_url"] and os.path.exists(profile["photo_url"]):
            st.image(profile["photo_url"], width=120)
        else:
            st.markdown(
                f'<div style="width:120px;height:120px;border-radius:60px;background:#E0E7FF;'
                f'display:flex;align-items:center;justify-content:center;font-size:2.5rem;">👤</div>',
                unsafe_allow_html=True,
            )
        nouvelle_photo = st.file_uploader("Changer la photo", type=["png", "jpg", "jpeg"], key="upload_photo")

    with col_form:
        with st.form("form_compte"):
            username_display = st.text_input("Nom d'utilisateur (identifiant de connexion)", value=profile["username"], disabled=True)
            nom_complet = st.text_input("Nom complet", value=profile["nom_complet"] or "")
            email = st.text_input("Email", value=profile["email"] or "")
            st.caption(f"Rôle : {badge_html(profile['role'], 'success' if profile['role'] == 'admin' else 'muted')}", unsafe_allow_html=True)

            if st.form_submit_button("💾 Enregistrer", use_container_width=True):
                photo_path = profile["photo_url"]
                if nouvelle_photo is not None:
                    dossier = os.path.join("avatars", str(user["id"]))
                    os.makedirs(dossier, exist_ok=True)
                    photo_path = os.path.join(dossier, nouvelle_photo.name)
                    with open(photo_path, "wb") as f:
                        f.write(nouvelle_photo.getbuffer())
                update_profile(user["id"], nom_complet, email, photo_path)
                st.toast("✅ Profil mis à jour avec succès.")
                st.rerun()

# ==============================================================================
# PROJET (préférences générales de travail)
# ==============================================================================
with tabs[1]:
    tip("projet", "Ces préférences s'appliquent à votre compte, sur tous vos projets.")

    with st.form("form_projet"):
        c1, c2 = st.columns(2)
        langue = c1.selectbox("Langue de l'application", ["fr", "en"], index=["fr", "en"].index(profile["langue"] or "fr"), format_func=lambda x: "Français" if x == "fr" else "English")
        fuseau = c2.selectbox(
            "Fuseau horaire",
            ["Africa/Dakar", "Europe/Paris", "UTC"],
            index=["Africa/Dakar", "Europe/Paris", "UTC"].index(profile["fuseau_horaire"]) if profile["fuseau_horaire"] in ["Africa/Dakar", "Europe/Paris", "UTC"] else 0,
        )
        modele_rapport = st.selectbox(
            "Modèle de rapport par défaut",
            ["Standard", "Résumé court", "Détaillé"],
            index=["Standard", "Résumé court", "Détaillé"].index(profile["modele_rapport"]) if profile["modele_rapport"] in ["Standard", "Résumé court", "Détaillé"] else 0,
        )
        if st.form_submit_button("💾 Enregistrer", use_container_width=True):
            update_preferences_projet(user["id"], langue, fuseau, modele_rapport)
            st.session_state["langue_utilisateur"] = langue
            st.toast("✅ Préférences mises à jour avec succès.")
            st.rerun()

    st.caption(
        "ℹ️ Traduction anglaise en cours : la navigation et les titres de pages s'adaptent déjà "
        "à cette préférence — le reste de l'application (formulaires, boutons) reste en français pour l'instant."
    )

# ==============================================================================
# IA
# ==============================================================================
with tabs[2]:
    tip("ia", "Un niveau de créativité plus élevé donne des rapports plus riches en formulation, mais moins littéraux.")

    with st.form("form_ia"):
        ia_modele = st.selectbox(
            "Modèle utilisé pour la génération de rapports",
            ["claude-sonnet-5", "claude-haiku-4-5-20251001"],
            index=["claude-sonnet-5", "claude-haiku-4-5-20251001"].index(profile["ia_modele"]) if profile["ia_modele"] in ["claude-sonnet-5", "claude-haiku-4-5-20251001"] else 0,
            format_func=lambda x: "Claude Sonnet 5 (qualité, recommandé)" if x == "claude-sonnet-5" else "Claude Haiku 4.5 (rapide, économique)",
        )
        ia_creativite = st.slider("Niveau de créativité", 0, 100, int(profile["ia_creativite"] or 50))
        ia_langue = st.selectbox(
            "Langue des réponses de l'IA", ["fr", "en"],
            index=["fr", "en"].index(profile["ia_langue_reponses"] or "fr"),
            format_func=lambda x: "Français" if x == "fr" else "English",
        )
        ia_suggestions = st.toggle("Activer les suggestions automatiques", value=bool(profile["ia_suggestions_auto"]))

        if st.form_submit_button("💾 Enregistrer", use_container_width=True):
            update_preferences_ia(user["id"], ia_modele, ia_creativite, ia_langue, ia_suggestions)
            st.toast("✅ Préférences IA mises à jour avec succès.")
            st.rerun()

# ==============================================================================
# NOTIFICATIONS
# ==============================================================================
with tabs[3]:
    tip("notifications", "Les notifications par email nécessitent encore une configuration technique — voir la remarque ci-dessous.")

    with st.form("form_notifications"):
        notif_app = st.toggle("Notifications dans l'application", value=bool(profile["notif_app"]))
        notif_alertes = st.toggle("Alertes de retards et de risques", value=bool(profile["notif_alertes"]))
        notif_email = st.toggle("Notifications par email", value=bool(profile["notif_email"]))

        if st.form_submit_button("💾 Enregistrer", use_container_width=True):
            update_notifications(user["id"], notif_email, notif_app, notif_alertes)
            st.toast("✅ Préférences de notification mises à jour avec succès.")
            st.rerun()

    st.info(
        "ℹ️ L'envoi d'email fonctionne pour recevoir vos rapports (page 📊 Rapports) et vos "
        "recommandations IA (page 🤖 IA) à la demande, en un clic. Les alertes automatiques en "
        "arrière-plan (ex: être prévenu dès qu'une tâche prend du retard sans avoir ouvert l'app) "
        "ne sont pas possibles sur ce type d'hébergement, qui met l'application en veille quand "
        "personne ne l'utilise."
    )

# ==============================================================================
# SÉCURITÉ
# ==============================================================================
with tabs[4]:
    section_title("🔑", "Changer le mot de passe")
    with st.form("form_password", clear_on_submit=True):
        mdp_actuel = st.text_input("Mot de passe actuel", type="password")
        mdp_nouveau = st.text_input("Nouveau mot de passe", type="password")
        mdp_confirm = st.text_input("Confirmez le nouveau mot de passe", type="password")

        if st.form_submit_button("💾 Changer le mot de passe", use_container_width=True):
            if not mdp_actuel or not mdp_nouveau:
                st.warning("Veuillez remplir tous les champs.")
            elif mdp_nouveau != mdp_confirm:
                st.warning("Les nouveaux mots de passe ne correspondent pas.")
            elif len(mdp_nouveau) < 6:
                st.warning("Le nouveau mot de passe doit contenir au moins 6 caractères.")
            else:
                success, message = change_password(user["id"], mdp_actuel, mdp_nouveau)
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(message)

    st.write("")
    section_title("🕓", "Connexions récentes")
    st.caption(
        "Historique des connexions à votre compte (pas de gestion multi-appareils en temps réel "
        "pour l'instant — juste un journal des dernières connexions réussies)."
    )
    sessions = get_recent_sessions(user["id"])
    if not sessions:
        st.info("Aucune connexion enregistrée pour l'instant.")
    else:
        for date_connexion in sessions:
            st.caption(f"🟢 {date_connexion.strftime('%d/%m/%Y à %H:%M')}")

    st.write("")
    section_title("⚠️", "Suppression du compte")
    st.warning("Cette action supprime définitivement votre compte de connexion. Vos projets et données créées via l'application ne sont pas supprimés.")

    if st.session_state.get("confirm_delete_account"):
        st.error("Confirmez-vous la suppression définitive de votre compte ?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Oui, supprimer mon compte", type="primary", use_container_width=True):
                delete_own_account(user["id"])
                st.session_state["authenticated"] = False
                st.session_state["user"] = None
                st.success("Compte supprimé. Vous allez être déconnecté.")
                st.rerun()
        with col2:
            if st.button("Annuler", use_container_width=True):
                st.session_state.pop("confirm_delete_account", None)
                st.rerun()
    else:
        if st.button("🗑️ Supprimer mon compte", use_container_width=False):
            st.session_state["confirm_delete_account"] = True
            st.rerun()

# ==============================================================================
# ADMINISTRATION (admin uniquement) — règles générales + accès lecteurs
# ==============================================================================
if is_admin:
    with tabs[5]:
        st.info(
            "💡 La configuration des indicateurs du tableau de bord se fait désormais "
            "directement depuis **🏠 Tableau de bord** (section « ⚙️ Choisir les "
            "indicateurs affichés »)."
        )

        section_title("🛡️", "Règles générales")
        with st.container(border=True):
            st.markdown("**📁 Noms de projet**")
            st.caption("Deux projets ne peuvent pas porter le même nom (vérification automatique).")
            st.markdown(badge_html("Activé", "success"), unsafe_allow_html=True)
        st.write("")
        with st.container(border=True):
            st.markdown("**🗑️ Suppression en cascade**")
            st.caption("Supprimer un projet supprime automatiquement tout ce qui en dépend, après confirmation explicite.")
            st.markdown(badge_html("Activé", "success"), unsafe_allow_html=True)

        st.divider()
        section_title("👁️", "Accès en lecture seule")
        tip("acces_lecteurs", "Un compte lecteur ne voit que les projets explicitement partagés ici.")

        lecteurs_df = crud.get_lecteurs()
        projets_df_settings = crud.get_projets()

        if lecteurs_df.empty:
            st.info("Aucun compte lecteur pour l'instant. Créez-en un avec `python generate_password_supabase.py` en choisissant le rôle **lecteur**.")
        elif projets_df_settings.empty:
            st.info("Aucun projet à partager pour l'instant.")
        else:
            lecteur_options = {row["id"]: row["username"] for _, row in lecteurs_df.iterrows()}
            selected_lecteur_id = st.selectbox("Compte lecteur", options=list(lecteur_options.keys()), format_func=lambda x: lecteur_options[x])

            projets_deja_accessibles = crud.get_acces_lecteur(selected_lecteur_id)
            projet_options_settings = {row["id"]: row["nom"] for _, row in projets_df_settings.iterrows()}

            selected_projets = st.multiselect(
                "Projets accessibles à ce compte",
                options=list(projet_options_settings.keys()),
                default=projets_deja_accessibles,
                format_func=lambda x: projet_options_settings[x],
            )

            if st.button("💾 Enregistrer les accès", use_container_width=True):
                for projet_id in selected_projets:
                    if projet_id not in projets_deja_accessibles:
                        crud.grant_acces_lecteur(selected_lecteur_id, projet_id)
                for projet_id in projets_deja_accessibles:
                    if projet_id not in selected_projets:
                        crud.revoke_acces_lecteur(selected_lecteur_id, projet_id)
                st.toast("✅ Accès mis à jour avec succès.")
                st.rerun()
