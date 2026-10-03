"""Parties des outils Windows testables sous Linux : données, ordre des appels ADO, simulateur."""

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from fake_pyodbc import FauxPyodbc
from outils import generer_mdb_test as gen
from outils import simuler_logiciel as sim
from traceur.moteur.profilage import cles_candidates_du_profil, profiler
from traceur.sources.sqlite import SourceSqlite


def _sqlite_synthetique(n: int = 60) -> sqlite3.Connection:
    base = sqlite3.connect(":memory:")
    for nom, ddl in gen.TABLES.items():
        base.execute(ddl.replace("TEXT(50)", "TEXT").replace("TEXT(10)", "TEXT").replace("TEXT(1)", "TEXT")
                     .replace("TEXT(3)", "TEXT").replace("LONG", "INTEGER").replace("MEMO", "TEXT"))
    for nom, lignes in gen.generer_donnees(n).items():
        marques = ",".join("?" * len(gen.COLONNES[nom]))
        base.executemany(f"INSERT INTO {nom} VALUES ({marques})",
                         [tuple(str(v) if isinstance(v, Decimal) else v.isoformat() if isinstance(v, datetime) else v
                                for v in ligne) for ligne in lignes])
    return base


# --- données synthétiques --------------------------------------------------------------------

def test_effectifs_documentes() -> None:
    d = gen.generer_donnees(1000)
    assert {k: len(v) for k, v in d.items()} == {
        "CLIENTS": 50, "FACTURES": 1000, "LIGNES": 2000, "COMPTEURS": 3, "SESSIONS": 3}
    assert sum(len(v) for v in d.values()) == 3056
    assert gen.generer_donnees(10)["CLIENTS"].__len__() == 20  # minimum 20 clients


def test_donnees_deterministes_et_colonnes_coherentes() -> None:
    assert gen.generer_donnees(50) == gen.generer_donnees(50)
    for table, lignes in gen.generer_donnees(50).items():
        assert all(len(ligne) == len(gen.COLONNES[table]) for ligne in lignes)
        assert f"CREATE TABLE [{table}] (" in gen.TABLES[table]


def test_le_profil_retrouve_les_cles_et_relations_prevues() -> None:
    profil = profiler(SourceSqlite(_sqlite_synthetique(200)))
    assert profil.table("FACTURES").cle_primaire == ("NUM",)
    assert cles_candidates_du_profil(profil) == {
        "LIGNES": ("NUM_FACT", "RANG"), "COMPTEURS": ("CODE_JOURNAL",)}
    relations = {(r.table_source, r.colonne_source, r.table_cible, r.colonne_cible)
                 for r in profil.relations if r.confiance == "normale"}
    assert ("FACTURES", "CLIENT_ID", "CLIENTS", "ID") in relations
    assert ("LIGNES", "NUM_FACT", "FACTURES", "NUM") in relations


def test_montants_exacts_sans_ecart_de_flottant() -> None:
    assert all(isinstance(f[2], Decimal) and f[2] == f[2].quantize(Decimal("0.01"))
               for f in gen.generer_donnees(100)["FACTURES"])
    assert gen.generer_donnees(5)["CLIENTS"][0][1] == "Société Générale"


# --- séquence d'appels ADOX/ADO (faux COM) ---------------------------------------------------

class _Champ:
    def __init__(self, jeu: "_Jeu", position: int) -> None:
        self.jeu, self.position = jeu, position

    @property
    def Value(self) -> Any:  # noqa: N802
        return None

    @Value.setter
    def Value(self, v: Any) -> None:  # noqa: N802
        self.jeu.ligne[self.position] = v


class _Champs:
    def __init__(self, jeu: "_Jeu") -> None:
        self.jeu = jeu

    def Item(self, position: int) -> _Champ:  # noqa: N802
        return _Champ(self.jeu, position)


