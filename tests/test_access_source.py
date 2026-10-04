import logging
import re
import sqlite3
from pathlib import Path

import pytest

from fake_pyodbc import FauxPyodbc
from traceur.config import Configuration
from traceur.moteur.diff import comparer_instantanes
from traceur.moteur.instantane import prendre_instantane
from traceur.moteur.profilage import profiler
from traceur.securite import configurer_journal
from traceur.sources import access
from traceur.sources.access import (
    ErreurAccess,
    ErreurConnexion,
    ErreurPilote,
    ParametresAccess,
    SourceAccess,
    choisir_pilote,
    construire_chaine_connexion,
    version_jet_de,
)

PILOTE = "Microsoft Access Driver (*.mdb)"


# --- pilotes ---------------------------------------------------------------------------------

def test_pilote_prefere_mdb_puis_mdb_accdb() -> None:
    both = ["SQL Server", "Microsoft Access Driver (*.mdb, *.accdb)", "Microsoft Access Driver (*.mdb)"]
    assert choisir_pilote(both) == "Microsoft Access Driver (*.mdb)"
    assert choisir_pilote(["x", "Microsoft Access Driver (*.mdb, *.accdb)"]) == (
        "Microsoft Access Driver (*.mdb, *.accdb)")


def test_aucun_pilote_message_clair() -> None:
    with pytest.raises(ErreurPilote) as e:
        choisir_pilote(["SQL Server", "PostgreSQL Unicode"])
    message = str(e.value)
    assert "Aucun pilote ODBC Access" in message and "32 bits" in message
    assert "SQL Server, PostgreSQL Unicode" in message
    with pytest.raises(ErreurPilote, match="aucun"):
        choisir_pilote([])


def test_pyodbc_absent_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(__import__("sys").modules, "pyodbc", None)
    with pytest.raises(ErreurPilote, match="pip install pyodbc") as e:
        access.importer_pyodbc()
    assert "Cause :" in str(e.value) and "même environnement" in str(e.value)


