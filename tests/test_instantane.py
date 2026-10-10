import sqlite3
from decimal import Decimal

from traceur.moteur.instantane import prendre_instantane
from traceur.sources.sqlite import SourceSqlite


def test_photo_schema_comptes_et_types(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE A (ID INTEGER PRIMARY KEY, M DECIMAL(10,2), D DATE, T TEXT)")
    base.execute("INSERT INTO A VALUES (1, '1234.56', '2025-01-15', 'x')")
    base.execute("CREATE TABLE B (X TEXT)")
    photo = prendre_instantane(source)
    a = photo.tables["A"]
    assert a.nb_lignes == 1 and photo.tables["B"].nb_lignes == 0
    assert a.schema.cle_primaire == ("ID",) and photo.tables["B"].schema.cle_primaire == ()
    assert a.lignes[0].valeurs[1] == Decimal("1234.56")
    assert photo.nb_lignes == 1


def test_tables_ignorees_insensible_a_la_casse(
    base: sqlite3.Connection, source: SourceSqlite
) -> None:
    base.execute("CREATE TABLE SESSIONS (X)")
    base.execute("CREATE TABLE A (X)")
    assert set(prendre_instantane(source, ["sessions"]).tables) == {"A"}


def test_empreinte_independante_de_l_ordre_des_lignes(
    base: sqlite3.Connection, source: SourceSqlite
) -> None:
    base.execute("CREATE TABLE A (X)")
    base.executemany("INSERT INTO A VALUES (?)", [(1,), (2,), (3,)])
    e1 = prendre_instantane(source).tables["A"].empreinte
    base.execute("DELETE FROM A")
    base.executemany("INSERT INTO A VALUES (?)", [(3,), (1,), (2,)])
    assert prendre_instantane(source).tables["A"].empreinte == e1


def test_resume_affiche_le_temps(base: sqlite3.Connection, source: SourceSqlite) -> None:
    base.execute("CREATE TABLE A (X)")
    horloge = iter([0.0, 0.0, 1.5, 2.0]).__next__
    resume = prendre_instantane(source, horloge=horloge).resume()
    assert "2.00 s" in resume and "A : 0 lignes, 1.50 s" in resume
