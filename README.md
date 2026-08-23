# Script pour la migration de données médicales sur MongoDB.  
Version : 1.1

## Description courte : 
Script à destination des clients pour migrer de données médicales depuis un fichier csv sur la base MongoDB 
\
## Prérequis : 
Docker version 29.7.2, fichier csv, script python, Dockerfile, requirements.txt, docker-compose.yml
\
## Installation : 
Avant utilisation du script, un fichier nommé healthcare_dataset.csv (contenant les données à migrer), le script python, le Dockerfile, le requirements.txt et le docker-compose.yml doivent être enregistrés dans un dossier commun.
\
## Utilisation : 
\
**<ins>Etape 1 : fichier csv</ins>**  
	Le fichier doit se nommer healthcare_dataset.csv. 
	Il doit être composés des champs suivants :    
	    "Name": "VARCHAR",  
	    "Age": "INTEGER",  
	    "Gender": "VARCHAR",  
	    "Blood Type": "VARCHAR",  
	    "Medical Condition": "VARCHAR",  
	    "Date of Admission": "DATE",  
	    "Doctor": "VARCHAR",  
	    "Hospital": "VARCHAR",  
	    "Insurance Provider": "VARCHAR",  
	    "Billing Amount": "FLOAT",  
	    "Room Number": "INTEGER",  
	    "Admission Type": "VARCHAR",  
	    "Discharge Date": "DATE",  
	    "Medication": "VARCHAR",  
	    "Test Results": "VARCHAR" 
 \
 \
	Il existe également des restrictions pour les champs ci-dessous:  
	    "Age": compris entre 0 et 150,    
	    "Gender": choix entre "MALE", "FEMALE",  
	    "Blood Type": choix entre "A+", "A-", "AB+", "AB-", "B+", "B-", "O+", "O-",  
	    "Room Number": obligatoirement positif,  
	    "Admission Type": choix entre "ELECTIVE", "URGENT", "EMERGENCY",  
	    "Test Results": choix entre "ABNORMAL", "INCONCLUSIVE", "NORMAL"  
\
**<ins>Etape 2 : mode script (audit simple ou migration)</ins>**
\
	_Dans le fichier docker-compose.yml_
\
	Pour effectuer uniquement un contrôle du fichier csv sans faire de migration, veuillez appliquer:
  
	line 22 - APPLY_CHANGES: "false" (ou toute autre valeur non nulle différente de true)
\
	Pour effectuer un contrôle du fichier csv puis la migration vers MongoDB, veuillez appliquer:
  
	line 22 - APPLY_CHANGES: "true"
\
	Pour contraindre l'absence de collection dans la base MongoDB, veuillez appliquer:
  
	line 24 - REQUIRE_EMPTY_COLLECTION: "true"
\
	Pour permettre l'enregistrement de nouvelles données dans la base MongoDB existante, veuillez appliquer:
  
	line 24 - REQUIRE_EMPTY_COLLECTION: "false" (ou toute autre valeur non nulle différente de true)

**<ins>Etape 3 : conteneurisation</ins>**
\
	1) Ouvrir le terminal de commande  
	2) Se positionner dans le dossier du script via la commande cd "chemin"\
	3) Pour monter l'image python, entrer la commande :
  

  docker compose build
\
**<ins>Etape 4 : lancement du script</ins>**
\
	1) Pour lancer mongodb, entrer la commande : 
  

  docker compose up -d mongodb
\
	2) Pour vérifier si mongodb est actif, entrer la commande :
  

  docker compose ps
 \
	3) Pour lancer le script, entrer la commande :
  

  docker compose up migration
 \
	3.1) En cas de modification du script (étape 2), entrer la commande :
  

  docker compose up --build migration
\
	Des volumes sont créés, la liste est accessible via la commande :
  

  docker volume ls
\
**<ins>Etape 5 : visualisation des logs</ins>**
\
	Pour les logs liés à la migration, entrer la commande :
  

  docker compose logs migration
\
	Pour les logs liés à MongoDB, entrer la commande :
  

  docker compose logs mongodb

**<ins>Etape 6 : arrêt du conteneur</ins>**
\
	Entrer la commande : 
  

  docker compose down
\
	Pour supprimer également les volumes lors de l'arrêt : 
  

  docker compose down -v



