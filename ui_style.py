"""
Module de style partagé — palette de couleurs, CSS et composants réutilisables
pour une interface cohérente sur toutes les pages de l'application.
"""

import streamlit as st
import streamlit.components.v1 as components

# ----------------------------------------------------------------------------
# Palette de couleurs (inspirée des outils modernes de gestion de projet)
# ----------------------------------------------------------------------------
PRIMARY = "#4F46E5"       # Indigo
PRIMARY_DARK = "#4338CA"
SUCCESS = "#16A34A"
WARNING = "#F59E0B"
DANGER = "#DC2626"
BG = "#F8FAFC"
CARD_BG = "#FFFFFF"
TEXT = "#0F172A"
MUTED = "#64748B"
BORDER = "#E2E8F0"


def inject_global_style():
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

            .main {{ background-color: {BG}; }}

            h1, h2, h3 {{ color: {TEXT}; font-weight: 800; letter-spacing: -0.01em; }}

            .app-card {{
                background-color: {CARD_BG};
                border-radius: 14px;
                padding: 20px 22px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                border: 1px solid {BORDER};
                margin-bottom: 10px;
                transition: box-shadow 0.15s ease, transform 0.15s ease;
            }}
            .app-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}

            .kpi-card {{
                background-color: {CARD_BG};
                border-radius: 14px;
                padding: 20px 22px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                border-left: 5px solid {PRIMARY};
                margin-bottom: 8px;
                transition: box-shadow 0.15s ease;
            }}
            .kpi-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
            .kpi-label {{
                font-size: 0.8rem; color: {MUTED}; font-weight: 600;
                text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px;
            }}
            .kpi-value {{ font-size: 1.8rem; font-weight: 700; color: {TEXT}; }}

            .section-title {{
                font-size: 1.05rem; font-weight: 700; color: {TEXT};
                margin-top: 6px; margin-bottom: 10px;
            }}

            .step-pill {{
                display: inline-block; padding: 4px 14px; border-radius: 999px;
                font-size: 0.8rem; font-weight: 600; margin-right: 6px; margin-bottom: 10px;
                transition: transform 0.15s ease;
            }}
            .step-done {{ background-color: #DCFCE7; color: {SUCCESS}; }}
            .step-active {{ background-color: #E0E7FF; color: {PRIMARY}; }}
            .step-pending {{ background-color: #F1F5F9; color: {MUTED}; }}

            .badge {{
                display: inline-block; padding: 2px 10px; border-radius: 999px;
                font-size: 0.75rem; font-weight: 600;
            }}
            .badge-success {{ background-color: #DCFCE7; color: {SUCCESS}; }}
            .badge-warning {{ background-color: #FEF3C7; color: {WARNING}; }}
            .badge-muted {{ background-color: #F1F5F9; color: {MUTED}; }}

            div.stButton > button, div.stFormSubmitButton > button {{
                border-radius: 10px; font-weight: 600;
                transition: transform 0.1s ease, box-shadow 0.15s ease;
            }}
            div.stButton > button:hover, div.stFormSubmitButton > button:hover {{
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.12);
            }}
            div.stButton > button:active, div.stFormSubmitButton > button:active {{
                transform: translateY(0px);
            }}

            [data-testid="stContainer"] {{ transition: box-shadow 0.15s ease; }}

            [data-testid="stSidebar"] .stCaption {{ color: {MUTED}; }}

            [data-testid="stMetricValue"] {{ font-size: 1.05rem; }}
            [data-testid="stMetricLabel"] {{ font-size: 0.72rem; }}
            [data-testid="stMetricDelta"] {{ font-size: 0.72rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def scroll_to_top():
    """Force un retour en haut de la page — à appeler juste après un changement de section,
    pas à chaque rerun (sinon ça interromprait la saisie dans les formulaires).

    Utilise components.html (et non st.markdown) : les balises <script> insérées via
    st.markdown ne s'exécutent jamais dans un navigateur (règle de sécurité HTML standard
    dès qu'on injecte du HTML via innerHTML) — seul components.html exécute du vrai JS,
    via une iframe qui accède à la fenêtre parente."""
    components.html(
        """<script>
            window.parent.scrollTo({top: 0, behavior: "instant"});
        </script>""",
        height=0,
    )


def scroll_anchor(element_id):
    """Pose un repère invisible à un endroit précis de la page (ex: juste avant le
    contenu d'une section) — à utiliser avec scroll_to_element()."""
    st.markdown(f'<div id="{element_id}"></div>', unsafe_allow_html=True)


def scroll_to_element(element_id):
    """Fait défiler jusqu'au repère posé par scroll_anchor() — à appeler juste après
    un changement de section, pas à chaque rerun."""
    components.html(
        f"""<script>
            const el = window.parent.document.getElementById("{element_id}");
            if (el) {{ el.scrollIntoView({{behavior: "instant", block: "start"}}); }}
        </script>""",
        height=0,
    )


def tip(key, text):
    """Astuce discrète et masquable, affichée une fois par section (par clé unique)."""
    if st.session_state.get(f"tip_hidden_{key}"):
        return
    col1, col2 = st.columns([25, 1])
    with col1:
        st.markdown(
            f'<div style="background-color:#EEF2FF; border-radius:8px; padding:8px 14px; '
            f'font-size:0.85rem; color:{PRIMARY_DARK}; margin-bottom:8px;">💡 {text}</div>',
            unsafe_allow_html=True,
        )
    with col2:
        if st.button("✕", key=f"tip_close_{key}", help="Masquer cette astuce"):
            st.session_state[f"tip_hidden_{key}"] = True
            st.rerun()


def ai_text_field(label, key, contexte="", height=None, is_area=True):
    """
    Champ de texte avec assistance IA intégrée (Améliorer / Pro / Résumer / Développer).

    Remplace un appel direct à st.text_area/st.text_input : gère correctement le fait
    que Streamlit interdit de modifier st.session_state[key] après que le widget
    correspondant a déjà été instancié dans le même run. La mise à jour IA est donc
    appliquée juste AVANT de créer le widget, au run suivant.
    """
    pending_key = f"{key}_pending"
    if pending_key in st.session_state:
        st.session_state[key] = st.session_state.pop(pending_key)

    if is_area:
        value = st.text_area(label, key=key, height=height) if height else st.text_area(label, key=key)
    else:
        value = st.text_input(label, key=key)

    cols = st.columns(4)
    boutons = [
        ("✨ Améliorer", "ameliorer"),
        ("📝 Pro", "professionnel"),
        ("✂️ Résumer", "resumer"),
        ("➕ Développer", "developper"),
    ]
    for col, (btn_label, mode) in zip(cols, boutons):
        with col:
            if st.button(btn_label, key=f"{key}_btn_{mode}", use_container_width=True):
                import ai_text_assist
                try:
                    with st.spinner("L'IA travaille..."):
                        nouveau_texte = ai_text_assist.rewrite_text(st.session_state.get(key, ""), mode, contexte)
                    st.session_state[pending_key] = nouveau_texte
                    st.rerun()
                except RuntimeError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Erreur IA : {e}")

    return value


def sidebar_brand():
    with st.sidebar:
        st.markdown(
            f"""<div style="padding: 6px 0 14px 0;">
                    <span style="font-size:1.3rem; font-weight:800; color:{TEXT};">📊 SuiviProjets</span><br>
                    <span style="font-size:0.8rem; color:{MUTED};">Gestion &amp; suivi de projets</span>
                </div>""",
            unsafe_allow_html=True,
        )
        st.divider()


def kpi_card_html(icon, label, value):
    return f"""<div class="kpi-card">
                    <div class="kpi-label">{icon} {label}</div>
                    <div class="kpi-value">{value}</div>
                </div>"""


def section_title(icon, text, help_text=None):
    if help_text:
        col1, col2 = st.columns([20, 1])
        with col1:
            st.markdown(f'<div class="section-title">{icon} {text}</div>', unsafe_allow_html=True)
        with col2:
            with st.popover("ℹ️", use_container_width=True):
                st.write(help_text)
    else:
        st.markdown(f'<div class="section-title">{icon} {text}</div>', unsafe_allow_html=True)


SECTION_HELP = {
    "objectifs": (
        "**Objectif général** : la finalité globale du projet, sa raison d'être.\n\n"
        "**Objectif spécifique** : un sous-objectif concret et mesurable qui contribue "
        "à l'objectif général. Un projet peut avoir plusieurs objectifs spécifiques."
    ),
    "resultats": (
        "Ce que le projet doit produire concrètement pour atteindre un objectif. "
        "Chaque résultat attendu est mesuré par un **indicateur** (valeur cible à atteindre "
        "vs valeur actuelle constatée)."
    ),
    "activites": (
        "Les actions concrètes à mener pour produire un résultat attendu "
        "(ex : construire, former, acheter, installer...)."
    ),
    "taches": (
        "Les étapes précises et assignables qui composent une activité — "
        "le niveau le plus fin de suivi, avec une priorité et une progression."
    ),
}


def badge_html(text, kind="muted"):
    return f'<span class="badge badge-{kind}">{text}</span>'


def step_pills(steps, current_index):
    """steps: liste de libellés. current_index: index de l'étape active (0-based)."""
    html = ""
    for i, label in enumerate(steps):
        if i < current_index:
            cls = "step-done"
            icon = "✅"
        elif i == current_index:
            cls = "step-active"
            icon = "🔵"
        else:
            cls = "step-pending"
            icon = "⚪"
        html += f'<span class="step-pill {cls}">{icon} {label}</span>'
    st.markdown(html, unsafe_allow_html=True)