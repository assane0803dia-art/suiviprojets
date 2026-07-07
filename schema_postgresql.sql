-- Schéma complet pour Supabase (PostgreSQL) — à exécuter dans l'éditeur SQL de Supabase
-- (Dashboard Supabase > SQL Editor > New query > coller > Run)

CREATE TABLE Utilisateurs (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    mot_de_passe VARCHAR(255) NOT NULL,
    role VARCHAR(50),
    date_creation TIMESTAMP DEFAULT NOW()
);

CREATE TABLE Users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'utilisateur',
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE Projets (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(200),
    description TEXT,
    date_debut DATE,
    date_fin DATE,
    budget DECIMAL(15,2),
    statut VARCHAR(50),
    responsable_id INT REFERENCES Utilisateurs(id)
);

CREATE TABLE Objectifs (
    id SERIAL PRIMARY KEY,
    projet_id INT NOT NULL REFERENCES Projets(id),
    type_objectif VARCHAR(30) NOT NULL,
    titre VARCHAR(255) NOT NULL,
    description TEXT,
    responsable_id INT REFERENCES Utilisateurs(id),
    date_debut DATE,
    date_fin DATE,
    statut VARCHAR(30)
);

CREATE TABLE Resultats (
    id SERIAL PRIMARY KEY,
    objectif_id INT NOT NULL REFERENCES Objectifs(id),
    titre VARCHAR(255) NOT NULL,
    description TEXT,
    indicateur VARCHAR(255),
    valeur_cible DECIMAL(10,2),
    valeur_actuelle DECIMAL(10,2) DEFAULT 0,
    unite VARCHAR(50),
    statut VARCHAR(30)
);

CREATE TABLE Activites (
    id SERIAL PRIMARY KEY,
    resultat_id INT NOT NULL REFERENCES Resultats(id),
    titre VARCHAR(255) NOT NULL,
    description TEXT,
    responsable_id INT REFERENCES Utilisateurs(id),
    date_debut DATE,
    date_fin DATE,
    statut VARCHAR(30),
    budget DECIMAL(15,2) DEFAULT 0,
    progression DECIMAL(5,2) DEFAULT 0
);

CREATE TABLE Taches (
    id SERIAL PRIMARY KEY,
    activite_id INT NOT NULL REFERENCES Activites(id),
    titre VARCHAR(255) NOT NULL,
    description TEXT,
    responsable_id INT REFERENCES Utilisateurs(id),
    priorite VARCHAR(20),
    statut VARCHAR(30),
    date_debut DATE,
    date_fin DATE,
    progression DECIMAL(5,2) DEFAULT 0
);

CREATE TABLE Dashboard_Indicateurs (
    id SERIAL PRIMARY KEY,
    cle VARCHAR(50) UNIQUE NOT NULL,
    libelle VARCHAR(100) NOT NULL,
    type_element VARCHAR(20) NOT NULL,
    colonne_source VARCHAR(50),
    agregation VARCHAR(20),
    format_affichage VARCHAR(20),
    icone VARCHAR(10),
    visible BOOLEAN NOT NULL DEFAULT TRUE,
    ordre INT NOT NULL DEFAULT 0
);

CREATE TABLE Parties_Prenantes (
    id SERIAL PRIMARY KEY,
    projet_id INT NOT NULL REFERENCES Projets(id),
    nom VARCHAR(200) NOT NULL,
    type_partie VARCHAR(50),
    role_contribution VARCHAR(500),
    contact VARCHAR(200),
    date_ajout TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE Documents (
    id SERIAL PRIMARY KEY,
    projet_id INT NOT NULL REFERENCES Projets(id),
    nom_fichier VARCHAR(255) NOT NULL,
    chemin_fichier VARCHAR(500) NOT NULL,
    type_document VARCHAR(50),
    description VARCHAR(500),
    date_ajout TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE Acces_Lecteurs (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES Users(id),
    projet_id INT NOT NULL REFERENCES Projets(id),
    date_ajout TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, projet_id)
);

-- Vue du tableau de bord
CREATE VIEW V_Dashboard_Projets AS
SELECT
    P.nom AS Projet,
    P.budget,
    COUNT(DISTINCT O.id) AS Total_Objectifs,
    COUNT(DISTINCT R.id) AS Total_Resultats,
    COUNT(DISTINCT A.id) AS Total_Activites,
    COUNT(DISTINCT T.id) AS Total_Taches,
    SUM(CASE WHEN T.statut = 'Terminé' THEN 1 ELSE 0 END) AS Taches_Terminees,
    CAST(
        SUM(CASE WHEN T.statut = 'Terminé' THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(T.id), 0)
    AS DECIMAL(5,2)) AS Progression_Projet
FROM Projets P
LEFT JOIN Objectifs O ON P.id = O.projet_id
LEFT JOIN Resultats R ON O.id = R.objectif_id
LEFT JOIN Activites A ON R.id = A.resultat_id
LEFT JOIN Taches T ON A.id = T.activite_id
GROUP BY P.nom, P.budget;

-- Indicateurs par défaut du tableau de bord
INSERT INTO Dashboard_Indicateurs (cle, libelle, type_element, colonne_source, agregation, format_affichage, icone, visible, ordre) VALUES
('nb_projets',          'Nombre de projets',       'kpi', NULL,                  'count', 'nombre',      '📁', TRUE,  1),
('budget_total',        'Budget total',             'kpi', 'budget',              'sum',   'montant',     '💰', TRUE,  2),
('budget_max',          'Budget max projet',        'kpi', 'budget',              'max',   'montant',     '📈', TRUE,  3),
('progression_moyenne', 'Progression moyenne',      'kpi', 'Progression_Projet',  'mean',  'pourcentage', '🎯', TRUE,  4),
('total_objectifs',     'Total objectifs',          'kpi', 'Total_Objectifs',     'sum',   'nombre',      '🧭', FALSE, 5),
('total_resultats',     'Total résultats',          'kpi', 'Total_Resultats',     'sum',   'nombre',      '✅', FALSE, 6),
('total_activites',     'Total activités',          'kpi', 'Total_Activites',     'sum',   'nombre',      '🛠️', FALSE, 7),
('total_taches',        'Total tâches',              'kpi', 'Total_Taches',        'sum',   'nombre',      '📋', FALSE, 8),
('taches_terminees',    'Tâches terminées',          'kpi', 'Taches_Terminees',    'sum',   'nombre',      '✔️', FALSE, 9);

INSERT INTO Dashboard_Indicateurs (cle, libelle, type_element, visible, ordre, icone) VALUES
('graph_budget_projet',      'Budget par projet',       'graphique', TRUE, 10, '💰'),
('graph_progression_projet', 'Progression par projet',  'graphique', TRUE, 11, '📈');
