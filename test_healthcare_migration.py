import os
#CONFIG du script
os.environ["CSV_INPUT"] = "test_input.csv"
os.environ["CSV_OUTPUT"] = "test_output.csv"
os.environ["CSV_DELIMITER"] = ","
os.environ["CSV_DUPLICATES"] ="test_doublons_csv.csv"
os.environ["MONGODB_DUPLICATES"] = "test_doublons_mongodb.csv"


os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
os.environ["DATABASE_NAME"] = "Healthcare"
os.environ["COLLECTION_NAME"] = "Patients"

os.environ["APPLY_CHANGES"] = "false"
os.environ["MAX_EXAMPLES"] = "10"
os.environ["REQUIRE_EMPTY_COLLECTION"] = "false"

from datetime import datetime

import pandas as pd
import pytest

import healthcare_migration as scripth

def valid_patient(**changes):
    patient = {
        "Name": "John Doe",
        "Age": 42,
        "Gender": "Male",
        "Blood Type": "O+",
        "Medical Condition": "Diabetes",
        "Date of Admission": "2026-08-01", 
        "Doctor": "Dr. Sam Smith",
        "Hospital": "General de Gaulle Hospital",
        "Insurance Provider": "Malakoff",
        "Billing Amount": 1250.51234,
        "Room Number": 101,
        "Admission Type": "URGENT",
        "Discharge Date": "2026-08-05",
        "Medication": "Aspirine",
        "Test Results": "NORMAL",
    }
    patient.update(changes)
    return patient


def test_valeur_manquante():
    assert scripth.val_manquante(None)
    assert scripth.val_manquante("")
    assert scripth.val_manquante("   ")
    assert scripth.val_manquante(pd.NA)
    assert not scripth.val_manquante("JOHN")


def test_refonte_texte():
    assert scripth.refonte_val_string("Name", " Dr. John Doe ") == "JOHN DOE"
    assert scripth.refonte_val_string("Doctor", "Mrs. Smith") == "SMITH"
    assert scripth.refonte_val_string("Hospital", " General Hospital ") == "GENERAL HOSPITAL"


def test_convert_csv():
    assert scripth.convert_valeurs_csv("42", "Age") == 42
    assert scripth.convert_valeurs_csv("abc", "Age") == "abc"
    assert scripth.convert_valeurs_csv("1250.499", "Billing Amount") == 1250.50
    assert scripth.convert_valeurs_csv("2025-10-01", "Date of Admission") == pd.Timestamp("2025-10-01")
    assert pd.isna(scripth.convert_valeurs_csv("ZZZZ", "Date of Admission"))#Test pour renvoyer valeur NaT en cas de donnée invalide

def test_regles_metier():
    assert scripth.validite_regles_restriction("Age", 42)
    assert not scripth.validite_regles_restriction("Age", 200)
    assert not scripth.validite_regles_restriction("Room Number", -200)
    assert scripth.validite_regles_restriction("Gender", "MALE")
    assert not scripth.validite_regles_restriction("Gender", "bleu")


def test_csv_charge(tmp_path):
    dataframe = pd.DataFrame([valid_patient()])
    chemin_csv = tmp_path / "patients.csv"
    dataframe.to_csv(chemin_csv, index=False)

    records = scripth.csv_charge(chemin_csv)

    assert len(records) == 1
    _, patient = records[0]
    assert patient["Age"] == 42
    assert patient["Billing Amount"] == 1250.51
    assert isinstance(patient["Date of Admission"], datetime)


def test_audit_doublons():
    records = [
        ("ligne 2", valid_patient()),
        ("ligne 3", valid_patient()),
    ]

    audit = scripth.audit_records(records, "TEST")

    assert audit["doublons_groupes"] == 1
    assert audit["doublons_nombre"] == 1


def test_clean_doublons():
    records = [
        ("ligne 2", valid_patient()),
        ("ligne 3", valid_patient(Name="JOHN DOE")),
    ]
    audit = scripth.audit_records(records, "TEST")

    cleaned = scripth.clean_records(audit)

    assert len(cleaned) == 1


def test_refonte_csv(tmp_path):
    output = tmp_path / "clean.csv"
    records = [("ligne 2", valid_patient())]

    scripth.refonte_csv(records, output)
    result = pd.read_csv(output, dtype=str, keep_default_na=False)

    assert list(result.columns) == scripth.CHAMPS_ATTENDUS
    assert result.loc[0, "Date of Admission"] == "2026-08-01"
    assert result.loc[0, "Discharge Date"] == "2026-08-05"


def test_comparaison_datasets_concordance(capsys):
    csv_records = [("ligne 2", valid_patient())]
    mongo_patient = valid_patient()
    mongo_patient["_id"] = "mongo-1"
    mongo_records = [("mongo-1", mongo_patient)]

    scripth.comparaison_datasets(csv_records, mongo_records)
    output = capsys.readouterr().out

    assert "Concordance exacte       : OUI" in output
