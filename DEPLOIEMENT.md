# Guide de déploiement — SuiviProjets (avec Supabase, sans carte bancaire)

Ce guide couvre les étapes pour passer de "l'app tourne sur mon PC" à
"l'app est en ligne, accessible de partout", **sans avoir besoin d'aucune
carte bancaire** — via Supabase (PostgreSQL gratuit) + Streamlit Community Cloud.

---

## Étape 1 — Créer le projet Supabase

1. Allez sur https://supabase.com et cliquez sur **"Start your project"**.
2. Inscrivez-vous (avec GitHub, c'est le plus rapide — aucune carte demandée).
3. Cliquez sur **"New project"** :
   - **Name** : `suiviprojets`
   - **Database Password** : choisissez un mot de passe fort — **notez-le
     précieusement**, vous ne pourrez plus le revoir ensuite
   - **Region** : choisissez la plus proche (ex. `Europe West`)
   - Plan : **Free** (déjà sélectionné par défaut)
4. Cliquez sur **"Create new project"**. La création prend 1 à 2 minutes.

### Récupérer les informations de connexion

5. Une fois le projet créé, allez dans **Project Settings** (icône ⚙️ dans
   le menu de gauche) → **Database**.
6. Notez les informations sous **"Connection parameters"** :
   - **Host** : quelque chose comme `db.xxxxxxxxxxxx.supabase.co`
   - **Port** : `5432`
   - **Database name** : `postgres`
   - **User** : `postgres`
   - **Password** : celui choisi à l'étape 3

---

## Étape 2 — Créer les tables dans Supabase

1. Dans le tableau de bord Supabase, allez dans **SQL Editor** (menu de
   gauche) → **New query**.
2. Ouvrez le fichier `schema_postgresql.sql` fourni, copiez tout son
   contenu, collez-le dans l'éditeur.
3. Cliquez sur **Run** (ou Ctrl+Entrée). Toutes vos tables, la vue
   `V_Dashboard_Projets`, et la configuration par défaut du tableau de bord
   sont créées en une seule fois.
4. Vérifiez dans **Table Editor** (menu de gauche) que toutes les tables
   apparaissent bien : `Projets`, `Objectifs`, `Resultats`, `Activites`,
   `Taches`, `Users`, `Utilisateurs`, `Dashboard_Indicateurs`,
   `Parties_Prenantes`, `Documents`, `Acces_Lecteurs`.

⚠️ Ce script crée une base **vide** (structure uniquement, pas vos données
actuelles). Si vous voulez transférer vos projets existants, dites-le-moi —
je peux préparer un script d'export/import de vos données locales vers
Supabase.

---

## Étape 3 — Créer votre compte admin dans Supabase

Vos anciens scripts (`generate_password.py`) sont écrits pour SQL Server.
Utilisez plutôt ce script adapté à Supabase :

```powershell
pip install psycopg2-binary bcrypt
python generate_password_supabase.py
```

(fourni ci-dessous — demandez-le-moi si vous ne l'avez pas encore).

---

## Étape 4 — Adapter et tester le code en local

1. Installez les nouvelles dépendances :
   ```powershell
   pip install psycopg2-binary
   ```
   Vous pouvez maintenant **désinstaller** `pyodbc` et `pymssql` si vous les
   aviez installés précédemment (plus utilisés) :
   ```powershell
   pip uninstall pyodbc pymssql
   ```
2. Créez `.streamlit/secrets.toml` (copiez `secrets.toml.example`) et
   remplissez avec les informations Supabase notées à l'étape 1 :
   ```toml
   DB_HOST     = "db.xxxxxxxxxxxx.supabase.co"
   DB_PORT     = 5432
   DB_DATABASE = "postgres"
   DB_USERNAME = "postgres"
   DB_PASSWORD = "votre_mot_de_passe"
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
3. Lancez `streamlit run app.py` **en local** — l'app se connecte maintenant
   à Supabase. Testez login, dashboard, création de projet, etc. avant de
   déployer.

---

## Étape 5 — Pousser sur GitHub

1. Si ce n'est pas déjà fait : https://git-scm.com/downloads
2. Dans le dossier du projet :
   ```powershell
   git init
   git add .
   git commit -m "Version initiale de SuiviProjets"
   ```
3. Créez un dépôt sur https://github.com/new (en **privé** de préférence).
4. Reliez et poussez :
   ```powershell
   git remote add origin https://github.com/votre-compte/suiviprojets.git
   git branch -M main
   git push -u origin main
   ```

Le `.gitignore` fourni exclut déjà `secrets.toml` — vos identifiants ne
partent jamais sur GitHub.

---

## Étape 6 — Déployer sur Streamlit Community Cloud

1. Allez sur https://share.streamlit.io, connectez-vous avec GitHub.
2. **"New app"** → sélectionnez le dépôt `suiviprojets`, branche `main`,
   fichier principal `app.py`.
3. **Avant** de cliquer sur Deploy : **"Advanced settings"** → **Secrets** →
   collez le contenu de votre `secrets.toml` local.
4. **Deploy**. Le premier déploiement prend 2-3 minutes.

Vous obtenez une URL du type `https://suiviprojets.streamlit.app`,
accessible de partout, sans qu'aucune carte bancaire n'ait été nécessaire
à aucune étape.

---

## Et après ? Comment continuer à modifier l'app

```powershell
git add .
git commit -m "Description du changement"
git push
```

Streamlit Cloud redéploie automatiquement après chaque `git push` sur `main`.

---

## Limite à connaître : la pause automatique

Les projets Supabase gratuits se **mettent en pause après 7 jours
d'inactivité** (aucune requête reçue). Ce n'est pas grave : il suffit de se
reconnecter au tableau de bord Supabase et de cliquer sur "Restore" pour la
réactiver (30 secondes). Si votre app est utilisée régulièrement, ça
n'arrivera jamais. Si vous voulez éviter ça complètement, on peut mettre en
place un petit ping automatique gratuit (GitHub Actions) qui garde le
projet actif — dites-le-moi si ça vous intéresse.

---

## Récapitulatif des fichiers concernés par cette migration

| Fichier | Rôle |
|---|---|
| `db.py` | Connexion centralisée via psycopg2 (nouveau) |
| `schema_postgresql.sql` | Création des tables sur Supabase (nouveau) |
| `crud.py`, `auth.py`, `indicators_config.py` | Migrés vers PostgreSQL |
| `requirements.txt` | psycopg2-binary au lieu de pymssql/pyodbc |
| `.gitignore` | Exclut les secrets et fichiers temporaires |
| `.streamlit/secrets.toml.example` | Modèle Supabase à remplir localement |

Les scripts utilitaires locaux (`reset_password.py`, `reset_demo_data.py`,
`debug_login.py`, `inspect_schema.py`, `generate_password.py`) utilisent
encore `pyodbc` + SQL Server local. Dites-moi si vous voulez que je les
adapte aussi à Supabase/psycopg2.
