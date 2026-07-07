-- À exécuter une seule fois dans ProjectMonitoringDB
-- Permet d'attribuer à un compte "lecteur" (Users.role = 'lecteur') l'accès en lecture
-- seule à un ou plusieurs projets spécifiques.

CREATE TABLE Acces_Lecteurs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    projet_id INT NOT NULL,
    date_ajout DATETIME NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (projet_id) REFERENCES Projets(id),
    CONSTRAINT UQ_Acces_Lecteur UNIQUE (user_id, projet_id)
);
