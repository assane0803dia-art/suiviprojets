import psycopg2
import pandas as pd
import numpy as np
import os
import streamlit as st
from db import get_connection


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
    conn = get_connection()
    df = pd.read_sql(query, conn, params=_convert_params(params))
    conn.close()
    return df


def run_execute(query, params=None):
    """
    Exécute une requête. Si la requête est un INSERT se terminant par
    "RETURNING id", retourne cet identifiant (motif standard PostgreSQL).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        params = _convert_params(params)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        new_id = None
        if cursor.description:  # une clause RETURNING produit un résultat
            row = cursor.fetchone()
            if row:
                new_id = row[0]

        conn.commit()
        return new_id
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# Utilisateurs (responsables)
# ----------------------------------------------------------------------------
def get_utilisateurs():
    return run_query("SELECT id, nom, email, role FROM Utilisateurs ORDER BY nom")


def create_utilisateur(nom, email, role):
    try:
        return run_execute(
            "INSERT INTO Utilisateurs (nom, email, mot_de_passe, role, date_creation) "
            "VALUES (%s, %s, '', %s, NOW()) RETURNING id",
            (nom, email, role),
        )
    except psycopg2.errors.UniqueViolation:
        raise ValueError(f"Un responsable avec l'email '{email}' existe déjà.")


# ----------------------------------------------------------------------------
# Projets
# ----------------------------------------------------------------------------
def get_projets():
    return run_query("""
        SELECT P.id, P.nom, P.description, P.date_debut, P.date_fin, P.budget, P.statut,
               P.responsable_id, U.nom AS responsable
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
    return run_execute(
        "INSERT INTO Projets (nom, description, date_debut, date_fin, budget, statut, responsable_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (nom, description, date_debut, date_fin, budget, statut, responsable_id),
    )


def update_projet(id, nom, description, date_debut, date_fin, budget, statut, responsable_id):
    if projet_name_exists(nom, exclude_id=id):
        raise ValueError(f"Un projet nommé « {nom} » existe déjà. Choisissez un autre nom.")
    run_execute(
        "UPDATE Projets SET nom=%s, description=%s, date_debut=%s, date_fin=%s, budget=%s, statut=%s, responsable_id=%s "
        "WHERE id=%s",
        (nom, description, date_debut, date_fin, budget, statut, responsable_id, id),
    )


def delete_projet(id):
    objectifs = run_query("SELECT id FROM Objectifs WHERE projet_id=%s", params=(id,))
    for obj_id in objectifs["id"]:
        delete_objectif(obj_id)

    run_execute("DELETE FROM Parties_Prenantes WHERE projet_id=%s", (id,))

    documents = run_query("SELECT id, chemin_fichier FROM Documents WHERE projet_id=%s", params=(id,))
    for _, doc in documents.iterrows():
        _delete_file_safely(doc["chemin_fichier"])
    run_execute("DELETE FROM Documents WHERE projet_id=%s", (id,))

    run_execute("DELETE FROM Projets WHERE id=%s", (id,))


# ----------------------------------------------------------------------------
# Objectifs
# ----------------------------------------------------------------------------
def get_objectifs(projet_id):
    return run_query("""
        SELECT O.id, O.type_objectif, O.titre, O.responsable_id, U.nom AS responsable
        FROM Objectifs O
        LEFT JOIN Utilisateurs U ON O.responsable_id = U.id
        WHERE O.projet_id = %s
        ORDER BY O.type_objectif, O.titre
    """, params=(projet_id,))


def create_objectif(projet_id, type_objectif, titre, responsable_id):
    return run_execute(
        "INSERT INTO Objectifs (projet_id, type_objectif, titre, responsable_id) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (projet_id, type_objectif, titre, responsable_id),
    )


def update_objectif(id, type_objectif, titre, responsable_id):
    run_execute(
        "UPDATE Objectifs SET type_objectif=%s, titre=%s, responsable_id=%s WHERE id=%s",
        (type_objectif, titre, responsable_id, id),
    )


