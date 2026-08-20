import psycopg2
import pandas as pd
import numpy as np
import os
import streamlit as st
import db


def _to_native(value):
    """Convertit les types numpy/pandas (int64, float64...) en types Python natifs."""
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


def _convert_params(params):
    if params is None:
        return None
    return tuple(_to_native(p) for p in params)


def run_query(query, params=None):
    """Exécute une requête SELECT via le pool de connexions partagé."""
    return db.run_query(query, params=_convert_params(params))


def run_execute(query, params=None):
    """Exécute une requête d'écriture via le pool de connexions partagé."""
    return db.run_execute(query, params=_convert_params(params))


# ----------------------------------------------------------------------------
# Utilisateurs (responsables)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def get_utilisateurs(projet_id):
    """Responsables rattachés à un projet précis uniquement — chaque projet a sa
    propre liste, pour garantir l'indépendance entre projets."""
    return run_query(
        "SELECT id, nom, email, role, user_id FROM Utilisateurs WHERE projet_id = %s ORDER BY nom",
        params=(projet_id,),
    )


def create_utilisateur(nom, email, role, projet_id, user_id=None):
    try:
        new_id = run_execute(
            "INSERT INTO Utilisateurs (nom, email, mot_de_passe, role, projet_id, user_id, date_creation) "
            "VALUES (%s, %s, '', %s, %s, %s, NOW()) RETURNING id",
            (nom, email, role, projet_id, user_id),
        )
        get_utilisateurs.clear()
        return new_id
    except psycopg2.errors.UniqueViolation:
        raise ValueError(f"Un responsable avec l'email '{email}' existe déjà.")


def update_utilisateur(id, nom, email, role, user_id=None):
    try:
        run_execute("UPDATE Utilisateurs SET nom=%s, email=%s, role=%s, user_id=%s WHERE id=%s", (nom, email, role, user_id, id))
        get_utilisateurs.clear()
    except psycopg2.errors.UniqueViolation:
        raise ValueError(f"Un responsable avec l'email '{email}' existe déjà.")


def get_comptes_utilisateurs():
    """Liste des comptes de connexion existants (table Users), pour associer un
    responsable à un compte capable de recevoir des notifications."""
    return run_query("SELECT id, username, nom_complet FROM Users ORDER BY username")


def delete_utilisateur(id):
    """Supprime un responsable, en détachant proprement toutes ses affectations existantes
    (projets, objectifs, activités, tâches) plutôt que de bloquer sur une contrainte."""
    run_execute("UPDATE Projets SET responsable_id=NULL WHERE responsable_id=%s", (id,))
    run_execute("UPDATE Objectifs SET responsable_id=NULL WHERE responsable_id=%s", (id,))
    run_execute("UPDATE Activites SET responsable_id=NULL WHERE responsable_id=%s", (id,))
    run_execute("UPDATE Taches SET responsable_id=NULL WHERE responsable_id=%s", (id,))
    run_execute("DELETE FROM Utilisateurs WHERE id=%s", (id,))
    get_utilisateurs.clear()
    get_projets.clear()
    get_objectifs.clear()
    get_activites_by_projet.clear()
    get_taches_by_projet.clear()


# ----------------------------------------------------------------------------
# Projets
# ----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def get_projets():
    return run_query("""
        SELECT P.id, P.nom, P.description, P.date_debut, P.date_fin, P.budget, P.statut,
               P.responsable_id, U.nom AS responsable,
               P.devise_principale, P.devise_secondaire, P.taux_conversion
        FROM Projets P
        LEFT JOIN Utilisateurs U ON P.responsable_id = U.id
        ORDER BY P.nom
    """)


def projet_name_exists(nom, exclude_id=None):
    df = run_query("SELECT id FROM Projets WHERE LOWER(LTRIM(RTRIM(nom))) = LOWER(LTRIM(RTRIM(%s)))", params=(nom,))
    if exclude_id is not None:
        df = df[df["id"] != exclude_id]
    return not df.empty


def create_projet(nom, description, date_debut, date_fin, budget, statut, responsable_id):
    if projet_name_exists(nom):
        raise ValueError(f"Un projet nommé « {nom} » existe déjà. Choisissez un autre nom.")
    new_id = run_execute(
        "INSERT INTO Projets (nom, description, date_debut, date_fin, budget, statut, responsable_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (nom, description, date_debut, date_fin, budget, statut, responsable_id),
    )
    get_projets.clear()
    return new_id


def update_projet(id, nom, description, date_debut, date_fin, budget, statut, responsable_id):
    if projet_name_exists(nom, exclude_id=id):
        raise ValueError(f"Un projet nommé « {nom} » existe déjà. Choisissez un autre nom.")
    run_execute(
        "UPDATE Projets SET nom=%s, description=%s, date_debut=%s, date_fin=%s, budget=%s, statut=%s, responsable_id=%s "
        "WHERE id=%s",
        (nom, description, date_debut, date_fin, budget, statut, responsable_id, id),
    )
    get_projets.clear()


def update_devise_projet(id, devise_principale, devise_secondaire, taux_conversion):
    run_execute(
        "UPDATE Projets SET devise_principale=%s, devise_secondaire=%s, taux_conversion=%s WHERE id=%s",
        (devise_principale, devise_secondaire, taux_conversion, id),
    )
    get_projets.clear()


