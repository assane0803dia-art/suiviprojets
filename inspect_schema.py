"""
Affiche la structure complète de la base (tables, colonnes, types, clés étrangères)
pour permettre de concevoir les formulaires de saisie correctement.

Lancez : python inspect_schema.py
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


def list_tables_and_columns(cursor):
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME NOT LIKE 'V_%'
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """)
    rows = cursor.fetchall()

    current_table = None
    for row in rows:
        table, column, dtype, nullable, max_len = row
        if table != current_table:
            print(f"\n📋 TABLE : {table}")
            print("-" * 60)
            current_table = table
        length_str = f"({max_len})" if max_len else ""
        null_str = "NULL" if nullable == "YES" else "NOT NULL"
        print(f"   {column:<30} {dtype}{length_str:<10} {null_str}")


def list_foreign_keys(cursor):
    cursor.execute("""
        SELECT
            fk.name AS fk_name,
            tp.name AS table_parent,
            cp.name AS column_parent,
            tr.name AS table_referenced,
            cr.name AS column_referenced
        FROM sys.foreign_keys fk
        INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
        INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id
        INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
        INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
        INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
    """)
    rows = cursor.fetchall()

    print("\n\n🔗 CLÉS ÉTRANGÈRES")
    print("-" * 60)
    if not rows:
        print("   Aucune clé étrangère trouvée.")
    for row in rows:
        fk_name, table_parent, column_parent, table_referenced, column_referenced = row
        print(f"   {table_parent}.{column_parent}  ->  {table_referenced}.{column_referenced}")


def show_view_definition(cursor):
    cursor.execute("""
        SELECT VIEW_DEFINITION
        FROM INFORMATION_SCHEMA.VIEWS
        WHERE TABLE_NAME = 'V_Dashboard_Projets'
    """)
    row = cursor.fetchone()
    print("\n\n👁️  DÉFINITION DE LA VUE V_Dashboard_Projets")
    print("-" * 60)
    if row:
        print(row[0])
    else:
        print("   Vue non trouvée.")


if __name__ == "__main__":
    conn = get_connection()
    cursor = conn.cursor()

    list_tables_and_columns(cursor)
    list_foreign_keys(cursor)
    show_view_definition(cursor)

    conn.close()
    print("\n\n✅ Copiez tout ce résultat et envoyez-le pour la suite.")
