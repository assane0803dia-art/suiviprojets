"""
Module de style partagé — palette de couleurs, CSS et composants réutilisables
pour une interface cohérente sur toutes les pages de l'application.
"""

import streamlit as st
import streamlit.components.v1 as components
import uuid

# ----------------------------------------------------------------------------
# Palette de couleurs (inspirée des outils modernes de gestion de projet)
# ----------------------------------------------------------------------------
PRIMARY = "#2563EB"       # Bleu — couleur principale
PRIMARY_DARK = "#1D4ED8"
SECONDARY = "#10B981"     # Vert — couleur secondaire
ACCENT = "#F59E0B"        # Orange — accent
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER = "#EF4444"        # Rouge doux (pas un rouge agressif)
BG = "#F8FAFC"
CARD_BG = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"
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
                transition: box-shadow 0.15s ease, transform 0.15s ease;
            }}
            .kpi-card:hover {{ box-shadow: 0 6px 16px rgba(0,0,0,0.10); transform: translateY(-2px); }}
            .kpi-icon-circle {{
                display: inline-flex; align-items: center; justify-content: center;
                width: 38px; height: 38px; border-radius: 999px;
                background-color: #EFF6FF; font-size: 1.1rem; margin-bottom: 10px;
            }}
            .kpi-label {{
                font-size: 0.8rem; color: {MUTED}; font-weight: 600;
                text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px;
            }}
            .kpi-value {{ font-size: 1.8rem; font-weight: 700; color: {TEXT}; }}
            .kpi-progress-track {{
                width: 100%; height: 6px; border-radius: 999px;
                background-color: #E5E7EB; margin-top: 12px; overflow: hidden;
            }}
            .kpi-progress-fill {{
                height: 100%; border-radius: 999px;
                background: linear-gradient(90deg, {PRIMARY}, {SECONDARY});
                transition: width 0.4s ease;
            }}

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
                transition: transform 0.1s ease, box-shadow 0.15s ease, background-color 0.15s ease;
            }}
            div.stButton > button:hover, div.stFormSubmitButton > button:hover {{
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.12);
            }}
            div.stButton > button:active, div.stFormSubmitButton > button:active {{
                transform: translateY(0px);
            }}

            /* Action principale (Créer / Enregistrer / Ajouter) : couleur pleine */
            button[kind="primary"], button[kind="primaryFormSubmit"] {{
                background-color: {PRIMARY}; color: white; border: 1px solid {PRIMARY};
            }}
            button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {{
                background-color: {PRIMARY_DARK}; border-color: {PRIMARY_DARK};
            }}
            /* Action secondaire (Annuler / Modifier / Supprimer) : contour discret */
            button[kind="secondary"], button[kind="secondaryFormSubmit"] {{
                background-color: white; color: {TEXT}; border: 1px solid {BORDER};
            }}
            button[kind="secondary"]:hover, button[kind="secondaryFormSubmit"]:hover {{
                background-color: #F1F5F9; border-color: {PRIMARY};
            }}

            [data-testid="stContainer"] {{ transition: box-shadow 0.15s ease; }}

            [data-testid="stSidebar"] .stCaption {{ color: {MUTED}; }}

            /* Sidebar premium : fond blanc distinct, séparation nette, navigation aérée */
            [data-testid="stSidebar"] {{
                background-color: #FFFFFF;
                border-right: 1px solid {BORDER};
            }}
            [data-testid="stSidebarNav"] a, [data-testid="stSidebarNavLink"] {{
                border-radius: 10px;
                margin: 2px 8px;
                padding: 6px 10px;
                transition: background-color 0.15s ease, color 0.15s ease;
            }}
            [data-testid="stSidebarNav"] a:hover, [data-testid="stSidebarNavLink"]:hover {{
                background-color: #EFF6FF;
                color: {PRIMARY};
            }}
            [data-testid="stSidebarNav"] a[aria-current="page"],
            [data-testid="stSidebarNavLink"][aria-current="page"] {{
                background-color: #EFF6FF;
                color: {PRIMARY};
                font-weight: 700;
            }}

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
    via une iframe qui accède à la fenêtre parente.

    Un identifiant unique (nonce) est glissé dans le script à chaque appel : sans ça,
    Streamlit considère un script identique au précédent comme "inchangé" et ne recharge
    pas l'iframe, donc le script ne se réexécute pas une deuxième fois."""
    nonce = uuid.uuid4().hex
    components.html(
        f"""<script>
            // nonce:{nonce}
            window.parent.scrollTo({{top: 0, behavior: "instant"}});
        </script>""",
        height=0,
    )


