"""
Module de génération de rapports par IA — utilise l'API Anthropic Claude.

Architecture :
  1. build_project_snapshot()   -> rassemble toute la hiérarchie du projet
  2. detect_delays_and_risks()  -> calcule les retards en Python (pas par l'IA,
                                    pour éviter les erreurs/hallucinations sur les dates)
  3. generate_execution_report() -> envoie un résumé structuré à Claude et récupère
                                     un rapport rédigé en français

Configuration requise : une clé API dans .streamlit/secrets.toml :
    ANTHROPIC_API_KEY = "sk-ant-..."
"""

from dataclasses import dataclass
from datetime import date
import streamlit as st
import anthropic


@dataclass
class ProjectSnapshot:
    projet: dict
    objectifs: list
    resultats: list
    activites: list
    taches: list


def build_project_snapshot(projet_id, projet_row, crud_module) -> ProjectSnapshot:
    """Rassemble toute la hiérarchie d'un projet dans une structure unique."""
    objectifs_df = crud_module.get_objectifs(projet_id)
    resultats_df = crud_module.get_resultats_by_projet(projet_id)
    activites_df = crud_module.get_activites_by_projet(projet_id)
    taches_df = crud_module.get_taches_by_projet(projet_id)

    return ProjectSnapshot(
        projet=projet_row.to_dict(),
        objectifs=objectifs_df.to_dict("records"),
        resultats=resultats_df.to_dict("records"),
        activites=activites_df.to_dict("records"),
        taches=taches_df.to_dict("records"),
    )


def detect_delays_and_risks(snapshot: ProjectSnapshot) -> dict:
    """
    Calcule les retards de façon déterministe (dates dépassées + statut non terminé),
    plutôt que de laisser l'IA deviner — plus fiable.
    """
    today = date.today()
    taches_en_retard = []
    activites_en_retard = []

    for t in snapshot.taches:
        date_fin = t.get("date_fin")
        if date_fin and date_fin < today and t.get("statut") != "Terminé":
            taches_en_retard.append(t)

    for a in snapshot.activites:
        date_fin = a.get("date_fin")
        if date_fin and date_fin < today and a.get("statut") != "Terminé":
            activites_en_retard.append(a)

    return {
        "taches_en_retard": taches_en_retard,
        "activites_en_retard": activites_en_retard,
    }


def _build_prompt(snapshot: ProjectSnapshot, risques: dict) -> str:
    projet = snapshot.projet
    nb_taches = len(snapshot.taches)
    nb_taches_terminees = sum(1 for t in snapshot.taches if t.get("statut") == "Terminé")
    taux_avancement = (nb_taches_terminees / nb_taches * 100) if nb_taches else 0

    lignes = [
        f"Projet : {projet.get('nom')}",
        f"Description : {projet.get('description') or 'N/A'}",
        f"Statut : {projet.get('statut')}",
        f"Budget global : {projet.get('budget') or 0} FCFA",
        f"Nombre d'objectifs : {len(snapshot.objectifs)}",
        f"Nombre de résultats attendus : {len(snapshot.resultats)}",
        f"Nombre d'activités : {len(snapshot.activites)}",
        f"Nombre de tâches : {nb_taches} (dont {nb_taches_terminees} terminées, soit {taux_avancement:.0f}%)",
        "",
        "OBJECTIFS ET RÉSULTATS ATTENDUS :",
    ]
    for o in snapshot.objectifs:
        lignes.append(f"- [{o.get('type_objectif')}] {o.get('titre')}")
    for r in snapshot.resultats:
        cible = r.get("valeur_cible")
        actuelle = r.get("valeur_actuelle")
        lignes.append(
            f"  • Résultat « {r.get('titre')} » — indicateur : {r.get('indicateur') or 'N/A'} "
            f"({actuelle}/{cible} {r.get('unite') or ''})"
        )

    lignes.append("")
    lignes.append("ACTIVITÉS EN RETARD (date de fin dépassée, non terminées) :")
    if risques["activites_en_retard"]:
        for a in risques["activites_en_retard"]:
            lignes.append(f"- {a.get('titre')} (échéance : {a.get('date_fin')}, statut : {a.get('statut')})")
    else:
        lignes.append("- Aucune")

    lignes.append("")
    lignes.append("TÂCHES EN RETARD (date de fin dépassée, non terminées) :")
    if risques["taches_en_retard"]:
        for t in risques["taches_en_retard"]:
            lignes.append(f"- {t.get('titre')} (échéance : {t.get('date_fin')}, statut : {t.get('statut')})")
    else:
        lignes.append("- Aucune")

    donnees = "\n".join(lignes)

    return f"""Tu es un assistant spécialisé en gestion de projet. Rédige un rapport d'exécution
professionnel en français, basé UNIQUEMENT sur les données ci-dessous (n'invente aucun chiffre).

DONNÉES DU PROJET :
{donnees}

Structure attendue du rapport (utilise des titres Markdown ## et des listes à puces -) :
## Résumé exécutif
## État d'avancement par objectif
## Indicateurs clés
## Retards et risques identifiés
## Recommandations

Reste factuel, concis (300-500 mots), et professionnel. Si une section n'a pas de données
suffisantes, indique-le brièvement plutôt que d'inventer du contenu."""


def generate_recommendations(snapshot: ProjectSnapshot, risques: dict) -> str:
    """
    Génère de courtes recommandations à partir des risques déjà détectés (pas besoin
    de refaire l'analyse complète). Utilise un modèle plus léger, adapté à cette tâche courte.
    """
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Clé API Anthropic manquante. Ajoutez ANTHROPIC_API_KEY dans .streamlit/secrets.toml."
        )

    projet_nom = snapshot.projet.get("nom", "")
    lignes = [f"Projet : {projet_nom}", ""]

    if risques["activites_en_retard"]:
        lignes.append("Activités en retard :")
        for a in risques["activites_en_retard"]:
            lignes.append(f"- {a.get('titre')} (échéance dépassée : {a.get('date_fin')})")
    if risques["taches_en_retard"]:
        lignes.append("Tâches en retard :")
        for t in risques["taches_en_retard"]:
            lignes.append(f"- {t.get('titre')} (échéance dépassée : {t.get('date_fin')})")

    if not risques["activites_en_retard"] and not risques["taches_en_retard"]:
        lignes.append("Aucun retard détecté actuellement.")

    donnees = "\n".join(lignes)

    prompt = f"""Voici les retards détectés sur un projet :

{donnees}

En 3 à 5 puces courtes (format Markdown "- "), propose des recommandations concrètes et
actionnables pour un chef de projet. Sois direct, sans préambule ni conclusion."""

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


def generate_execution_report(snapshot: ProjectSnapshot) -> str:
    """Génère un rapport d'exécution via l'API Anthropic Claude."""
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Clé API Anthropic manquante. Ajoutez ANTHROPIC_API_KEY dans .streamlit/secrets.toml."
        )

    risques = detect_delays_and_risks(snapshot)
    prompt = _build_prompt(snapshot, risques)

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    return "".join(block.text for block in response.content if hasattr(block, "text"))