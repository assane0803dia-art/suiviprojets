-- Module de suivi financier : permet d'enregistrer les dépenses réelles par activité,
-- pour calculer l'écart et le taux d'exécution par rapport au budget prévu.
-- À exécuter dans l'éditeur SQL de Supabase

CREATE TABLE IF NOT EXISTS Depenses (
    id SERIAL PRIMARY KEY,
    activite_id INT NOT NULL REFERENCES Activites(id),
    montant DECIMAL(15,2) NOT NULL,
    date_depense DATE,
    description VARCHAR(500),
    date_ajout TIMESTAMP NOT NULL DEFAULT NOW()
);
