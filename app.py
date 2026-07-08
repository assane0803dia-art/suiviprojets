import streamlit as st

st.set_page_config(page_title="SuiviProjets", page_icon="📊", layout="wide")

pg = st.navigation([
    st.Page("vue_dashboard.py", title="Tableau de bord", icon="🏠", default=True),
    st.Page("pages/1_📁_Nouveau_Projet.py", title="Nouveau projet", icon="📁"),
    st.Page("pages/2_📂_Mes_Projets.py", title="Mes projets", icon="📂"),
    st.Page("pages/3_📊_Rapports.py", title="Rapports", icon="📊"),
    st.Page("pages/4_🤖_IA.py", title="IA", icon="🤖"),
    st.Page("pages/5_⚙️_Parametres.py", title="Paramètres", icon="⚙️"),
])

pg.run()
