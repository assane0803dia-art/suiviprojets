"""
Ventilation temporelle des indicateurs : génère des périodes calées sur le
calendrier (trimestres = janv-mars, avril-juin... ; semestres = janv-juin,
juil-déc...) découpées à l'intérieur des dates du projet, et calcule le statut
d'un indicateur à partir de la comparaison CUMULÉE cible vs réalisé — pas
uniquement le taux final, pour détecter un retard avant la fin du projet.

Seuils de classification (volontairement isolés ici pour rester facilement
modifiables, comme demandé) :
"""
from datetime import date, timedelta

SEUIL_CONFORME = 100      # % cumulé au-dessus duquel c'est conforme/en avance
SEUIL_RETARD = 70         # % cumulé en dessous duquel c'est "en retard"
                          # (en dessous de ce seuil -> "critique")


def generer_periodes(date_debut_projet, date_fin_projet, frequence, cible_finale=0, baseline=0):
    """
    Génère la liste des périodes calées sur le calendrier entre les dates
    choisies, avec une cible par période pré-remplie par répartition égale de
    (cible finale - baseline) — la baseline représente un acquis de départ,
    seul l'écart restant à parcourir doit être réparti dans le temps.
    Modifiable ensuite par l'utilisateur, période par période.

    Retourne une liste de dicts : {label, date_debut, date_fin, cible_periode}
    """
    if not date_debut_projet or not date_fin_projet or frequence == "aucune":
        return []

    periodes_brutes = []  # (label, date_debut_periode, date_fin_periode) avant découpage

    if frequence == "mensuelle":
        courant = date_debut_projet.replace(day=1)
        while courant <= date_fin_projet:
            fin_mois = _fin_de_mois(courant)
            periodes_brutes.append((courant.strftime("%B %Y"), courant, fin_mois))
            courant = fin_mois + timedelta(days=1)

    elif frequence == "trimestrielle":
        annee = date_debut_projet.year
        while date(annee, 1, 1) <= date_fin_projet:
            for trimestre, mois_debut in enumerate([1, 4, 7, 10], start=1):
                debut_t = date(annee, mois_debut, 1)
                fin_t = _fin_de_mois(date(annee, mois_debut + 2, 1))
                if fin_t >= date_debut_projet and debut_t <= date_fin_projet:
                    periodes_brutes.append((f"T{trimestre} {annee}", debut_t, fin_t))
            annee += 1

    elif frequence == "semestrielle":
        annee = date_debut_projet.year
        while date(annee, 1, 1) <= date_fin_projet:
            for semestre, mois_debut in enumerate([1, 7], start=1):
                debut_s = date(annee, mois_debut, 1)
                fin_s = _fin_de_mois(date(annee, mois_debut + 5, 1))
                if fin_s >= date_debut_projet and debut_s <= date_fin_projet:
                    periodes_brutes.append((f"S{semestre} {annee}", debut_s, fin_s))
            annee += 1

    elif frequence == "annuelle":
        annee = date_debut_projet.year
        while date(annee, 1, 1) <= date_fin_projet:
            periodes_brutes.append((str(annee), date(annee, 1, 1), date(annee, 12, 31)))
            annee += 1

    elif frequence == "hebdomadaire":
        courant = date_debut_projet - timedelta(days=date_debut_projet.weekday())  # lundi de la semaine
        semaine = 1
        while courant <= date_fin_projet:
            fin_semaine = courant + timedelta(days=6)
            periodes_brutes.append((f"Semaine du {courant.strftime('%d/%m/%Y')}", courant, fin_semaine))
            courant = fin_semaine + timedelta(days=1)
            semaine += 1

    # Découpe chaque période aux bornes réelles du projet
    periodes = []
    for label, debut, fin in periodes_brutes:
        debut_clip = max(debut, date_debut_projet)
        fin_clip = min(fin, date_fin_projet)
        if debut_clip <= fin_clip:
            periodes.append({"label": label, "date_debut": debut_clip, "date_fin": fin_clip})

    # Répartition égale de l'écart (cible finale - baseline) entre les périodes —
    # la baseline est un acquis de départ, pas une part du chemin à parcourir.
    valeur_a_repartir = (cible_finale or 0) - (baseline or 0)
    nb = len(periodes)
    if nb and valeur_a_repartir:
        cible_par_periode = round(valeur_a_repartir / nb, 2)
        for p in periodes:
            p["cible_periode"] = cible_par_periode
    else:
        for p in periodes:
            p["cible_periode"] = 0

    return periodes


def _fin_de_mois(premier_jour_du_mois):
    if premier_jour_du_mois.month == 12:
        suivant = date(premier_jour_du_mois.year + 1, 1, 1)
    else:
        suivant = date(premier_jour_du_mois.year, premier_jour_du_mois.month + 1, 1)
    return suivant - timedelta(days=1)


def calculer_statuts_cumules(periodes, aujourdhui=None):
    """
    Prend une liste de périodes (avec date_debut/date_fin/cible_periode/
    realise_periode, déjà triées chronologiquement) et calcule pour chacune :
    cible cumulée, réalisé cumulé, écart, statut.

    Statut : "À venir" (pas encore commencée), "Conforme"/"En avance" (cumulé
    >= 100% de la cible cumulée), "En retard" (70-99%), "Critique" (<70%).
    """
    aujourdhui = aujourdhui or date.today()
    cible_cumulee = 0
    realise_cumule = 0
    resultat = []

    for p in periodes:
        cible_cumulee += p.get("cible_periode") or 0
        realise_cumule += p.get("realise_periode") or 0
        ecart = realise_cumule - cible_cumulee

        if p["date_debut"] > aujourdhui:
            statut = "À venir"
            taux_cumule = None
        else:
            taux_cumule = (realise_cumule / cible_cumulee * 100) if cible_cumulee else None
            if taux_cumule is None:
                statut = "À venir"
            elif taux_cumule >= SEUIL_CONFORME:
                statut = "En avance" if taux_cumule > 110 else "Conforme"
            elif taux_cumule >= SEUIL_RETARD:
                statut = "En retard"
            else:
                statut = "Critique"

        resultat.append({
            **p,
            "cible_cumulee": cible_cumulee, "realise_cumule": realise_cumule,
            "ecart": ecart, "taux_cumule": taux_cumule, "statut": statut,
        })

    return resultat
