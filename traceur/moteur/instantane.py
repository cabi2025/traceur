"""Photo d'une base via une SourceDonnees (F4, SPEC §6.2). Le temps de photo est mesuré."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Collection

from .normalisation import empreinte_ligne, empreinte_table
from .source import SchemaTable, SourceDonnees

journal = logging.getLogger("traceur.instantane")


@dataclass(frozen=True)
class Ligne:
    empreinte: str
    valeurs: tuple[Any, ...]


@dataclass
class TableInstantane:
    nom: str
    schema: SchemaTable
    nb_lignes: int
    empreinte: str
    lignes: list[Ligne]
    duree_s: float


@dataclass
class Instantane:
    tables: dict[str, TableInstantane] = field(default_factory=dict)
    duree_s: float = 0.0

    @property
    def nb_lignes(self) -> int:
        return sum(t.nb_lignes for t in self.tables.values())

    def resume(self) -> str:
        """Ligne affichable : temps total, puis temps par table (les plus longues d'abord)."""
        entete = (
            f"Photo : {len(self.tables)} tables, {self.nb_lignes} lignes "
            f"en {self.duree_s:.2f} s"
        )
        details = sorted(self.tables.values(), key=lambda t: t.duree_s, reverse=True)
        lignes = [f"  {t.nom} : {t.nb_lignes} lignes, {t.duree_s:.2f} s" for t in details]
        return "\n".join([entete, *lignes])


Progression = Callable[[str, int, int], None]
LOT_PROGRESSION = 20_000  # lignes lues entre deux notifications de progression


def prendre_instantane(
    source: SourceDonnees,
    tables_ignorees: Collection[str] = (),
    horloge: Callable[[], float] = time.perf_counter,
    progression: Progression | None = None,
) -> Instantane:
    """Photographie toutes les tables non ignorées (comparaison des noms insensible à la casse).

    `progression(message, fait, total)` est appelée à chaque table et tous les `LOT_PROGRESSION`
    lignes ; elle peut lever une exception pour interrompre la photo (annulation).
    """
    ignorees = {nom.lower() for nom in tables_ignorees}
    instantane = Instantane()
    debut = horloge()
    noms = [n for n in source.lister_tables() if n.lower() not in ignorees]
    for position, nom in enumerate(noms):
        debut_table = horloge()
        if progression is not None:
            progression(f"Lecture de la table {nom}", position, len(noms))
        schema = source.schema(nom)
        lignes: list[Ligne] = []
        for valeurs in source.lire_lignes(nom):
            lignes.append(Ligne(empreinte_ligne(valeurs), valeurs))
            if progression is not None and len(lignes) % LOT_PROGRESSION == 0:
                progression(f"Lecture de la table {nom} : {len(lignes)} lignes", position, len(noms))
        instantane.tables[nom] = TableInstantane(
            nom=nom,
            schema=schema,
            nb_lignes=len(lignes),
            empreinte=empreinte_table(ligne.empreinte for ligne in lignes),
            lignes=lignes,
            duree_s=horloge() - debut_table,
        )
    instantane.duree_s = horloge() - debut
    journal.info("%s", instantane.resume().splitlines()[0])
    return instantane