def delete_projet(id):
    objectifs = run_query("SELECT id FROM Objectifs WHERE projet_id=%s", params=(id,))
    for obj_id in objectifs["id"]:
        delete_objectif(obj_id)

    run_execute("DELETE FROM Parties_Prenantes WHERE projet_id=%s", (id,))
    get_parties_prenantes.clear()

    documents = run_query("SELECT id, chemin_fichier FROM Documents WHERE projet_id=%s", params=(id,))
    for _, doc in documents.iterrows():
        _delete_file_safely(doc["chemin_fichier"])
    run_execute("DELETE FROM Documents WHERE projet_id=%s", (id,))
    get_documents.clear()

    # Budget hiérarchique (Rubriques → Sous-rubriques → Lignes)
    rubriques = run_query("SELECT id FROM Budget_Rubriques WHERE projet_id=%s", params=(id,))
    for rub_id in rubriques["id"]:
        delete_budget_rubrique(rub_id)

    # Rapports sauvegardés, accès lecteurs, notifications liées à ce projet
    run_execute("DELETE FROM Rapports WHERE projet_id=%s", (id,))
    run_execute("DELETE FROM Acces_Lecteurs WHERE projet_id=%s", (id,))
    run_execute("DELETE FROM Notifications WHERE projet_id=%s", (id,))

    # Responsables rattachés à ce projet (table Utilisateurs, indépendante par projet)
    # On détache d'abord le responsable du projet lui-même (référence circulaire :
    # Projets.responsable_id -> Utilisateurs.id -> Utilisateurs.projet_id -> Projets.id)
    run_execute("UPDATE Projets SET responsable_id=NULL WHERE id=%s", (id,))
    run_execute("DELETE FROM Utilisateurs WHERE projet_id=%s", (id,))
    get_utilisateurs.clear()

    # Le "dernier projet consulté" de chaque utilisateur (redirection après connexion)
    # peut pointer vers ce projet — à détacher avant de le supprimer.
    run_execute("UPDATE Users SET dernier_projet_id=NULL WHERE dernier_projet_id=%s", (id,))

    run_execute("DELETE FROM Projets WHERE id=%s", (id,))
    get_projets.clear()


# ----------------------------------------------------------------------------
# Objectifs
# ----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def get_objectifs(projet_id):
    return run_query("""
        SELECT O.id, O.type_objectif, O.titre, O.responsable_id, U.nom AS responsable
        FROM Objectifs O
        LEFT JOIN Utilisateurs U ON O.responsable_id = U.id
        WHERE O.projet_id = %s
        ORDER BY O.type_objectif, O.titre
    """, params=(projet_id,))


def create_objectif(projet_id, type_objectif, titre, responsable_id):
    new_id = run_execute(
        "INSERT INTO Objectifs (projet_id, type_objectif, titre, responsable_id) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (projet_id, type_objectif, titre, responsable_id),
    )
    get_objectifs.clear()
    return new_id


def update_objectif(id, type_objectif, titre, responsable_id):
    run_execute(
        "UPDATE Objectifs SET type_objectif=%s, titre=%s, responsable_id=%s WHERE id=%s",
        (type_objectif, titre, responsable_id, id),
    )
    get_objectifs.clear()


def delete_objectif(id):
    resultats = run_query("SELECT id FROM Resultats WHERE objectif_id=%s", params=(id,))
    for res_id in resultats["id"]:
        delete_resultat(res_id)
    run_execute("DELETE FROM Objectifs WHERE id=%s", (id,))
    get_objectifs.clear()


# ----------------------------------------------------------------------------
# Resultats
# ----------------------------------------------------------------------------
def get_resultats(objectif_id):
    return run_query("""
        SELECT id, titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut,
               source_verification, baseline
        FROM Resultats
        WHERE objectif_id = %s
        ORDER BY titre
    """, params=(objectif_id,))


def create_resultat(objectif_id, titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut,
                     source_verification=None, baseline=None):
    new_id = run_execute(
        "INSERT INTO Resultats (objectif_id, titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut, "
        "source_verification, baseline) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (objectif_id, titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut,
         source_verification, baseline),
    )
    get_resultats_by_projet.clear()
    return new_id


def update_resultat(id, titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut,
                     source_verification=None, baseline=None):
    run_execute(
        "UPDATE Resultats SET titre=%s, description=%s, indicateur=%s, valeur_cible=%s, valeur_actuelle=%s, unite=%s, "
        "statut=%s, source_verification=%s, baseline=%s WHERE id=%s",
        (titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut,
         source_verification, baseline, id),
    )
    get_resultats_by_projet.clear()


def delete_resultat(id):
    activites = run_query("SELECT id FROM Activites WHERE resultat_id=%s", params=(id,))
    for act_id in activites["id"]:
        delete_activite(act_id)
    run_execute("DELETE FROM Indicateurs_Supplementaires WHERE resultat_id=%s", (id,))
    run_execute("DELETE FROM Resultats WHERE id=%s", (id,))
    get_resultats_by_projet.clear()


# ----------------------------------------------------------------------------
# Activites
# ----------------------------------------------------------------------------
def get_activites(resultat_id):
    return run_query("""
        SELECT A.id, A.titre, A.description, A.statut, A.budget, A.progression,
               A.date_debut, A.date_fin, A.responsable_id, U.nom AS responsable
        FROM Activites A
        LEFT JOIN Utilisateurs U ON A.responsable_id = U.id
        WHERE A.resultat_id = %s
        ORDER BY A.titre
    """, params=(resultat_id,))


def create_activite(resultat_id, titre, description, responsable_id, date_debut, date_fin, statut, budget, progression, depend_de_activite_id=None, observation=None):
    new_id = run_execute(
        "INSERT INTO Activites (resultat_id, titre, description, responsable_id, date_debut, date_fin, statut, budget, progression, depend_de_activite_id, observation) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (resultat_id, titre, description, responsable_id, date_debut, date_fin, statut, budget, progression, depend_de_activite_id, observation),
    )
    get_activites_by_projet.clear()
    return new_id


def update_activite(id, titre, description, responsable_id, date_debut, date_fin, statut, budget, progression, depend_de_activite_id=None, observation=None):
    run_execute(
        "UPDATE Activites SET titre=%s, description=%s, responsable_id=%s, date_debut=%s, date_fin=%s, statut=%s, budget=%s, progression=%s, "
        "depend_de_activite_id=%s, observation=%s WHERE id=%s",
        (titre, description, responsable_id, date_debut, date_fin, statut, budget, progression, depend_de_activite_id, observation, id),
    )
    get_activites_by_projet.clear()


