import streamlit as st
from auth import require_login, logout_button
from ui_style import sidebar_brand, section_title, badge_html
from indicators_config import load_all_indicators, update_indicator
import crud

st.set_page_config(page_title="Paramètres - SuiviProjets", page_icon="⚙️", layout="wide")
require_login()
sidebar_brand()
logout_button()

user = st.session_state.get("user", {})
if user.get("role") != "admin":
    st.error("🚫 Accès réservé aux administrateurs.")
    st.stop()

st.title("⚙️ Paramètres")
st.caption("Configuration du tableau de bord et des règles générales de l'application.")
st.divider()

df = load_all_indicators()

# ----------------------------------------------------------------------------
# Résumé rapide
# ----------------------------------------------------------------------------
kpi_count = len(df[df["type_element"] == "kpi"])
kpi_actifs = len(df[(df["type_element"] == "kpi") & (df["visible"] == 1)])
graph_count = len(df[df["type_element"] == "graphique"])
graph_actifs = len(df[(df["type_element"] == "graphique") & (df["visible"] == 1)])

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""<div class="app-card">
        <div class="kpi-label">📊 KPI actifs</div>
        <div class="kpi-value">{kpi_actifs} / {kpi_count}</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="app-card">
        <div class="kpi-label">📈 Graphiques actifs</div>
        <div class="kpi-value">{graph_actifs} / {graph_count}</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="app-card">
        <div class="kpi-label">👤 Connecté en tant que</div>
        <div class="kpi-value" style="font-size:1.2rem;">{user.get('username', '')}</div>
    </div>""", unsafe_allow_html=True)

st.write("")
st.divider()

# ----------------------------------------------------------------------------
# Configuration des indicateurs du tableau de bord
# ----------------------------------------------------------------------------
section_title("📊", "Indicateurs du tableau de bord")
st.caption(
    "Choisissez quels indicateurs et graphiques apparaissent sur le tableau de bord, et dans quel ordre. "
    "Ces réglages s'appliquent à toute l'équipe."
)

col_reload, _ = st.columns([1, 4])
with col_reload:
    if st.button("🔄 Recharger", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.write("")

TYPE_LABELS = {"kpi": ("📊", "Indicateurs clés (KPI)"), "graphique": ("📈", "Graphiques")}

for type_element, (icon, label) in TYPE_LABELS.items():
    subset = df[df["type_element"] == type_element]

    with st.container(border=True):
        st.markdown(f"**{icon} {label}**")

        if subset.empty:
            st.caption("Aucun indicateur de ce type.")
            continue

        with st.form(f"form_{type_element}"):
            updated_rows = []

            for _, row in subset.iterrows():
                cols = st.columns([0.6, 3.4, 1.2, 1.8])
                visible = cols[0].checkbox(
                    "Actif", value=bool(row["visible"]), key=f"visible_{row['id']}",
                    label_visibility="collapsed",
                )
                cols[1].write(f"{row['icone'] or ''} {row['libelle']}")
                ordre = cols[2].number_input(
                    "Ordre", value=int(row["ordre"]), min_value=0, max_value=100,
                    step=1, key=f"ordre_{row['id']}", label_visibility="collapsed",
                )
                badge_kind = "success" if row["visible"] else "muted"
                cols[3].markdown(badge_html("Actif" if row["visible"] else "Masqué", badge_kind), unsafe_allow_html=True)
                updated_rows.append((row["id"], visible, ordre))

            if st.form_submit_button(f"💾 Enregistrer les {label.lower()}", use_container_width=True):
                for indicateur_id, visible, ordre in updated_rows:
                    update_indicator(indicateur_id, visible, ordre)
                st.cache_data.clear()
                st.success("✅ Configuration enregistrée avec succès.")
                st.rerun()

    st.write("")

st.divider()

# ----------------------------------------------------------------------------
# Accès lecteurs (comptes en lecture seule)
# ----------------------------------------------------------------------------
section_title("👁️", "Accès en lecture seule")
st.caption(
    "Attribuez à un compte « lecteur » l'accès à un ou plusieurs projets spécifiques. "
    "Ces comptes peuvent consulter les données mais ne peuvent rien ajouter, modifier ou supprimer."
)

lecteurs_df = crud.get_lecteurs()
projets_df_settings = crud.get_projets()

if lecteurs_df.empty:
    st.info(
        "Aucun compte lecteur pour l'instant. Créez-en un avec `python generate_password.py` "
        "en choisissant le rôle **lecteur**."
    )
elif projets_df_settings.empty:
    st.info("Aucun projet à partager pour l'instant.")
else:
    lecteur_options = {row["id"]: row["username"] for _, row in lecteurs_df.iterrows()}
    selected_lecteur_id = st.selectbox(
        "Compte lecteur", options=list(lecteur_options.keys()), format_func=lambda x: lecteur_options[x],
    )

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
        st.success("✅ Accès mis à jour avec succès.")
        st.rerun()

st.divider()

# ----------------------------------------------------------------------------
# Règles générales de l'application
# ----------------------------------------------------------------------------
section_title("🛡️", "Règles générales")

with st.container(border=True):
    st.markdown("**📁 Noms de projet**")
    st.caption("Deux projets ne peuvent pas porter le même nom (vérification automatique, insensible à la casse et aux espaces).")
    st.markdown(badge_html("Activé", "success"), unsafe_allow_html=True)

st.write("")

with st.container(border=True):
    st.markdown("**🗑️ Suppression en cascade**")
    st.caption("Supprimer un projet supprime automatiquement tous ses objectifs, résultats, activités et tâches liés — une confirmation explicite est toujours demandée.")
    st.markdown(badge_html("Activé", "success"), unsafe_allow_html=True)

st.write("")
st.caption("D'autres réglages (rôles avancés, notifications, intégration IA) seront ajoutés ici au fil des prochaines évolutions.")
