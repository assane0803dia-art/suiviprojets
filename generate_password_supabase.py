"""
Crée un utilisateur (compte de connexion) directement dans Supabase.
Lancez ce script en ligne de commande (jamais dans l'app Streamlit) :

    python generate_password_supabase.py

Nécessite un fichier .streamlit/secrets.toml déjà rempli avec vos
informations Supabase (DB_HOST, DB_PORT, DB_DATABASE, DB_USERNAME, DB_PASSWORD).
"""

import bcrypt
import psycopg2
import getpass

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # pip install tomli (Python < 3.11)


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


def create_user(secrets, username: str, plain_password: str, role: str = "utilisateur"):
    conn = get_connection(secrets)
    cursor = conn.cursor()
    password_hash = hash_password(plain_password)
    cursor.execute(
        "INSERT INTO Users (username, password_hash, role) VALUES (%s, %s, %s)",
        (username, password_hash, role),
    )
    conn.commit()
    conn.close()
    print(f"✅ Utilisateur '{username}' créé avec le rôle '{role}'.")


if __name__ == "__main__":
    secrets = load_secrets()

    print("=== Création d'un utilisateur (Supabase) ===")
    username = input("Nom d'utilisateur : ").strip()
    password = getpass.getpass("Mot de passe : ")
    password_confirm = getpass.getpass("Confirmez le mot de passe : ")

    if password != password_confirm:
        print("❌ Les mots de passe ne correspondent pas.")
    elif len(password) < 6:
        print("❌ Le mot de passe doit contenir au moins 6 caractères.")
    else:
        role = input("Rôle (admin / utilisateur / lecteur) [utilisateur] : ").strip() or "utilisateur"
        create_user(secrets, username, password, role)
