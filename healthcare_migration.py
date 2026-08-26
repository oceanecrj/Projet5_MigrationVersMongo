import os
from pathlib import Path

import pandas as pd
from pymongo import MongoClient


# CONFIG
# Les valeurs sont fournies par docker-compose.yml.

CSV_INPUT = Path(os.environ["CSV_INPUT"])
CSV_OUTPUT = Path(os.environ["CSV_OUTPUT"])
CSV_DELIMITER = os.environ["CSV_DELIMITER"]

MONGODB_URI = os.environ["MONGODB_URI"]
DATABASE = os.environ["DATABASE_NAME"]
COLLECTION = os.environ["COLLECTION_NAME"]

APPLY_CHANGES = os.environ["APPLY_CHANGES"].lower() == "true"
MAX_EXAMPLES = int(os.environ["MAX_EXAMPLES"])
REQUIRE_EMPTY_COLLECTION = os.environ["REQUIRE_EMPTY_COLLECTION"].lower() == "true"


# REGLES

STRUCTURE_DB = {
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
    "Test Results": "VARCHAR",
}

CHAMPS_ATTENDUS = list(STRUCTURE_DB.keys())

RESTRICTION = {
    "Gender": ["MALE", "FEMALE"],
    "Blood Type": ["A+", "A-", "AB+", "AB-", "B+", "B-", "O+", "O-"],
    "Admission Type": ["ELECTIVE", "URGENT", "EMERGENCY"],
    "Test Results": ["ABNORMAL", "INCONCLUSIVE", "NORMAL"],
}

CHAMPS_ID = ["Name", "Doctor", "Date of Admission","Discharge Date", "Billing Amount", "Hospital"]

DISTINCTION = ["MRS.", "MRS", "MR.", "MR", "MS.", "MS", "DR.", "DR"]


# CONTROLE / RETRAITEMENT

def decompte_champs_vides():
    return {champ: 0 for champ in CHAMPS_ATTENDUS}


def incrementer(compteur, key):
    compteur[key] = compteur.get(key, 0) + 1


def val_manquante(valeur):
    if valeur is None:
        return True
    if isinstance(valeur, str):
        return valeur.strip() == ""
    return bool(pd.isna(valeur))


def refonte_val_string(champ, valeur):
    valeur = valeur.strip()

    if champ in ["Name", "Doctor"]:
        en_majuscule = valeur.upper()
        for abreviation in DISTINCTION:
            prefix = abreviation + " "
            if en_majuscule.startswith(prefix):
                valeur = valeur[len(prefix):].strip()
                break

    return valeur.upper()

def convert_valeurs_csv(valeur, champ):
    if val_manquante(valeur):
        return valeur

    valeur = valeur.strip()
    type_attendu = STRUCTURE_DB[champ]

    if type_attendu == "VARCHAR":
        return valeur

    if type_attendu == "INTEGER":
        try:
            return int(valeur)
        except ValueError:
            return valeur

    if type_attendu == "FLOAT":
        try:
            return round(float(valeur),2)
        except ValueError:
            return valeur

    if type_attendu == "DATE":
        return pd.to_datetime(valeur, format="%Y-%m-%d", errors="coerce")

    return valeur

def validite_type(valeur, type_attendu):
    types = {
        "VARCHAR": str,
        "INTEGER": int,
        "FLOAT": float,
        "DATE": pd.Timestamp
    }

    return isinstance(valeur, types[type_attendu])

def validite_regles_restriction(champ, valeur):
    if champ == "Age":
        return 0 < valeur < 150
    if champ == "Room Number":
        return valeur > 0
    if champ in RESTRICTION:
        return valeur in RESTRICTION[champ]
    return True

# CSV

def csv_charge(chemin):
    dataframe_csv = pd.read_csv(chemin, sep=CSV_DELIMITER, encoding="utf-8-sig", dtype=str, keep_default_na=False)

    dataframe_csv.columns = dataframe_csv.columns.str.strip()
    entetes = dataframe_csv.columns.tolist()

    colonnes_manquantes = []
    for champ in CHAMPS_ATTENDUS:
        if champ not in entetes:
            colonnes_manquantes.append(champ)

    colonnes_atypiques = []
    for champ in entetes:
        if champ not in STRUCTURE_DB:
            colonnes_atypiques.append(champ)

    print(f"Colonnes CSV présentes : {len(entetes)} / {len(CHAMPS_ATTENDUS)}")
    print(f"Manquantes              : {colonnes_manquantes}")
    print(f"Inattendues             : {colonnes_atypiques}")

    # Conversion colonne par colonne avec pandas.

    for champ in entetes:
        if champ in STRUCTURE_DB:
            dataframe_csv[champ] = dataframe_csv[champ].apply(convert_valeurs_csv, champ=champ)

    documents = dataframe_csv.to_dict(orient="records")

    return [
        (f"ligne {num_ligne}", document)
        for num_ligne, document in enumerate(documents, start=2)
    ]


