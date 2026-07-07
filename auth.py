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
