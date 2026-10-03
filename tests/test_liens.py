import sqlite3
from decimal import Decimal
from typing import Callable

import pytest

from conftest import Scenario, saisie
import traceur.moteur.liens as liens_module
from traceur.moteur.liens import distance

Jouer = Callable[..., Scenario]


@pytest.mark.parametrize(
    ("declare", "stocke", "type_", "valeur", "attendu"),
    [
        ("DECIMAL(12,2)", "1234.56", "montant", "1234.56", ("exacte", "haute")),
        ("DECIMAL(12,2)", "1234.56", "montant", "1 234,56", ("exacte", "haute")),
        ("DECIMAL(12,2)", "0", "montant", "0.00", ("exacte", "haute")),
        ("DECIMAL(12,2)", "-1234.56", "montant", "1234.56", ("signe_inverse", "moyenne")),
        ("DECIMAL(12,2)", "123456", "montant", "1234.56", ("x100", "faible")),
        ("DECIMAL(12,2)", "12.3456", "montant", "1234.56", ("div100", "faible")),
        ("DATE", "2025-01-15", "date", "2025-01-15", ("exacte", "haute")),
        ("DATE", "2025-01-15", "date", "15/01/2025", ("exacte", "haute")),
        ("DATE", "2025-01-15", "date", "15-01-2025", ("exacte", "haute")),
        ("DATETIME", "2025-01-15T00:00:00", "date", "2025-01-15", ("exacte", "haute")),  # minuit pile
        ("DATETIME", "2025-01-15T00:00:01", "date", "2025-01-15", ("date_heure", "haute")),
        ("DATETIME", "2025-01-15T10:30:00", "date", "2025-01-15", ("date_heure", "haute")),
        ("TEXT", "15/01/2025", "date", "2025-01-15", ("exacte", "haute")),
        ("TEXT", "TEST-S003", "texte", "TEST-S003", ("exacte", "haute")),
        ("TEXT", "TEST-S003", "texte", "Test-S003", ("majuscules", "moyenne")),
        ("TEXT", "TEST-S", "texte", "TEST-S003", ("tronque", "moyenne")),
        ("TEXT", "6111", "code", "6111", ("exacte", "haute")),
        ("INTEGER", 6111, "code", "6111", ("exacte", "haute")),
        ("TEXT", "ACH", "code", "ACH", ("exacte", "haute")),
    ],
)
def test_un_cas_par_type_de_correspondance(
    base: sqlite3.Connection, jouer: Jouer, declare: str, stocke: object, type_: str,
    valeur: str, attendu: tuple[str, str],
) -> None:
    base.execute(f"CREATE TABLE T (ID INTEGER PRIMARY KEY, V {declare})")
    s = jouer(["INSERT INTO T VALUES (1, %r)" % (stocke,)], [saisie("Champ", valeur, type_)])
    assert [(x.table, x.colonne, x.type_correspondance, x.confiance) for x in s.interpretation.liens] \
        == [("T", "V", *attendu)]
    assert s.interpretation.liens[0].valeur == valeur
    assert not s.interpretation.ecarts_saisie


@pytest.mark.parametrize(
    ("declare", "stocke", "type_", "valeur"),
    [
        ("TEXT", "TE", "texte", "TEST-S003"),  # tronqué trop court (< 3)
        ("TEXT", "TEST-S003 ", "texte", "TEST-S003"),  # l'espace final est une donnée
        ("INTEGER", 42, "code", "0042"),  # zéro de tête
        ("DECIMAL(12,2)", "5", "montant", "0"),  # aucune tolérance pour 0 (et 5 ≠ 0)
        ("TEXT", "1234.56", "montant", "1234.56"),  # montant stocké en texte : refusé
        ("TEXT", "x", "date", "2025-01-15"),
        ("DATETIME", "2025-01-16T00:00:00", "date", "2025-01-15"),  # autre jour
    ],
)
def test_non_correspondances(
    base: sqlite3.Connection, jouer: Jouer, declare: str, stocke: object, type_: str, valeur: str
) -> None:
    base.execute(f"CREATE TABLE T (ID INTEGER PRIMARY KEY, V {declare})")
    s = jouer(["INSERT INTO T VALUES (10, %r)" % (stocke,)], [saisie("Champ", valeur, type_)])
    assert not s.interpretation.liens
    assert [e.type_ecart for e in s.interpretation.ecarts_saisie] == ["introuvable"]


