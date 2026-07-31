import streamlit as st
from i18n import t

st.set_page_config(page_title="SuiviProjets", page_icon="assets/logo_icone.png", layout="wide")

pg = st.navigation([
    st.Page("vue_dashboard.py", title=t("nav_dashboard"), icon="🏠", default=True),
    st.Page("pages/1_📁_Nouveau_Projet.py", title=t("nav_new_project"), icon="📁"),
    st.Page("pages/2_📂_Mes_Projets.py", title=t("nav_my_projects"), icon="📂"),
    st.Page("pages/3_📊_Rapports.py", title=t("nav_reports"), icon="📊"),
    st.Page("pages/4_🤖_IA.py", title=t("nav_ai"), icon="🤖"),
    st.Page("pages/5_⚙️_Parametres.py", title=t("nav_settings"), icon="⚙️"),
])

pg.run()
