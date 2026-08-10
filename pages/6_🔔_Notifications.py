import streamlit as st
from auth import require_login, logout_button
from ui_style import sidebar_brand, section_title, badge_html
import crud

require_login()
sidebar_brand()
logout_button()

user = st.session_state.get("user", {})

st.title("🔔 Notifications")
st.caption(
    "Générées à chaque chargement de cette page ou du tableau de bord — pas d'alerte en "
    "temps réel en arrière-plan (l'application n'étant active que lorsqu'elle est ouverte)."
)
st.divider()

onglet_toutes, onglet_non_lues = st.tabs(["Toutes", "Non lues"])

TYPE_ICONES = {
    "activite_a_venir": ("🟠", "warning"),
    "nouvelle_affectation": ("🔵", "muted"),
}


def afficher_notifications(df):
    if df.empty:
        st.info("Aucune notification pour l'instant.")
        return

    if st.button("✅ Tout marquer comme lu", key=f"tout_lu_{id(df)}"):
        crud.mark_all_notifications_read(user["id"])
        st.toast("✅ Toutes les notifications ont été marquées comme lues.")
        st.rerun()

    for _, notif in df.iterrows():
        icone, kind = TYPE_ICONES.get(notif["type"], ("🔔", "muted"))
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                statut_badge = "" if notif["lu"] else badge_html("Non lu", "warning")
                st.markdown(f"{icone} **{notif['titre']}** {statut_badge}", unsafe_allow_html=True)
                st.write(notif["message"])
                st.caption(str(notif["date_creation"]))
            with c2:
                if notif["projet_id"]:
                    if st.button("📂 Ouvrir", key=f"open_notif_{notif['id']}", use_container_width=True):
                        if not notif["lu"]:
                            crud.mark_notification_read(notif["id"])
                        st.session_state["jump_to_projet_id"] = int(notif["projet_id"])
                        st.session_state["hub_active_section"] = "activites" if notif["activite_id"] else None
                        st.switch_page("pages/2_📂_Mes_Projets.py")
                if not notif["lu"]:
                    if st.button("Marquer comme lu", key=f"read_notif_{notif['id']}", use_container_width=True):
                        crud.mark_notification_read(notif["id"])
                        st.rerun()


with onglet_toutes:
    afficher_notifications(crud.get_notifications(user["id"], only_unread=False))

with onglet_non_lues:
    afficher_notifications(crud.get_notifications(user["id"], only_unread=True))
