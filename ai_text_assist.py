"""
Module d'assistance IA pour le remplissage intelligent des champs.

Deux capacités :
  1. rewrite_text()   -> améliorer / réécrire pro / résumer / développer un texte existant
  2. suggest_items()  -> proposer des éléments enfants (résultats, activités, tâches)
                          à partir du contexte du projet, sans ressaisie manuelle

Nécessite ANTHROPIC_API_KEY dans .streamlit/secrets.toml (même clé que les rapports).
"""

import json
import streamlit as st
import anthropic

MODES = {
    "ameliorer": "Améliore ce texte : corrige le style, la clarté et la fluidité, sans changer le sens ni la longueur de façon significative.",
    "professionnel": "Réécris ce texte dans un registre professionnel et formel, adapté à un rapport de gestion de projet.",
    "resumer": "Résume ce texte en 1 à 2 phrases courtes, en gardant uniquement l'essentiel.",
    "developper": "Développe ce texte en 2 à 3 phrases supplémentaires, avec des précisions cohérentes et réalistes par rapport au contexte donné — n'invente pas de chiffres précis.",
    "smart": (
        "Reformule cet objectif spécifique pour qu'il respecte les critères SMART : "
        "Spécifique (précis, sans ambiguïté), Mesurable (quantifiable), Atteignable (réaliste "
        "compte tenu du contexte), pertinent (aligné sur l'objectif général et le contexte du "
        "projet), et Temporellement défini (avec une échéance implicite ou explicite si le "
        "contexte le permet). Garde une seule phrase concise, sans expliquer la méthode SMART, "
        "juste l'objectif reformulé."
    ),
    "pertinent": (
        "Reformule cet objectif général pour qu'il soit plus pertinent : qu'il exprime clairement "
        "la finalité globale du projet, en cohérence avec le contexte donné, sans devenir trop "
        "détaillé ou mesurable (ça reste le rôle des objectifs spécifiques). Garde une seule phrase "
        "claire et ambitieuse, sans explication de la reformulation."
    ),
}


def _client():
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Clé API Anthropic manquante. Ajoutez ANTHROPIC_API_KEY dans .streamlit/secrets.toml.")
    return anthropic.Anthropic(api_key=api_key)


def rewrite_text(text: str, mode: str, contexte: str = "", model: str = "claude-haiku-4-5-20251001") -> str:
    """Réécrit un texte selon le mode choisi (ameliorer / professionnel / resumer / developper)."""
    if mode not in MODES:
        raise ValueError(f"Mode inconnu : {mode}")

    instruction = MODES[mode]
    contexte_bloc = f"\n\nContexte du projet (pour rester cohérent) : {contexte}" if contexte else ""

    prompt = f"""{instruction}

Texte à traiter :
\"\"\"{text or "(vide)"}\"\"\"{contexte_bloc}

Réponds UNIQUEMENT avec le texte réécrit, sans préambule, sans guillemets, sans commentaire."""

    client = _client()
    response = client.messages.create(
        model=model,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if hasattr(block, "text")).strip()


def suggest_items(niveau: str, contexte_projet: str, parent_titre: str, n: int = 4,
                   model: str = "claude-haiku-4-5-20251001") -> list:
    """
    Suggère une liste d'éléments enfants cohérents avec le contexte.
    niveau : "resultats", "activites" ou "taches"
    Retourne une liste de dicts avec au moins une clé "titre" (et "description" si pertinent).
    """
    libelles = {
        "resultats": "résultats attendus (avec un indicateur mesurable chacun)",
        "activites": "activités concrètes à mener",
        "taches": "tâches précises et assignables",
    }
    if niveau not in libelles:
        raise ValueError(f"Niveau inconnu : {niveau}")

    schema_exemple = {
        "resultats": '[{"titre": "...", "description": "...", "indicateur": "...", "unite": "..."}]',
        "activites": '[{"titre": "...", "description": "..."}]',
        "taches": '[{"titre": "...", "description": "..."}]',
    }[niveau]

    prompt = f"""Contexte du projet : {contexte_projet or "Non renseigné"}
Élément parent : {parent_titre}

Propose {n} {libelles[niveau]}, cohérents avec ce contexte et cet élément parent.

Réponds UNIQUEMENT avec un tableau JSON valide, dans exactement ce format :
{schema_exemple}

Pas de texte avant ou après le JSON, pas de bloc markdown ```json."""

    client = _client()
    response = client.messages.create(
        model=model,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(block.text for block in response.content if hasattr(block, "text")).strip()

    # Sécurité : au cas où le modèle ajoute quand même un bloc markdown
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        items = json.loads(raw)
        if isinstance(items, list):
            return items
    except json.JSONDecodeError:
        pass
    return []
