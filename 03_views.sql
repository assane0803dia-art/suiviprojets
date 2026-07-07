CREATE VIEW V_Dashboard_Taches AS

SELECT

P.nom AS Projet,
O.titre AS Objectif,
R.titre AS Resultat,
A.titre AS Activite,

COUNT(T.id) AS Total_Taches,

SUM(CASE WHEN T.statut = 'Terminé' THEN 1 ELSE 0 END) AS Taches_Terminees,

CAST(
    SUM(CASE WHEN T.statut = 'Terminé' THEN 1 ELSE 0 END) * 100.0
    / NULLIF(COUNT(T.id), 0)
AS DECIMAL(5,2)) AS Progression_Taches

FROM Projets P

JOIN Objectifs O ON P.id = O.projet_id
JOIN Resultats R ON O.id = R.objectif_id
JOIN Activites A ON R.id = A.resultat_id
JOIN Taches T ON A.id = T.activite_id

GROUP BY
P.nom, O.titre, R.titre, A.titre;


SELECT *
FROM V_Dashboard_Taches;



CREATE VIEW V_Dashboard_Projets AS

SELECT

P.nom AS Projet,
P.budget,

COUNT(DISTINCT O.id) AS Total_Objectifs,
COUNT(DISTINCT R.id) AS Total_Resultats,
COUNT(DISTINCT A.id) AS Total_Activites,
COUNT(DISTINCT T.id) AS Total_Taches,

SUM(CASE WHEN T.statut = 'Terminé' THEN 1 ELSE 0 END) AS Taches_Terminees,

CAST(
    SUM(CASE WHEN T.statut = 'Terminé' THEN 1 ELSE 0 END) * 100.0
    / NULLIF(COUNT(T.id), 0)
AS DECIMAL(5,2)) AS Progression_Projet

FROM Projets P

LEFT JOIN Objectifs O ON P.id = O.projet_id
LEFT JOIN Resultats R ON O.id = R.objectif_id
LEFT JOIN Activites A ON R.id = A.resultat_id
LEFT JOIN Taches T ON A.id = T.activite_id

GROUP BY
P.nom, P.budget;  


SELECT *
FROM V_Dashboard_Projets;


CREATE VIEW V_KPI_Projets AS

SELECT

P.nom AS Projet,

COUNT(T.id) AS Total_Taches,

SUM(CASE WHEN T.statut = 'Terminé' THEN 1 ELSE 0 END) AS Taches_Terminees,

SUM(CASE WHEN T.statut = 'En cours' THEN 1 ELSE 0 END) AS Taches_En_Cours,

SUM(CASE WHEN T.statut = 'Non commencé' THEN 1 ELSE 0 END) AS Taches_Non_Commencees,

CAST(
    SUM(CASE WHEN T.statut = 'Terminé' THEN 1 ELSE 0 END) * 100.0
    / NULLIF(COUNT(T.id), 0)
AS DECIMAL(5,2)) AS Taux_Execution

FROM Projets P

LEFT JOIN Objectifs O ON P.id = O.projet_id
LEFT JOIN Resultats R ON O.id = R.objectif_id
LEFT JOIN Activites A ON R.id = A.resultat_id
LEFT JOIN Taches T ON A.id = T.activite_id

GROUP BY P.nom;  


SELECT *
FROM V_KPI_Projets;

SELECT *
FROM V_Dashboard_Projets;