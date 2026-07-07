"""
Utilitaire pour créer un utilisateur avec mot de passe hashé.
Lancez ce script en ligne de commande (jamais dans l'app Streamlit) :

    python generate_password.py

Il vous demandera un nom d'utilisateur et un mot de passe, générera le hash,
et l'insérera directement dans la table Users de la base de données.
"""

import bcrypt
import pyodbc
import getpass

SERVER = "DESKTOP-HIVDVQT"
DATABASE = "ProjectMonitoringDB"


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_user(username: str, plain_password: str, role: str = "utilisateur"):
    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
    )
    cursor = conn.cursor()

    password_hash = hash_password(plain_password)

    cursor.execute(
        "INSERT INTO Users (username, password_hash, role) VALUES (?, ?, ?)",
        username, password_hash, role,
    )
    conn.commit()
    conn.close()
    print(f"✅ Utilisateur '{username}' créé avec le rôle '{role}'.")


if __name__ == "__main__":
    print("=== Création d'un utilisateur ===")
    username = input("Nom d'utilisateur : ").strip()
    password = getpass.getpass("Mot de passe : ")
    password_confirm = getpass.getpass("Confirmez le mot de passe : ")

    if password != password_confirm:
        print("❌ Les mots de passe ne correspondent pas.")
    elif len(password) < 6:
        print("❌ Le mot de passe doit contenir au moins 6 caractères.")
    else:
        role = input("Rôle (admin / utilisateur) [utilisateur] : ").strip() or "utilisateur"
        create_user(username, password, role)