def test_cause_reelle_de_l_echec_d_import(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    reel = builtins.__import__

    def import_casse(nom: str, *args: object, **kwargs: object) -> object:
        if nom == "pyodbc":
            raise ImportError("DLL load failed while importing pyodbc : %1 n'est pas une application Win32 valide.")
        return reel(nom, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.delitem(__import__("sys").modules, "pyodbc", raising=False)
    monkeypatch.setattr(builtins, "__import__", import_casse)
    with pytest.raises(ErreurPilote, match="DLL load failed"):
        access.importer_pyodbc()


# --- chaîne de connexion ---------------------------------------------------------------------

def test_chaine_lecture_seule_et_partagee() -> None:
    chaine = construire_chaine_connexion(ParametresAccess(r"\\SERVEUR\Compta_TEST\compta_test.mdb"), PILOTE)
    assert chaine == (r"DRIVER={Microsoft Access Driver (*.mdb)};DBQ=\\SERVEUR\Compta_TEST\compta_test.mdb;"
                      "ReadOnly=1;Exclusive=0;")
    assert "PWD" not in chaine and "SystemDB" not in chaine


def test_chaine_avec_mot_de_passe_et_masquage() -> None:
    p = ParametresAccess(r"C:\t.mdb", mot_de_passe="S3cr;et}")
    assert "PWD={S3cr;et}}};" in construire_chaine_connexion(p, PILOTE)  # accolades, } doublée
    masquee = construire_chaine_connexion(p, PILOTE, masquer=True)
    assert "PWD=***" in masquee and "S3cr" not in masquee
    assert "S3cr" not in repr(p) and "mot_de_passe" not in repr(p)


def test_chaine_groupe_de_travail() -> None:
    p = ParametresAccess(r"C:\t.mdb", fichier_mdw=r"C:\dir x\sys.mdw", utilisateur="comptable",
                         mot_de_passe_mdw="pw")
    chaine = construire_chaine_connexion(p, PILOTE)
    assert "SystemDB=C:\\dir x\\sys.mdw;UID=comptable;PWD=pw;" in chaine and "ReadOnly=1" in chaine


def test_parametres_depuis_configuration() -> None:
    c = Configuration("a.mdb", "r.mdb", ("p.mdb",), "out", fichier_fiches="f.json", mot_de_passe="pw",
                      encodage_texte="cp1252")
    p = ParametresAccess.depuis_configuration(c)
    assert (p.chemin, p.mot_de_passe, p.encodage_texte) == ("a.mdb", "pw", "cp1252")
    assert p.secrets() == ["pw"]


# --- connexion -------------------------------------------------------------------------------

def test_connexion_en_lecture_seule_et_encodage(base: sqlite3.Connection) -> None:
    faux = FauxPyodbc(base)
    source = SourceAccess(ParametresAccess(r"C:\t.mdb", encodage_texte="cp1252"), faux)
    (connexion,) = faux.connexions
    assert connexion.readonly is True and connexion.autocommit is True
    assert "ReadOnly=1" in connexion.chaine
    assert connexion.decodages == [(faux.SQL_CHAR, "cp1252"), (faux.SQL_WCHAR, "utf-16le")]
    assert source.pilote == PILOTE
    source.fermer()
    assert connexion.fermee


def test_echec_de_connexion_message_explicite_sans_mot_de_passe(
    base: sqlite3.Connection, tmp_path: Path
) -> None:
    faux = FauxPyodbc(base, erreur_connexion="[HY000] Not a valid password. ({chaine})")
    gestionnaire = configurer_journal(["S3cr3t!"], tmp_path)
    try:
        with pytest.raises(ErreurConnexion) as e:
            SourceAccess(ParametresAccess(r"C:\t.mdb", mot_de_passe="S3cr3t!"), faux)
    finally:
        logging.getLogger("traceur").removeHandler(gestionnaire)
        gestionnaire.close()
    assert "Mot de passe incorrect" in str(e.value) and "S3cr3t!" not in str(e.value)
    contenu = (tmp_path / "journal.log").read_text(encoding="utf-8")
    assert "Connexion refusée" in contenu and "S3cr3t!" not in contenu and "***" in contenu


def test_mot_de_passe_absent_du_journal_a_la_connexion(base: sqlite3.Connection, tmp_path: Path) -> None:
    gestionnaire = configurer_journal(["S3cr3t!"], tmp_path)
    try:
        SourceAccess(ParametresAccess(r"C:\t.mdb", mot_de_passe="S3cr3t!"), FauxPyodbc(base)).fermer()
    finally:
        logging.getLogger("traceur").removeHandler(gestionnaire)
        gestionnaire.close()
    contenu = (tmp_path / "journal.log").read_text(encoding="utf-8")
    assert "PWD=***" in contenu and "S3cr3t!" not in contenu


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [("Could not find file 'x.mdb'", "introuvable"), ("file already in use", "exclusif"),
     ("Data source name not found and no default driver specified", "32 ou 64 bits"),
     ("Unrecognized database format", "Format de base"), ("autre chose", "journal.log")],
)
def test_explication_des_erreurs_du_pilote(texte: str, attendu: str) -> None:
    assert attendu in access.expliquer_erreur_odbc(texte)


# --- lecture ---------------------------------------------------------------------------------

@pytest.fixture
def source_access(base: sqlite3.Connection) -> SourceAccess:
    base.execute("CREATE TABLE FACTURES (NUM INTEGER PRIMARY KEY, MONTANT CURRENCY, NOTE TEXT)")
    base.execute("CREATE TABLE LIGNES (NUM_FACT INTEGER, RANG INTEGER, DEBIT CURRENCY, PRIMARY KEY (NUM_FACT, RANG))")
    base.execute('CREATE TABLE "Mon ]Table" (X INTEGER)')
    base.execute("CREATE TABLE VIDE (A TEXT)")
    base.executemany("INSERT INTO FACTURES VALUES (?,?,?)", [(i, f"{i}.50", f"n{i}") for i in range(1, 6)])
    base.executemany("INSERT INTO LIGNES VALUES (?,?,?)", [(1, 1, "10"), (1, 2, "20")])
    base.execute('INSERT INTO "Mon ]Table" VALUES (7)')
    return SourceAccess(ParametresAccess(r"C:\t.mdb"), FauxPyodbc(base))


def test_lister_tables_sans_tables_systeme(source_access: SourceAccess, base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE MSysACEs (X)")
    base.execute('CREATE TABLE "~TMPCLP1" (X)')
    base.execute("CREATE TABLE USysFoo (X)")
    assert source_access.lister_tables() == ["FACTURES", "LIGNES", "Mon ]Table", "VIDE"]


def test_schema_types_et_cle_primaire_ordonnee(source_access: SourceAccess) -> None:
    f = source_access.schema("FACTURES")
    assert [(c.nom, c.type_declare) for c in f.colonnes] == [
        ("NUM", "INTEGER"), ("MONTANT", "CURRENCY"), ("NOTE", "TEXT")]
    assert f.cle_primaire == ("NUM",)
    assert source_access.schema("LIGNES").cle_primaire == ("NUM_FACT", "RANG")


def test_lire_lignes_par_lots_et_noms_speciaux(
    source_access: SourceAccess, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(access, "TAILLE_LOT", 2)
    lignes = list(source_access.lire_lignes("FACTURES"))
    assert len(lignes) == 5 and lignes[0] == (1, 1.5, "n1") and isinstance(lignes[0], tuple)
    assert list(source_access.lire_lignes("Mon ]Table")) == [(7,)]
    assert list(source_access.lire_lignes("VIDE")) == []


def test_aucune_ecriture_possible(source_access: SourceAccess) -> None:
    for sql in ("INSERT INTO FACTURES VALUES (9, '1', 'x')", "UPDATE FACTURES SET NOTE='x'",
                "DELETE FROM FACTURES", "DROP TABLE FACTURES", "  select * from FACTURES; DROP TABLE X"):
        if sql.lstrip().upper().startswith("SELECT "):
            continue
        with pytest.raises(ErreurAccess, match="que des SELECT"):
            SourceAccess._select(source_access._connexion.cursor(), sql)
    # même en contournant la garde de la classe, la connexion en lecture seule refuse l'écriture
    with pytest.raises(FauxPyodbc.Error):
        source_access._connexion.cursor().execute("INSERT INTO FACTURES VALUES (9, '1', 'x')")
    assert not [m for m in dir(SourceAccess) if re.search(r"ecri|insert|update|delete|execute", m, re.I)]


def test_le_code_d_acces_ne_contient_aucune_instruction_d_ecriture() -> None:
    code = Path(access.__file__).read_text(encoding="utf-8")
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b", code)


def test_moteur_sur_source_access(base: sqlite3.Connection, source_access: SourceAccess) -> None:
    profil = profiler(source_access, version_jet="Jet 4")
    assert profil.version_jet == "Jet 4" and profil.table("FACTURES").nb_lignes == 5
    avant = prendre_instantane(source_access)
    base.execute("INSERT INTO FACTURES VALUES (6, '99.99', 'neuf')")
    base.execute("UPDATE FACTURES SET NOTE='modif' WHERE NUM=1")
    d = comparer_instantanes(avant, prendre_instantane(source_access))
    (t,) = d.changements
    assert (t.type_cle, [i.cle for i in t.inserts], [u.cle for u in t.updates]) == (
        "primaire", [{"NUM": 6}], [{"NUM": 1}])


def test_version_jet_de(tmp_path: Path) -> None:
    f = tmp_path / "a.mdb"
    entete = bytearray(64)
    entete[4:19] = b"Standard Jet DB"
    entete[0x14] = 1
    f.write_bytes(bytes(entete))
    assert version_jet_de(str(f)) == "Jet 4"
    assert version_jet_de(str(tmp_path / "absent.mdb")) is None
    (tmp_path / "x.mdb").write_bytes(b"abc")
    assert version_jet_de(str(tmp_path / "x.mdb")) is None


# --- clé primaire avec le pilote Jet (SQLPrimaryKeys non pris en charge, AMB-028) -------------

@pytest.fixture
def source_jet(base: sqlite3.Connection) -> tuple[SourceAccess, FauxPyodbc]:
    base.execute("CREATE TABLE FACTURES (NUM INTEGER PRIMARY KEY, CODE TEXT, X INTEGER)")
    base.execute("CREATE UNIQUE INDEX idx_code ON FACTURES (CODE)")  # index unique qui n'est PAS la clé
    base.execute("CREATE TABLE LIGNES (NUM_FACT INTEGER, RANG INTEGER, PRIMARY KEY (RANG, NUM_FACT))")
    base.execute("CREATE TABLE SANS_CLE (A TEXT)")
    faux = FauxPyodbc(base, pk_supportee=False)
    return SourceAccess(ParametresAccess(r"C:\t.mdb"), faux), faux


def test_cle_primaire_lue_via_les_index_quand_le_pilote_ne_gere_pas_sqlprimarykeys(
    source_jet: tuple[SourceAccess, FauxPyodbc],
) -> None:
    source, _ = source_jet
    assert source.schema("FACTURES").cle_primaire == ("NUM",)  # pas l'index unique idx_code
    assert source.schema("LIGNES").cle_primaire == ("RANG", "NUM_FACT")  # ordre de l'index
    assert source.schema("SANS_CLE").cle_primaire == ()


def test_sqlprimarykeys_n_est_essaye_qu_une_fois(
    source_jet: tuple[SourceAccess, FauxPyodbc], caplog: pytest.LogCaptureFixture
) -> None:
    source, faux = source_jet
    caplog.set_level(logging.INFO, "traceur")
    for _ in range(3):
        for table in ("FACTURES", "LIGNES", "SANS_CLE"):
            source.schema(table)
    assert faux.connexions[0].appels_primary_keys == 1
    assert caplog.text.count("ne gère pas SQLPrimaryKeys") == 1
    assert "WARNING" not in caplog.text  # plus de message d'alerte répété


def test_sans_primarykeys_ni_statistiques_cle_vide_et_une_seule_alerte(
    base: sqlite3.Connection, caplog: pytest.LogCaptureFixture
) -> None:
    base.execute("CREATE TABLE A (ID INTEGER PRIMARY KEY)")
    base.execute("CREATE TABLE B (ID INTEGER PRIMARY KEY)")
    source = SourceAccess(ParametresAccess(r"C:\t.mdb"),
                          FauxPyodbc(base, pk_supportee=False, statistiques_supportees=False))
    caplog.set_level(logging.WARNING, "traceur")
    assert source.schema("A").cle_primaire == () and source.schema("B").cle_primaire == ()
    assert caplog.text.count("clés candidates du profilage") == 1


def test_profil_et_diff_avec_pilote_sans_sqlprimarykeys(
    source_jet: tuple[SourceAccess, FauxPyodbc], base: sqlite3.Connection
) -> None:
    source, _ = source_jet
    base.executemany("INSERT INTO FACTURES VALUES (?,?,?)", [(1, "a", 1), (2, "b", 1)])
    profil = profiler(source)
    assert profil.table("FACTURES").cle_primaire == ("NUM",)
    avant = prendre_instantane(source)
    base.execute("INSERT INTO FACTURES VALUES (3, 'c', 2)")
    (t,) = comparer_instantanes(avant, prendre_instantane(source)).changements
    assert t.type_cle == "primaire" and [i.cle for i in t.inserts] == [{"NUM": 3}]


def test_index_pk_au_nom_inattendu_diagnostic_dans_le_journal_et_cle_vide(
    base: sqlite3.Connection, caplog: pytest.LogCaptureFixture
) -> None:
    """Si Jet nomme l'index autrement que « PrimaryKey », le journal dit quels index existent."""
    base.execute("CREATE TABLE FACTURES (NUM INTEGER PRIMARY KEY, CODE TEXT, X INTEGER)")
    base.execute("CREATE INDEX idx_x ON FACTURES (X)")
    source = SourceAccess(ParametresAccess(r"C:\t.mdb"),
                          FauxPyodbc(base, pk_supportee=False, nom_index_pk="PK__FACTURES__1"))
    caplog.set_level(logging.INFO, "traceur")
    assert source.schema("FACTURES").cle_primaire == ()
    assert source.schema("FACTURES").cle_primaire == ()  # lecture mise en cache : un seul message
    assert caplog.text.count("aucun index « PrimaryKey »") == 1
    assert "PK__FACTURES__1 (unique) → NUM" in caplog.text and "idx_x → X" in caplog.text


def test_cles_relues_apres_rafraichissement(
    source_jet: tuple[SourceAccess, FauxPyodbc], base: sqlite3.Connection
) -> None:
    source, faux = source_jet
    assert source.schema("SANS_CLE").cle_primaire == ()
    source.rafraichir()  # nouvelle connexion : le cache des clés est vidé
    assert len(faux.connexions) == 2 and source._cles_lues == {}
    assert source.schema("FACTURES").cle_primaire == ("NUM",)