def refonte_csv(records, chemin):
    documents = []
    for _, doc in records:
        documents.append(doc)

    dataframe = pd.DataFrame(documents, columns=CHAMPS_ATTENDUS)

    refonte_date = []
    for champ in CHAMPS_ATTENDUS:
        if STRUCTURE_DB[champ] == "DATE":
            refonte_date.append(champ)

    for champ in refonte_date:
        dataframe[champ] = pd.to_datetime(dataframe[champ]).dt.strftime("%Y-%m-%d")

    dataframe.to_csv(chemin, sep=CSV_DELIMITER, encoding="utf-8-sig", index=False, )


# AUDIT

def audit_fonct(source):
    return {
        "source": source,
        "total": 0,
        "egal_15": 0,
        "inf_15": 0,
        "sup_15": 0,
        "presence": decompte_champs_vides(),
        "complet": decompte_champs_vides(),
        "type_ok": decompte_champs_vides(),
        "manquant": decompte_champs_vides(),
        "invalides_types": decompte_champs_vides(),
        "invalides_val": decompte_champs_vides(),
        "champs_inattendus": {},
        "exemples": {},
        "records_normalises": [],
        "a_normaliser": 0,
        "doublons_groupes": 0,
        "doublons_nombre": 0,
        "erreurs_bloquantes": 0,
    }


def ajout_exemple(audit, cat, champ, record_id, valeur):
    key = f"{cat} - {champ}"

    if key not in audit["exemples"]:
        audit["exemples"][key] = []

    if len(audit["exemples"][key]) < MAX_EXAMPLES:
        audit["exemples"][key].append((record_id, valeur))


def audit_records(records, source):
    #Contrôle chaque document.
    audit = audit_fonct(source)
    #Verification des attributs de chaque document (et correspondance avec la structure de base)
    for record_id, document in records:
        audit["total"] += 1
        champs = []
        for x in document:
            if x !="_id":
                champs.append(x)
        if len(champs) == len(CHAMPS_ATTENDUS):
            audit["egal_15"] += 1
        elif len(champs) < len(CHAMPS_ATTENDUS):
            audit["inf_15"] += 1
        else:
            audit["sup_15"] += 1
        # Décompte des champs hors structure de base
        for x in champs:
            if x not in STRUCTURE_DB:
                incrementer(audit["champs_inattendus"], x)

        doc_normalise = dict(document)
        mod = False
        # Décompte des documents avec champ(s) manquant(s)
        for x in CHAMPS_ATTENDUS:
            if x not in document:
                audit["manquant"][x] += 1
                continue

            audit["presence"][x] += 1
            value = document[x]

            if val_manquante(value):
                audit["manquant"][x] += 1
                continue

            audit["complet"][x] += 1
            type_attendu = STRUCTURE_DB[x]
            # Décompte des documents avec valeur associée au mauvais type
            if not validite_type(value, type_attendu):
                audit["invalides_types"][x] += 1
                ajout_exemple(
                    audit,
                    "TYPE",
                    x,
                    record_id,
                    f"{value!r} ({type(value).__name__}) attendu={type_attendu}",
                )
                continue

            audit["type_ok"][x] += 1

            if type_attendu == "VARCHAR":
                clean_value = refonte_val_string(x, value)
                doc_normalise[x] = clean_value
                mod = mod or clean_value != value
                value = clean_value

            if not validite_regles_restriction(x, value):
                audit["invalides_val"][x] += 1
                ajout_exemple(audit, "VALUE", x, record_id, value)

        if mod:
            audit["a_normaliser"] += 1

        audit["records_normalises"].append((record_id, doc_normalise))

    documents = []
    for _, document in audit["records_normalises"]:
        documents.append(document)

    if documents:
        dataframe = pd.DataFrame(documents)

        doublons = dataframe.duplicated(subset=CHAMPS_ID, keep="first")

        audit["doublons_nombre"] = int(doublons.sum())

        groupes = dataframe.groupby(CHAMPS_ID, dropna=False).size()

        audit["doublons_groupes"] = int((groupes > 1).sum())

    audit["erreurs_bloquantes"] = (
        sum(audit["champs_inattendus"].values())
        + sum(audit["invalides_types"].values())
        + sum(audit["invalides_val"].values())
    )

    return audit


