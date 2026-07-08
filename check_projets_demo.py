"""
Vérifie l'état de vos projets existants (nombre d'objectifs, résultats, activités, tâches)
pour savoir s'ils sont prêts à servir de démonstration.

Lancez : python check_projets_demo.py
"""

import psycopg2

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def load_secrets():
    with open(".streamlit/secrets.toml", "rb") as f:
        return tomllib.load(f)


def get_connection(secrets):
    return psycopg2.connect(
        host=secrets["DB_HOST"],
        port=secrets.get("DB_PORT", 5432),
        dbname=secrets["DB_DATABASE"],
        user=secrets["DB_USERNAME"],
        password=secrets["DB_PASSWORD"],
    )


if __name__ == "__main__":
    secrets = load_secrets()
    conn = get_connection(secrets)
    cursor = conn.cursor()

    cursor.execute("SELECT id, nom, statut FROM Projets ORDER BY id")
    projets = cursor.fetchall()

    if not projets:
        print("❌ Aucun projet trouvé dans la base.")
    else:
        print(f"📋 {len(projets)} projet(s) trouvé(s) :\n")
        for projet_id, nom, statut in projets:
            cursor.execute("SELECT COUNT(*) FROM Objectifs WHERE projet_id = %s", (projet_id,))
            nb_objectifs = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM Resultats R JOIN Objectifs O ON R.objectif_id = O.id WHERE O.projet_id = %s",
                (projet_id,),
            )
            nb_resultats = cursor.fetchone()[0]

            cursor.execute(
                """SELECT COUNT(*) FROM Activites A
                   JOIN Resultats R ON A.resultat_id = R.id
                   JOIN Objectifs O ON R.objectif_id = O.id
                   WHERE O.projet_id = %s""",
                (projet_id,),
            )
            nb_activites = cursor.fetchone()[0]

            cursor.execute(
                """SELECT COUNT(*) FROM Taches T
                   JOIN Activites A ON T.activite_id = A.id
                   JOIN Resultats R ON A.resultat_id = R.id
                   JOIN Objectifs O ON R.objectif_id = O.id
                   WHERE O.projet_id = %s""",
                (projet_id,),
            )
            nb_taches = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM Rapports WHERE projet_id = %s", (projet_id,))
            nb_rapports = cursor.fetchone()[0]

            print(f"  [{projet_id}] {nom} (statut : {statut})")
            print(f"      Objectifs : {nb_objectifs} | Résultats : {nb_resultats} | Activités : {nb_activites} | Tâches : {nb_taches} | Rapports sauvegardés : {nb_rapports}")

            pret = nb_objectifs > 0 and nb_resultats > 0 and nb_activites > 0 and nb_taches > 0
            if pret:
                print("      ✅ Assez complet pour servir de démo")
            else:
                manquant = []
                if nb_objectifs == 0: manquant.append("objectifs")
                if nb_resultats == 0: manquant.append("résultats")
                if nb_activites == 0: manquant.append("activités")
                if nb_taches == 0: manquant.append("tâches")
                print(f"      ⚠️ Incomplet — il manque : {', '.join(manquant)}")
            print()

    conn.close()