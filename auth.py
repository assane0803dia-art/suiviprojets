import streamlit as st
import bcrypt
from ui_style import inject_global_style
from db import get_connection


def verify_credentials(username: str, password: str):
    """Vérifie les identifiants et retourne l'utilisateur (dict) ou None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, password_hash, role FROM Users WHERE username = %s AND actif = TRUE",
        (username,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    user_id, db_username, password_hash, role = row

    if bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
        return {"id": user_id, "username": db_username, "role": role}

    return None


def _log_connexion(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Historique_Connexions (user_id) VALUES (%s)", (user_id,))
    cursor.execute("UPDATE Users SET derniere_connexion = NOW() WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()


def get_profile(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT username, nom_complet, email, photo_url, role, langue, fuseau_horaire,
                  modele_rapport, ia_modele, ia_creativite, ia_langue_reponses, ia_suggestions_auto,
                  notif_email, notif_app, notif_alertes, derniere_connexion
           FROM Users WHERE id = %s""",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    cols = ["username", "nom_complet", "email", "photo_url", "role", "langue", "fuseau_horaire",
            "modele_rapport", "ia_modele", "ia_creativite", "ia_langue_reponses", "ia_suggestions_auto",
            "notif_email", "notif_app", "notif_alertes", "derniere_connexion"]
    return dict(zip(cols, row))


def get_recent_sessions(user_id, limit=5):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date_connexion FROM Historique_Connexions WHERE user_id = %s ORDER BY date_connexion DESC LIMIT %s",
        (user_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def update_profile(user_id, nom_complet, email, photo_url):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Users SET nom_complet = %s, email = %s, photo_url = %s WHERE id = %s",
        (nom_complet, email, photo_url, user_id),
    )
    conn.commit()
    conn.close()


def update_preferences_projet(user_id, langue, fuseau_horaire, modele_rapport):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Users SET langue = %s, fuseau_horaire = %s, modele_rapport = %s WHERE id = %s",
        (langue, fuseau_horaire, modele_rapport, user_id),
    )
    conn.commit()
    conn.close()


def update_preferences_ia(user_id, ia_modele, ia_creativite, ia_langue_reponses, ia_suggestions_auto):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE Users SET ia_modele = %s, ia_creativite = %s, ia_langue_reponses = %s,
           ia_suggestions_auto = %s WHERE id = %s""",
        (ia_modele, ia_creativite, ia_langue_reponses, bool(ia_suggestions_auto), user_id),
    )
    conn.commit()
    conn.close()


def update_notifications(user_id, notif_email, notif_app, notif_alertes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Users SET notif_email = %s, notif_app = %s, notif_alertes = %s WHERE id = %s",
        (bool(notif_email), bool(notif_app), bool(notif_alertes), user_id),
    )
    conn.commit()
    conn.close()


def change_password(user_id, current_password, new_password):
    """Change le mot de passe après vérification de l'ancien. Retourne (succès, message)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM Users WHERE id = %s", (user_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return False, "Utilisateur introuvable."

    current_hash = row[0]
    if not bcrypt.checkpw(current_password.encode("utf-8"), current_hash.encode("utf-8")):
        conn.close()
        return False, "Le mot de passe actuel est incorrect."

    new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cursor.execute("UPDATE Users SET password_hash = %s WHERE id = %s", (new_hash, user_id))
    conn.commit()
    conn.close()
    return True, "Mot de passe mis à jour avec succès."


def delete_own_account(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Historique_Connexions WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM Users WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()


def login_form():
    """Affiche le formulaire de connexion. Retourne True si l'utilisateur est connecté."""
    if st.session_state.get("authenticated"):
        return True

    inject_global_style()

    st.markdown(
        "<h2 style='text-align:center;'>🔒 Connexion</h2>",
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            submit_label = "Se connecter"
            submitted = st.form_submit_button(submit_label, use_container_width=True)

            if submitted:
                if not username or not password:
                    st.warning("Veuillez remplir tous les champs.")
                else:
                    user = verify_credentials(username.strip(), password)
                    if user:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user
                        _log_connexion(user["id"])
                        st.rerun()
                    else:
                        st.error("Nom d'utilisateur ou mot de passe incorrect.")

    return False


def logout_button():
    """Affiche les infos utilisateur et un bouton de déconnexion dans la barre latérale."""
    with st.sidebar:
        user = st.session_state.get("user", {})
        st.write(f"👤 **{user.get('username', '')}**")
        st.caption(f"Rôle : {user.get('role', '')}")
        if st.button("🚪 Se déconnecter", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["user"] = None
            st.rerun()
        st.divider()


def require_login():
    """À appeler en haut de chaque page. Bloque l'exécution tant que l'utilisateur n'est pas connecté."""
    if not st.session_state.get("authenticated"):
        login_form()
        st.stop()
    else:
        inject_global_style()