class _Jeu:
    def __init__(self, journal: list[tuple[str, Any]], donnees: dict[str, list[dict[int, Any]]]) -> None:
        self.journal, self.donnees, self.ligne, self.table = journal, donnees, {}, ""

    def Open(self, table: str, *args: Any) -> None:  # noqa: N802
        self.table = table
        self.journal.append(("recordset", (table, args)))

    def AddNew(self) -> None:  # noqa: N802
        self.ligne = {}

    @property
    def Fields(self) -> "_Champs":  # noqa: N802
        return _Champs(self)

    def Update(self) -> None:  # noqa: N802
        self.donnees.setdefault(self.table, []).append(self.ligne)

    def Close(self) -> None:  # noqa: N802
        pass


class _Connexion:
    def __init__(self, journal: list[tuple[str, Any]]) -> None:
        self.journal = journal

    def Open(self, chaine: str) -> None:  # noqa: N802
        self.journal.append(("open", chaine))

    def Execute(self, sql: str) -> None:  # noqa: N802
        self.journal.append(("execute", sql))

    def BeginTrans(self) -> None:  # noqa: N802
        self.journal.append(("begin", None))

    def CommitTrans(self) -> None:  # noqa: N802
        self.journal.append(("commit", None))

    def Close(self) -> None:  # noqa: N802
        self.journal.append(("close", None))


class _Catalogue:
    def __init__(self, journal: list[tuple[str, Any]]) -> None:
        self.journal = journal
        self.ActiveConnection = _Connexion(journal)

    def Create(self, chaine: str) -> None:  # noqa: N802
        self.journal.append(("create", chaine))


def _faux_com() -> tuple[Any, list[tuple[str, Any]], dict[str, list[dict[int, Any]]]]:
    journal: list[tuple[str, Any]] = []
    donnees: dict[str, list[dict[int, Any]]] = {}

    def dispatch(nom: str) -> Any:
        return {"ADOX.Catalog": lambda: _Catalogue(journal), "ADODB.Connection": lambda: _Connexion(journal),
                "ADODB.Recordset": lambda: _Jeu(journal, donnees)}[nom]()

    return dispatch, journal, donnees


def test_creation_jet4_tables_puis_lignes(tmp_path: Path) -> None:
    dispatch, journal, donnees = _faux_com()
    effectifs = gen.creer_base(tmp_path / "s.mdb", 30, dispatch=dispatch, progression=lambda t: None)
    creation = next(v for k, v in journal if k == "create")
    assert "Engine Type=5" in creation and "Microsoft.Jet.OLEDB.4.0" in creation
    ddl = [v for k, v in journal if k == "execute"]
    assert ddl == list(gen.TABLES.values())
    assert effectifs == {"CLIENTS": 20, "FACTURES": 30, "LIGNES": 60, "COMPTEURS": 3, "SESSIONS": 3}
    assert {t: len(v) for t, v in donnees.items()} == effectifs
    assert journal.count(("begin", None)) == journal.count(("commit", None)) == 5
    # montant écrit en flottant à 2 décimales, nul non écrit (champ laissé vide)
    assert donnees["FACTURES"][0][2] == 100.0 and 5 not in donnees["FACTURES"][0]  # commentaire nul (i=0)


def test_creation_jet3_et_mot_de_passe(tmp_path: Path) -> None:
    dispatch, journal, _ = _faux_com()
    gen.creer_base(tmp_path / "s.mdb", 5, jet3=True, mot_de_passe="S3cr3t]!", dispatch=dispatch,
                   progression=lambda t: None)
    assert "Engine Type=4" in next(v for k, v in journal if k == "create")
    assert ("execute", "ALTER DATABASE PASSWORD [S3cr3t]]!] Null") in journal
    assert any(k == "open" and "Share Exclusive" in v for k, v in journal)


def test_refuse_d_ecraser_une_base_existante(tmp_path: Path) -> None:
    (tmp_path / "s.mdb").write_bytes(b"x")
    with pytest.raises(FileExistsError, match="existe déjà"):
        gen.creer_base(tmp_path / "s.mdb", 5, dispatch=_faux_com()[0])


# --- script tiers ----------------------------------------------------------------------------

