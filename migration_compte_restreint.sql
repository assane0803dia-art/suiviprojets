-- Permet de créer un compte "restreint" : un compte utilisateur normal (avec
-- droits d'édition complets), mais qui ne voit QUE les projets qui lui sont
-- explicitement accordés — contrairement à un compte lecteur, qui peut
-- seulement consulter, ce compte peut modifier son projet.
-- Utile pour un client externe qui ne doit voir ni gérer que son propre projet
-- confidentiel, sans accès aux autres projets de la plateforme.
-- À exécuter dans l'éditeur SQL de Supabase

ALTER TABLE Users ADD COLUMN IF NOT EXISTS compte_restreint BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS Acces_Restreint (
    user_id INT NOT NULL REFERENCES Users(id),
    projet_id INT NOT NULL REFERENCES Projets(id),
    PRIMARY KEY (user_id, projet_id)
);
