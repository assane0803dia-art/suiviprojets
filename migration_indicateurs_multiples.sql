-- Permet d'ajouter plusieurs indicateurs à un même résultat attendu.
-- L'indicateur déjà présent sur Resultats (colonnes indicateur/valeur_cible/...)
-- reste l'indicateur "principal" et n'est pas touché par cette migration.
-- À exécuter dans l'éditeur SQL de Supabase

CREATE TABLE IF NOT EXISTS Indicateurs_Supplementaires (
    id SERIAL PRIMARY KEY,
    resultat_id INT NOT NULL REFERENCES Resultats(id),
    nom VARCHAR(255) NOT NULL,
    valeur_cible DECIMAL(10,2),
    valeur_actuelle DECIMAL(10,2) DEFAULT 0,
    unite VARCHAR(50),
    date_ajout TIMESTAMP NOT NULL DEFAULT NOW()
);
