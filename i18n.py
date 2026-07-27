"""
Fondation de traduction (i18n) — première passe couvrant les éléments les plus
visibles de l'application : navigation, titres et sous-titres de chaque page.

Portée assumée : ceci n'est PAS une traduction complète de l'application (chaque
champ de formulaire, chaque bouton, chaque message reste en français pour l'instant).
C'est la structure qui permet d'étendre la couverture progressivement, avec les
éléments qui ont le plus d'impact visuel déjà traduits.

Pour ajouter une traduction : ajoutez la même clé dans "fr" et "en" ci-dessous,
puis utilisez t("votre_cle") à l'endroit voulu dans le code.
"""

import streamlit as st

TRANSLATIONS = {
    "fr": {
        "nav_dashboard": "Tableau de bord",
        "nav_new_project": "Nouveau projet",
        "nav_my_projects": "Mes projets",
        "nav_reports": "Rapports",
        "nav_ai": "IA",
        "nav_settings": "Paramètres",

        "dashboard_title": "🏠 Tableau de bord",
        "dashboard_subtitle": "Suivi en temps réel, projet par projet.",

        "new_project_title": "📁 Nouveau projet",
        "new_project_subtitle": (
            "Créez votre projet en quelques secondes. Vous compléterez objectifs, "
            "résultats, activités, tâches et indicateurs ensuite, dans l'ordre que vous voulez."
        ),

        "my_projects_title": "📂 Mes projets",
        "my_projects_subtitle": "Votre espace de gestion : ouvrez n'importe quelle section, dans l'ordre que vous voulez.",

        "reports_title": "📊 Rapports",
        "reports_subtitle": (
            "Génération automatique de rapports d'exécution par IA, à partir des "
            "données déjà saisies dans le projet."
        ),

        "ai_title": "🤖 Assistant IA",
        "ai_subtitle": "Détection de risques en temps réel sur tous vos projets, et recommandations sur demande.",

        "settings_title": "⚙️ Paramètres",
    },
    "en": {
        "nav_dashboard": "Dashboard",
        "nav_new_project": "New Project",
        "nav_my_projects": "My Projects",
        "nav_reports": "Reports",
        "nav_ai": "AI",
        "nav_settings": "Settings",

        "dashboard_title": "🏠 Dashboard",
        "dashboard_subtitle": "Real-time tracking, project by project.",

        "new_project_title": "📁 New Project",
        "new_project_subtitle": (
            "Create your project in seconds. You can fill in objectives, results, "
            "activities, tasks and indicators afterwards, in any order you like."
        ),

        "my_projects_title": "📂 My Projects",
        "my_projects_subtitle": "Your workspace: open any section, in whatever order you like.",

        "reports_title": "📊 Reports",
        "reports_subtitle": (
            "Automatic AI-generated execution reports, based on the data already "
            "entered in the project."
        ),

        "ai_title": "🤖 AI Assistant",
        "ai_subtitle": "Real-time risk detection across all your projects, plus recommendations on demand.",

        "settings_title": "⚙️ Settings",
    },
}


def get_current_language() -> str:
    """
    Langue actuelle : celle enregistrée en session pour l'utilisateur connecté,
    ou "fr" par défaut (avant connexion, ou si la préférence n'a jamais été définie).
    """
    return st.session_state.get("langue_utilisateur", "fr")


def t(key: str, lang: str = None) -> str:
    """
    Traduit une clé dans la langue donnée (ou la langue courante si non précisée).
    Repli sur le français, puis sur la clé elle-même, si la traduction manque —
    pour ne jamais casser l'affichage à cause d'une clé oubliée.
    """
    if lang is None:
        lang = get_current_language()
    return TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["fr"].get(key, key)
