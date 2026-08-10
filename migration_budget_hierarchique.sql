-- Module budgétaire hiérarchique : Rubrique → Sous-rubrique → Ligne budgétaire,
-- entièrement configurable par l'utilisateur (aucune rubrique imposée par le système).
-- Le coût total d'une ligne (quantité × coût unitaire) n'est JAMAIS stocké : il est
-- toujours recalculé à la lecture, pour rester exact en toute circonstance.
-- À exécuter dans l'éditeur SQL de Supabase

CREATE TABLE IF NOT EXISTS Budget_Rubriques (
    id SERIAL PRIMARY KEY,
    projet_id INT NOT NULL REFERENCES Projets(id),
    nom VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    code_budgetaire VARCHAR(50),
    ordre INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS Budget_Sous_Rubriques (
    id SERIAL PRIMARY KEY,
    rubrique_id INT NOT NULL REFERENCES Budget_Rubriques(id),
    nom VARCHAR(255) NOT NULL,
    ordre INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS Budget_Lignes (
    id SERIAL PRIMARY KEY,
    sous_rubrique_id INT NOT NULL REFERENCES Budget_Sous_Rubriques(id),
    description VARCHAR(500) NOT NULL,
    unite VARCHAR(50) NOT NULL,
    quantite DECIMAL(12,2) NOT NULL DEFAULT 0,
    cout_unitaire DECIMAL(15,2) NOT NULL DEFAULT 0,
    activite_id INT REFERENCES Activites(id),  -- rattachement facultatif
    ordre INT NOT NULL DEFAULT 0
);

-- Configuration devise, au niveau du projet
ALTER TABLE Projets ADD COLUMN IF NOT EXISTS devise_principale VARCHAR(10) DEFAULT 'XOF';
ALTER TABLE Projets ADD COLUMN IF NOT EXISTS devise_secondaire VARCHAR(10) DEFAULT 'EUR';
ALTER TABLE Projets ADD COLUMN IF NOT EXISTS taux_conversion DECIMAL(14,6) DEFAULT 1;
