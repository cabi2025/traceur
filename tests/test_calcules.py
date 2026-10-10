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


# --- AMB-041.2 : bruit de `copie` ------------------------------------------------------------------

def _base_copie_triviale(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE CLIENTS (ID INTEGER PRIMARY KEY, SOLDE DECIMAL(12,2), NOTE TEXT, NB INTEGER)")
    base.execute("CREATE TABLE FACTURES (NUM INTEGER PRIMARY KEY, CLIENT_ID INTEGER, SOLDE DECIMAL(12,2), "
                 "NOTE TEXT, NB INTEGER, REF TEXT)")
    base.execute("ALTER TABLE CLIENTS ADD COLUMN REF TEXT")
    for i in range(101, 106):
        base.execute("INSERT INTO CLIENTS VALUES (?, '0.00', '   ', 0, ?)", (i, f"R{i}"))
        base.execute("INSERT INTO FACTURES (CLIENT_ID, SOLDE, NOTE, NB, REF) VALUES (?, '0.00', '   ', 0, ?)",
                     (i, f"R{i}"))


def test_copie_exclut_les_valeurs_triviales(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_copie_triviale(base)
    s = jouer(["INSERT INTO FACTURES (CLIENT_ID, SOLDE, NOTE, NB, REF) VALUES (103, '0.00', '   ', 0, 'R103')"],
              avec_profil=True)
    for colonne in ("SOLDE", "NOTE", "NB"):
        for c in (x for x in s.interpretation.champs_calcules if x.colonne == colonne):
            assert "copie" not in c.hypotheses, (colonne, c)
    # une valeur non triviale reste détectée
    assert _champ(s, "FACTURES", "REF").hypotheses == ("copie",)


def test_copie_non_triviale_numerique_encore_detectee(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_copie_triviale(base)
    base.execute("UPDATE CLIENTS SET SOLDE = '12.50' WHERE ID = 103")
    s = jouer(["INSERT INTO FACTURES (CLIENT_ID, SOLDE, NOTE, NB, REF) VALUES (103, '12.50', 'x', 7, 'R103')"],
              avec_profil=True)
    assert "copie" in _champ(s, "FACTURES", "SOLDE", Decimal("12.50")).hypotheses


def _base_tables_parasites(base: sqlite3.Connection) -> None:
    base.execute('CREATE TABLE "Table des erreurs" (ID INTEGER PRIMARY KEY, CODE TEXT)')
    base.execute('CREATE TABLE "Erreurs de conversion (1)" (ID INTEGER PRIMARY KEY, CODE TEXT)')
    base.execute("CREATE TABLE FACTURES (NUM INTEGER PRIMARY KEY, CLIENT_ID INTEGER, CODE TEXT)")
    for i in range(101, 106):
        base.execute('INSERT INTO "Table des erreurs" VALUES (?, ?)', (i, f"ERR{i}"))
        base.execute('INSERT INTO "Erreurs de conversion (1)" VALUES (?, ?)', (i, f"ERR{i}"))
        base.execute("INSERT INTO FACTURES (CLIENT_ID, CODE) VALUES (?, ?)", (i, f"ERR{i}"))


ACTION_PARASITE = ["INSERT INTO FACTURES (CLIENT_ID, CODE) VALUES (103, 'ERR103')"]


def test_copie_ignore_les_tables_parasites_par_defaut(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_tables_parasites(base)
    s = jouer(ACTION_PARASITE, avec_profil=True)
    for c in s.interpretation.champs_calcules:
        assert "Table des erreurs" not in c.details and "Erreurs de conversion" not in c.details, c


def test_copie_tables_ignorees_analyse_vide_les_reactive(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_tables_parasites(base)
    s = jouer(ACTION_PARASITE, avec_profil=True, tables_ignorees_analyse=())
    assert any("copie" in c.hypotheses and ("Table des erreurs" in c.details or "Erreurs de conversion" in c.details)
               for c in s.interpretation.champs_calcules)


def test_copie_motif_personnalise_et_casse_ignoree(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_tables_parasites(base)
    s = jouer(ACTION_PARASITE, avec_profil=True, tables_ignorees_analyse=("table DES erreurs", "erreurs de conv*"))
    assert not any("erreurs" in c.details.casefold() for c in s.interpretation.champs_calcules)


def test_table_ignoree_pour_analyse() -> None:
    from traceur.moteur.calcules import est_valeur_triviale, table_ignoree_pour_analyse

    motifs = ("Table des erreurs", "Erreurs de conversion*")
    assert table_ignoree_pour_analyse("Table des erreurs", motifs)
    assert table_ignoree_pour_analyse("Erreurs de conversion (2)", motifs)
    assert not table_ignoree_pour_analyse("Table des erreurs2", motifs)
    assert not table_ignoree_pour_analyse("ecrit", motifs)
    for v in (None, 0, 0.0, Decimal("0.0000"), "", "   ", " "):
        assert est_valeur_triviale(v), v
    for v in (1, Decimal("0.01"), "0", "A"):
        assert not est_valeur_triviale(v), v


# --- AMB-041.3 : compteur réservé aux entiers et aux codes texte numériques -------------------------

def test_compteur_jamais_sur_une_colonne_montant(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE M (V DECIMAL(12,2))")
    base.executemany("INSERT INTO M VALUES (?)", [("1.00",), ("2.00",), ("3.00",)])
    s = jouer(["INSERT INTO M VALUES ('4.00')"])
    assert _champ(s, "M", "V").hypotheses == ("inconnu",)


def test_compteur_jamais_sur_un_cumul_decimal(base: sqlite3.Connection, jouer: Jouer) -> None:
    """Cas réel S-201 : compte.Credit 39650045.36 → 39651526.83 n'est pas un compteur."""
    base.execute("CREATE TABLE compte (Compte TEXT PRIMARY KEY, Credit DECIMAL(15,4))")
    base.executemany("INSERT INTO compte VALUES (?, ?)", [("44", "39650045.3600"), ("441", "26834581.7100")])
    s = jouer(["UPDATE compte SET Credit = ROUND(Credit + 1481.47, 2)"], [saisie("Crédit", "1481.47")])
    for c in s.interpretation.champs_calcules:
        assert "compteur" not in c.hypotheses, c
    assert all(c.hypotheses == ("cumul_mis_a_jour", "cumul_hierarchique") for c in s.interpretation.champs_calcules)


def test_compteur_jamais_sur_un_montant_ecrit_en_texte(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE M (V TEXT)")
    base.executemany("INSERT INTO M VALUES (?)", [("1.00",), ("2.00",), ("3.00",)])
    assert _champ(jouer(["INSERT INTO M VALUES ('4.00')"]), "M", "V").hypotheses == ("inconnu",)


def test_compteur_jamais_sur_un_flottant(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE F (V REAL)")
    base.executemany("INSERT INTO F VALUES (?)", [(1.0,), (2.0,), (3.0,)])
    assert _champ(jouer(["INSERT INTO F VALUES (4.0)"]), "F", "V").hypotheses == ("inconnu",)


def test_compteur_code_texte_numerique_reste_eligible(base: sqlite3.Connection, jouer: Jouer) -> None:
    """`ecrit.Piece` (texte « 990201 ») reste éligible : les codes texte numériques sont conservés."""
    base.execute("CREATE TABLE ECR (ID INTEGER PRIMARY KEY, PIECE TEXT)")
    base.executemany("INSERT INTO ECR (PIECE) VALUES (?)", [("990199",), ("990200",)])
    c = _champ(jouer(["INSERT INTO ECR (PIECE) VALUES ('990201')"]), "ECR", "PIECE")
    assert (c.hypotheses, c.details) == (("compteur",), "max avant = 990200")


# --- AMB-041.4 : cumul_hierarchique --------------------------------------------------------------------

def _base_comptes(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE compte (Compte TEXT PRIMARY KEY, Debit DECIMAL(15,4), Credit DECIMAL(15,4))")
    base.execute("CREATE TABLE scompte (Compte TEXT, Mois TEXT, Debit DECIMAL(15,4), Credit DECIMAL(15,4), "
                 "PRIMARY KEY (Compte, Mois))")
    for compte in ("6", "61", "612", "6126", "61263    ", "34", "345", "3455", "34552    ",
                   "44", "441", "4411", "44111", "441110024", "71", "72"):
        base.execute("INSERT INTO compte VALUES (?, '1000.0000', '2000.0000')", (compte,))


ACTION_FACTURE = [
    "UPDATE compte SET Debit = ROUND(Debit + 1234.56, 2) WHERE Compte IN ('61', '612', '6126', '61263    ')",
    "UPDATE compte SET Debit = ROUND(Debit + 246.91, 2) WHERE Compte IN ('34', '345', '3455', '34552    ')",
    "UPDATE compte SET Credit = ROUND(Credit + 1481.47, 2) WHERE Compte IN ('44', '441', '4411', '44111', '441110024')",
]
SAISIES_FACTURE_CUMUL = [saisie("Débit ou HT", "1234.56"), saisie("Crédit", "1481.47")]


def test_cumul_hierarchique_trois_chaines(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_comptes(base)
    s = jouer(ACTION_FACTURE, SAISIES_FACTURE_CUMUL)
    par_valeur = {(c.colonne, Decimal(str(c.valeur))): c for c in s.interpretation.champs_calcules}
    # 61263, 6126, 612, 61 : cumul d'un montant saisi ET cumul sur la chaîne de préfixes
    c = par_valeur[("Debit", Decimal("2234.56"))]
    assert c.hypotheses == ("cumul_mis_a_jour", "cumul_hierarchique")
    assert "61, 612, 6126, 61263" in c.details
    # 34552 et ses parents : le delta 246,91 (TVA) n'est pas un montant saisi → hiérarchique seul
    tva = par_valeur[("Debit", Decimal("1246.91"))]
    assert tva.hypotheses == ("cumul_hierarchique",)
    assert "34, 345, 3455, 34552" in tva.details
    # 441110024 et ses parents
    cr = par_valeur[("Credit", Decimal("3481.47"))]
    assert cr.hypotheses == ("cumul_mis_a_jour", "cumul_hierarchique")
    assert "44, 441, 4411, 44111, 441110024" in cr.details
    # 13 comptes touchés, tous expliqués : aucun « inconnu »
    assert not [x for x in s.interpretation.champs_calcules if x.hypotheses == ("inconnu",)]


def test_cumul_hierarchique_jamais_le_niveau_classe(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_comptes(base)
    s = jouer(["UPDATE compte SET Debit = ROUND(Debit + 5.00, 2) WHERE Compte IN ('6', '61', '612')"])
    details = " | ".join(c.details for c in s.interpretation.champs_calcules)
    assert "comptes liés par préfixe : 61, 612" in details  # le compte « 6 » n'est jamais dans la chaîne
    # le compte de classe (« 6 ») lui-même ne reçoit pas l'hypothèse
    seul = [c for c in s.interpretation.champs_calcules if "cumul_hierarchique" not in c.hypotheses]
    assert len(seul) == 1 and seul[0].valeur == Decimal("1005")


def test_cumul_hierarchique_exige_le_meme_delta(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_comptes(base)
    s = jouer(["UPDATE compte SET Debit = ROUND(Debit + 10, 2) WHERE Compte = '61'",
               "UPDATE compte SET Debit = ROUND(Debit + 11, 2) WHERE Compte = '612'"])
    assert all("cumul_hierarchique" not in c.hypotheses for c in s.interpretation.champs_calcules)


def test_cumul_hierarchique_exige_un_lien_de_prefixe(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_comptes(base)
    s = jouer(["UPDATE compte SET Debit = ROUND(Debit + 7, 2) WHERE Compte IN ('71', '72')"])
    assert all("cumul_hierarchique" not in c.hypotheses for c in s.interpretation.champs_calcules)


def test_cumul_hierarchique_une_seule_ligne_isolee(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_comptes(base)
    s = jouer(["UPDATE compte SET Debit = ROUND(Debit + 7, 2) WHERE Compte = '61'"])
    assert [c.hypotheses for c in s.interpretation.champs_calcules] == [("inconnu",)]


def test_cumul_hierarchique_scompte_par_mois_et_insertion(base: sqlite3.Connection, jouer: Jouer) -> None:
    _base_comptes(base)
    for compte in ("61", "612"):
        base.execute("INSERT INTO scompte VALUES (?, '10', '100.0000', '0.0000')", (compte,))
        base.execute("INSERT INTO scompte VALUES (?, '09', '100.0000', '0.0000')", (compte,))
    s = jouer([
        "UPDATE scompte SET Debit = ROUND(Debit + 20, 2) WHERE Mois = '10'",
        "INSERT INTO scompte VALUES ('6126', '10', '20.0000', '0.0000')",  # INSERT : delta = valeur
        "UPDATE scompte SET Debit = ROUND(Debit + 3, 2) WHERE Mois = '09' AND Compte = '61'",  # autre mois : isolé
    ])
    par = {(c.table, Decimal(str(c.valeur))): c for c in s.interpretation.champs_calcules}
    assert par[("scompte", Decimal("120"))].hypotheses == ("cumul_hierarchique",)
    assert "61, 612, 6126" in par[("scompte", Decimal("120"))].details
    assert par[("scompte", Decimal("103"))].hypotheses == ("inconnu",)
