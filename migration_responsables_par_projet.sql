-- Rattache chaque responsable à UN projet précis, pour garantir l'indépendance
-- entre projets : un responsable ajouté sur un projet n'apparaît plus dans la
-- liste des autres projets.
-- À exécuter dans l'éditeur SQL de Supabase

ALTER TABLE Utilisateurs ADD COLUMN IF NOT EXISTS projet_id INT REFERENCES Projets(id);

-- Note : les responsables déjà existants (créés avant cette migration) auront
-- projet_id = NULL et n'apparaîtront donc plus dans aucune liste tant qu'ils ne
-- sont pas recréés depuis le bon projet. Si vous voulez les rattacher à un
-- projet existant sans les recréer, utilisez par exemple :
--   UPDATE Utilisateurs SET projet_id = <id_du_projet> WHERE id = <id_du_responsable>;
