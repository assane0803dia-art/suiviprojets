"""
Nettoie les données de démonstration/test insérées directement en SQL pendant le développement.

Supprime toutes les lignes de : Projets (+ Objectifs, Resultats, Activites, Taches en cascade).
NE TOUCHE PAS à : Utilisateurs (créés via l'app, probablement légitimes), Users (comptes de
connexion), Dashboard_Indicateurs (configuration du tableau de bord).

Lancez : python reset_demo_data.py
"""

import pyodbc

SERVER = "DESKTOP-HIVDVQT"
DATABASE = "ProjectMonitoringDB"


def get_connection():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
    )


def count_rows(cursor, table):
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    return cursor.fetchone()[0]


if __name__ == "__main__":
    conn = get_connection()
    cursor = conn.cursor()

    tables = ["Projets", "Objectifs", "Resultats", "Activites", "Taches"]

    print("📋 État actuel de la base :\n")
    for t in tables:
        print(f"  {t:<12} : {count_rows(cursor, t)} ligne(s)")

    print("\n⚠️  Cette action va supprimer DÉFINITIVEMENT toutes les lignes des tables ci-dessus.")
    print("    Les tables Utilisateurs, Users et Dashboard_Indicateurs ne seront PAS touchées.\n")

    confirm = input("Tapez SUPPRIMER (en majuscules) pour confirmer : ")

    if confirm != "SUPPRIMER":
        print("❌ Annulé — aucune donnée n'a été supprimée.")
    else:
        cursor.execute("DELETE FROM Taches")
        cursor.execute("DELETE FROM Activites")
        cursor.execute("DELETE FROM Resultats")
        cursor.execute("DELETE FROM Objectifs")
        cursor.execute("DELETE FROM Projets")
        conn.commit()
        print("\n✅ Toutes les données de projets ont été supprimées. Base propre.")

    conn.close()