def test_tolerees_seulement_sans_exacte(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (ID INTEGER PRIMARY KEY, M1 DECIMAL(12,2), M2 DECIMAL(12,2))")
    s = jouer(["INSERT INTO T VALUES (1, '1234.56', '123456')"], [saisie("Débit", "1234.56")])
    assert [(x.colonne, x.type_correspondance) for x in s.interpretation.liens] == [("M1", "exacte")]


def test_lien_par_valeur_deux_saisies_meme_champ(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE LIGNES (NUM INTEGER, DEBIT DECIMAL(12,2))")
    s = jouer(
        ["INSERT INTO LIGNES VALUES (1, '1234.56')", "INSERT INTO LIGNES VALUES (1, '246.91')"],
        [saisie("Débit", "1234.56"), saisie("Débit", "246.91")],
    )
    assert [(x.champ_ecran, x.valeur, x.colonne) for x in s.interpretation.liens] == [
        ("Débit", "1234.56", "DEBIT"), ("Débit", "246.91", "DEBIT")]


def test_cellules_non_modifiees_ignorees(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (ID INTEGER PRIMARY KEY, M DECIMAL(12,2))")
    base.execute("INSERT INTO T VALUES (1, '1234.56')")  # déjà là avant l'action
    s = jouer(["INSERT INTO T VALUES (2, '5.00')"], [saisie("Débit", "1234.56")])
    assert not s.interpretation.liens


def test_seul_le_champ_modifie_est_lie(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (ID INTEGER PRIMARY KEY, M1 DECIMAL(12,2), M2 DECIMAL(12,2))")
    base.execute("INSERT INTO T VALUES (1, '1234.56', '10.00')")
    s = jouer(["UPDATE T SET M2='1234.56' WHERE ID=1"], [saisie("Débit", "1234.56")])
    assert [(x.colonne) for x in s.interpretation.liens] == ["M2"]


def test_update_probable_lie(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE L (C TEXT, M DECIMAL(12,2), K TEXT)")
    base.execute("INSERT INTO L VALUES ('A', '1.00', 'x')")
    s = jouer(["UPDATE L SET M='7.00'"], [saisie("Montant", "7.00")])
    assert s.diff.changements[0].updates_probables
    assert [(x.table, x.colonne) for x in s.interpretation.liens] == [("L", "M")]


def test_valeur_de_fiche_invalide(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (ID INTEGER PRIMARY KEY)")
    s = jouer(["INSERT INTO T VALUES (1)"], [saisie("Débit", "abc"), saisie("Date", "32/13/2025", "date")])
    codes = [(a.code, a.details["champ_ecran"]) for a in s.interpretation.avertissements
             if a.code == "valeur_saisie_invalide"]
    assert codes == [("valeur_saisie_invalide", "Débit"), ("valeur_saisie_invalide", "Date")]
    assert not s.interpretation.ecarts_saisie


def test_ecart_introuvable(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (ID INTEGER PRIMARY KEY, M DECIMAL(12,2))")
    s = jouer(["INSERT INTO T VALUES (1, '5.00')"], [saisie("Débit", "999.99")])
    (e,) = s.interpretation.ecarts_saisie
    assert (e.type_ecart, e.table, e.colonne, e.valeur_attendue) == ("introuvable", None, None, "999.99")
    assert s.interpretation.a_un_ecart_de_saisie


def test_ecart_valeur_differente_meme_colonne(base: sqlite3.Connection, jouer: Jouer) -> None:
    """Exemple de la SPEC §7.4 : 1 243,56 trouvé au lieu de 1 234,56."""
    base.execute("CREATE TABLE LIGNES (NUM INTEGER, DEBIT DECIMAL(12,2))")
    s = jouer(
        ["INSERT INTO LIGNES VALUES (1, '1243.56')", "INSERT INTO LIGNES VALUES (1, '246.91')"],
        [saisie("Débit", "1234.56"), saisie("Débit", "246.91")],
    )
    (e,) = s.interpretation.ecarts_saisie
    assert (e.type_ecart, e.table, e.colonne, e.valeur_trouvee) == (
        "valeur_differente", "LIGNES", "DEBIT", Decimal("1243.56"))
    assert e.vers_dict()["valeur_trouvee"] == "1243.56"
    assert [x.valeur for x in s.interpretation.liens] == ["246.91"]


def test_ecart_sans_colonne_soeur_reste_introuvable(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE LIGNES (NUM INTEGER, DEBIT DECIMAL(12,2))")
    s = jouer(["INSERT INTO LIGNES VALUES (1, '1243.56')"], [saisie("Débit", "1234.56")])
    assert [e.type_ecart for e in s.interpretation.ecarts_saisie] == ["introuvable"]


def test_pas_d_ecart_quand_une_tolerance_trouve(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (ID INTEGER PRIMARY KEY, M DECIMAL(12,2))")
    s = jouer(["INSERT INTO T VALUES (1, '-1234.56')"], [saisie("Débit", "1234.56")])
    assert not s.interpretation.ecarts_saisie and s.interpretation.liens


def test_ecart_texte_trop_court_non_compare(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE T (ID INTEGER PRIMARY KEY, A TEXT, B TEXT)")
    s = jouer(["INSERT INTO T VALUES (1, 'ACH', 'ACX')"],
              [saisie("J", "ACH", "code"), saisie("J", "ACW", "code")])
    assert [e.type_ecart for e in s.interpretation.ecarts_saisie] == ["introuvable"]


@pytest.mark.parametrize(
    ("a", "b", "attendu"),
    [("1234.56", "1234.56", 0), ("1234.56", "1243.56", 1), ("abc", "abd", 1), ("abc", "ab", 1),
     ("ab", "abc", 1), ("1234.56", "1324.65", 2)],
)
def test_distance(a: str, b: str, attendu: int) -> None:
    assert distance(a, b) == attendu


def _levenshtein_simple(a: str, b: str) -> int:
    """Levenshtein sans transposition : référence pour prouver que la transposition compte."""
    ligne = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        precedent, ligne[0] = ligne[0], i
        for j, cb in enumerate(b, 1):
            precedent, ligne[j] = ligne[j], min(ligne[j] + 1, ligne[j - 1] + 1, precedent + (ca != cb))
    return ligne[-1]


def test_1243_56_detecte_par_la_transposition_et_non_par_accident(
    base: sqlite3.Connection, jouer: Jouer, monkeypatch: pytest.MonkeyPatch
) -> None:
    # La transposition « 34 » → « 43 » compte pour 1 en Damerau-Levenshtein, 2 en Levenshtein simple.
    assert distance("1234.56", "1243.56") == 1
    assert _levenshtein_simple("1234.56", "1243.56") == 2
    base.execute("CREATE TABLE LIGNES (NUM INTEGER, DEBIT DECIMAL(12,2))")
    requetes = ["INSERT INTO LIGNES VALUES (1, '1243.56')", "INSERT INTO LIGNES VALUES (1, '246.91')"]
    saisies = [saisie("Débit", "1234.56"), saisie("Débit", "246.91")]
    s = jouer(requetes, saisies)
    assert [e.type_ecart for e in s.interpretation.ecarts_saisie] == ["valeur_differente"]
    # Contre-épreuve : avec la distance sans transposition, l'écart n'est plus reconnu.
    base.execute("DELETE FROM LIGNES")
    monkeypatch.setattr(liens_module, "distance", _levenshtein_simple)
    s = jouer(requetes, saisies)
    assert [e.type_ecart for e in s.interpretation.ecarts_saisie] == ["introuvable"]


def test_ecart_compare_sur_la_valeur_normalisee(base: sqlite3.Connection, jouer: Jouer) -> None:
    """1234.50 attendu, 1243.5 trouvé : zéros finals sans effet, transposition reconnue."""
    base.execute("CREATE TABLE LIGNES (NUM INTEGER, DEBIT DECIMAL(12,2))")
    s = jouer(["INSERT INTO LIGNES VALUES (1, '1243.5')", "INSERT INTO LIGNES VALUES (1, '246.91')"],
              [saisie("Débit", "1234.50"), saisie("Débit", "246.91")])
    assert [e.type_ecart for e in s.interpretation.ecarts_saisie] == ["valeur_differente"]


def test_deux_transpositions_ne_sont_pas_un_ecart(base: sqlite3.Connection, jouer: Jouer) -> None:
    base.execute("CREATE TABLE LIGNES (NUM INTEGER, DEBIT DECIMAL(12,2))")
    s = jouer(["INSERT INTO LIGNES VALUES (1, '1324.65')", "INSERT INTO LIGNES VALUES (1, '246.91')"],
              [saisie("Débit", "1234.56"), saisie("Débit", "246.91")])
    assert [e.type_ecart for e in s.interpretation.ecarts_saisie] == ["introuvable"]
