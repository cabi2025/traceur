import sqlite3
from datetime import datetime
from decimal import Decimal

import pytest

from traceur.moteur.diff import comparer_instantanes
from traceur.moteur.instantane import prendre_instantane
from traceur.moteur.profilage import cles_candidates_du_profil, profiler
from traceur.sources.sqlite import SourceSqlite


@pytest.fixture
def compta(base: sqlite3.Connection) -> sqlite3.Connection:
    """Base à relations connues : LIGNES -> FACTURES -> CLIENTS."""
    base.execute("CREATE TABLE CLIENTS (ID INTEGER PRIMARY KEY, NOM TEXT, CODE TEXT)")
    base.execute(
        "CREATE TABLE FACTURES (NUM INTEGER PRIMARY KEY, CLIENT_ID INTEGER, CODE_CLIENT TEXT, "
        "NUM_TEXTE TEXT, MONTANT DECIMAL(12,2), DATE_F DATE, STATUT TEXT, NOTE TEXT)"
    )
    base.execute("CREATE TABLE LIGNES (NUM_FACT INTEGER, RANG INTEGER, REF TEXT, QTE INTEGER)")
    base.executemany(
        "INSERT INTO CLIENTS VALUES (?,?,?)",
        [(101 + i, f"Client {101 + i}", f"C{101 + i}") for i in range(20)],
    )
    for i in range(200):
        client = 101 + i % 20
        base.execute(
            "INSERT INTO FACTURES VALUES (?,?,?,?,?,?,?,?)",
            (1001 + i, client, f"C{client}", str(1001 + i), f"{1001 + i}.37",
             f"2025-01-{1 + i % 10:02d}", "P" if i % 2 else "V", "x" if i % 4 else None),
        )
        for rang in (1, 2):
            base.execute("INSERT INTO LIGNES VALUES (?,?,?,?)",
                         (1001 + i, rang, f"R{i % 10:02d}", 1 + i % 5))
    return base


def _relations(profil):  # type: ignore[no-untyped-def]
    return {(r.table_source, r.colonne_source, r.table_cible, r.colonne_cible)
            for r in profil.relations}


def test_statistiques_par_colonne(compta: sqlite3.Connection) -> None:
    profil = profiler(SourceSqlite(compta))
    f = profil.table("FACTURES")
    assert f.nb_lignes == 200 and f.cle_primaire == ("NUM",)
    col = {c.nom: c for c in f.colonnes}
    assert col["NOTE"].nb_nuls == 50 and col["NOTE"].pct_nuls == Decimal("25.00")
    assert col["NUM"].types_observes == ("int",) and col["NUM"].type_declare == "INTEGER"
    assert col["MONTANT"].types_observes == ("Decimal",)
    assert (col["MONTANT"].min, col["MONTANT"].max) == (Decimal("1001.37"), Decimal("1200.37"))
    assert col["DATE_F"].nb_distincts == 10 and str(col["DATE_F"].min) == "2025-01-01"
    assert (col["STATUT"].min, col["STATUT"].max) == ("P", "V")
    assert col["NOTE"].types_observes == ("str",) and col["NOTE"].nb_distincts == 1


def test_cles_candidates(compta: sqlite3.Connection) -> None:
    profil = profiler(SourceSqlite(compta))
    cles_f = set(profil.table("FACTURES").cles_candidates)
    assert {("NUM",), ("NUM_TEXTE",), ("MONTANT",)} <= cles_f
    assert ("NOTE",) not in cles_f  # colonne avec des nuls
    assert ("CLIENT_ID",) not in cles_f  # doublons
    # LIGNES : aucune colonne seule, mais le couple (NUM_FACT, RANG) est unique
    assert profil.table("LIGNES").cles_candidates == (("NUM_FACT", "RANG"),)
    # pas de couple non minimal (contenant déjà une clé simple)
    assert all(len(c) == 1 or not set(c) & {x[0] for x in cles_f if len(x) == 1} for c in cles_f)


def test_relations_candidates_vraies_et_fausses(compta: sqlite3.Connection) -> None:
    profil = profiler(SourceSqlite(compta))
    assert _relations(profil) == {
        ("FACTURES", "CLIENT_ID", "CLIENTS", "ID"),
        ("FACTURES", "CODE_CLIENT", "CLIENTS", "CODE"),
        ("LIGNES", "NUM_FACT", "FACTURES", "NUM"),
    }
    rel = next(r for r in profil.relations if r.table_source == "LIGNES")
    assert rel.taux_inclusion == Decimal("1.0000") and rel.nb_valeurs == rel.nb_incluses == 400
    # NUM_TEXTE (texte) n'est pas rattaché à NUM (numérique) : types incompatibles
    assert ("FACTURES", "NUM_TEXTE", "FACTURES", "NUM") not in _relations(profil)


