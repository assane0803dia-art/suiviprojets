-- À exécuter une seule fois dans ProjectMonitoringDB

CREATE TABLE Parties_Prenantes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    projet_id INT NOT NULL,
    nom NVARCHAR(200) NOT NULL,
    type_partie NVARCHAR(50) NULL,          -- Bailleur, Partenaire technique, Bénéficiaire, Communauté, Autre
    role_contribution NVARCHAR(500) NULL,
    contact NVARCHAR(200) NULL,
    date_ajout DATETIME NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (projet_id) REFERENCES Projets(id)
);

CREATE TABLE Documents (
    id INT IDENTITY(1,1) PRIMARY KEY,
    projet_id INT NOT NULL,
    nom_fichier NVARCHAR(255) NOT NULL,
    chemin_fichier NVARCHAR(500) NOT NULL,   -- chemin relatif sur le disque, ex: documents/12/rapport.pdf
    type_document NVARCHAR(50) NULL,          -- Rapport, Contrat, Fiche projet, Photo, Autre
    description NVARCHAR(500) NULL,
    date_ajout DATETIME NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (projet_id) REFERENCES Projets(id)
);