def delete_activite(id):
    run_execute("DELETE FROM Taches WHERE activite_id=%s", (id,))
    run_execute("DELETE FROM Depenses WHERE activite_id=%s", (id,))
    run_execute("UPDATE Budget_Lignes SET activite_id=NULL WHERE activite_id=%s", (id,))
    # D'autres activités peuvent dépendre de celle-ci (champ "Dépend de", chemin critique)
    run_execute("UPDATE Activites SET depend_de_activite_id=NULL WHERE depend_de_activite_id=%s", (id,))
    run_execute("DELETE FROM Activites WHERE id=%s", (id,))
    get_activites_by_projet.clear()
    get_taches_by_projet.clear()
    get_budget_lignes_by_projet.clear()


# ----------------------------------------------------------------------------
# Taches
# ----------------------------------------------------------------------------
def get_taches(activite_id):
    return run_query("""
        SELECT T.id, T.titre, T.description, T.priorite, T.statut, T.progression,
               T.date_debut, T.date_fin, T.responsable_id, U.nom AS responsable
        FROM Taches T
        LEFT JOIN Utilisateurs U ON T.responsable_id = U.id
        WHERE T.activite_id = %s
        ORDER BY T.titre
    """, params=(activite_id,))


def create_tache(activite_id, titre, description, responsable_id, priorite, statut, date_debut, date_fin, progression):
    new_id = run_execute(
        "INSERT INTO Taches (activite_id, titre, description, responsable_id, priorite, statut, date_debut, date_fin, progression) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (activite_id, titre, description, responsable_id, priorite, statut, date_debut, date_fin, progression),
    )
    get_taches_by_projet.clear()
    return new_id


def update_tache(id, titre, description, responsable_id, priorite, statut, date_debut, date_fin, progression):
    run_execute(
        "UPDATE Taches SET titre=%s, description=%s, responsable_id=%s, priorite=%s, statut=%s, date_debut=%s, date_fin=%s, progression=%s "
        "WHERE id=%s",
        (titre, description, responsable_id, priorite, statut, date_debut, date_fin, progression, id),
    )
    get_taches_by_projet.clear()


def delete_tache(id):
    run_execute("DELETE FROM Taches WHERE id=%s", (id,))
    get_taches_by_projet.clear()


def recalculate_activite_progression(activite_id):
    """
    Recalcule automatiquement la progression et le statut d'une activité à partir
    de ses tâches : progression = moyenne des progressions des tâches, et l'activité
    passe à "Terminé" seulement si TOUTES ses tâches le sont.

    Si l'activité n'a aucune tâche, rien n'est recalculé : la valeur reste celle
    saisie manuellement — c'est la seule mesure pertinente possible sans données
    à agréger.

    Un statut "Bloqué" positionné manuellement est préservé (pas écrasé par le calcul
    automatique), car il signale un blocage indépendant de l'avancement des tâches.
    """
    taches_df = run_query(
        "SELECT statut, progression FROM Taches WHERE activite_id = %s",
        params=(activite_id,),
    )
    if taches_df.empty:
        return

    moyenne = float(taches_df["progression"].fillna(0).mean())
    toutes_terminees = bool((taches_df["statut"] == "Terminé").all())

    activite_actuelle = run_query("SELECT statut FROM Activites WHERE id = %s", params=(activite_id,))
    statut_actuel = activite_actuelle.iloc[0]["statut"] if not activite_actuelle.empty else None

    if toutes_terminees:
        nouveau_statut, moyenne = "Terminé", 100.0
    elif statut_actuel == "Bloqué":
        nouveau_statut = "Bloqué"
    elif moyenne > 0:
        nouveau_statut = "En cours"
    else:
        nouveau_statut = "À faire"

    run_execute(
        "UPDATE Activites SET progression=%s, statut=%s WHERE id=%s",
        (moyenne, nouveau_statut, activite_id),
    )
    get_activites_by_projet.clear()


# ----------------------------------------------------------------------------
# Vues "à plat" — tous les éléments d'un projet, indépendamment de leur parent
# (nécessaires pour un accès direct par section, sans ordre imposé)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def get_resultats_by_projet(projet_id):
    return run_query("""
        SELECT R.id, R.titre, R.description, R.indicateur, R.valeur_cible, R.valeur_actuelle, R.unite, R.statut,
               R.source_verification, R.baseline, R.objectif_id, O.titre AS objectif_titre, R.frequence_ventilation
        FROM Resultats R
        JOIN Objectifs O ON R.objectif_id = O.id
        WHERE O.projet_id = %s
        ORDER BY O.titre, R.titre
    """, params=(projet_id,))


@st.cache_data(ttl=15)
def get_activites_by_projet(projet_id):
    return run_query("""
        SELECT A.id, A.titre, A.description, A.statut, A.budget, A.progression, A.date_debut, A.date_fin,
               A.responsable_id, U.nom AS responsable, A.resultat_id, R.titre AS resultat_titre,
               A.depend_de_activite_id, P.titre AS depend_de_titre, A.observation
        FROM Activites A
        JOIN Resultats R ON A.resultat_id = R.id
        JOIN Objectifs O ON R.objectif_id = O.id
        LEFT JOIN Utilisateurs U ON A.responsable_id = U.id
        LEFT JOIN Activites P ON A.depend_de_activite_id = P.id
        WHERE O.projet_id = %s
        ORDER BY R.titre, A.titre
    """, params=(projet_id,))


