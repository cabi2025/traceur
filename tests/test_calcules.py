import json
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Callable

from conftest import Scenario, saisie
from traceur.moteur.calcules import ChampCalcule

Jouer = Callable[..., Scenario]
EXEMPLE = Path(__file__).parent.parent / "docs" / "formats" / "trace.example.json"


def _champ(s: Scenario, table: str, colonne: str, valeur: object = None) -> ChampCalcule:
    trouves = [c for c in s.interpretation.champs_calcules
               if c.table == table and c.colonne == colonne and (valeur is None or c.valeur == valeur)]
    assert len(trouves) == 1, trouves
    return trouves[0]


# --- compteur ---------------------------------------------------------------------------------

def test_compteur_numerique(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE ECR (NUM INTEGER PRIMARY KEY, J TEXT)")
    base.executemany("INSERT INTO ECR (J) VALUES (?)", [("A",)] * 3)
    s = jouer(["INSERT INTO ECR (J) VALUES ('B')"])
    c = _champ(s, "ECR", "NUM")
    assert (c.valeur, c.hypotheses, c.details) == (4, ("compteur",), "max avant = 3")


def test_compteur_pas_constant(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE C (V INTEGER)")
    base.executemany("INSERT INTO C VALUES (?)", [(10,), (20,), (30,)])
    assert _champ(jouer(["INSERT INTO C VALUES (40)"]), "C", "V").hypotheses == ("compteur",)


def test_compteur_refuse_un_ecart_hors_pas(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE C (V INTEGER)")
    base.executemany("INSERT INTO C VALUES (?)", [(10,), (20,), (30,)])
    assert _champ(jouer(["INSERT INTO C VALUES (35)"]), "C", "V").hypotheses == ("inconnu",)
    assert _champ(jouer(["INSERT INTO C VALUES (70)"]), "C", "V").hypotheses == ("inconnu",)


def test_compteur_plusieurs_lignes_inserees(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE L (V INTEGER)")
    base.executemany("INSERT INTO L VALUES (?)", [(99,), (100,)])
    s = jouer(["INSERT INTO L VALUES (101)", "INSERT INTO L VALUES (102)", "INSERT INTO L VALUES (103)"])
    assert [(c.valeur, c.hypotheses) for c in s.interpretation.champs_calcules] == [
        (101, ("compteur",)), (102, ("compteur",)), (103, ("compteur",))]


def test_compteur_texte_largeur_conservee(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE ECR (ID INTEGER PRIMARY KEY, PIECE TEXT)")
    base.executemany("INSERT INTO ECR (PIECE) VALUES (?)", [("0040",), ("0041",)])
    c = _champ(jouer(["INSERT INTO ECR (PIECE) VALUES ('0042')"]), "ECR", "PIECE")
    assert (c.hypotheses, c.details) == (("compteur",), "max avant = 0041")


def test_compteur_texte_avec_prefixe(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE ECR (ID INTEGER PRIMARY KEY, PIECE TEXT)")
    base.executemany("INSERT INTO ECR (PIECE) VALUES (?)", [("ACH-0098",), ("ACH-0099",), ("VTE-0500",)])
    for piece, attendu in (("ACH-0100", ("compteur",)), ("ACH-100", ("inconnu",)),
                           ("ACH-0102", ("inconnu",)), ("VTE-0100", ("inconnu",)),
                           ("XYZ-0100", ("inconnu",))):
        s = jouer([f"INSERT INTO ECR (PIECE) VALUES ('{piece}')"])
        assert _champ(s, "ECR", "PIECE", piece).hypotheses == attendu, piece
        base.execute("DELETE FROM ECR WHERE PIECE = ?", (piece,))


def test_compteur_ligne_modifiee(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE COMPTEURS (CODE TEXT PRIMARY KEY, DERNIER INTEGER)")
    base.executemany("INSERT INTO COMPTEURS VALUES (?,?)", [("ACH", 41), ("VTE", 57)])
    c = _champ(jouer(["UPDATE COMPTEURS SET DERNIER=42 WHERE CODE='ACH'"]), "COMPTEURS", "DERNIER")
    assert (c.hypotheses, c.details) == (("compteur",), "41 → 42")


def test_compteur_ligne_modifiee_pas_constant(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE COMPTEURS (CODE TEXT PRIMARY KEY, DERNIER INTEGER)")
    base.executemany("INSERT INTO COMPTEURS VALUES (?,?)", [("ACH", 41), ("VTE", 57), ("OD", 3)])
    s = jouer(["UPDATE COMPTEURS SET DERNIER=DERNIER+5 WHERE CODE IN ('ACH','VTE')"])
    assert {c.hypotheses for c in s.interpretation.champs_calcules} == {("compteur",)}
    s = jouer(["UPDATE COMPTEURS SET DERNIER=DERNIER+5 WHERE CODE='OD'"])
    assert _champ(s, "COMPTEURS", "DERNIER").hypotheses == ("inconnu",)


# --- horodatage_systeme -----------------------------------------------------------------------

def test_horodatage_systeme(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE E (ID INTEGER PRIMARY KEY, CREE DATETIME, ANCIEN DATETIME, "
                 "JOUR DATE, AUTRE_JOUR DATE)")
    s = jouer(["INSERT INTO E VALUES (1, '2026-10-05T10:16:03', '2026-10-05T10:21:00', "
               "'2026-10-05', '2026-10-06')"])
    assert _champ(s, "E", "CREE").hypotheses == ("horodatage_systeme",)
    assert "2026-10-05T10:16:03 dans [2026-10-05T10:15:22, 2026-10-05T10:18:04]" in _champ(s, "E", "CREE").details
    assert _champ(s, "E", "ANCIEN").hypotheses == ("inconnu",)  # après Fin + 2 min
    assert _champ(s, "E", "JOUR").hypotheses == ("horodatage_systeme",)  # date seule : le jour
    assert _champ(s, "E", "AUTRE_JOUR").hypotheses == ("inconnu",)


def test_horodatage_marge_de_deux_minutes(base: sqlite3.Connection, jouer: Jouer) -> None:
    """Début 10:15:22, Fin 10:18:04 : fenêtre [10:13:22, 10:20:04] (AMB-022)."""
    base.execute("CREATE TABLE E (ID INTEGER PRIMARY KEY, T DATETIME)")
    cas = {"2026-10-05T10:13:22": True, "2026-10-05T10:13:21": False,
           "2026-10-05T10:20:04": True, "2026-10-05T10:20:05": False}
    for valeur, dedans in cas.items():
        s = jouer([f"INSERT INTO E (T) VALUES ('{valeur}')"])
        h = _champ(s, "E", "T", __import__("datetime").datetime.fromisoformat(valeur)).hypotheses
        assert (h == ("horodatage_systeme",)) is dedans, valeur


# --- somme_lignes -----------------------------------------------------------------------------

def _base_ecritures(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE ECRITURES (NUM INTEGER PRIMARY KEY, TOTAL DECIMAL(12,2))")
    base.execute("CREATE TABLE LIGNES (NUM_ECR INTEGER, DEBIT DECIMAL(12,2), RANG INTEGER)")
    for i in range(1, 6):
        base.execute("INSERT INTO ECRITURES VALUES (?, ?)", (i, f"{i}0.00"))
        base.execute("INSERT INTO LIGNES VALUES (?, ?, 1)", (i, "5.00"))


ACTION_ECRITURE = [
    "INSERT INTO ECRITURES VALUES (6, '1481.47')",
    "INSERT INTO LIGNES VALUES (6, '1234.56', 1)",
    "INSERT INTO LIGNES VALUES (6, '246.91', 2)",
]
SAISIES_ECRITURE = [saisie("Débit", "1234.56"), saisie("Débit", "246.91")]


def test_somme_lignes(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_ecritures(base)
    s = jouer(ACTION_ECRITURE, SAISIES_ECRITURE, avec_profil=True)
    c = _champ(s, "ECRITURES", "TOTAL")
    assert (c.hypotheses, c.details) == (("somme_lignes",), "somme de LIGNES.DEBIT (2 lignes liées)")
    assert not [x for x in s.interpretation.champs_calcules if x.colonne == "DEBIT"]  # expliquées par F6


def test_somme_lignes_desactivee_sans_profil(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_ecritures(base)
    s = jouer(ACTION_ECRITURE, SAISIES_ECRITURE, avec_profil=False)
    assert _champ(s, "ECRITURES", "TOTAL").hypotheses == ("inconnu",)
    (a,) = [x for x in s.interpretation.avertissements if x.code == "profil_absent"]
    assert a.details["hypotheses_desactivees"] == ["somme_lignes", "copie", "constante"]
    assert "Profil absent" in a.message


def test_somme_lignes_ignore_les_relations_faibles(base: sqlite3.Connection, jouer: Jouer) -> None:
    """LIGNES.NUM_ECR n'a que 2 valeurs distinctes avant l'action : relation `faible`, exclue."""
    base.execute("CREATE TABLE ECRITURES (NUM INTEGER PRIMARY KEY, TOTAL DECIMAL(12,2))")
    base.execute("CREATE TABLE LIGNES (NUM_ECR INTEGER, DEBIT DECIMAL(12,2))")
    for i in range(1, 6):
        base.execute("INSERT INTO ECRITURES VALUES (?, ?)", (i, f"{i}0.00"))
    for i in (1, 2, 1, 2):
        base.execute("INSERT INTO LIGNES VALUES (?, '5.00')", (i,))
    s = jouer(["INSERT INTO ECRITURES VALUES (6, '1481.47')",
               "INSERT INTO LIGNES VALUES (6, '1234.56')", "INSERT INTO LIGNES VALUES (6, '246.91')"],
              [saisie("Débit", "1234.56"), saisie("Débit", "246.91")], avec_profil=True)
    assert _champ(s, "ECRITURES", "TOTAL").hypotheses == ("inconnu",)


# --- copie ------------------------------------------------------------------------------------

def test_copie(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE CLIENTS (ID INTEGER PRIMARY KEY, NOM TEXT)")
    base.execute("CREATE TABLE FACTURES (NUM INTEGER PRIMARY KEY, CLIENT_ID INTEGER, TEL TEXT)")
    base.execute("ALTER TABLE CLIENTS ADD COLUMN TEL TEXT")
    for i in range(101, 106):
        base.execute("INSERT INTO CLIENTS VALUES (?,?,?)", (i, f"Client {i}", f"05{i}"))
        base.execute("INSERT INTO FACTURES (CLIENT_ID, TEL) VALUES (?,?)", (i, f"05{i}"))
    s = jouer(["INSERT INTO FACTURES (CLIENT_ID, TEL) VALUES (103, '05103')"], avec_profil=True)
    c = _champ(s, "FACTURES", "TEL")
    assert (c.hypotheses, c.details) == (("copie",), "copie de CLIENTS.TEL (ligne ID = 103)")
    # CLIENT_ID est aussi la copie de CLIENTS.ID, lue via la relation TEL → TEL : c'est une hypothèse
    assert _champ(s, "FACTURES", "CLIENT_ID").details == "copie de CLIENTS.ID (ligne TEL = 05103)"
    s = jouer(["INSERT INTO FACTURES (CLIENT_ID, TEL) VALUES (103, 'autre')"], avec_profil=True)
    assert _champ(s, "FACTURES", "TEL", "autre").hypotheses == ("inconnu",)
    s = jouer(["INSERT INTO FACTURES (CLIENT_ID, TEL) VALUES (104, '05104')"], avec_profil=False)
    assert _champ(s, "FACTURES", "TEL", "05104").hypotheses == ("inconnu",)


def test_copie_ignore_les_relations_faibles(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE CLIENTS (ID INTEGER PRIMARY KEY, TEL TEXT)")
    base.execute("CREATE TABLE FACTURES (NUM INTEGER PRIMARY KEY, CLIENT_ID INTEGER, TEL TEXT)")
    for i in range(101, 106):
        base.execute("INSERT INTO CLIENTS VALUES (?,?)", (i, f"05{i}"))
    for i in (101, 102, 101, 102):  # 2 valeurs distinctes : relation faible
        base.execute("INSERT INTO FACTURES (CLIENT_ID, TEL) VALUES (?,?)", (i, f"05{i}"))
    s = jouer(["INSERT INTO FACTURES (CLIENT_ID, TEL) VALUES (103, '05103')"], avec_profil=True)
    assert _champ(s, "FACTURES", "TEL").hypotheses != ("copie",)


# --- constante --------------------------------------------------------------------------------

def test_constante(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (ID INTEGER PRIMARY KEY, STATUT TEXT, NOTE TEXT)")
    base.executemany("INSERT INTO T (STATUT, NOTE) VALUES (?, ?)", [("A", "x"), ("A", None), ("A", "y")])
    s = jouer(["INSERT INTO T (STATUT, NOTE) VALUES ('A', 'z')"], avec_profil=True)
    c = _champ(s, "T", "STATUT")
    assert (c.hypotheses, c.details) == (("constante",), "valeur constante sur toute la table (A)")
    assert _champ(s, "T", "NOTE").hypotheses == ("inconnu",)
    s = jouer(["INSERT INTO T (STATUT, NOTE) VALUES ('B', 'z')"], avec_profil=True)
    assert _champ(s, "T", "STATUT").hypotheses == ("inconnu",)
    s = jouer(["INSERT INTO T (STATUT, NOTE) VALUES ('A', 'z')"], avec_profil=False)
    assert _champ(s, "T", "STATUT").hypotheses == ("inconnu",)


def test_constante_ignoree_sur_table_a_une_ligne(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (STATUT TEXT)")
    base.execute("INSERT INTO T VALUES ('A')")
    s = jouer(["INSERT INTO T VALUES ('A')"], avec_profil=True)
    assert _champ(s, "T", "STATUT").hypotheses == ("inconnu",)


# --- cumul_mis_a_jour -------------------------------------------------------------------------

def test_cumul_mis_a_jour(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE SOLDES (CPT TEXT PRIMARY KEY, SOLDE DECIMAL(12,2))")
    base.executemany("INSERT INTO SOLDES VALUES (?,?)", [("6111", "100.00"), ("4411", "0.00")])
    s = jouer(["UPDATE SOLDES SET SOLDE='1334.56' WHERE CPT='6111'"], [saisie("Débit", "1234.56")])
    c = _champ(s, "SOLDES", "SOLDE")
    assert (c.hypotheses, c.details) == (
        ("cumul_mis_a_jour",), "delta 1234.56 = montant saisi Débit (1234.56)")
    base.execute("UPDATE SOLDES SET SOLDE='100.00' WHERE CPT='6111'")  # état de départ
    s = jouer(["UPDATE SOLDES SET SOLDE='-1134.56' WHERE CPT='6111'"], [saisie("Débit", "1234.56")])
    assert "opposé du montant saisi" in _champ(s, "SOLDES", "SOLDE").details
    base.execute("UPDATE SOLDES SET SOLDE='100.00' WHERE CPT='6111'")
    s = jouer(["UPDATE SOLDES SET SOLDE='150.00' WHERE CPT='6111'"], [saisie("Débit", "1234.56")])
    assert _champ(s, "SOLDES", "SOLDE").hypotheses == ("inconnu",)


# --- inconnu, plusieurs hypothèses, exclusions ------------------------------------------------

def test_inconnu(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (ID INTEGER PRIMARY KEY, X TEXT)")
    c = _champ(jouer(["INSERT INTO T VALUES (1, 'ZZ')"]), "T", "X")
    assert (c.hypotheses, c.details) == (("inconnu",), "")


def test_plusieurs_hypotheses_retenues(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE COMPTEURS (CODE TEXT PRIMARY KEY, DERNIER INTEGER)")
    base.execute("INSERT INTO COMPTEURS VALUES ('ACH', 41)")
    s = jouer(["UPDATE COMPTEURS SET DERNIER=42"], [saisie("Quantité", "1")])
    c = _champ(s, "COMPTEURS", "DERNIER")
    assert c.hypotheses == ("compteur", "cumul_mis_a_jour")
    assert c.details == "compteur : 41 → 42 ; cumul_mis_a_jour : delta 1 = montant saisi Quantité (1)"


def test_cellules_expliquees_nulles_et_bruit_exclues(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (ID INTEGER PRIMARY KEY, M DECIMAL(12,2), N TEXT)")
    base.execute("CREATE TABLE SESSIONS (ID INTEGER PRIMARY KEY, V TEXT)")
    base.execute("INSERT INTO SESSIONS VALUES (1, 'a')")
    s = jouer(["INSERT INTO T VALUES (7, '1234.56', NULL)", "UPDATE SESSIONS SET V='b'"],
              [saisie("Débit", "1234.56")], tables_bruit=["SESSIONS"])
    assert [(c.table, c.colonne) for c in s.interpretation.champs_calcules] == [("T", "ID")]


def test_doublons_fusionnes(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (X TEXT)")
    s = jouer(["INSERT INTO T VALUES ('ZZ')", "INSERT INTO T VALUES ('ZZ')"])
    assert len(s.interpretation.champs_calcules) == 1


def test_forme_conforme_a_l_exemple(base: sqlite3.Connection, jouer: Jouer) -> None:
    """Scénario de la SPEC (facture achat) : compteur de pièce, compteur mis à jour, liens exacts."""
    base.execute("CREATE TABLE ECRITURES (NUM_ECR INTEGER PRIMARY KEY, JOURNAL TEXT, DATE_ECR DATETIME, "
                 "PIECE TEXT)")
    base.execute("CREATE TABLE LIGNES (NUM_ECR INTEGER, COMPTE TEXT, LIBELLE TEXT, DEBIT DECIMAL(12,2), "
                 "CREDIT DECIMAL(12,2))")
    base.execute("CREATE TABLE COMPTEURS (CODE_JOURNAL TEXT PRIMARY KEY, DERNIER_NUM INTEGER)")
    base.execute("INSERT INTO ECRITURES VALUES (18341, 'ACH', '2025-01-10T00:00:00', '0041')")
    base.execute("INSERT INTO COMPTEURS VALUES ('ACH', 41)")
    s = jouer([
        "INSERT INTO ECRITURES VALUES (18342, 'ACH', '2025-01-15T00:00:00', '0042')",
        "INSERT INTO LIGNES VALUES (18342, '6111', 'TEST-S003', '1234.56', '0.00')",
        "UPDATE COMPTEURS SET DERNIER_NUM=42 WHERE CODE_JOURNAL='ACH'",
    ], [saisie("Journal", "ACH", "code"), saisie("Date", "2025-01-15", "date"),
        saisie("Compte", "6111", "code"), saisie("Libellé", "TEST-S003", "texte"),
        saisie("Débit", "1234.56")])
    exemple = json.loads(EXEMPLE.read_text(encoding="utf-8"))
    d = s.interpretation.vers_dict()
    assert set(d["liens"][0]) == set(exemple["liens"][0])
    assert set(d["champs_calcules"][0]) == set(exemple["champs_calcules"][0])
    liens = {(x["champ_ecran"], x["table"], x["colonne"], x["type_correspondance"]) for x in d["liens"]}
    assert ("Débit", "LIGNES", "DEBIT", "exacte") in liens and ("Date", "ECRITURES", "DATE_ECR", "exacte") in liens
    by = {(c["table"], c["colonne"]): c for c in d["champs_calcules"]}
    assert by[("ECRITURES", "PIECE")] == {
        "table": "ECRITURES", "colonne": "PIECE", "valeur": "0042", "hypotheses": ["compteur"],
        "details": "max avant = 0041"}
    assert by[("COMPTEURS", "DERNIER_NUM")]["details"] == "41 → 42"
    assert d["ecarts_saisie"] == [] and not s.interpretation.a_un_ecart_de_saisie
    json.dumps(d)
    assert Decimal("1234.56")  # montants en chaîne dans la trace
    assert all(isinstance(x["valeur"], str) for x in d["liens"])
