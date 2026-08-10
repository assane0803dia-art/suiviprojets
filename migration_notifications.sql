-- Centre de notifications + lien optionnel entre un responsable (Utilisateurs,
-- rattaché à un projet) et un vrai compte de connexion (Users) — nécessaire pour
-- qu'un responsable puisse recevoir des notifications.
-- À exécuter dans l'éditeur SQL de Supabase

ALTER TABLE Utilisateurs ADD COLUMN IF NOT EXISTS user_id INT REFERENCES Users(id);

CREATE TABLE IF NOT EXISTS Notifications (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES Users(id),
    projet_id INT REFERENCES Projets(id),
    activite_id INT REFERENCES Activites(id),
    type VARCHAR(50) NOT NULL,
    titre VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    date_creation TIMESTAMP NOT NULL DEFAULT NOW(),
    date_evenement TIMESTAMP,
    lu BOOLEAN NOT NULL DEFAULT FALSE
);