@st.cache_data(ttl=15)
def get_performance_responsables(projet_id):
    """
    Performance moyenne de chaque responsable = moyenne de la progression de ses
    activités assignées dans ce projet. Les responsables sans aucune activité
    assignée n'apparaissent pas (pas de performance artificielle à 0%).
    """
    return run_query("""
        SELECT U.id AS responsable_id, U.nom AS responsable,
               COUNT(A.id) AS nb_activites,
               AVG(A.progression) AS performance_moyenne,
               SUM(CASE WHEN A.statut = 'Terminé' THEN 1 ELSE 0 END) AS nb_terminees,
               SUM(CASE WHEN A.statut = 'En cours' THEN 1 ELSE 0 END) AS nb_en_cours,
               SUM(CASE WHEN A.date_fin < CURRENT_DATE AND A.statut != 'Terminé' THEN 1 ELSE 0 END) AS nb_en_retard,
               SUM(CASE WHEN A.date_debut > CURRENT_DATE THEN 1 ELSE 0 END) AS nb_a_venir
        FROM Utilisateurs U
        JOIN Activites A ON A.responsable_id = U.id
        JOIN Resultats R ON A.resultat_id = R.id
        JOIN Objectifs O ON R.objectif_id = O.id
        WHERE O.projet_id = %s
        GROUP BY U.id, U.nom
        ORDER BY performance_moyenne DESC
    """, params=(projet_id,))


@st.cache_data(ttl=15)
def get_taches_by_projet(projet_id):
    return run_query("""
        SELECT T.id, T.titre, T.description, T.priorite, T.statut, T.progression, T.date_debut, T.date_fin,
               T.responsable_id, U.nom AS responsable, T.activite_id, A.titre AS activite_titre
        FROM Taches T
        JOIN Activites A ON T.activite_id = A.id
        JOIN Resultats R ON A.resultat_id = R.id
        JOIN Objectifs O ON R.objectif_id = O.id
        LEFT JOIN Utilisateurs U ON T.responsable_id = U.id
        WHERE O.projet_id = %s
        ORDER BY A.titre, T.titre
    """, params=(projet_id,))


# ----------------------------------------------------------------------------
# Accès lecteurs (comptes en lecture seule limités à certains projets)
# ----------------------------------------------------------------------------
def get_lecteurs():
    """Liste des comptes utilisateurs ayant le rôle 'lecteur'."""
    return run_query("SELECT id, username FROM Users WHERE role = 'lecteur' AND actif = TRUE ORDER BY username")


def get_projets_accessibles(user_id):
    """Projets qu'un compte lecteur est autorisé à consulter."""
    return run_query("""
        SELECT P.id, P.nom, P.description, P.date_debut, P.date_fin, P.budget, P.statut,
               P.responsable_id, U.nom AS responsable,
               P.devise_principale, P.devise_secondaire, P.taux_conversion
        FROM Projets P
        JOIN Acces_Lecteurs AL ON P.id = AL.projet_id
        LEFT JOIN Utilisateurs U ON P.responsable_id = U.id
        WHERE AL.user_id = %s
        ORDER BY P.nom
    """, params=(user_id,))


def get_acces_lecteur(user_id):
    """IDs des projets déjà partagés avec ce lecteur."""
    df = run_query("SELECT projet_id FROM Acces_Lecteurs WHERE user_id = %s", params=(user_id,))
    return df["projet_id"].tolist() if not df.empty else []


def grant_acces_lecteur(user_id, projet_id):
    try:
        run_execute("INSERT INTO Acces_Lecteurs (user_id, projet_id) VALUES (%s, %s)", (user_id, projet_id))
    except psycopg2.errors.UniqueViolation:
        return  # Accès déjà accordé, pas de nouvelle notification

    projet = run_query("SELECT nom FROM Projets WHERE id = %s", params=(projet_id,))
    projet_nom = projet.iloc[0]["nom"] if not projet.empty else "un projet"
    ajoute_par = st.session_state.get("user", {}).get("username", "un administrateur")
    notifier_nouvelle_affectation(user_id, projet_id, projet_nom, ajoute_par)


def revoke_acces_lecteur(user_id, projet_id):
    run_execute("DELETE FROM Acces_Lecteurs WHERE user_id = %s AND projet_id = %s", (user_id, projet_id))


def update_resultat_valeur_actuelle(id, valeur_actuelle):
    run_execute("UPDATE Resultats SET valeur_actuelle=%s WHERE id=%s", (valeur_actuelle, id))
    get_resultats_by_projet.clear()


# ----------------------------------------------------------------------------
# Indicateurs supplémentaires (au-delà de l'indicateur principal d'un résultat)
# ----------------------------------------------------------------------------
def get_indicateurs_supplementaires(resultat_id):
    return run_query(
        "SELECT id, nom, valeur_cible, valeur_actuelle, unite, baseline, source_verification "
        "FROM Indicateurs_Supplementaires WHERE resultat_id = %s ORDER BY date_ajout",
        params=(resultat_id,),
    )


@st.cache_data(ttl=15)
def get_indicateurs_supplementaires_by_projet(projet_id):
    return run_query(
        """SELECT I.id, I.nom, I.valeur_cible, I.valeur_actuelle, I.unite, I.baseline, I.source_verification,
                  R.titre AS resultat_titre, O.titre AS objectif_titre, I.frequence_ventilation
           FROM Indicateurs_Supplementaires I
           JOIN Resultats R ON I.resultat_id = R.id
           JOIN Objectifs O ON R.objectif_id = O.id
           WHERE O.projet_id = %s
           ORDER BY R.titre, I.nom""",
        params=(projet_id,),
    )


# ----------------------------------------------------------------------------
# Export pour Power BI / analyse externe — tables relationnelles à plat,
# sur l'ensemble des projets (chaque table garde ses clés id/parent_id pour
# permettre de recréer les relations dans Power BI).
# ----------------------------------------------------------------------------
def export_projets():
    return run_query("""
        SELECT P.id AS projet_id, P.nom, P.description, P.date_debut, P.date_fin,
               P.budget, P.statut, U.nom AS responsable
        FROM Projets P
        LEFT JOIN Utilisateurs U ON P.responsable_id = U.id
        ORDER BY P.id
    """)