def scroll_anchor(element_id):
    """Pose un repère invisible à un endroit précis de la page (ex: juste avant le
    contenu d'une section) — à utiliser avec scroll_to_element()."""
    st.markdown(f'<div id="{element_id}"></div>', unsafe_allow_html=True)


def style_plotly_chart(fig):
    """
    Applique un style cohérent et moderne à un graphique Plotly : fond transparent
    (s'intègre à la carte qui l'entoure au lieu d'un bloc blanc), légende horizontale
    épurée, et infobulles (tooltips) au survol dans le même style que le reste de
    l'application. À appeler juste après avoir créé le graphique — les réglages
    spécifiques (titres d'axes, hauteur...) peuvent toujours être ajoutés après,
    via un fig.update_layout(...) supplémentaire.
    """
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=TEXT, size=13),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor="white", bordercolor=BORDER,
            font=dict(family="Inter, sans-serif", color=TEXT, size=12),
        ),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#F1F5F9", zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig


def scroll_to_element(element_id):
    """Fait défiler jusqu'au repère posé par scroll_anchor() — à appeler juste après
    un changement de section, pas à chaque rerun. Voir la note sur le nonce dans
    scroll_to_top()."""
    nonce = uuid.uuid4().hex
    components.html(
        f"""<script>
            // nonce:{nonce}
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


def ai_text_field(label, key, contexte="", height=None, is_area=True, boutons=None):
    """
    Champ de texte avec assistance IA intégrée. Par défaut : Améliorer / Pro / Résumer /
    Développer — mais un jeu de boutons personnalisé peut être fourni via `boutons`
    (liste de tuples (libellé, mode), mode devant exister dans ai_text_assist.MODES).

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

    if boutons is None:
        boutons = [
            ("✨ Améliorer", "ameliorer"),
            ("📝 Pro", "professionnel"),
            ("✂️ Résumer", "resumer"),
            ("➕ Développer", "developper"),
        ]
    cols = st.columns(len(boutons))
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
        st.markdown('<div style="padding-top: 6px;"></div>', unsafe_allow_html=True)
        col_logo, col_text = st.columns([1, 3], vertical_alignment="center")
        with col_logo:
            st.image("assets/logo_icone.png", width=42)
        with col_text:
            st.markdown(
                f"""<div style="padding-bottom: 2px;">
                        <span style="font-size:1.25rem; font-weight:800; color:{TEXT};">SuiviProjets</span><br>
                        <span style="font-size:0.75rem; color:{MUTED};">Gestion &amp; suivi de projets</span>
                    </div>""",
                unsafe_allow_html=True,
            )
        st.write("")
        st.divider()


def kpi_card_html(icon, label, value, progress_percent=None):
    """
    Carte KPI enrichie : icône dans un badge coloré, valeur mise en avant, et une
    mini barre de progression optionnelle — affichée uniquement quand une vraie
    valeur en pourcentage est disponible (jamais une tendance inventée sans donnée
    historique réelle pour la calculer).

    Construite en une seule ligne HTML continue (sans saut de ligne) : une ligne
    vide au milieu du HTML (ex: quand `barre` est une chaîne vide) fait que
    Streamlit interrompt le bloc HTML et affiche la suite comme du texte brut.
    """
    barre = ""
    if progress_percent is not None:
        pct = max(0, min(100, progress_percent))
        barre = f'<div class="kpi-progress-track"><div class="kpi-progress-fill" style="width:{pct}%;"></div></div>'
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-icon-circle">{icon}</div>'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{barre}'
        f'</div>'
    )


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
