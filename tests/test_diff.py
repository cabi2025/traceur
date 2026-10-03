import sqlite3
from typing import Sequence

from traceur.moteur.diff import ResultatDiff, comparer_instantanes
from traceur.moteur.instantane import prendre_instantane
from traceur.sources.sqlite import SourceSqlite


def _diff(
    base: sqlite3.Connection,
    source: SourceSqlite,
    modifier: Sequence[str],
    cles: dict[str, Sequence[str]] | None = None,
) -> ResultatDiff:
    avant = prendre_instantane(source)
    for requete in modifier:
        base.execute(requete)
    return comparer_instantanes(avant, prendre_instantane(source), cles)


def test_cle_primaire_insert_update_delete(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE E (ID INTEGER PRIMARY KEY, J TEXT, M DECIMAL(10,2))")
    base.executemany("INSERT INTO E VALUES (?,?,?)", [(1, "ACH", "10.00"), (2, "VTE", "20.00")])
    d = _diff(base, source, [
        "INSERT INTO E VALUES (3, 'ACH', '1234.56')",
        "UPDATE E SET M='25.50' WHERE ID=1",
        "DELETE FROM E WHERE ID=2",
    ])
    (t,) = d.changements
    assert (t.type_cle, t.colonnes_cle) == ("primaire", ("ID",))
    assert [i.cle for i in t.inserts] == [{"ID": 3}]
    assert [(u.cle, [(c.colonne, str(c.avant), str(c.apres)) for c in u.champs])
            for u in t.updates] == [({"ID": 1}, [("M", "10", "25.5")])]
    assert [x.cle for x in t.deletes] == [{"ID": 2}]


def test_table_inchangee_ignoree(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE A (X)")
    base.execute("CREATE TABLE B (X)")
    d = _diff(base, source, ["INSERT INTO B VALUES (1)"])
    assert [t.table for t in d.changements] == ["B"]


def test_espace_final_detecte_comme_update(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE E (ID INTEGER PRIMARY KEY, L TEXT)")
    base.execute("INSERT INTO E VALUES (1, 'TEST')")
    (t,) = _diff(base, source, ["UPDATE E SET L='TEST ' WHERE ID=1"]).changements
    assert t.updates[0].champs[0].apres == "TEST "


def test_nuls_et_dates(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE E (ID INTEGER PRIMARY KEY, D DATETIME, N TEXT)")
    base.execute("INSERT INTO E VALUES (1, '2025-01-15T00:00:00', NULL)")
    (t,) = _diff(base, source, [
        "UPDATE E SET D='2025-01-15T10:30:00', N='' WHERE ID=1"]).changements
    assert {c.colonne for c in t.updates[0].champs} == {"D", "N"}
    nul = next(c for c in t.updates[0].champs if c.colonne == "N")
    assert nul.avant is None and nul.apres == ""


def test_decimaux_exacts(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE E (ID INTEGER PRIMARY KEY, M DECIMAL(10,2))")
    base.execute("INSERT INTO E VALUES (1, '1234.56')")
    assert not _diff(base, source, ["UPDATE E SET M='1234.56'"]).changements
    (t,) = _diff(base, source, ["UPDATE E SET M='1234.57'"]).changements
    assert str(t.updates[0].champs[0].apres) == "1234.57"


def test_sans_cle_doublons_comptes(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE L (C TEXT, M DECIMAL(10,2))")
    base.executemany("INSERT INTO L VALUES (?,?)", [("A", "1.00"), ("A", "1.00")])
    d = _diff(base, source, ["INSERT INTO L VALUES ('A', '1.00')"])
    (t,) = d.changements
    assert t.type_cle == "aucune" and len(t.lignes_ajoutees) == 1 and not t.lignes_supprimees
    d = _diff(base, source, ["DELETE FROM L WHERE rowid = (SELECT MIN(rowid) FROM L)"])
    assert len(d.changements[0].lignes_supprimees) == 1


def test_sans_cle_ajout_et_suppression(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE L (C TEXT, M TEXT, K TEXT)")
    base.executemany("INSERT INTO L VALUES (?,?,?)", [("A", "1", "x"), ("B", "2", "y")])
    (t,) = _diff(base, source, [
        "DELETE FROM L WHERE C='A'", "INSERT INTO L VALUES ('Z', '9', 'w')"]).changements
    assert t.lignes_ajoutees == [{"C": "Z", "M": "9", "K": "w"}]
    assert t.lignes_supprimees == [{"C": "A", "M": "1", "K": "x"}]
    assert not t.updates_probables  # 3 champs différents : pas un update probable


def test_update_probable(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE L (C TEXT, M TEXT, K TEXT)")
    base.executemany("INSERT INTO L VALUES (?,?,?)", [("A", "1", "x"), ("B", "2", "y")])
    (t,) = _diff(base, source, ["UPDATE L SET M='7' WHERE C='A'"]).changements
    assert not t.lignes_ajoutees and not t.lignes_supprimees
    (u,) = t.updates_probables
    assert [(c.colonne, c.avant, c.apres) for c in u.champs] == [("M", "1", "7")]


def test_cle_candidate_du_profilage(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE C (CODE TEXT, DERNIER INTEGER)")
    base.execute("INSERT INTO C VALUES ('ACH', 41)")
    (t,) = _diff(base, source, ["UPDATE C SET DERNIER=42"], {"C": ["CODE"]}).changements
    assert (t.type_cle, t.colonnes_cle) == ("candidate", ("CODE",))
    assert t.updates[0].cle == {"CODE": "ACH"}


def test_cle_candidate_non_unique_repli_multiensembles(
    base: sqlite3.Connection, source: SourceSqlite
) -> None:
    base.execute("CREATE TABLE C (CODE TEXT, V INTEGER)")
    base.execute("INSERT INTO C VALUES ('A', 1)")
    (t,) = _diff(base, source, ["INSERT INTO C VALUES ('A', 2)"], {"C": ["CODE"]}).changements
    assert t.type_cle == "aucune" and len(t.lignes_ajoutees) == 1


def test_schema_modifie(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE A (X TEXT)")
    base.execute("CREATE TABLE B (X TEXT)")
    base.execute("CREATE TABLE G (X TEXT)")
    d = _diff(base, source, ["ALTER TABLE A ADD COLUMN Y TEXT", "INSERT INTO A VALUES ('1','2')",
                             "DROP TABLE G", "CREATE TABLE N (X TEXT)"])
    natures = {s.table: s.nature for s in d.schema_modifie}
    assert natures == {"A": "colonnes_modifiees", "N": "table_ajoutee", "G": "table_supprimee"}
    assert not d.changements  # TODO(AMB-012) : pas de diff de lignes


def test_tables_ignorees_absentes_du_diff(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE S (X)")
    avant = prendre_instantane(source, ["S"])
    base.execute("INSERT INTO S VALUES (1)")
    assert not comparer_instantanes(avant, prendre_instantane(source, ["S"])).changements
