from __future__ import annotations

import sqlite3
from typing import Iterator

import pytest

from traceur.sources.sqlite import SourceSqlite


@pytest.fixture(autouse=True)
def dns_hermetique(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aucun test ne fait de vraie requête DNS : un nom de serveur se résout en lui-même."""
    import traceur.securite as securite

    monkeypatch.setattr(securite, "resoudre_hote_dns", lambda hote, delai_s=3.0: frozenset({hote.casefold()}))


@pytest.fixture
def base() -> Iterator[sqlite3.Connection]:
    connexion = sqlite3.connect(":memory:")
    yield connexion
    connexion.close()


@pytest.fixture
def source(base: sqlite3.Connection) -> SourceSqlite:
    return SourceSqlite(base)


# --- scénarios d'interprétation (J3) -------------------------------------------------------

from dataclasses import dataclass  # noqa: E402
from datetime import datetime  # noqa: E402
from typing import Any, Callable, Sequence  # noqa: E402

from traceur.moteur.diff import ResultatDiff, comparer_instantanes  # noqa: E402
from traceur.moteur.instantane import Instantane, prendre_instantane  # noqa: E402
from traceur.moteur.interpretation import ResultatInterpretation, interpreter  # noqa: E402
from traceur.moteur.liens import ValeurSaisie  # noqa: E402
from traceur.moteur.profilage import cles_candidates_du_profil, profiler  # noqa: E402

DEBUT = datetime(2026, 10, 5, 10, 15, 22)
FIN = datetime(2026, 10, 5, 10, 18, 4)


def saisie(champ: str, valeur: str, type_: str = "montant", ecran: str = "001") -> ValeurSaisie:
    return ValeurSaisie(champ, ecran, valeur, type_)


@dataclass
class Scenario:
    diff: ResultatDiff
    interpretation: ResultatInterpretation
    avant: Instantane
    apres: Instantane


@pytest.fixture
def jouer(base: sqlite3.Connection, source: SourceSqlite) -> Callable[..., Scenario]:
    """Photo avant, requêtes de l'action, photo après, diff, interprétation."""

    def _jouer(
        requetes: Sequence[str],
        saisies: Sequence[ValeurSaisie] = (),
        avec_profil: bool = False,
        tables_bruit: Sequence[str] = (),
    ) -> Scenario:
        profil = profiler(source) if avec_profil else None
        avant = prendre_instantane(source)
        for requete in requetes:
            base.execute(requete)
        apres = prendre_instantane(source)
        cles = cles_candidates_du_profil(profil) if profil is not None else None
        diff = comparer_instantanes(avant, apres, cles, tables_bruit)
        return Scenario(diff, interpreter(diff, avant, apres, saisies, DEBUT, FIN, profil), avant, apres)

    return _jouer


# --- traces d'exemple (J5) -----------------------------------------------------------------------

from traceur.rapports.trace import Execution, FicheTrace, construire_trace  # noqa: E402


def _creer_base_facture(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE ECRITURES (NUM_ECR INTEGER PRIMARY KEY, JOURNAL TEXT, DATE_ECR DATETIME, PIECE TEXT)")
    base.execute("CREATE TABLE LIGNES (NUM_ECR INTEGER, COMPTE TEXT, LIBELLE TEXT, DEBIT DECIMAL(12,2), CREDIT DECIMAL(12,2))")
    base.execute("CREATE TABLE COMPTEURS (CODE_JOURNAL TEXT PRIMARY KEY, DERNIER_NUM INTEGER)")
    base.execute("CREATE TABLE SESSIONS (ID INTEGER PRIMARY KEY, DERNIER TEXT)")
    base.execute("INSERT INTO ECRITURES VALUES (18341, 'ACH', '2025-01-10T00:00:00', '0041')")
    base.execute("INSERT INTO COMPTEURS VALUES ('ACH', 41)")
    base.execute("INSERT INTO SESSIONS VALUES (1, 'avant')")


SAISIES_FACTURE = [saisie("Journal", "ACH", "code"), saisie("Date", "2025-01-15", "date"),
                   saisie("Compte", "6111", "code"), saisie("Libellé", "TEST-S003", "texte"),
                   saisie("Débit", "1234.56")]


def _requetes_facture(debit: str) -> list[str]:
    return [
        "INSERT INTO ECRITURES VALUES (18342, 'ACH', '2025-01-15T00:00:00', '0042')",
        f"INSERT INTO LIGNES VALUES (18342, '6111', 'TEST-S003', '{debit}', '0.00')",
        "UPDATE COMPTEURS SET DERNIER_NUM=42 WHERE CODE_JOURNAL='ACH'",
        "UPDATE SESSIONS SET DERNIER='apres'",
    ]


def _trace_facture(base: sqlite3.Connection, jouer: Callable[..., Scenario], debit: str, **options: Any) -> dict[str, Any]:
    _creer_base_facture(base)
    s = jouer(_requetes_facture(debit), SAISIES_FACTURE, tables_bruit=["SESSIONS"])
    execution = Execution(DEBUT, FIN, "PC-COMPTA", "comptable", "Message : Écriture enregistrée sous le n° 2025-ACH-0042",
                          **options)
    fiche = FicheTrace("S-003", "Saisie facture achat avec TVA", tuple(SAISIES_FACTURE))
    return construire_trace(fiche, execution, r"\\SERVEUR\Compta_TEST\compta_test.mdb", s.diff, s.interpretation,
                            "sha256:abc")


@pytest.fixture
def trace_facture(base: sqlite3.Connection, jouer: Callable[..., Scenario]) -> dict[str, Any]:
    """Trace d'une facture d'achat : insertions, mise à jour, lien exact, hypothèses, bruit."""
    return _trace_facture(base, jouer, "1234.56")


@pytest.fixture
def trace_avec_ecart(base: sqlite3.Connection, jouer: Callable[..., Scenario]) -> dict[str, Any]:
    """Même scénario, mais 1243.56 a été saisi au lieu de 1234.56 : écart de saisie."""
    return _trace_facture(base, jouer, "1243.56")