def export_objectifs():
    return run_query("""
        SELECT O.id AS objectif_id, O.projet_id, O.type_objectif, O.titre, U.nom AS responsable
        FROM Objectifs O
        LEFT JOIN Utilisateurs U ON O.responsable_id = U.id
        ORDER BY O.projet_id, O.id
    """)


def export_resultats():
    return run_query("""
        SELECT R.id AS resultat_id, O.projet_id, R.objectif_id, R.titre, R.indicateur,
               R.valeur_cible, R.valeur_actuelle, R.unite, R.statut, R.baseline, R.source_verification
        FROM Resultats R
        JOIN Objectifs O ON R.objectif_id = O.id
        ORDER BY O.projet_id, R.id
    """)


def export_activites():
    return run_query("""
        SELECT A.id AS activite_id, O.projet_id, A.resultat_id, A.titre, A.statut,
               A.date_debut, A.date_fin, A.budget, A.progression, U.nom AS responsable
        FROM Activites A
        JOIN Resultats R ON A.resultat_id = R.id
        JOIN Objectifs O ON R.objectif_id = O.id
        LEFT JOIN Utilisateurs U ON A.responsable_id = U.id
        ORDER BY O.projet_id, A.id
    """)


def export_taches():
    return run_query("""
        SELECT T.id AS tache_id, O.projet_id, T.activite_id, T.titre, T.priorite, T.statut,
               T.date_debut, T.date_fin, T.progression, U.nom AS responsable
        FROM Taches T
        JOIN Activites A ON T.activite_id = A.id
        JOIN Resultats R ON A.resultat_id = R.id
        JOIN Objectifs O ON R.objectif_id = O.id
        LEFT JOIN Utilisateurs U ON T.responsable_id = U.id
        ORDER BY O.projet_id, T.id
    """)


def export_indicateurs():
    return run_query("""
        SELECT I.id AS indicateur_id, O.projet_id, I.resultat_id, I.nom,
               I.valeur_cible, I.valeur_actuelle, I.unite, I.baseline, I.source_verification
        FROM Indicateurs_Supplementaires I
        JOIN Resultats R ON I.resultat_id = R.id
        JOIN Objectifs O ON R.objectif_id = O.id
        ORDER BY O.projet_id, I.id
    """)


def export_depenses():
    return run_query("""
        SELECT D.id AS depense_id, O.projet_id, D.activite_id, D.montant, D.date_depense, D.description
        FROM Depenses D
        JOIN Activites A ON D.activite_id = A.id
        JOIN Resultats R ON A.resultat_id = R.id
        JOIN Objectifs O ON R.objectif_id = O.id
        ORDER BY O.projet_id, D.id
    """)


def create_indicateur_supplementaire(resultat_id, nom, valeur_cible, valeur_actuelle, unite, baseline=None, source_verification=None):
    new_id = run_execute(
        "INSERT INTO Indicateurs_Supplementaires (resultat_id, nom, valeur_cible, valeur_actuelle, unite, baseline, source_verification) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (resultat_id, nom, valeur_cible, valeur_actuelle, unite, baseline, source_verification),
    )
    get_indicateurs_supplementaires_by_projet.clear()
    return new_id


def update_indicateur_supplementaire(id, nom, valeur_cible, valeur_actuelle, unite, baseline=None, source_verification=None):
    run_execute(
        "UPDATE Indicateurs_Supplementaires SET nom=%s, valeur_cible=%s, valeur_actuelle=%s, unite=%s, "
        "baseline=%s, source_verification=%s WHERE id=%s",
        (nom, valeur_cible, valeur_actuelle, unite, baseline, source_verification, id),
    )
    get_indicateurs_supplementaires_by_projet.clear()


def delete_indicateur_supplementaire(id):
    run_execute("DELETE FROM Indicateurs_Supplementaires WHERE id=%s", (id,))
    get_indicateurs_supplementaires_by_projet.clear()


# ----------------------------------------------------------------------------
# Budget hiérarchique — Rubriques → Sous-rubriques → Lignes budgétaires
# (budget prévisionnel détaillé, configurable librement par l'utilisateur)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def get_budget_lignes_by_projet(projet_id):
    """
    Toutes les lignes budgétaires d'un projet, à plat, avec le contexte complet
    (rubrique, sous-rubrique, activité éventuellement associée) et le coût total
    déjà calculé (quantité × coût unitaire) — jamais stocké, toujours recalculé.
    """
    return run_query("""
        SELECT L.id, L.description, L.unite, L.quantite, L.cout_unitaire,
               (L.quantite * L.cout_unitaire) AS cout_total,
               L.activite_id, A.titre AS activite_titre,
               SR.id AS sous_rubrique_id, SR.nom AS sous_rubrique_nom, SR.ordre AS sous_rubrique_ordre,
               R.id AS rubrique_id, R.nom AS rubrique_nom, R.ordre AS rubrique_ordre
        FROM Budget_Lignes L
        JOIN Budget_Sous_Rubriques SR ON L.sous_rubrique_id = SR.id
        JOIN Budget_Rubriques R ON SR.rubrique_id = R.id
        LEFT JOIN Activites A ON L.activite_id = A.id
        WHERE R.projet_id = %s
        ORDER BY R.ordre, R.nom, SR.ordre, SR.nom, L.ordre, L.description
    """, params=(projet_id,))


@st.cache_data(ttl=15)
def get_budget_rubriques(projet_id):
    return run_query(
        "SELECT id, nom, description, code_budgetaire, ordre FROM Budget_Rubriques "
        "WHERE projet_id = %s ORDER BY ordre, nom",
        params=(projet_id,),
    )


