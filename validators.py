"""
Règles de validation des dates, utilisées par les formulaires de création/modification.
Toutes les fonctions retournent True si valide, False sinon (bornes vides = pas de contrainte).
"""


def dates_valides(date_debut, date_fin):
    """False si la date de fin est antérieure à la date de début."""
    if date_debut and date_fin and date_fin < date_debut:
        return False
    return True


def tache_dans_intervalle_activite(date_debut_tache, date_fin_tache, date_debut_activite, date_fin_activite):
    """
    False si les dates de la tâche sortent de l'intervalle de dates de son activité parente.
    Ignore les bornes non renseignées (ni côté tâche, ni côté activité).
    """
    if date_debut_activite and date_debut_tache and date_debut_tache < date_debut_activite:
        return False
    if date_fin_activite and date_fin_tache and date_fin_tache > date_fin_activite:
        return False
    if date_debut_activite and date_fin_tache and date_fin_tache < date_debut_activite:
        return False
    if date_fin_activite and date_debut_tache and date_debut_tache > date_fin_activite:
        return False
    return True


def cree_une_boucle(activite_id, nouveau_depend_de_id, activites_df):
    """
    True si faire dépendre `activite_id` de `nouveau_depend_de_id` créerait une
    boucle de dépendances (une activité ne peut pas dépendre, même indirectement,
    d'elle-même). On remonte la chaîne de prédécesseurs à partir de la dépendance
    proposée ; si on retombe sur activite_id, c'est une boucle.
    """
    if nouveau_depend_de_id is None:
        return False
    if nouveau_depend_de_id == activite_id:
        return True

    predecesseurs = dict(zip(activites_df["id"], activites_df["depend_de_activite_id"]))
    courant = nouveau_depend_de_id
    vus = set()
    while courant is not None and courant not in vus:
        if courant == activite_id:
            return True
        vus.add(courant)
        courant = predecesseurs.get(courant)
    return False
