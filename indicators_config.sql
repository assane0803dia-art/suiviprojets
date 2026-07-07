-- À exécuter une seule fois dans ProjectMonitoringDB

CREATE TABLE Dashboard_Indicateurs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    cle NVARCHAR(50) NOT NULL UNIQUE,       -- identifiant technique unique
    libelle NVARCHAR(100) NOT NULL,          -- nom affiché
    type_element NVARCHAR(20) NOT NULL,      -- 'kpi' ou 'graphique'
    colonne_source NVARCHAR(50) NULL,        -- colonne de V_Dashboard_Projets utilisée (KPI uniquement)
    agregation NVARCHAR(20) NULL,            -- 'sum', 'max', 'mean', 'count' (KPI uniquement)
    format_affichage NVARCHAR(20) NULL,      -- 'nombre', 'montant', 'pourcentage'
    icone NVARCHAR(10) NULL,
    visible BIT NOT NULL DEFAULT 1,
    ordre INT NOT NULL DEFAULT 0
);

-- Indicateurs KPI de base
INSERT INTO Dashboard_Indicateurs (cle, libelle, type_element, colonne_source, agregation, format_affichage, icone, visible, ordre) VALUES
('nb_projets',          'Nombre de projets',       'kpi', NULL,                  'count', 'nombre',      '📁', 1, 1),
('budget_total',        'Budget total',             'kpi', 'budget',              'sum',   'montant',     '💰', 1, 2),
('budget_max',          'Budget max projet',        'kpi', 'budget',              'max',   'montant',     '📈', 1, 3),
('progression_moyenne', 'Progression moyenne',      'kpi', 'Progression_Projet',  'mean',  'pourcentage', '🎯', 1, 4),
('total_objectifs',     'Total objectifs',          'kpi', 'Total_Objectifs',     'sum',   'nombre',      '🧭', 0, 5),
('total_resultats',     'Total résultats',          'kpi', 'Total_Resultats',     'sum',   'nombre',      '✅', 0, 6),
('total_activites',     'Total activités',          'kpi', 'Total_Activites',     'sum',   'nombre',      '🛠️', 0, 7),
('total_taches',        'Total tâches',              'kpi', 'Total_Taches',        'sum',   'nombre',      '📋', 0, 8),
('taches_terminees',    'Tâches terminées',          'kpi', 'Taches_Terminees',    'sum',   'nombre',      '✔️', 0, 9);

-- Graphiques
INSERT INTO Dashboard_Indicateurs (cle, libelle, type_element, visible, ordre, icone) VALUES
('graph_budget_projet',      'Budget par projet',       'graphique', 1, 10, '💰'),
('graph_progression_projet', 'Progression par projet',  'graphique', 1, 11, '📈');
