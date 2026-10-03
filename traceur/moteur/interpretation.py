"""Interprétation d'un diff : liens, écarts de saisie, champs calculés (F6, F7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence

from .calcules import ChampCalcule, detecter_champs_calcules
from .cellules import extraire_cellules
from .diff import Avertissement, ResultatDiff
from .instantane import Instantane
from .liens import EcartSaisie, Lien, ValeurSaisie, chercher_liens
from .profilage import Profil


@dataclass
class ResultatInterpretation:
    liens: list[Lien] = field(default_factory=list)
    ecarts_saisie: list[EcartSaisie] = field(default_factory=list)
    champs_calcules: list[ChampCalcule] = field(default_factory=list)
    avertissements: list[Avertissement] = field(default_factory=list)

    @property
    def a_un_ecart_de_saisie(self) -> bool:
        """La trace porte alors le statut `ecart_saisie` (SPEC §7.4, §8.2)."""
        return bool(self.ecarts_saisie)

    def vers_dict(self) -> dict[str, Any]:
        return {
            "liens": [x.vers_dict() for x in self.liens],
            "champs_calcules": [x.vers_dict() for x in self.champs_calcules],
            "ecarts_saisie": [x.vers_dict() for x in self.ecarts_saisie],
            "avertissements": [x.vers_dict() for x in self.avertissements],
        }


def interpreter(
    diff: ResultatDiff,
    avant: Instantane,
    apres: Instantane,
    saisies: Sequence[ValeurSaisie],
    debut: datetime,
    fin: datetime,
    profil: Profil | None = None,
) -> ResultatInterpretation:
    """Lie les valeurs saisies aux colonnes écrites, puis émet des hypothèses pour le reste.

    `profil` : profil de la base avant l'action ; sans lui, `constante`, `copie` et
    `somme_lignes` sont désactivées avec un avertissement (AMB-010).
    """
    resultat = ResultatInterpretation()
    cellules = extraire_cellules(diff, apres)
    resultat.liens, resultat.ecarts_saisie, expliquees = chercher_liens(
        saisies, cellules, resultat.avertissements
    )
    resultat.champs_calcules = detecter_champs_calcules(
        diff, cellules, expliquees, avant, apres, saisies, debut, fin, profil,
        resultat.avertissements,
    )
    return resultat
