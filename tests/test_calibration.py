import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from traceur.moteur.calibration import calibrer
from traceur.moteur.diff import comparer_instantanes
from traceur.moteur.instantane import prendre_instantane
from traceur.rapports.calibration import ecrire_bruit, lire_tables_bruit
from traceur.sources.sqlite import SourceSqlite

EXEMPLE = Path(__file__).parent.parent / "docs" / "formats" / "bruit.example.json"


@pytest.fixture
def logiciel(base: sqlite3.Connection) -> sqlite3.Connection:
    base.execute("CREATE TABLE SESSIONS (ID INTEGER PRIMARY KEY, DERNIER TEXT)")
    base.execute("CREATE TABLE JOURNAL (MSG TEXT)")
    base.execute("CREATE TABLE ECRITURES (ID INTEGER PRIMARY KEY)")
    base.execute("INSERT INTO SESSIONS VALUES (1, 't0')")
    return base


def _bruit(base: sqlite3.Connection, pauses: list[float]):  # type: ignore[no-untyped-def]
    def dormir(secondes: float) -> None:
        pauses.append(secondes)
        base.execute("UPDATE SESSIONS SET DERNIER='t1'")
        base.execute("INSERT INTO JOURNAL VALUES ('ping')")
        base.execute("INSERT INTO JOURNAL VALUES ('pong')")
    return dormir


def test_tables_qui_bougent_proposees(logiciel: sqlite3.Connection) -> None:
    pauses: list[float] = []
    c = calibrer(SourceSqlite(logiciel), dormir=_bruit(logiciel, pauses))
    assert pauses == [30.0]  # intervalle par défaut
    assert c.proposees == {"JOURNAL": "2 lignes ajoutées", "SESSIONS": "1 ligne modifiée"}
    assert sorted(c.tables_bruit) == ["JOURNAL", "SESSIONS"]  # par défaut : tout retenu


def test_intervalle_configurable_et_aucun_bruit(logiciel: sqlite3.Connection) -> None:
    pauses: list[float] = []
    c = calibrer(SourceSqlite(logiciel), 5, dormir=pauses.append)
    assert pauses == [5] and c.proposees == {} and c.tables_bruit == []


def test_validation_par_l_utilisateur(logiciel: sqlite3.Connection) -> None:
    c = calibrer(SourceSqlite(logiciel), dormir=_bruit(logiciel, []))
    c.valider(["SESSIONS"])
    assert c.tables_bruit == ["SESSIONS"]
    with pytest.raises(ValueError):
        c.valider(["ECRITURES"])


def test_tables_ignorees_exclues(logiciel: sqlite3.Connection) -> None:
    c = calibrer(SourceSqlite(logiciel), tables_ignorees=["journal"],
                 dormir=_bruit(logiciel, []))
    assert list(c.proposees) == ["SESSIONS"] and c.tables_ignorees == ["journal"]


def test_bruit_json_conforme_a_l_exemple_et_relu(
    logiciel: sqlite3.Connection, tmp_path: Path
) -> None:
    horloge = iter([datetime(2026, 10, 5, 9, 58, 0), datetime(2026, 10, 5, 9, 58, 31)])
    c = calibrer(SourceSqlite(logiciel), dormir=_bruit(logiciel, []), maintenant=horloge.__next__)
    c.valider(["SESSIONS"])
    chemin = ecrire_bruit(c, tmp_path / "calibration")
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    exemple = json.loads(EXEMPLE.read_text(encoding="utf-8"))
    assert set(donnees) == set(exemple)
    assert set(donnees["tables_bruit_proposees"][0]) == set(exemple["tables_bruit_proposees"][0])
    assert (donnees["debut"], donnees["fin"]) == ("2026-10-05T09:58:00", "2026-10-05T09:58:31")
    assert lire_tables_bruit(chemin) == ["SESSIONS"]


def test_tables_de_bruit_isolees_dans_le_diff(logiciel: sqlite3.Connection, tmp_path: Path) -> None:
    source = SourceSqlite(logiciel)
    c = calibrer(source, dormir=_bruit(logiciel, []))
    bruit = lire_tables_bruit(ecrire_bruit(c, tmp_path))
    avant = prendre_instantane(source)
    logiciel.execute("UPDATE SESSIONS SET DERNIER='t2'")
    logiciel.execute("INSERT INTO ECRITURES VALUES (1)")
    d = comparer_instantanes(avant, prendre_instantane(source), tables_bruit=bruit)
    assert [t.table for t in d.changements] == ["ECRITURES"]
    assert d.bruit == [{"table": "SESSIONS", "resume": "1 ligne modifiée (ignorée : table de bruit)"}]
