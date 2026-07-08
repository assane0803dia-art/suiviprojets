"""
Crée trois comptes de démonstration (admin, utilisateur, lecteur) en une seule fois,
avec des identifiants simples à partager avec vos profs et camarades.

Nécessite un fichier .streamlit/secrets.toml déjà rempli (DB_HOST, DB_PORT, DB_DATABASE,
DB_USERNAME, DB_PASSWORD).

Lancez : python create_demo_accounts.py
"""

import bcrypt
import psycopg2

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # pip install tomli (Python < 3.11)


DEMO_PASSWORD = "Demo@2026"  # même mot de passe pour les 3 comptes, simple à partager

COMPTES_DEMO = [
    {"username": "demo.admin", "role": "admin"},
    {"username": "demo.utilisateur", "role": "utilisateur"},
    {"username": "demo.lecteur", "role": "lecteur"},
]


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


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def user_exists(cursor, username):
    cursor.execute("SELECT id FROM Users WHERE username = %s", (username,))
    return cursor.fetchone() is not None


def create_or_update_demo_account(cursor, username, role, password_hash):
    if user_exists(cursor, username):
        cursor.execute(
            "UPDATE Users SET password_hash = %s, role = %s, actif = TRUE WHERE username = %s",
            (password_hash, role, username),
        )
        return "mis à jour"
    else:
        cursor.execute(
            "INSERT INTO Users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, password_hash, role),
        )
        return "créé"


if __name__ == "__main__":
    secrets = load_secrets()
    conn = get_connection(secrets)
    cursor = conn.cursor()

    password_hash = hash_password(DEMO_PASSWORD)

    print("=== Création des comptes de démonstration ===\n")
    for compte in COMPTES_DEMO:
        statut = create_or_update_demo_account(cursor, compte["username"], compte["role"], password_hash)
        print(f"  ✅ {compte['username']:<20} (rôle : {compte['role']:<12}) — {statut}")

    conn.commit()
    conn.close()

    print("\n=== Identifiants à partager ===")
    print(f"Mot de passe commun aux 3 comptes : {DEMO_PASSWORD}\n")
    for compte in COMPTES_DEMO:
        print(f"  {compte['role']:<12} → utilisateur : {compte['username']}")

    print(
        "\n💡 Pensez à ensuite partager un projet de démonstration avec 'demo.lecteur' "
        "depuis Paramètres → Accès en lecture seule (dans l'app, connecté en admin)."
    )