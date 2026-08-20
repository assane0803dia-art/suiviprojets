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
    depenses: list = None
    budget_detaille_total: float = 0.0
    indicateurs_calendrier: list = None


def build_project_snapshot(projet_id, projet_row, crud_module, periode_debut=None, periode_fin=None) -> ProjectSnapshot:
    """
    Rassemble toute la hiérarchie d'un projet dans une structure unique.

    Si `periode_debut`/`periode_fin` sont fournis, le rapport ne porte que sur
    cette période : activités et tâches chevauchant la période, dépenses dont la
    date tombe dedans. Les indicateurs restent calculés en CUMULÉ depuis le début
    du projet jusqu'à la fin de la période choisie (cohérent avec la logique de
    détection de retard déjà en place — un cumul tronqué n'aurait pas de sens).
    """
    objectifs_df = crud_module.get_objectifs(projet_id)
    resultats_df = crud_module.get_resultats_by_projet(projet_id)
    activites_df = crud_module.get_activites_by_projet(projet_id)
    taches_df = crud_module.get_taches_by_projet(projet_id)
    indicateurs_suppl_df = crud_module.get_indicateurs_supplementaires_by_projet(projet_id)
    depenses_df = crud_module.get_depenses_by_projet(projet_id)
    lignes_budget_df = crud_module.get_budget_lignes_by_projet(projet_id)
    toutes_periodes_df = crud_module.get_toutes_periodes_projet(projet_id)

    if periode_debut and periode_fin:
        if not activites_df.empty:
            chevauche = (
                (activites_df["date_debut"].isna() | (activites_df["date_debut"] <= periode_fin))
                & (activites_df["date_fin"].isna() | (activites_df["date_fin"] >= periode_debut))
            )
            activites_df = activites_df[chevauche]
        if not taches_df.empty:
            chevauche_t = (
                (taches_df["date_debut"].isna() | (taches_df["date_debut"] <= periode_fin))
                & (taches_df["date_fin"].isna() | (taches_df["date_fin"] >= periode_debut))
            )
            taches_df = taches_df[chevauche_t]
        if not depenses_df.empty:
            depenses_df = depenses_df[
                (depenses_df["date_depense"] >= periode_debut) & (depenses_df["date_depense"] <= periode_fin)
            ]
        if not toutes_periodes_df.empty:
            # On garde tout l'historique cumulé jusqu'à la fin de la période choisie
            # (pas seulement les périodes strictement à l'intérieur), pour que le
            # cumulé cible/réalisé reste correct.
            toutes_periodes_df = toutes_periodes_df[toutes_periodes_df["date_debut"] <= periode_fin]

    # Le budget détaillé par rubriques (s'il est renseigné) est la référence
    # officielle du budget prévisionnel — le champ Activites.budget est un
    # ancien réglage simplifié par activité, pas nécessairement complet
    # (RH, missions, équipements partagés... n'y sont pas rattachés).
    budget_detaille_total = float(lignes_budget_df["cout_total"].sum()) if not lignes_budget_df.empty else 0.0

    # Statut calendaire de chaque indicateur ventilé (même logique que le Dashboard) :
    # comparaison cumulée cible vs réalisé, pas le taux final brut.
    indicateurs_calendrier = []
    if not toutes_periodes_df.empty:
        import indicateurs_temporels
        for _, groupe in toutes_periodes_df.groupby("indicateur_key"):
            periodes_ind = groupe.rename(columns={"periode_label": "label"}).to_dict("records")
            periodes_calc = indicateurs_temporels.calculer_statuts_cumules(sorted(periodes_ind, key=lambda p: p["date_debut"]))
            periodes_commencees = [p for p in periodes_calc if p["statut"] != "À venir"]
            statut_actuel = periodes_commencees[-1] if periodes_commencees else periodes_calc[-1]
            indicateurs_calendrier.append({
                "nom": groupe.iloc[0]["nom_indicateur"], "statut": statut_actuel["statut"],
                "cible_cumulee": statut_actuel["cible_cumulee"], "realise_cumule": statut_actuel["realise_cumule"],
                "ecart": statut_actuel["ecart"], "derniere_periode": statut_actuel["label"],
            })

    return ProjectSnapshot(
        projet=projet_row.to_dict(),
        objectifs=objectifs_df.to_dict("records"),
        resultats=resultats_df.to_dict("records"),
        activites=activites_df.to_dict("records"),
        taches=taches_df.to_dict("records"),
        indicateurs_supplementaires=indicateurs_suppl_df.to_dict("records"),
        depenses=depenses_df.to_dict("records"),
        budget_detaille_total=budget_detaille_total,
        indicateurs_calendrier=indicateurs_calendrier,
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


def _build_prompt(snapshot: ProjectSnapshot, risques: dict, modele_rapport: str = "Standard", periode_debut=None, periode_fin=None) -> str:
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

    depense_reelle_total = sum(d.get("montant") or 0 for d in (snapshot.depenses or []))
    reference_budget = snapshot.budget_detaille_total if snapshot.budget_detaille_total > 0 else budget_active_total
    taux_execution = (depense_reelle_total / reference_budget * 100) if reference_budget else 0

    niveau_detail = {
        "Résumé court": "Reste très concis : un résumé exécutif de quelques phrases par section, pas de développement long.",
        "Détaillé": "Développe chaque section en profondeur, avec une analyse fine de chaque écart et de ses implications.",
        "Standard": "Niveau de détail standard : équilibré, ni trop bref ni trop long.",
    }.get(modele_rapport, "Niveau de détail standard : équilibré, ni trop bref ni trop long.")

    lignes = [
        f"Projet : {projet.get('nom')}",
        f"Description (sert de base au Contexte) : {projet.get('description') or 'N/A'}",
        f"Statut actuel : {projet.get('statut')}",
        f"Dates prévues du projet : {projet.get('date_debut') or 'N/A'} au {projet.get('date_fin') or 'N/A'}",
    ]
    if periode_debut and periode_fin:
        lignes.append(
            f"⚠️ PÉRIODE DU RAPPORT : ce rapport ne couvre QUE la période du {periode_debut} au {periode_fin} — "
            f"toutes les données ci-dessous sont déjà filtrées sur cette période (sauf les indicateurs, en cumulé "
            f"depuis le début du projet jusqu'à la fin de cette période). Précise cette période dans le rapport."
        )
    lignes.append(f"Niveau de détail attendu ({modele_rapport}) : {niveau_detail}")
    lignes += [
        f"Budget prévisionnel du projet (détail par rubriques) : {reference_budget:,.0f} {projet.get('devise_principale') or 'FCFA'}".replace(",", " "),
        f"Dépenses réelles enregistrées à ce jour : {depense_reelle_total:,.0f} {projet.get('devise_principale') or 'FCFA'} (taux d'exécution : {taux_execution:.0f}%)".replace(",", " "),
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
        ligne = f"- {a.get('titre')} — statut : {a.get('statut')}, progression : {a.get('progression') or 0}%"
        if a.get("observation"):
            ligne += f" — observation du responsable : « {a.get('observation')} »"
        lignes.append(ligne)
    lignes.append(
        "Consigne pour les activités ci-dessus : quand une observation existe, utilise-la pour EXPLIQUER "
        "le taux de réalisation (pas seulement le constater) — par exemple relier un retard à la cause "
        "rapportée. N'invente JAMAIS de cause si aucune observation n'est renseignée ; dans ce cas, "
        "contente-toi de constater le taux sans supposer de raison."
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

    if snapshot.indicateurs_calendrier:
        lignes.append("")
        lignes.append("INDICATEURS AVEC VENTILATION TEMPORELLE (comparaison CUMULÉE cible vs réalisé à ce jour, pas le taux final) :")
        for ind in snapshot.indicateurs_calendrier:
            lignes.append(
                f"- {ind['nom']} — statut : {ind['statut']} (à la période {ind['derniere_periode']}) — "
                f"cible cumulée : {ind['cible_cumulee']:.1f}, réalisé cumulé : {ind['realise_cumule']:.1f}, écart : {ind['ecart']:+.1f}"
            )
        lignes.append(
            "Consigne pour ces indicateurs : base ton analyse de retard sur ce statut cumulé (Conforme/En avance/"
            "En retard/Critique), PAS sur le taux d'atteinte de la cible finale du projet — un indicateur peut "
            "sembler bas en valeur absolue tout en étant parfaitement conforme à son calendrier. Si un écart "
            "existe, tu peux le relier à une observation d'activité pertinente si elle est disponible ci-dessus, "
            "sans jamais inventer de lien qui ne serait pas clairement établi par les données."
        )

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


def generate_execution_report(snapshot: ProjectSnapshot, model: str = "claude-sonnet-5", modele_rapport: str = "Standard", periode_debut=None, periode_fin=None) -> str:
    """Génère un rapport d'exécution via l'API Anthropic Claude."""
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Clé API Anthropic manquante. Ajoutez ANTHROPIC_API_KEY dans .streamlit/secrets.toml."
        )

    risques = detect_delays_and_risks(snapshot)
    prompt = _build_prompt(snapshot, risques, modele_rapport=modele_rapport, periode_debut=periode_debut, periode_fin=periode_fin)

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )

    return "".join(block.text for block in response.content if hasattr(block, "text"))
