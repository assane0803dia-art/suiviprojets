USE ProjectMonitoringDB;
GO


CREATE TABLE Utilisateurs (

    id INT PRIMARY KEY IDENTITY(1,1),

    nom VARCHAR(100) NOT NULL,

    email VARCHAR(100) UNIQUE NOT NULL,

    mot_de_passe VARCHAR(255) NOT NULL,

    role VARCHAR(50),

    date_creation DATETIME DEFAULT GETDATE()

);




INSERT INTO Utilisateurs
(nom,email,mot_de_passe,role)

VALUES

('Aliou','aliou@gmail.com','123456','Chef de projet'),

('Fatou','fatou@gmail.com','abcdef','Gestionnaire');


SELECT *
FROM Utilisateurs;


CREATE TABLE Projets(

    id INT PRIMARY KEY IDENTITY(1,1),

    nom VARCHAR(200),

    description TEXT,

    date_debut DATE,

    date_fin DATE,

    budget DECIMAL(15,2),

    statut VARCHAR(50),

    responsable_id INT,

    FOREIGN KEY(responsable_id)

    REFERENCES Utilisateurs(id)

);



INSERT INTO Projets

(nom,
description,
date_debut,
date_fin,
budget,
statut,
responsable_id)

VALUES

(
'Projet Agriculture',

'Formation des agriculteurs',

'2026-07-01',

'2027-06-30',

50000000,

'En cours',

1
);


SELECT *

FROM Projets;



CREATE TABLE Objectifs (

    id INT PRIMARY KEY IDENTITY(1,1),

    projet_id INT NOT NULL,

    type_objectif VARCHAR(30) NOT NULL,

    titre VARCHAR(255) NOT NULL,

    description TEXT,

    responsable_id INT,

    date_debut DATE,

    date_fin DATE,

    statut VARCHAR(30) DEFAULT 'Non commencé',

    FOREIGN KEY (projet_id)
        REFERENCES Projets(id),

    FOREIGN KEY (responsable_id)
        REFERENCES Utilisateurs(id)

);



INSERT INTO Objectifs
(
projet_id,
type_objectif,
titre,
description,
responsable_id,
date_debut,
date_fin
)

VALUES
(
1,
'General',
'Améliorer la productivité agricole',
'Augmenter la productivité des exploitations agricoles.',
1,
'2026-07-01',
'2027-06-30'
);





INSERT INTO Objectifs
(
projet_id,
type_objectif,
titre,
description,
responsable_id,
date_debut,
date_fin
)

VALUES
(
1,
'Specifique',
'Former les producteurs',
'Former 500 producteurs aux nouvelles techniques.',
1,
'2026-07-01',
'2026-10-31'
);   



INSERT INTO Objectifs
(
projet_id,
type_objectif,
titre,
description,
responsable_id,
date_debut,
date_fin
)

VALUES
(
1,
'Specifique',
'Améliorer l''accès aux équipements',
'Distribuer des équipements agricoles modernes.',
2,
'2026-08-01',
'2027-02-28'
);



SELECT *
FROM Objectifs;



SELECT

P.nom AS Projet,

O.type_objectif,

O.titre,

O.statut

FROM Projets P

INNER JOIN Objectifs O

ON P.id = O.projet_id;



CREATE TABLE Resultats (

    id INT PRIMARY KEY IDENTITY(1,1),

    objectif_id INT NOT NULL,

    titre VARCHAR(255) NOT NULL,

    description TEXT,

    indicateur VARCHAR(255),

    valeur_cible DECIMAL(10,2),

    valeur_actuelle DECIMAL(10,2) DEFAULT 0,

    unite VARCHAR(50),

    statut VARCHAR(30) DEFAULT 'Non commencé',

    FOREIGN KEY (objectif_id)
        REFERENCES Objectifs(id)

);



INSERT INTO Resultats
(
objectif_id,
titre,
description,
indicateur,
valeur_cible,
unite
)

VALUES

(
2,
'500 producteurs formés',
'Les producteurs maîtrisent les nouvelles techniques agricoles.',
'Nombre de producteurs formés',
500,
'Personnes'
);