def delete_objectif(id):
    resultats = run_query("SELECT id FROM Resultats WHERE objectif_id=%s", params=(id,))
    for res_id in resultats["id"]:
        delete_resultat(res_id)
    run_execute("DELETE FROM Objectifs WHERE id=%s", (id,))


# ----------------------------------------------------------------------------
# Resultats
# ----------------------------------------------------------------------------
def get_resultats(objectif_id):
    return run_query("""
        SELECT id, titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut
        FROM Resultats
        WHERE objectif_id = %s
        ORDER BY titre
    """, params=(objectif_id,))


def create_resultat(objectif_id, titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut):
    return run_execute(
        "INSERT INTO Resultats (objectif_id, titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (objectif_id, titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut),
    )


def update_resultat(id, titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut):
    run_execute(
        "UPDATE Resultats SET titre=%s, description=%s, indicateur=%s, valeur_cible=%s, valeur_actuelle=%s, unite=%s, statut=%s "
        "WHERE id=%s",
        (titre, description, indicateur, valeur_cible, valeur_actuelle, unite, statut, id),
    )


def delete_resultat(id):
    activites = run_query("SELECT id FROM Activites WHERE resultat_id=%s", params=(id,))
    for act_id in activites["id"]:
        delete_activite(act_id)
    run_execute("DELETE FROM Resultats WHERE id=%s", (id,))


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


def create_activite(resultat_id, titre, description, responsable_id, date_debut, date_fin, statut, budget, progression):
    return run_execute(
        "INSERT INTO Activites (resultat_id, titre, description, responsable_id, date_debut, date_fin, statut, budget, progression) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (resultat_id, titre, description, responsable_id, date_debut, date_fin, statut, budget, progression),
    )


def update_activite(id, titre, description, responsable_id, date_debut, date_fin, statut, budget, progression):
    run_execute(
        "UPDATE Activites SET titre=%s, description=%s, responsable_id=%s, date_debut=%s, date_fin=%s, statut=%s, budget=%s, progression=%s "
        "WHERE id=%s",
        (titre, description, responsable_id, date_debut, date_fin, statut, budget, progression, id),
    )


def delete_activite(id):
    run_execute("DELETE FROM Taches WHERE activite_id=%s", (id,))
    run_execute("DELETE FROM Activites WHERE id=%s", (id,))


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
    return run_execute(
        "INSERT INTO Taches (activite_id, titre, description, responsable_id, priorite, statut, date_debut, date_fin, progression) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (activite_id, titre, description, responsable_id, priorite, statut, date_debut, date_fin, progression),
    )


def update_tache(id, titre, description, responsable_id, priorite, statut, date_debut, date_fin, progression):
    run_execute(
        "UPDATE Taches SET titre=%s, description=%s, responsable_id=%s, priorite=%s, statut=%s, date_debut=%s, date_fin=%s, progression=%s "
        "WHERE id=%s",
        (titre, description, responsable_id, priorite, statut, date_debut, date_fin, progression, id),
    )


def delete_tache(id):
    run_execute("DELETE FROM Taches WHERE id=%s", (id,))


# ----------------------------------------------------------------------------
# Vues "à plat" — tous les éléments d'un projet, indépendamment de leur parent
# (nécessaires pour un accès direct par section, sans ordre imposé)
# ----------------------------------------------------------------------------
def get_resultats_by_projet(projet_id):
    return run_query("""
        SELECT R.id, R.titre, R.description, R.indicateur, R.valeur_cible, R.valeur_actuelle, R.unite, R.statut,
               R.objectif_id, O.titre AS objectif_titre
        FROM Resultats R
        JOIN Objectifs O ON R.objectif_id = O.id
        WHERE O.projet_id = %s
        ORDER BY O.titre, R.titre
    """, params=(projet_id,))


