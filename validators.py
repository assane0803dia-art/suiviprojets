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