def test_simulateur_modifie_la_base_comme_attendu() -> None:
    base = _sqlite_synthetique(60)
    faux = FauxPyodbc(base, pilotes=["Microsoft Access Driver (*.mdb)"])
    resultat = sim.simuler(r"C:\t.mdb", "S3cr3t!", faux)
    assert resultat["facture"] == 1061 and resultat["montant"] == "1234.56"
    (connexion,) = faux.connexions
    assert "ReadOnly=0" in connexion.chaine and "PWD={S3cr3t!}" in connexion.chaine and connexion.readonly is False
    assert base.execute("SELECT COUNT(*) FROM FACTURES WHERE NUM=1061").fetchone() == (1,)
    assert base.execute("SELECT COUNT(*) FROM LIGNES WHERE NUM_FACT=1061").fetchone() == (2,)
    assert base.execute("SELECT DERNIER_NUM FROM COMPTEURS WHERE CODE_JOURNAL='ACH'").fetchone() == (41,)
    assert base.execute("SELECT COUNT(*) FROM CLIENTS WHERE ID=?", (resultat["client_supprime"],)).fetchone() == (0,)
    json.dumps(resultat)


def test_simulateur_sans_pilote() -> None:
    with pytest.raises(RuntimeError, match="32 bits"):
        sim.simuler(r"C:\t.mdb", None, FauxPyodbc(sqlite3.connect(":memory:"), pilotes=[]))


# Mots réservés ou noms de types Jet : jamais comme identifiant non protégé (régression J4, Windows).
MOTS_JET = {"NOTE", "MEMO", "TEXT", "DATE", "TIME", "LONG", "INTEGER", "CURRENCY", "DATETIME", "YESNO",
            "COUNTER", "USER", "NAME", "VALUE", "LEVEL", "SELECT", "TABLE", "ORDER", "GROUP"}


def test_tous_les_identifiants_du_ddl_sont_entre_crochets() -> None:
    import re

    for table, ddl in gen.TABLES.items():
        corps = ddl[ddl.index("(") + 1 : ddl.rindex(")")]
        corps = re.sub(r",\s*CONSTRAINT \[PrimaryKey\] PRIMARY KEY \(\[[^\]]+\]\)", "", corps)
        colonnes = re.findall(r"\[([^\]]+)\]\s+[A-Z]+", corps)
        assert tuple(colonnes) == gen.COLONNES[table], table
        assert ddl.startswith(f"CREATE TABLE [{table}] (")
        # aucune colonne non protégée : hors crochets, il ne reste que types, tailles et clauses
        hors_crochets = re.sub(r"\[[^\]]+\]", "", corps)
        assert not re.search(r"\b[A-Z_]{2,}_[A-Z_]+\b", hors_crochets), (table, hors_crochets)
    assert not (set(sum((list(c) for c in gen.COLONNES.values()), [])) & MOTS_JET)


def test_echec_du_ddl_nomme_la_table_et_l_instruction(tmp_path: Path) -> None:
    dispatch, journal, _ = _faux_com()
    base_dispatch = dispatch

    def dispatch_cassee(nom: str) -> Any:
        objet = base_dispatch(nom)
        if nom == "ADODB.Connection":
            def execute(sql: str) -> None:
                if "[FACTURES]" in sql:
                    raise RuntimeError("Erreur de syntaxe dans la définition de champ.")

            objet.Execute = execute
        return objet

    with pytest.raises(RuntimeError, match=r"(?s)table FACTURES.*syntaxe.*CREATE TABLE \[FACTURES\]"):
        gen.creer_base(tmp_path / "s.mdb", 5, dispatch=dispatch_cassee, progression=lambda t: None)


def test_cles_primaires_nommees_primarykey() -> None:
    avec_cle = {t for t, ddl in gen.TABLES.items() if "PRIMARY KEY" in ddl}
    assert avec_cle == {"CLIENTS", "FACTURES", "SESSIONS"}
    for table in avec_cle:
        assert "CONSTRAINT [PrimaryKey] PRIMARY KEY (" in gen.TABLES[table]