def print_anomalies(title, values):
    anomalies = {champ: count for champ, count in values.items() if count > 0}

    print(f"\n{title}")
    if not anomalies:
        print("Aucune anomalie détectée.")
    else:
        dataframe = pd.DataFrame(
            [{"Champ": champ, "Nombre": count} for champ, count in anomalies.items()]
        )
        print(dataframe.to_string(index=False))


def recap_rapport_audit(audit):
    print("\n" + "=" * 80)
    print(f"RAPPORT D'INTEGRITE - {audit['source']}")
    print("=" * 80)
    print(f"Enregistrements              : {audit['total']}")
    print(f"15 champs                    : {audit['egal_15']}")
    print(f"Moins de 15 champs           : {audit['inf_15']}")
    print(f"Plus de 15 champs            : {audit['sup_15']}")

    lignes_rapport = []
    total_complet = 0

    for champ in CHAMPS_ATTENDUS:
        complet = audit["complet"][champ]
        total_complet += complet

        completude = 100 * complet / audit["total"] if audit["total"] else 0
        type_rate = 100 * audit["type_ok"][champ] / complet if complet else 0

        lignes_rapport.append({
            "Champ": champ,
            "Présent": audit["presence"][champ],
            "Complet": complet,
            "Complétude": f"{completude:.2f}%",
            "Type OK": f"{type_rate:.2f}%",
        })

    print("\nCOMPLETUDE / TYPES")
    print(pd.DataFrame(lignes_rapport).to_string(index=False))

    print_anomalies("VALEURS MANQUANTES", audit["manquant"])
    print_anomalies("TYPES INCORRECTS", audit["invalides_types"])
    print_anomalies("VALEURS HORS REGLES", audit["invalides_val"])
    print_anomalies("CHAMPS INATTENDUS", audit["champs_inattendus"])

    for title, exemples in audit["exemples"].items():
        print(f"\nExemples {title} :")
        for record_id, value in exemples:
            print(f"  {record_id} -> {value}")

    val_attendues = audit["total"] * len(CHAMPS_ATTENDUS)
    completude = 100 * total_complet / val_attendues if val_attendues else 0

    print("\nDOUBLONS")
    print(f"  Groupes de doublons        : {audit['doublons_groupes']}")
    print(f"  Doublons à supprimer       : {audit['doublons_nombre']}")

    print("\nSYNTHESE")
    print(f"  Complétude globale         : {completude:.2f} %")
    print(f"  Valeurs manquantes         : {sum(audit['manquant'].values())}")
    print(f"  Types incorrects           : {sum(audit['invalides_types'].values())}")
    print(f"  Valeurs hors règles        : {sum(audit['invalides_val'].values())}")
    print(f"  Documents à normaliser     : {audit['a_normaliser']}")
    print(f"  Doublons                   : {audit['doublons_nombre']}")
    print(f"  Migration bloquée          : {'OUI' if audit['erreurs_bloquantes'] else 'NON'}")


# NETTOYAGE CSV

def clean_records(audit):
    documents = []
    for _, document in audit["records_normalises"]:
        documents.append(document)

    if not documents:
        return []

    dataframe = pd.DataFrame(documents)

    dataframe = dataframe.drop_duplicates(subset=CHAMPS_ID, keep="first")

    enregistrement_clean = []

    for numero, document in enumerate(dataframe.to_dict(orient="records"),start=1):
        enregistrement_clean.append((f"enregistrement {numero}", document))
    return enregistrement_clean


# MONGODB

def mongodb_connexion():
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    collectiondb = client[DATABASE][COLLECTION]
    return client, collectiondb


def import_mongodb(collectiondb, records):
    nbre_doc_presents = collectiondb.count_documents({})

    if REQUIRE_EMPTY_COLLECTION and nbre_doc_presents > 0:
        raise RuntimeError(
            f"Collection non vide ({nbre_doc_presents} document(s)) : import interrompu."
        )

    documents = []
    for _, document in records:
        documents.append(document)

    if not documents:
        return 0

    resultat = collectiondb.insert_many(documents, ordered=False)
    return len(resultat.inserted_ids)


