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
    indicateurs_supplementaires: list = None


def build_project_snapshot(projet_id, projet_row, crud_module) -> ProjectSnapshot:
    """Rassemble toute la hiérarchie d'un projet dans une structure unique."""
    objectifs_df = crud_module.get_objectifs(projet_id)
    resultats_df = crud_module.get_resultats_by_projet(projet_id)
    activites_df = crud_module.get_activites_by_projet(projet_id)
    taches_df = crud_module.get_taches_by_projet(projet_id)
    indicateurs_suppl_df = crud_module.get_indicateurs_supplementaires_by_projet(projet_id)

    return ProjectSnapshot(
        projet=projet_row.to_dict(),
        objectifs=objectifs_df.to_dict("records"),
        resultats=resultats_df.to_dict("records"),
        activites=activites_df.to_dict("records"),
        taches=taches_df.to_dict("records"),
        indicateurs_supplementaires=indicateurs_suppl_df.to_dict("records"),
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

    nb_activites = len(snapshot.activites)
    nb_activites_terminees = sum(1 for a in snapshot.activites if a.get("statut") == "Terminé")
    budget_active_total = sum(a.get("budget") or 0 for a in snapshot.activites)

    dates_debut = [a.get("date_debut") for a in snapshot.activites if a.get("date_debut")] + \
                  [t.get("date_debut") for t in snapshot.taches if t.get("date_debut")]
    dates_fin = [a.get("date_fin") for a in snapshot.activites if a.get("date_fin")] + \
                [t.get("date_fin") for t in snapshot.taches if t.get("date_fin")]
    periode_min = min(dates_debut) if dates_debut else None
    periode_max = max(dates_fin) if dates_fin else None

    lignes = [
        f"Projet : {projet.get('nom')}",
        f"Description (sert de base au Contexte) : {projet.get('description') or 'N/A'}",
        f"Statut actuel : {projet.get('statut')}",
        f"Dates prévues du projet : {projet.get('date_debut') or 'N/A'} au {projet.get('date_fin') or 'N/A'}",
        f"Budget global déclaré : {projet.get('budget') or 0} FCFA",
        f"Somme des budgets d'activités : {budget_active_total:.0f} FCFA",
        f"Période effective d'activités/tâches observée : {periode_min or 'N/A'} au {periode_max or 'N/A'}",
        f"Nombre d'objectifs : {len(snapshot.objectifs)}",
        f"Nombre de résultats attendus : {len(snapshot.resultats)}",
        f"Nombre d'activités : {nb_activites} (dont {nb_activites_terminees} terminées)",
        f"Nombre de tâches : {nb_taches} (dont {nb_taches_terminees} terminées, soit {taux_avancement:.0f}%)",
        "",
        "OBJECTIFS ET RÉSULTATS ATTENDUS (avec indicateurs) :",
    ]
    for o in snapshot.objectifs:
        lignes.append(f"- {o.get('titre')} (objectif {(o.get('type_objectif') or '').lower()})")
    for r in snapshot.resultats:
        cible = r.get("valeur_cible")
        actuelle = r.get("valeur_actuelle")
        lignes.append(
            f"  • Résultat « {r.get('titre')} » — indicateur : {r.get('indicateur') or 'N/A'} "
            f"({actuelle}/{cible} {r.get('unite') or ''})"
        )
        for ind in (snapshot.indicateurs_supplementaires or []):
            if ind.get("resultat_titre") == r.get("titre"):
                lignes.append(
                    f"    - Indicateur additionnel : {ind.get('nom')} "
                    f"({ind.get('valeur_actuelle')}/{ind.get('valeur_cible')} {ind.get('unite') or ''})"
                )

    lignes.append("")
    lignes.append("ACTIVITÉS (réalisées ou en cours) :")
    for a in snapshot.activites:
        lignes.append(f"- {a.get('titre')} — statut : {a.get('statut')}, progression : {a.get('progression') or 0}%")

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
complet et professionnel en français, basé UNIQUEMENT sur les données ci-dessous (n'invente
aucun chiffre, aucune date, aucun fait qui n'y figure pas).

DONNÉES DU PROJET :
{donnees}

Structure attendue du rapport — une section par ligne de titre ci-dessous, chacune
suivie de son contenu en texte simple (aucun symbole de mise en forme, voir consignes) :
Résumé exécutif
Contexte
(déduis le contexte à partir de la description du projet — reste factuel)
Problématique
(le problème que le projet cherche à résoudre, déduit du contexte et des objectifs)
Objectifs
Résultats attendus
Activités réalisées
Indicateurs
Risques identifiés
Budget
Calendrier
Conclusion
Recommandations

Consignes :
- Si une section manque de données suffisantes (ex: pas de description fournie pour le
  Contexte), indique-le brièvement ("Non renseigné" ou équivalent) plutôt que d'inventer.
- Reste factuel et professionnel, 500-800 mots au total.
- N'utilise AUCUN symbole de mise en forme Markdown : pas de #, pas de ##, pas de **,
  pas de crochets [ ]. Écris chaque titre de section seul sur sa ligne, en texte simple
  (comme dans la liste ci-dessus), suivi d'un saut de ligne puis du contenu.
- Pour les listes, utilise un tiret simple "- " en début de ligne, rien d'autre."""


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


def generate_execution_report(snapshot: ProjectSnapshot, model: str = "claude-sonnet-5") -> str:
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
        model=model,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )

    return "".join(block.text for block in response.content if hasattr(block, "text"))
