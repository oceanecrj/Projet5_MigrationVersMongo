# Script pour la migration de données médicales sur MongoDB.  
Version : **2.1**

## Description : 
Script à destination des clients pour migrer de données médicales depuis un fichier csv sur la base MongoDB.  
## Prérequis : 
Docker 29.7.2, données sous format csv, script python, Dockerfile, requirements.txt, mongo-init.js, docker-compose.yml
## Installation : 
Avant utilisation du script, un fichier nommé healthcare_dataset.csv (contenant les données à migrer), le script python, le Dockerfile, le requirements.txt, le mongo-init.js et le docker-compose.yml doivent être enregistrés dans un dossier commun.
## Utilisation : 
### **<ins>Etape 1 : fichier csv</ins>**  
Le fichier doit se nommer healthcare_dataset.csv. 
Il est composé des champs suivants :    
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

### **<ins>Etape 2 : mode script (audit simple ou migration)</ins>**
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

### **<ins>Etape 3 : conteneurisation</ins>**
1) Ouvrir le terminal de commande  
2) Se positionner dans le dossier du script via la commande `cd "chemin"`
3) Pour monter l'image python, entrer la commande : `docker compose build`
### **<ins>Etape 4 : lancement de MongoDB et vérification des utilisateurs</ins>**
1) Pour lancer mongodb, entrer la commande :`docker compose up -d mongodb`
2) Pour vérifier si mongodb est actif, entrer la commande : `docker compose ps`
3) Pour vérifier la liste des utilisateurs, il faut :  
	a) accéder à MongoDB via : `docker compose exec mongodb mongosh --username NOM_ADMIN --authenticationDatabase Healthcare --password`. Puis entrer votre mot de passe  
	b) entrer `use Healthcare`,  
	c) entrer `db.getUsers()`  
### **<ins>Etape 5 : lancement du script</ins>**
1) Pour lancer le script, entrer la commande : `docker compose run migration`\
   Lors du lancement, il faudra renseigner le nom de l'utilisateur et le mot de passe. Si un utilisateur avec des droits de lecture uniquement est entré, le script ne pourra pas procéder à la phase d'intégration des données dans MongoDB.
    
_Note_: En cas de modification du script (étape 2), entrer la commande : `docker compose run --build migration` 
 
Des volumes sont créés, la liste est accessible via la commande : `docker volume ls`
### **<ins>Etape 6 : visualisation des logs</ins>**
Pour les logs liés à la migration, entrer la commande : `docker compose logs migration`\
Pour les logs liés à MongoDB, entrer la commande : `docker compose logs mongodb`
### **<ins>Etape 7 : connexion à MongoDB Compass</ins>**
Pour visualiser la base de données sur l'application Mongo Compass, se connecter via l'URI:  `mongodb://NOM_UTILISATEUR:MDP_UTILISATEUR@localhost:27018/?authSource=Healthcare`  
  
<ins>Alternative:<ins>  
1) ajoutez une nouvelle connexion et copiez dans la partie URI `mongodb://localhost:27018`
2) cliquez sur "Advanced Connection Options" et entrez votre Username, votre Password et inserer "Healthcare" dans la case Authentication Database
3) cliquez sur "Save & Connect".

Vous avez maintenant accès à la base de données et pouvez faire des requêtes directement depuis MongoDB Compass.  
Selon vos droits, vous aurez uniquement la possibilité de visualiser la base de données ou également de la modifier.
### **<ins>Etape 8 : arrêt du conteneur</ins>**
Entrer la commande : `docker compose down`
\
Pour supprimer également les volumes lors de l'arrêt : `docker compose down -v`  
**ATTENTION**: en cas de suppression des volumes, toutes les données de MongoDB sont perdues (collections).



