-- Ajoute un champ libre "Observation" sur les activités, pour que les responsables
-- documentent les difficultés/contraintes rencontrées — exploité ensuite par le
-- rapport IA pour expliquer un taux de réalisation, pas seulement le constater.
-- À exécuter dans l'éditeur SQL de Supabase

ALTER TABLE Activites ADD COLUMN IF NOT EXISTS observation TEXT;
