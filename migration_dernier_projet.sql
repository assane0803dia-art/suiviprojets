-- Permet de rediriger automatiquement l'utilisateur vers le dernier projet
-- qu'il a consulté, juste après la connexion.
-- À exécuter dans l'éditeur SQL de Supabase

ALTER TABLE Users ADD COLUMN IF NOT EXISTS dernier_projet_id INT REFERENCES Projets(id);
