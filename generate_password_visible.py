"""
Version de secours de generate_password.py, avec mot de passe VISIBLE à l'écran.
À utiliser uniquement si getpass ne fonctionne pas dans votre terminal.
Attention : le mot de passe s'affichera en clair pendant que vous le tapez.

Lancez : python generate_password_visible.py
"""

import bcrypt
import pyodbc

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
    print("=== Création d'un utilisateur (mot de passe visible) ===")
    username = input("Nom d'utilisateur : ").strip()
    password = input("Mot de passe (sera visible) : ").strip()

    if len(password) < 6:
        print("❌ Le mot de passe doit contenir au moins 6 caractères.")
    else:
        role = input("Rôle (admin / utilisateur) [utilisateur] : ").strip() or "utilisateur"
        create_user(username, password, role)