@st.cache_data(ttl=15)
def get_budget_sous_rubriques(rubrique_id):
    return run_query(
        "SELECT id, nom, ordre FROM Budget_Sous_Rubriques WHERE rubrique_id = %s ORDER BY ordre, nom",
        params=(rubrique_id,),
    )


def create_budget_rubrique(projet_id, nom, description, code_budgetaire):
    new_id = run_execute(
        "INSERT INTO Budget_Rubriques (projet_id, nom, description, code_budgetaire) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (projet_id, nom, description, code_budgetaire),
    )
    get_budget_rubriques.clear()
    return new_id


def update_budget_rubrique(id, nom, description, code_budgetaire):
    run_execute(
        "UPDATE Budget_Rubriques SET nom=%s, description=%s, code_budgetaire=%s WHERE id=%s",
        (nom, description, code_budgetaire, id),
    )
    get_budget_rubriques.clear()


def delete_budget_rubrique(id):
    sous_rubriques = run_query("SELECT id FROM Budget_Sous_Rubriques WHERE rubrique_id=%s", params=(id,))
    for sr_id in sous_rubriques["id"]:
        delete_budget_sous_rubrique(sr_id)
    run_execute("DELETE FROM Budget_Rubriques WHERE id=%s", (id,))
    get_budget_rubriques.clear()


def create_budget_sous_rubrique(rubrique_id, nom):
    new_id = run_execute(
        "INSERT INTO Budget_Sous_Rubriques (rubrique_id, nom) VALUES (%s, %s) RETURNING id",
        (rubrique_id, nom),
    )
    get_budget_sous_rubriques.clear()
    return new_id


def update_budget_sous_rubrique(id, nom):
    run_execute("UPDATE Budget_Sous_Rubriques SET nom=%s WHERE id=%s", (nom, id))
    get_budget_sous_rubriques.clear()


def delete_budget_sous_rubrique(id):
    run_execute("DELETE FROM Budget_Lignes WHERE sous_rubrique_id=%s", (id,))
    run_execute("DELETE FROM Budget_Sous_Rubriques WHERE id=%s", (id,))
    get_budget_sous_rubriques.clear()
    get_budget_lignes_by_projet.clear()


def create_budget_ligne(sous_rubrique_id, description, unite, quantite, cout_unitaire, activite_id=None):
    new_id = run_execute(
        "INSERT INTO Budget_Lignes (sous_rubrique_id, description, unite, quantite, cout_unitaire, activite_id) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (sous_rubrique_id, description, unite, quantite, cout_unitaire, activite_id),
    )
    get_budget_lignes_by_projet.clear()
    return new_id


def update_budget_ligne(id, description, unite, quantite, cout_unitaire, activite_id=None):
    run_execute(
        "UPDATE Budget_Lignes SET description=%s, unite=%s, quantite=%s, cout_unitaire=%s, activite_id=%s WHERE id=%s",
        (description, unite, quantite, cout_unitaire, activite_id, id),
    )
    get_budget_lignes_by_projet.clear()


def delete_budget_ligne(id):
    run_execute("DELETE FROM Budget_Lignes WHERE id=%s", (id,))
    get_budget_lignes_by_projet.clear()


UNITES_BUDGET = ["mois", "jour", "homme/jour", "unité", "forfait", "kg", "tonne", "mètre", "litre", "autre"]


# ----------------------------------------------------------------------------
# Module financier — dépenses réelles, écarts, taux d'exécution budgétaire
# ----------------------------------------------------------------------------
def get_depenses(activite_id):
    return run_query(
        "SELECT id, montant, date_depense, description FROM Depenses "
        "WHERE activite_id = %s ORDER BY date_depense DESC",
        params=(activite_id,),
    )


@st.cache_data(ttl=15)
def get_depenses_by_projet(projet_id):
    return run_query(
        """SELECT D.id, D.montant, D.date_depense, D.description,
                  A.id AS activite_id, A.titre AS activite_titre, A.budget AS budget_prevu
           FROM Depenses D
           JOIN Activites A ON D.activite_id = A.id
           JOIN Resultats R ON A.resultat_id = R.id
           JOIN Objectifs O ON R.objectif_id = O.id
           WHERE O.projet_id = %s
           ORDER BY A.titre, D.date_depense""",
        params=(projet_id,),
    )


def create_depense(activite_id, montant, date_depense, description):
    new_id = run_execute(
        "INSERT INTO Depenses (activite_id, montant, date_depense, description) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (activite_id, montant, date_depense, description),
    )
    get_depenses_by_projet.clear()
    return new_id


def delete_depense(id):
    run_execute("DELETE FROM Depenses WHERE id=%s", (id,))
    get_depenses_by_projet.clear()


# ----------------------------------------------------------------------------
# Rapports sauvegardés
# ----------------------------------------------------------------------------
def get_rapports(projet_id):
    return run_query(
        """SELECT R.id, R.titre, R.contenu, R.date_creation, U.username AS cree_par
           FROM Rapports R
           LEFT JOIN Users U ON R.cree_par = U.id
           WHERE R.projet_id = %s
           ORDER BY R.date_creation DESC""",
        params=(projet_id,),
    )


def create_rapport(projet_id, titre, contenu, cree_par):
    return run_execute(
        "INSERT INTO Rapports (projet_id, titre, contenu, cree_par) VALUES (%s, %s, %s, %s) RETURNING id",
        (projet_id, titre, contenu, cree_par),
    )


def delete_rapport(id):
    run_execute("DELETE FROM Rapports WHERE id=%s", (id,))


# ----------------------------------------------------------------------------
# Parties prenantes
# ----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def get_parties_prenantes(projet_id):
    return run_query(
        "SELECT id, nom, type_partie, role_contribution, contact FROM Parties_Prenantes "
        "WHERE projet_id = %s ORDER BY nom",
        params=(projet_id,),
    )