def test_seuil_de_99_pour_cent(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE P (ID INTEGER PRIMARY KEY)")
    base.executemany("INSERT INTO P VALUES (?)", [(i,) for i in range(1, 201)])
    for nom, orphelins in (("Q99", 1), ("Q98", 2)):
        base.execute(f"CREATE TABLE {nom} (P_ID INTEGER)")
        base.executemany(f"INSERT INTO {nom} VALUES (?)",
                         [(i,) for i in range(1, 101 - orphelins)]
                         + [(9000 + i,) for i in range(orphelins)])
    profil = profiler(SourceSqlite(base))
    rel = {r.table_source: r for r in profil.relations if r.table_cible == "P"}
    assert set(rel) == {"Q99"}  # 99 % : retenue (≥ 99) ; 98 % : écartée
    assert rel["Q99"].taux_inclusion == Decimal("0.9900")


def test_valeurs_numeriques_comparables_entre_types(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE K (ID DECIMAL(5,1) PRIMARY KEY)")
    base.executemany("INSERT INTO K VALUES (?)", [("10.0",), ("20.0",)])
    base.execute("CREATE TABLE R (K_ID INTEGER)")
    base.executemany("INSERT INTO R VALUES (?)", [(10,), (20,), (10,)])
    assert ("R", "K_ID", "K", "ID") in _relations(profiler(SourceSqlite(base)))


def test_petites_tables_sans_cle_ni_relation(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE UNE (A INTEGER)")
    base.execute("INSERT INTO UNE VALUES (1)")
    base.execute("CREATE TABLE VIDE (A INTEGER)")
    base.execute("CREATE TABLE R (A INTEGER)")
    base.executemany("INSERT INTO R VALUES (?)", [(1,), (1,)])
    profil = profiler(SourceSqlite(base))
    assert profil.table("UNE").cles_candidates == () and profil.table("VIDE").cles_candidates == ()
    assert not profil.relations
    vide = profil.table("VIDE").colonnes[0]
    assert vide.pct_nuls == Decimal("0.00") and vide.min is None and vide.nb_distincts == 0


def test_types_melanges_pas_de_min_max(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE M (V)")
    base.executemany("INSERT INTO M VALUES (?)", [(1,), ("a",), (None,)])
    c = profiler(SourceSqlite(base)).table("M").colonnes[0]
    assert c.types_observes == ("int", "str") and c.min is None and c.max is None


def test_tables_ignorees_et_version_jet(compta: sqlite3.Connection) -> None:
    profil = profiler(SourceSqlite(compta), ["lignes"], version_jet="Jet 4",
                      maintenant=lambda: datetime(2026, 10, 5, 9, 0, 0))
    assert [t.nom for t in profil.tables] == ["CLIENTS", "FACTURES"]
    d = profil.vers_dict()
    assert d["version_jet"] == "Jet 4" and d["date"] == "2026-10-05T09:00:00"
    assert d["format_version"] == "1.0"


def test_cles_candidates_pour_le_diff_sans_pk(compta: sqlite3.Connection) -> None:
    source = SourceSqlite(compta)
    profil = profiler(source)
    cles = cles_candidates_du_profil(profil)
    assert cles == {"LIGNES": ("NUM_FACT", "RANG")}  # CLIENTS et FACTURES ont une PK
    avant = prendre_instantane(source)
    compta.execute("UPDATE LIGNES SET QTE=99 WHERE NUM_FACT=1005 AND RANG=2")
    (t,) = comparer_instantanes(avant, prendre_instantane(source), cles).changements
    assert t.type_cle == "candidate" and t.colonnes_cle == ("NUM_FACT", "RANG")
    assert t.updates[0].cle == {"NUM_FACT": 1005, "RANG": 2}
    assert [c.colonne for c in t.updates[0].champs] == ["QTE"]
    # sans clé candidate : repli sur les multiensembles (update probable)
    (t2,) = comparer_instantanes(avant, prendre_instantane(source)).changements
    assert t2.type_cle == "aucune" and len(t2.updates_probables) == 1


def test_cle_candidate_preferee_la_plus_courte(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE T (A INTEGER, B INTEGER, C INTEGER)")
    base.executemany("INSERT INTO T VALUES (?,?,?)", [(1, 7, 1), (2, 7, 1), (3, 8, 2)])
    assert cles_candidates_du_profil(profiler(SourceSqlite(base))) == {"T": ("A",)}
