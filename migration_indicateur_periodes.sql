-- Ventilation temporelle des indicateurs : permet de définir des cibles par
-- période (trimestre, mois, etc.) plutôt que d'attendre la fin du projet pour
-- savoir si un indicateur est en retard.
-- À exécuter dans l'éditeur SQL de Supabase

ALTER TABLE Resultats ADD COLUMN IF NOT EXISTS frequence_ventilation VARCHAR(20) DEFAULT 'aucune';
ALTER TABLE Indicateurs_Supplementaires ADD COLUMN IF NOT EXISTS frequence_ventilation VARCHAR(20) DEFAULT 'aucune';

CREATE TABLE IF NOT EXISTS Indicateur_Periodes (
    id SERIAL PRIMARY KEY,
    resultat_id INT REFERENCES Resultats(id),
    indicateur_supplementaire_id INT REFERENCES Indicateurs_Supplementaires(id),
    periode_label VARCHAR(50) NOT NULL,
    date_debut DATE NOT NULL,
    date_fin DATE NOT NULL,
    cible_periode DECIMAL(14,2) NOT NULL DEFAULT 0,
    realise_periode DECIMAL(14,2) NOT NULL DEFAULT 0,
    CONSTRAINT chk_un_seul_parent CHECK (
        (resultat_id IS NOT NULL AND indicateur_supplementaire_id IS NULL) OR
        (resultat_id IS NULL AND indicateur_supplementaire_id IS NOT NULL)
    )
);