def create_partie_prenante(projet_id, nom, type_partie, role_contribution, contact):
    new_id = run_execute(
        "INSERT INTO Parties_Prenantes (projet_id, nom, type_partie, role_contribution, contact) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (projet_id, nom, type_partie, role_contribution, contact),
    )
    get_parties_prenantes.clear()
    return new_id


def update_partie_prenante(id, nom, type_partie, role_contribution, contact):
    run_execute(
        "UPDATE Parties_Prenantes SET nom=%s, type_partie=%s, role_contribution=%s, contact=%s WHERE id=%s",
        (nom, type_partie, role_contribution, contact, id),
    )
    get_parties_prenantes.clear()


def delete_partie_prenante(id):
    run_execute("DELETE FROM Parties_Prenantes WHERE id=%s", (id,))
    get_parties_prenantes.clear()


TYPES_PARTIE_PRENANTE = ["Bailleur", "Partenaire technique", "Bénéficiaire", "Communauté", "Autre"]


# ----------------------------------------------------------------------------
# Documents
# ----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def get_documents(projet_id):
    return run_query(
        "SELECT id, nom_fichier, chemin_fichier, type_document, description, date_ajout "
        "FROM Documents WHERE projet_id = %s ORDER BY date_ajout DESC",
        params=(projet_id,),
    )


def create_document(projet_id, nom_fichier, chemin_fichier, type_document, description):
    new_id = run_execute(
        "INSERT INTO Documents (projet_id, nom_fichier, chemin_fichier, type_document, description) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (projet_id, nom_fichier, chemin_fichier, type_document, description),
    )
    get_documents.clear()
    return new_id


def _delete_file_safely(chemin_fichier):
    """Supprime le fichier associé — dans Supabase Storage si configuré, sinon sur le
    disque local (ancien comportement, conservé en repli pour les documents créés
    avant la migration vers un stockage durable)."""
    if not chemin_fichier:
        return
    import storage_service
    if storage_service.is_configured():
        storage_service.delete_file(chemin_fichier)
    else:
        try:
            if os.path.exists(chemin_fichier):
                os.remove(chemin_fichier)
        except OSError:
            pass


def delete_document(id):
    row = run_query("SELECT chemin_fichier FROM Documents WHERE id=%s", params=(id,))
    if not row.empty:
        _delete_file_safely(row.iloc[0]["chemin_fichier"])
    run_execute("DELETE FROM Documents WHERE id=%s", (id,))
    get_documents.clear()


TYPES_DOCUMENT = ["Rapport", "Contrat", "Fiche projet", "Photo", "Autre"]


# ----------------------------------------------------------------------------
# Centre de notifications
# ----------------------------------------------------------------------------
def get_notifications(user_id, only_unread=False):
    query = "SELECT id, projet_id, activite_id, type, titre, message, date_creation, date_evenement, lu FROM Notifications WHERE user_id = %s"
    if only_unread:
        query += " AND lu = FALSE"
    query += " ORDER BY date_creation DESC"
    return run_query(query, params=(user_id,))


def count_unread_notifications(user_id):
    df = run_query("SELECT COUNT(*) AS n FROM Notifications WHERE user_id = %s AND lu = FALSE", params=(user_id,))
    return int(df.iloc[0]["n"]) if not df.empty else 0


def mark_notification_read(id):
    run_execute("UPDATE Notifications SET lu = TRUE WHERE id = %s", (id,))


def mark_all_notifications_read(user_id):
    run_execute("UPDATE Notifications SET lu = TRUE WHERE user_id = %s AND lu = FALSE", (user_id,))


def _notification_existe_deja(user_id, type_notif, activite_id=None, projet_id=None):
    """Anti-doublon : True si une notification identique existe déjà pour cet utilisateur."""
    df = run_query(
        "SELECT id FROM Notifications WHERE user_id=%s AND type=%s "
        "AND activite_id IS NOT DISTINCT FROM %s AND projet_id IS NOT DISTINCT FROM %s",
        params=(user_id, type_notif, activite_id, projet_id),
    )
    return not df.empty


def create_notification(user_id, type_notif, titre, message, projet_id=None, activite_id=None, date_evenement=None):
    if _notification_existe_deja(user_id, type_notif, activite_id, projet_id):
        return None
    return run_execute(
        "INSERT INTO Notifications (user_id, projet_id, activite_id, type, titre, message, date_evenement) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (user_id, projet_id, activite_id, type_notif, titre, message, date_evenement),
    )


def generer_notifications_activites_a_venir(delai_heures=24):
    """
    Parcourt toutes les activités dont la date de début approche, et notifie leur
    responsable — uniquement s'il a un compte de connexion associé (sinon, on ne
    peut matériellement pas le notifier). Anti-doublon intégré : une activité déjà
    notifiée pour ce délai n'est pas notifiée une seconde fois.
    """
    activites = run_query("""
        SELECT A.id AS activite_id, A.titre AS activite_titre, A.date_debut,
               O.projet_id, P.nom AS projet_nom, U.user_id
        FROM Activites A
        JOIN Resultats R ON A.resultat_id = R.id
        JOIN Objectifs O ON R.objectif_id = O.id
        JOIN Projets P ON O.projet_id = P.id
        JOIN Utilisateurs U ON A.responsable_id = U.id
        WHERE A.date_debut IS NOT NULL
          AND A.statut != 'Terminé'
          AND U.user_id IS NOT NULL
          AND A.date_debut BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '%s hours'
    """ % int(delai_heures))

    for _, act in activites.iterrows():
        create_notification(
            user_id=int(act["user_id"]),
            type_notif="activite_a_venir",
            titre="🔔 Activité à venir",
            message=f"L'activité « {act['activite_titre']} » (projet « {act['projet_nom']} ») doit bientôt commencer, le {act['date_debut']}.",
            projet_id=int(act["projet_id"]),
            activite_id=int(act["activite_id"]),
            date_evenement=act["date_debut"],
        )


