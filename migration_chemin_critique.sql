-- Permet de définir qu'une activité dépend d'une autre (doit démarrer après elle),
-- nécessaire pour calculer un vrai chemin critique.
-- Limite assumée : une activité ne peut dépendre que d'UNE SEULE activité précédente
-- (pas de dépendances multiples type "attendre A ET B").
-- À exécuter dans l'éditeur SQL de Supabase

ALTER TABLE Activites ADD COLUMN IF NOT EXISTS depend_de_activite_id INT REFERENCES Activites(id);
