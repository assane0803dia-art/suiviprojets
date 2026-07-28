"""
Calcule le chemin critique d'un projet à partir des dépendances entre activités
(champ "Dépend de" sur chaque activité).

Méthode : plus long chemin cumulé en durée à travers l'arbre des dépendances —
équivalent, pour ce modèle simplifié à un seul prédécesseur par activité, à la
méthode du chemin critique (CPM) classique : la séquence d'activités qui
détermine la durée totale minimale du projet.

Limite assumée : chaque activité ne peut dépendre que d'UNE SEULE activité
prédécesseure (pas de dépendances multiples type "attendre A ET B"). Suffisant
pour des enchaînements simples ou avec quelques branches, mais pas pour des
réseaux de dépendances complexes.

Tant qu'aucune dépendance n'est renseignée, chaque activité est son propre
chemin isolé : le "chemin critique" se réduit alors à l'activité la plus
longue prise individuellement — c'est un résultat attendu, pas une erreur.
"""


def _duree_jours(activite: dict) -> float:
    debut = activite.get("date_debut")
    fin = activite.get("date_fin")
    if debut and fin and fin >= debut:
        return (fin - debut).days + 1
    return 1  # Durée par défaut si les dates ne sont pas renseignées


def compute_critical_path(activites_df) -> set:
    """
    activites_df : DataFrame avec au moins les colonnes id, date_debut, date_fin,
    depend_de_activite_id.

    Retourne l'ensemble des id d'activités qui font partie du chemin critique.
    """
    if activites_df.empty:
        return set()

    activites = activites_df.set_index("id").to_dict("index")

    enfants = {}
    racines = []
    for act_id, act in activites.items():
        pred = act.get("depend_de_activite_id")
        if pred is not None and pred in activites:
            enfants.setdefault(pred, []).append(act_id)
        else:
            racines.append(act_id)

    memo = {}

    def plus_long_chemin(act_id):
        if act_id in memo:
            return memo[act_id]
        duree = _duree_jours(activites[act_id])
        enfants_ids = enfants.get(act_id, [])
        if not enfants_ids:
            resultat = (duree, [act_id])
        else:
            meilleur = max((plus_long_chemin(e) for e in enfants_ids), key=lambda x: x[0])
            resultat = (duree + meilleur[0], [act_id] + meilleur[1])
        memo[act_id] = resultat
        return resultat

    meilleur_global = (0, [])
    for racine in racines:
        candidat = plus_long_chemin(racine)
        if candidat[0] > meilleur_global[0]:
            meilleur_global = candidat

    return set(meilleur_global[1])
