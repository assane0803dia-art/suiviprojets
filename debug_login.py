"""
Script de diagnostic pour comprendre pourquoi la connexion échoue.
Lancez : python debug_login.py
"""

import pyodbc
import bcrypt
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


def list_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, actif, LEN(password_hash) AS hash_len FROM Users")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("❌ Aucun utilisateur trouvé dans la table Users.")
        print("   -> Avez-vous bien lancé generate_password.py avec succès ?")
        return

    print(f"✅ {len(rows)} utilisateur(s) trouvé(s) dans la table Users :\n")
    for row in rows:
        user_id, username, role, actif, hash_len = row
        print(f"  id={user_id} | username='{username}' | role={role} | actif={actif} | longueur_hash={hash_len}")


def test_login():
    print("\n=== Test de connexion ===")
    username = input("Nom d'utilisateur à tester : ")
    password = getpass.getpass("Mot de passe à tester : ")

    print(f"\n-> Nom d'utilisateur saisi : '{username}' (longueur={len(username)})")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, password_hash, role, actif FROM Users WHERE username = ?",
        username,
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        print("❌ Aucun utilisateur trouvé avec ce nom exact dans la base.")
        print("   Vérifiez les espaces avant/après, la casse (majuscules/minuscules).")
        return

    user_id, db_username, password_hash, role, actif = row
    print(f"✅ Utilisateur trouvé : id={user_id}, username='{db_username}', actif={actif}")

    if actif != 1:
        print("❌ Ce compte est marqué comme inactif (actif=0).")
        return

    if not password_hash or not password_hash.startswith("$2"):
        print(f"❌ Le hash stocké ne ressemble pas à un hash bcrypt valide : {password_hash[:10]}...")
        return

    match = bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    if match:
        print("✅ Le mot de passe correspond ! La connexion devrait fonctionner.")
    else:
        print("❌ Le mot de passe ne correspond PAS au hash stocké.")
        print("   -> Le mot de passe saisi ici est différent de celui utilisé lors de la création.")


if __name__ == "__main__":
    list_users()
    test_login()
