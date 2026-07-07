-- Table pour sauvegarder les rapports générés (et éventuellement édités) dans un projet
-- À exécuter dans l'éditeur SQL de Supabase

CREATE TABLE IF NOT EXISTS Rapports (
    id SERIAL PRIMARY KEY,
    projet_id INT NOT NULL REFERENCES Projets(id),
    titre VARCHAR(255) NOT NULL,
    contenu TEXT NOT NULL,
    cree_par INT REFERENCES Users(id),
    date_creation TIMESTAMP NOT NULL DEFAULT NOW()
);
