# 📊 SuiviProjets

**Application web de suivi et gestion de projets, avec génération de rapports assistée par IA.**

Conçue pour les chefs de projet, gestionnaires et organisations (ONG, structures de développement local) ayant besoin de suivre des projets selon une logique de cadre logique : objectifs → résultats attendus → activités → tâches, avec indicateurs mesurables à chaque niveau.

---

## ✨ Fonctionnalités

- **Hiérarchie de suivi complète** : objectifs généraux/spécifiques, résultats attendus (avec indicateurs cible/actuel), activités, tâches — chaque niveau gérable indépendamment, sans ordre de saisie imposé
- **Tableau de bord dynamique** : indicateurs clés et graphiques configurables par l'équipe (Paramètres → Tableau de bord)
- **Génération de rapports par IA** (Claude, Anthropic) : rapport d'exécution complet (résumé, contexte, problématique, objectifs, résultats, activités, indicateurs, risques, budget, calendrier, conclusion, recommandations), éditable avant sauvegarde, exportable en **Word** et **PDF**
- **Assistance IA au remplissage** : amélioration/réécriture/résumé/développement de texte en un clic, suggestions automatiques de résultats/activités/tâches à partir du contexte du projet
- **Détection automatique de risques** : retards d'activités/tâches identifiés en temps réel (calcul déterministe, sans appel IA), avec recommandations générées à la demande
- **Gestion des rôles** : administrateur, utilisateur, et lecteur (accès en lecture seule limité à des projets spécifiques — utile pour partager avec des parties prenantes externes)
- **Parties prenantes & documents** : suivi des contacts liés à un projet, dépôt de fichiers (rapports, contrats...)
- **Astuces contextuelles** : conseils méthodologiques (objectifs SMART, indicateurs mesurables...) affichés dans chaque section

## 🏗️ Stack technique

| Composant | Choix | Pourquoi |
|---|---|---|
| Interface | [Streamlit](https://streamlit.io) | Développement rapide d'applications de données en Python pur |
| Base de données | PostgreSQL ([Supabase](https://supabase.com)) | Hébergement géré, gratuit, sans carte bancaire requise |
| Driver DB | `psycopg2` + pool de connexions | Réutilisation des connexions pour de meilleures performances |
| IA | API Anthropic (Claude Sonnet 5 / Haiku 4.5) | Génération de rapports et suggestions contextuelles |
| Export documents | `python-docx`, `reportlab` | Génération de fichiers Word et PDF |
| Authentification | `bcrypt` | Hachage des mots de passe (jamais stockés en clair) |
| Déploiement | Streamlit Community Cloud + GitHub | CI/CD automatique à chaque `git push` |

## 🗂️ Architecture du code

```
app.py                      # Routeur de navigation (st.navigation)
vue_dashboard.py            # Page d'accueil : tableau de bord
db.py                       # Pool de connexions PostgreSQL centralisé
crud.py                     # Toutes les opérations base de données (projets → tâches)
auth.py                     # Authentification, profils, sécurité
ai_report_generator.py      # Génération de rapports d'exécution par IA
ai_text_assist.py           # Réécriture de texte + suggestions par IA
report_export.py            # Export Word/PDF
ui_style.py                  # Composants d'interface réutilisables (cartes, badges, astuces)
validators.py                 # Règles de validation (cohérence des dates)
indicators_config.py        # Configuration des indicateurs du tableau de bord
pages/
├── 1_📁_Nouveau_Projet.py   # Création rapide d'un projet
├── 2_📂_Mes_Projets.py      # Espace de gestion (cartes indépendantes par section)
├── 3_📊_Rapports.py         # Génération et export de rapports IA
├── 4_🤖_IA.py               # Détection de risques + recommandations
└── 5_⚙️_Parametres.py       # Compte, préférences, sécurité, administration
```

**Choix d'architecture notables :**
- Navigation par cartes indépendantes plutôt qu'un assistant séquentiel — un chef de projet réel ne remplit pas ses données dans un ordre linéaire imposé
- Détection de retards calculée en Python (dates), pas déléguée à l'IA — plus fiable, gratuit, instantané
- Pool de connexions partagé (`st.cache_resource`) — évite une reconnexion réseau à chaque requête

## 🚀 Déploiement

Voir [`DEPLOIEMENT.md`](DEPLOIEMENT.md) pour le guide complet (Supabase + Streamlit Community Cloud, sans carte bancaire requise).

## 🔑 Comptes de démonstration

| Rôle | Identifiant | Accès |
|---|---|---|
| Administrateur | `demo.admin` | Complet (configuration, tous les projets) |
| Utilisateur | `demo.utilisateur` | Création/modification de projets |
| Lecteur | `demo.lecteur` | Consultation seule, projets partagés uniquement |

*(mot de passe communiqué séparément)*

## 🔮 Pistes d'évolution

- Remplissage assisté par IA étendu à davantage de champs (activités, tâches)
- Gestion multi-organisations (pour servir plusieurs structures indépendantes depuis une seule instance)
- Notifications par email (l'infrastructure de préférences existe déjà, l'envoi reste à connecter)
- Parties prenantes et documents avec permissions plus fines

## 📄 Licence

Projet académique — usage et démonstration. Contactez l'auteur pour toute réutilisation.

---

*Développé par Assane Dia dans le cadre d'un projet de formation, avec l'assistance de Claude (Anthropic) pour le développement.*
