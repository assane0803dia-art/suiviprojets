-- Ajoute deux colonnes standards de cadre logique aux résultats (indicateur principal) :
-- la source de vérification et la valeur de référence (baseline).
-- À exécuter dans l'éditeur SQL de Supabase

ALTER TABLE Resultats ADD COLUMN IF NOT EXISTS source_verification VARCHAR(255);
ALTER TABLE Resultats ADD COLUMN IF NOT EXISTS baseline DECIMAL(10,2);

-- Mêmes colonnes pour les indicateurs supplémentaires (au-delà de l'indicateur principal)
ALTER TABLE Indicateurs_Supplementaires ADD COLUMN IF NOT EXISTS source_verification VARCHAR(255);
ALTER TABLE Indicateurs_Supplementaires ADD COLUMN IF NOT EXISTS baseline DECIMAL(10,2);

