"""Interface d'accès aux données (SPEC §6.1). Le moteur ne connaît que ceci."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Protocol


@dataclass(frozen=True)
class Colonne:
    nom: str
    type_declare: str


@dataclass(frozen=True)
class SchemaTable:
    colonnes: tuple[Colonne, ...]
    cle_primaire: tuple[str, ...] = ()

    def noms(self) -> tuple[str, ...]:
        return tuple(c.nom for c in self.colonnes)


class SourceDonnees(Protocol):
    """Source en lecture seule. Les lignes sont des tuples dans l'ordre de `schema().colonnes`."""

    def lister_tables(self) -> list[str]: ...

    def schema(self, table: str) -> SchemaTable: ...

    def lire_lignes(self, table: str) -> Iterator[tuple[Any, ...]]: ...
