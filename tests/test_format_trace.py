"""Le dict produit par le moteur doit avoir la forme de docs/formats/trace.example.json."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from traceur.moteur.diff import comparer_instantanes
from traceur.moteur.instantane import prendre_instantane
from traceur.sources.sqlite import SourceSqlite

EXEMPLE = Path(__file__).parent.parent / "docs" / "formats" / "trace.example.json"


def _contient_flottant(x: Any) -> bool:
    if isinstance(x, float):
        return True
    if isinstance(x, dict):
        return any(_contient_flottant(v) for v in x.values())
    if isinstance(x, list):
        return any(_contient_flottant(v) for v in x)
    return False


def test_forme_conforme_a_l_exemple(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE ECRITURES (NUM_ECR INTEGER PRIMARY KEY, DATE_ECR DATETIME)")
    base.execute("CREATE TABLE LIGNES (NUM_ECR INTEGER, DEBIT DECIMAL(12,2))")
    base.execute("CREATE TABLE COMPTEURS (CODE_JOURNAL TEXT, DERNIER_NUM INTEGER)")
    base.execute("INSERT INTO COMPTEURS VALUES ('ACH', 41)")
    avant = prendre_instantane(source)
    base.execute("INSERT INTO ECRITURES VALUES (18342, '2025-01-15T00:00:00')")
    base.execute("INSERT INTO LIGNES VALUES (18342, '1234.56')")
    base.execute("UPDATE COMPTEURS SET DERNIER_NUM=42")
    resultat = comparer_instantanes(
        avant, prendre_instantane(source), {"COMPTEURS": ["CODE_JOURNAL"]}
    ).vers_dict()
    json.dumps(resultat)  # sérialisable
    assert not _contient_flottant(resultat)

    exemple = {c["table"]: c for c in json.loads(EXEMPLE.read_text("utf-8"))["changements"]}
    ours = {c["table"]: c for c in resultat["changements"]}
    assert set(ours) == set(exemple)
    for table, attendu in exemple.items():
        assert set(ours[table]) == set(attendu), table
        assert ours[table]["cle_utilisee"]["type"] == attendu["cle_utilisee"]["type"]
    ins = ours["ECRITURES"]["inserts"][0]
    assert set(ins) == {"cle", "valeurs"}
    assert ins["valeurs"]["DATE_ECR"] == "2025-01-15T00:00:00"
    assert ours["LIGNES"]["lignes_ajoutees"][0]["valeurs"]["DEBIT"] == "1234.56"
    assert ours["COMPTEURS"]["updates"][0]["champs"][0] == {
        "colonne": "DERNIER_NUM", "avant": 41, "apres": 42}
