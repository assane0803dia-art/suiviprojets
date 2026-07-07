-- Migration pour la refonte de la page Paramètres
-- À exécuter dans l'éditeur SQL de Supabase

-- Profil et préférences, ajoutés à la table Users existante
ALTER TABLE Users ADD COLUMN IF NOT EXISTS nom_complet VARCHAR(150);
ALTER TABLE Users ADD COLUMN IF NOT EXISTS email VARCHAR(150);
ALTER TABLE Users ADD COLUMN IF NOT EXISTS photo_url VARCHAR(500);

ALTER TABLE Users ADD COLUMN IF NOT EXISTS langue VARCHAR(10) DEFAULT 'fr';
ALTER TABLE Users ADD COLUMN IF NOT EXISTS fuseau_horaire VARCHAR(50) DEFAULT 'Africa/Dakar';
ALTER TABLE Users ADD COLUMN IF NOT EXISTS modele_rapport VARCHAR(30) DEFAULT 'Standard';

ALTER TABLE Users ADD COLUMN IF NOT EXISTS ia_modele VARCHAR(50) DEFAULT 'claude-sonnet-5';
ALTER TABLE Users ADD COLUMN IF NOT EXISTS ia_creativite INT DEFAULT 50;  -- 0 à 100
ALTER TABLE Users ADD COLUMN IF NOT EXISTS ia_langue_reponses VARCHAR(10) DEFAULT 'fr';
ALTER TABLE Users ADD COLUMN IF NOT EXISTS ia_suggestions_auto BOOLEAN DEFAULT TRUE;

ALTER TABLE Users ADD COLUMN IF NOT EXISTS notif_email BOOLEAN DEFAULT FALSE;
ALTER TABLE Users ADD COLUMN IF NOT EXISTS notif_app BOOLEAN DEFAULT TRUE;
ALTER TABLE Users ADD COLUMN IF NOT EXISTS notif_alertes BOOLEAN DEFAULT TRUE;

ALTER TABLE Users ADD COLUMN IF NOT EXISTS derniere_connexion TIMESTAMP;

-- Historique de connexion (base d'une vue "sessions" simplifiée)
CREATE TABLE IF NOT EXISTS Historique_Connexions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES Users(id),
    date_connexion TIMESTAMP NOT NULL DEFAULT NOW()
);