INSERT INTO Resultats
(
objectif_id,
titre,
description,
indicateur,
valeur_cible,
unite
)

VALUES

(
2,
'80 % des producteurs appliquent les techniques',
'Les bénéficiaires appliquent les techniques enseignées.',
'Taux d''application',
80,
'%'
);   


SELECT *
FROM Resultats;



SELECT

O.titre AS Objectif,

R.titre AS Resultat,

R.indicateur,

R.valeur_cible,

R.valeur_actuelle

FROM Objectifs O

INNER JOIN Resultats R

ON O.id = R.objectif_id;


CREATE TABLE Activites (

    id INT PRIMARY KEY IDENTITY(1,1),

    resultat_id INT NOT NULL,

    titre VARCHAR(255) NOT NULL,

    description TEXT,

    responsable_id INT,

    date_debut DATE,

    date_fin DATE,

    statut VARCHAR(30) DEFAULT 'Non commencé',

    budget DECIMAL(15,2) DEFAULT 0,

    progression DECIMAL(5,2) DEFAULT 0,

    FOREIGN KEY (resultat_id)
        REFERENCES Resultats(id),

    FOREIGN KEY (responsable_id)
        REFERENCES Utilisateurs(id)
);  



INSERT INTO Activites
(
resultat_id,
titre,
description,
responsable_id,
date_debut,
date_fin,
budget
)

VALUES

(
1,
'Organisation des sessions de formation',
'Planification et exécution des formations',
1,
'2026-07-01',
'2026-08-31',
2000000
); 

INSERT INTO Activites
(
resultat_id,
titre,
description,
responsable_id,
date_debut,
date_fin,
budget
)

VALUES

(
1,
'Préparation des supports pédagogiques',
'Création des modules de formation',
2,
'2026-07-01',
'2026-07-20',
500000
);               



INSERT INTO Activites
(
resultat_id,
titre,
description,
responsable_id,
date_debut,
date_fin,
budget
)

VALUES

(
1,
'Mobilisation des formateurs',
'Recrutement et coordination des formateurs',
1,
'2026-07-05',
'2026-07-15',
300000
); 


SELECT *
FROM Activites;  


SELECT

R.titre AS Resultat,
A.titre AS Activite,
A.statut,
A.progression,
A.budget

FROM Resultats R

INNER JOIN Activites A
ON R.id = A.resultat_id;


CREATE TABLE Taches (

    id INT PRIMARY KEY IDENTITY(1,1),

    activite_id INT NOT NULL,

    titre VARCHAR(255) NOT NULL,

    description TEXT,

    responsable_id INT,

    priorite VARCHAR(20) DEFAULT 'Moyenne',

    statut VARCHAR(30) DEFAULT 'Non commencé',

    date_debut DATE,

    date_fin DATE,

    progression DECIMAL(5,2) DEFAULT 0,

    FOREIGN KEY (activite_id)
        REFERENCES Activites(id),

    FOREIGN KEY (responsable_id)
        REFERENCES Utilisateurs(id)
);   


INSERT INTO Taches
(
activite_id,
titre,
description,
responsable_id,
priorite,
date_debut,
date_fin
)

VALUES
(
1,
'Réserver la salle',
'Trouver et réserver une salle de formation adaptée',
1,
'Haute',
'2026-07-01',
'2026-07-03'
);    


INSERT INTO Taches
(
activite_id,
titre,
description,
responsable_id,
priorite,
date_debut,
date_fin
)

VALUES
(
1,
'Envoyer les invitations',
'Contacter les producteurs et envoyer les convocations',
2,
'Moyenne',
'2026-07-02',
'2026-07-05'
);      

INSERT INTO Taches
(
activite_id,
titre,
description,
responsable_id,
priorite,
date_debut,
date_fin
)

VALUES
(
1,
'Préparer les supports de formation',
'Imprimer et organiser les supports pédagogiques',
1,
'Haute',
'2026-07-01',
'2026-07-10'
); 

SELECT *
FROM Taches;   


SELECT

A.titre AS Activite,
T.titre AS Tache,
T.statut,
T.priorite,
T.progression

FROM Activites A

INNER JOIN Taches T
ON A.id = T.activite_id;  


