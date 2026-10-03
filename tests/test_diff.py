import sqlite3
from typing import Sequence

import pytest

import traceur.moteur.diff as diff_module
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


def test_table_ajoutee_avec_pk_lignes_en_inserts(
    base: sqlite3.Connection, source: SourceSqlite
) -> None:
    d = _diff(base, source, [
        "CREATE TABLE N (ID INTEGER PRIMARY KEY, V TEXT)",
        "INSERT INTO N VALUES (1,'a'), (2,'b')"])
    assert [(s.table, s.nature) for s in d.schema_modifie] == [("N", "table_ajoutee")]
    (t,) = d.changements
    assert t.type_cle == "primaire" and [i.cle for i in t.inserts] == [{"ID": 1}, {"ID": 2}]
    assert not t.deletes and not d.avertissements


def test_table_ajoutee_sans_cle_lignes_ajoutees(
    base: sqlite3.Connection, source: SourceSqlite
) -> None:
    d = _diff(base, source, ["CREATE TABLE N (V TEXT)", "INSERT INTO N VALUES ('a')"])
    (t,) = d.changements
    assert t.type_cle == "aucune" and t.lignes_ajoutees == [{"V": "a"}]


def test_table_supprimee_lignes_en_deletes(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE G (ID INTEGER PRIMARY KEY, V TEXT)")
    base.execute("INSERT INTO G VALUES (7,'x')")
    d = _diff(base, source, ["DROP TABLE G"])
    assert [(s.table, s.nature) for s in d.schema_modifie] == [("G", "table_supprimee")]
    (t,) = d.changements
    assert [x.cle for x in t.deletes] == [{"ID": 7}] and not t.inserts


def test_table_ajoutee_ou_supprimee_vide_signalee_sans_ligne(
    base: sqlite3.Connection, source: SourceSqlite
) -> None:
    base.execute("CREATE TABLE G (X)")
    d = _diff(base, source, ["DROP TABLE G", "CREATE TABLE N (X)"])
    assert {s.table: s.nature for s in d.schema_modifie} == {
        "N": "table_ajoutee", "G": "table_supprimee"}
    assert not d.changements


def test_schema_modifie_diff_sur_colonnes_communes(
    base: sqlite3.Connection, source: SourceSqlite
) -> None:
    base.execute("CREATE TABLE A (ID INTEGER PRIMARY KEY, X TEXT, VIEUX TEXT)")
    base.executemany("INSERT INTO A VALUES (?,?,?)", [(1, "a", "v"), (2, "b", "v")])
    d = _diff(base, source, [
        "ALTER TABLE A ADD COLUMN NEUF TEXT",
        "ALTER TABLE A DROP COLUMN VIEUX",
        "UPDATE A SET X='z' WHERE ID=1",
        "INSERT INTO A VALUES (3, 'c', 'n')"])
    assert [(s.table, s.nature) for s in d.schema_modifie] == [("A", "colonnes_modifiees")]
    (t,) = d.changements
    assert t.type_cle == "primaire"
    assert [(u.cle, [c.colonne for c in u.champs]) for u in t.updates] == [({"ID": 1}, ["X"])]
    assert t.inserts[0].valeurs == {"ID": 3, "X": "c"}  # colonne NEUF hors comparaison
    (w,) = d.avertissements
    assert w.code == "schema_modifie_colonnes_communes" and w.table == "A"
    assert w.details["colonnes_ajoutees"] == ["NEUF"]
    assert w.details["colonnes_supprimees"] == ["VIEUX"]
    assert "NEUF" in w.message and "VIEUX" in w.message


def test_schema_modifie_sans_difference_de_lignes(
    base: sqlite3.Connection, source: SourceSqlite
) -> None:
    base.execute("CREATE TABLE A (X TEXT)")
    base.execute("INSERT INTO A VALUES ('a')")
    d = _diff(base, source, ["ALTER TABLE A ADD COLUMN Y TEXT"])
    assert not d.changements and len(d.schema_modifie) == 1 and len(d.avertissements) == 1


def test_plafond_d_appariement_produit_un_avertissement(
    base: sqlite3.Connection, source: SourceSqlite, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(diff_module, "LIMITE_APPARIEMENT", 3)
    base.execute("CREATE TABLE L (C TEXT, M TEXT)")
    base.executemany("INSERT INTO L VALUES (?,?)", [(f"c{i}", "1") for i in range(3)])
    d = _diff(base, source, [
        "UPDATE L SET M='2'", "INSERT INTO L VALUES ('n1','9')", "INSERT INTO L VALUES ('n2','9')"])
    (t,) = d.changements
    assert not t.updates_probables and len(t.lignes_ajoutees) == 5 and len(t.lignes_supprimees) == 3
    (w,) = d.avertissements
    assert (w.table, w.code) == ("L", "appariement_plafond_atteint")
    assert w.details == {"lignes_ajoutees_non_appariees": 5, "lignes_supprimees_non_appariees": 3}
    assert "L" in w.message and "5" in w.message and "3" in w.message


def test_sous_le_plafond_aucun_avertissement(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE L (C TEXT, M TEXT)")
    base.execute("INSERT INTO L VALUES ('a','1')")
    d = _diff(base, source, ["UPDATE L SET M='2'"])
    assert d.changements[0].updates_probables and not d.avertissements


def test_tables_de_bruit_rapportees_a_part(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE SESSIONS (ID INTEGER PRIMARY KEY, V TEXT)")
    base.execute("CREATE TABLE A (X)")
    base.execute("INSERT INTO SESSIONS VALUES (1,'a')")
    avant = prendre_instantane(source)
    base.execute("UPDATE SESSIONS SET V='b'")
    base.execute("INSERT INTO A VALUES (1)")
    d = comparer_instantanes(avant, prendre_instantane(source), tables_bruit=["sessions"])
    assert [t.table for t in d.changements] == ["A"]
    assert d.bruit == [{"table": "SESSIONS",
                        "resume": "1 ligne modifiée (ignorée : table de bruit)"}]
    assert d.vers_dict()["bruit"] == d.bruit


def test_resume_bruit_pluriel(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE S (ID INTEGER PRIMARY KEY)")
    avant = prendre_instantane(source)
    base.execute("INSERT INTO S VALUES (1),(2)")
    d = comparer_instantanes(avant, prendre_instantane(source), tables_bruit=["S"])
    assert d.bruit[0]["resume"] == "2 lignes ajoutées (ignorée : table de bruit)"


def test_tables_ignorees_absentes_du_diff(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE S (X)")
    avant = prendre_instantane(source, ["S"])
    base.execute("INSERT INTO S VALUES (1)")
    assert not comparer_instantanes(avant, prendre_instantane(source, ["S"])).changements