def notifier_nouvelle_affectation(user_id, projet_id, projet_nom, ajoute_par_nom, role="lecteur"):
    create_notification(
        user_id=user_id,
        type_notif="nouvelle_affectation",
        titre="📁 Nouveau projet",
        message=f"Vous avez été ajouté au projet « {projet_nom} » par {ajoute_par_nom} (rôle : {role}).",
        projet_id=projet_id,
    )


# ----------------------------------------------------------------------------
# Ventilation temporelle des indicateurs
# ----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def get_periodes_resultat(resultat_id):
    return run_query(
        "SELECT id, periode_label, date_debut, date_fin, cible_periode, realise_periode "
        "FROM Indicateur_Periodes WHERE resultat_id = %s ORDER BY date_debut",
        params=(resultat_id,),
    )


@st.cache_data(ttl=15)
def get_periodes_indicateur_supplementaire(indicateur_id):
    return run_query(
        "SELECT id, periode_label, date_debut, date_fin, cible_periode, realise_periode "
        "FROM Indicateur_Periodes WHERE indicateur_supplementaire_id = %s ORDER BY date_debut",
        params=(indicateur_id,),
    )


def set_frequence_ventilation_resultat(resultat_id, frequence):
    run_execute("UPDATE Resultats SET frequence_ventilation=%s WHERE id=%s", (frequence, resultat_id))
    get_resultats_by_projet.clear()


def set_frequence_ventilation_indicateur_suppl(indicateur_id, frequence):
    run_execute("UPDATE Indicateurs_Supplementaires SET frequence_ventilation=%s WHERE id=%s", (frequence, indicateur_id))
    get_indicateurs_supplementaires_by_projet.clear()


def regenerer_periodes_resultat(resultat_id, periodes):
    """Remplace toutes les périodes existantes d'un résultat par la nouvelle liste
    générée — les réalisations déjà saisies sont perdues si on régénère, d'où la
    confirmation demandée côté interface avant d'appeler cette fonction."""
    run_execute("DELETE FROM Indicateur_Periodes WHERE resultat_id=%s", (resultat_id,))
    for p in periodes:
        run_execute(
            "INSERT INTO Indicateur_Periodes (resultat_id, periode_label, date_debut, date_fin, cible_periode) "
            "VALUES (%s, %s, %s, %s, %s)",
            (resultat_id, p["label"], p["date_debut"], p["date_fin"], p["cible_periode"]),
        )
    get_periodes_resultat.clear()


def regenerer_periodes_indicateur_suppl(indicateur_id, periodes):
    run_execute("DELETE FROM Indicateur_Periodes WHERE indicateur_supplementaire_id=%s", (indicateur_id,))
    for p in periodes:
        run_execute(
            "INSERT INTO Indicateur_Periodes (indicateur_supplementaire_id, periode_label, date_debut, date_fin, cible_periode) "
            "VALUES (%s, %s, %s, %s, %s)",
            (indicateur_id, p["label"], p["date_debut"], p["date_fin"], p["cible_periode"]),
        )
    get_periodes_indicateur_supplementaire.clear()


def update_periode(id, cible_periode, realise_periode, est_resultat=True):
    run_execute("UPDATE Indicateur_Periodes SET cible_periode=%s, realise_periode=%s WHERE id=%s", (cible_periode, realise_periode, id))
    if est_resultat:
        get_periodes_resultat.clear()
    else:
        get_periodes_indicateur_supplementaire.clear()


@st.cache_data(ttl=15)
def get_toutes_periodes_projet(projet_id):
    """Toutes les périodes de tous les indicateurs (résultats + suppl.) d'un
    projet, avec le nom de l'indicateur et l'objectif associé — utilisé pour le
    Dashboard et le rapport IA."""
    periodes_resultats = run_query("""
        SELECT IP.id, IP.periode_label, IP.date_debut, IP.date_fin, IP.cible_periode, IP.realise_periode,
               R.indicateur AS nom_indicateur, O.titre AS objectif_titre, CONCAT('R', IP.resultat_id) AS indicateur_key
        FROM Indicateur_Periodes IP
        JOIN Resultats R ON IP.resultat_id = R.id
        JOIN Objectifs O ON R.objectif_id = O.id
        WHERE O.projet_id = %s
    """, params=(projet_id,))
    periodes_suppl = run_query("""
        SELECT IP.id, IP.periode_label, IP.date_debut, IP.date_fin, IP.cible_periode, IP.realise_periode,
               I.nom AS nom_indicateur, O.titre AS objectif_titre, CONCAT('S', IP.indicateur_supplementaire_id) AS indicateur_key
        FROM Indicateur_Periodes IP
        JOIN Indicateurs_Supplementaires I ON IP.indicateur_supplementaire_id = I.id
        JOIN Resultats R ON I.resultat_id = R.id
        JOIN Objectifs O ON R.objectif_id = O.id
        WHERE O.projet_id = %s
    """, params=(projet_id,))
    import pandas as pd
    return pd.concat([periodes_resultats, periodes_suppl], ignore_index=True)


FREQUENCES_VENTILATION = ["aucune", "hebdomadaire", "mensuelle", "trimestrielle", "semestrielle", "annuelle"]


# ----------------------------------------------------------------------------
# Constantes pour les listes déroulantes
# ----------------------------------------------------------------------------
STATUTS_PROJET = ["Planifié", "En cours", "Terminé", "Suspendu"]
TYPES_OBJECTIF = ["Général", "Spécifique"]
STATUTS_GENERIQUE = ["À faire", "En cours", "Terminé", "Bloqué"]
PRIORITES_TACHE = ["Basse", "Moyenne", "Haute", "Urgente"]
