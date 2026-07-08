"""
Identifie précisément les trous dans la hiérarchie d'un projet :
- quels objectifs n'ont aucun résultat attendu
- quelles activités n'ont aucune tâche

Lancez : python check_projet_details.py
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

    cursor.execute("SELECT id, nom FROM Projets ORDER BY id")
    projets = cursor.fetchall()

    for projet_id, nom_projet in projets:
        print(f"\n📋 Projet : {nom_projet}\n")

        # Objectifs sans résultat
        cursor.execute("""
            SELECT O.id, O.titre, O.type_objectif
            FROM Objectifs O
            LEFT JOIN Resultats R ON R.objectif_id = O.id
            WHERE O.projet_id = %s AND R.id IS NULL
        """, (projet_id,))
        objectifs_sans_resultat = cursor.fetchall()

        if objectifs_sans_resultat:
            print("  ⚠️ Objectifs SANS résultat attendu :")
            for obj_id, titre, type_obj in objectifs_sans_resultat:
                print(f"      - [{type_obj}] {titre}")
        else:
            print("  ✅ Tous les objectifs ont au moins un résultat attendu.")

        # Activités sans tâche
        cursor.execute("""
            SELECT A.id, A.titre, R.titre
            FROM Activites A
            JOIN Resultats R ON A.resultat_id = R.id
            JOIN Objectifs O ON R.objectif_id = O.id
            LEFT JOIN Taches T ON T.activite_id = A.id
            WHERE O.projet_id = %s AND T.id IS NULL
        """, (projet_id,))
        activites_sans_tache = cursor.fetchall()

        if activites_sans_tache:
            print(f"\n  ⚠️ Activités SANS tâche ({len(activites_sans_tache)}) :")
            for act_id, titre_act, titre_res in activites_sans_tache:
                print(f"      - {titre_act} (résultat : {titre_res})")
        else:
            print("\n  ✅ Toutes les activités ont au moins une tâche.")

    conn.close()
    print("\n💡 Complétez les éléments manquants ci-dessus depuis '📂 Mes projets' dans l'application.")