def get_activites_by_projet(projet_id):
    return run_query("""
        SELECT A.id, A.titre, A.description, A.statut, A.budget, A.progression, A.date_debut, A.date_fin,
               A.responsable_id, U.nom AS responsable, A.resultat_id, R.titre AS resultat_titre
        FROM Activites A
        JOIN Resultats R ON A.resultat_id = R.id
        JOIN Objectifs O ON R.objectif_id = O.id
        LEFT JOIN Utilisateurs U ON A.responsable_id = U.id
        WHERE O.projet_id = %s
        ORDER BY R.titre, A.titre
    """, params=(projet_id,))


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
               P.responsable_id, U.nom AS responsable
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
        pass  # Accès déjà accordé


def revoke_acces_lecteur(user_id, projet_id):
    run_execute("DELETE FROM Acces_Lecteurs WHERE user_id = %s AND projet_id = %s", (user_id, projet_id))


def update_resultat_valeur_actuelle(id, valeur_actuelle):
    run_execute("UPDATE Resultats SET valeur_actuelle=%s WHERE id=%s", (valeur_actuelle, id))


# ----------------------------------------------------------------------------
# Parties prenantes
# ----------------------------------------------------------------------------
def get_parties_prenantes(projet_id):
    return run_query(
        "SELECT id, nom, type_partie, role_contribution, contact FROM Parties_Prenantes "
        "WHERE projet_id = %s ORDER BY nom",
        params=(projet_id,),
    )


def create_partie_prenante(projet_id, nom, type_partie, role_contribution, contact):
    return run_execute(
        "INSERT INTO Parties_Prenantes (projet_id, nom, type_partie, role_contribution, contact) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (projet_id, nom, type_partie, role_contribution, contact),
    )


def update_partie_prenante(id, nom, type_partie, role_contribution, contact):
    run_execute(
        "UPDATE Parties_Prenantes SET nom=%s, type_partie=%s, role_contribution=%s, contact=%s WHERE id=%s",
        (nom, type_partie, role_contribution, contact, id),
    )


def delete_partie_prenante(id):
    run_execute("DELETE FROM Parties_Prenantes WHERE id=%s", (id,))


TYPES_PARTIE_PRENANTE = ["Bailleur", "Partenaire technique", "Bénéficiaire", "Communauté", "Autre"]


# ----------------------------------------------------------------------------
# Documents
# ----------------------------------------------------------------------------
def get_documents(projet_id):
    return run_query(
        "SELECT id, nom_fichier, chemin_fichier, type_document, description, date_ajout "
        "FROM Documents WHERE projet_id = %s ORDER BY date_ajout DESC",
        params=(projet_id,),
    )


def create_document(projet_id, nom_fichier, chemin_fichier, type_document, description):
    return run_execute(
        "INSERT INTO Documents (projet_id, nom_fichier, chemin_fichier, type_document, description) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (projet_id, nom_fichier, chemin_fichier, type_document, description),
    )


def _delete_file_safely(chemin_fichier):
    try:
        if chemin_fichier and os.path.exists(chemin_fichier):
            os.remove(chemin_fichier)
    except OSError:
        pass  # Le fichier reste orphelin sur le disque, mais on n'interrompt pas la suppression en base


def delete_document(id):
    row = run_query("SELECT chemin_fichier FROM Documents WHERE id=%s", params=(id,))
    if not row.empty:
        _delete_file_safely(row.iloc[0]["chemin_fichier"])
    run_execute("DELETE FROM Documents WHERE id=%s", (id,))


TYPES_DOCUMENT = ["Rapport", "Contrat", "Fiche projet", "Photo", "Autre"]


# ----------------------------------------------------------------------------
# Constantes pour les listes déroulantes
# ----------------------------------------------------------------------------
STATUTS_PROJET = ["Planifié", "En cours", "Terminé", "Suspendu"]
TYPES_OBJECTIF = ["Général", "Spécifique"]
STATUTS_GENERIQUE = ["À faire", "En cours", "Terminé", "Bloqué"]
PRIORITES_TACHE = ["Basse", "Moyenne", "Haute", "Urgente"]
