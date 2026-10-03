from __future__ import annotations

import sqlite3
from typing import Iterator

import pytest

from traceur.sources.sqlite import SourceSqlite


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
from typing import Callable, Sequence  # noqa: E402

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
