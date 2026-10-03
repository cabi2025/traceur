"""Calibration du bruit (F3, SPEC §6.5) : tables qui bougent sans aucune action."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Collection

from .diff import comparer_instantanes, resume_table
from .instantane import prendre_instantane
from .source import SourceDonnees

INTERVALLE_DEFAUT_S = 30.0


@dataclass
class Calibration:
    debut: datetime
    fin: datetime
    intervalle_s: float
    proposees: dict[str, str] = field(default_factory=dict)  # table -> résumé
    tables_ignorees: list[str] = field(default_factory=list)  # TODO(AMB-018)
    tables_bruit: list[str] = field(default_factory=list)  # validées par l'utilisateur

    def valider(self, tables: Collection[str]) -> None:
        """Enregistre le choix de l'utilisateur (sous-ensemble des tables proposées)."""
        inconnues = set(tables) - set(self.proposees)
        if inconnues:
            raise ValueError(f"Tables non proposées par la calibration : {sorted(inconnues)}")
        self.tables_bruit = [t for t in self.proposees if t in set(tables)]

    def vers_dict(self) -> dict[str, Any]:
        return {
            "format_version": "1.0",
            "debut": self.debut.isoformat(timespec="seconds"),
            "fin": self.fin.isoformat(timespec="seconds"),
            "intervalle_s": self.intervalle_s,
            "tables_bruit_proposees": [
                {"table": t, "resume": r} for t, r in self.proposees.items()
            ],
            "tables_bruit": list(self.tables_bruit),
            "tables_ignorees": list(self.tables_ignorees),
        }


def calibrer(
    source: SourceDonnees,
    intervalle_s: float = INTERVALLE_DEFAUT_S,
    tables_ignorees: Collection[str] = (),
    dormir: Callable[[float], None] = time.sleep,
    maintenant: Callable[[], datetime] = datetime.now,
) -> Calibration:
    """Deux photos espacées de `intervalle_s` secondes, sans action. Propose les tables qui changent.

    Par défaut toutes les tables proposées sont retenues ; l'utilisateur ajuste avec `valider`.
    Les `tables_ignorees` (configuration) sont exclues des photos (AMB-018, provisoire).
    """
    debut = maintenant()
    avant = prendre_instantane(source, tables_ignorees)
    dormir(intervalle_s)
    apres = prendre_instantane(source, tables_ignorees)
    resultat = comparer_instantanes(avant, apres)
    calibration = Calibration(
        debut, maintenant(), intervalle_s, tables_ignorees=sorted(tables_ignorees)
    )
    for diff in resultat.changements:
        calibration.proposees[diff.table] = resume_table(diff)
    for modif in resultat.schema_modifie:
        calibration.proposees.setdefault(modif.table, "schéma modifié")
    calibration.tables_bruit = list(calibration.proposees)
    return calibration