def charger_mongodb(collectiondb):
    documents = list(collectiondb.find({}))

    if not documents:
        print("Doublons MongoDB supprimés : 0")
        return []

    dataframe = pd.DataFrame(documents)

    for champ in CHAMPS_ATTENDUS:
        if STRUCTURE_DB[champ] == "DATE":
            dataframe[champ] = pd.to_datetime(dataframe[champ], errors="coerce")

    doublons = dataframe.duplicated(subset=CHAMPS_ID, keep="first")

    # Liste des id des doublons
    id_doublons = dataframe.loc[doublons,"_id"].tolist()

    # Suppression physique dans MongoDB
    if id_doublons:
        collectiondb.delete_many({
            "_id": {
                "$in": id_doublons
            }
        })

    dataframe = dataframe.loc[~doublons]

    records = []
    for document in dataframe.to_dict(orient="records"):
        records.append((document["_id"], document))

    print(f"Doublons MongoDB supprimés : {len(id_doublons)}" )

    return records

# CONTROLE POST MIGRATION

def comparaison_datasets(csv_records, mongo_records):
    documents_csv = []

    for _, document in csv_records:
        documents_csv.append(document)

    dataframe_csv = pd.DataFrame(documents_csv)

    dataframe_csv = dataframe_csv[CHAMPS_ATTENDUS]

    documents_mongodb = []

    for _, document in mongo_records:
        documents_mongodb.append(document)

    dataframe_mongodb = pd.DataFrame(documents_mongodb)

    dataframe_mongodb = dataframe_mongodb[CHAMPS_ATTENDUS]

    # Tri nécessaire pour l'utilisation de equals()
    dataframe_csv = dataframe_csv.sort_values(CHAMPS_ID).reset_index(drop=True)
    dataframe_mongodb = dataframe_mongodb.sort_values(CHAMPS_ID).reset_index(drop=True)

    concordance = dataframe_csv.equals(dataframe_mongodb)

    print("\nCONCORDANCE CSV -> MONGODB")
    print(f"  CSV nettoyé              : {len(dataframe_csv)}")
    print(f"  MongoDB                  : {len(dataframe_mongodb)}")
    print(f"  Concordance exacte       : {'OUI' if concordance else 'NON'}")


# MAIN

def main():
    # PHASE 1 : contrôler le CSV.
    print("\nPHASE 1 - AUDIT CSV")
    csv_records = csv_charge(CSV_INPUT)
    csv_audit = audit_records(csv_records, "CSV AVANT MIGRATION")
    recap_rapport_audit(csv_audit)

    version_clean = None

    # PHASE 2 : nettoyer le CSV et l'importer dans MongoDB.
    if APPLY_CHANGES:
        print("\nPHASE 2 - NETTOYAGE ET MIGRATION")

        if csv_audit["erreurs_bloquantes"]:
            raise RuntimeError(
                "Migration bloquée : corriger d'abord les anomalies de la phase 1."
            )

        version_clean = clean_records(csv_audit)
        refonte_csv(version_clean, CSV_OUTPUT)

        print(f"CSV nettoyé                : {CSV_OUTPUT}")
        print(f"Doublons supprimés         : {csv_audit['doublons_nombre']}")

        client, collection_db = mongodb_connexion()
        try:
            nbre_doc_inseres = import_mongodb(collection_db, version_clean)
            print(f"Documents MongoDB insérés  : {nbre_doc_inseres}")
 #Assure que le flux est arrêté même en cas de problème d'import
        finally:
            client.close()
    else:
        print("\nPHASE 2 - IGNORÉE (APPLY_CHANGES = False)")

    # PHASE 3 : contrôler MongoDB avec les mêmes règles.
    # Cette phase est toujours exécutée, même si la phase 2 est désactivée.
    print("\nPHASE 3 - AUDIT MONGODB")

    client, collection_db = mongodb_connexion()
    try:
        mongo_records = charger_mongodb(collection_db)
        mongo_audit = audit_records(mongo_records, "MONGODB APRES MIGRATION")
        recap_rapport_audit(mongo_audit)

        # La comparaison n'est possible que si un CSV nettoyé a été produit pendant la phase 2.
        if version_clean is not None:
            comparaison_datasets(version_clean, mongo_records)
    finally:
        print("\nPHASE 3 - Fermeture de la connexion MongoDB en cours.")
        client.close()


if __name__ == "__main__":
    main()
