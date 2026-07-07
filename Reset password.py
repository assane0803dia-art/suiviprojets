"""
Réinitialise le mot de passe d'un utilisateur existant (le mot de passe original
ne peut pas être récupéré, seulement remplacé par un nouveau).

Lancez : python reset_password.py
"""

import bcrypt
import pyodbc
import getpass

SERVER = "DESKTOP-HIVDVQT"
DATABASE = "ProjectMonitoringDB"


def get_connection():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
    )


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def user_exists(username: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Users WHERE username = ?", username)
    row = cursor.fetchone()
    conn.close()
    return row is not None


def reset_password(username: str, new_password: str):
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = hash_password(new_password)
    cursor.execute("UPDATE Users SET password_hash = ? WHERE username = ?", password_hash, username)
    conn.commit()
    conn.close()
    print(f"✅ Mot de passe réinitialisé pour '{username}'.")


if __name__ == "__main__":
    print("=== Réinitialisation de mot de passe ===")
    username = input("Nom d'utilisateur : ").strip()

    if not user_exists(username):
        print(f"❌ Aucun utilisateur trouvé avec le nom '{username}'.")
    else:
        new_password = getpass.getpass("Nouveau mot de passe : ")
        confirm = getpass.getpass("Confirmez le nouveau mot de passe : ")

        if new_password != confirm:
            print("❌ Les mots de passe ne correspondent pas.")
        elif len(new_password) < 6:
            print("❌ Le mot de passe doit contenir au moins 6 caractères.")
        else:
            reset_password(username, new_password)