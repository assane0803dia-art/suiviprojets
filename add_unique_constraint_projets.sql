-- Optionnel mais recommandé : ajoute une contrainte UNIQUE au niveau de la base de données,
-- en complément de la vérification déjà faite dans l'application (double sécurité).
-- Attention : si des doublons existent déjà, cette commande échouera — nettoyez-les d'abord.

ALTER TABLE Projets
ADD CONSTRAINT UQ_Projets_Nom UNIQUE (nom);
