"""SourceDonnees SQLite, utilisée par les tests du moteur (SPEC §6.1)."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterator

from traceur.moteur.source import Colonne, SchemaTable

Convertisseur = Callable[[Any], Any]


def _vers_decimal(valeur: Any) -> Any:
    if valeur is None or isinstance(valeur, Decimal):
        return valeur
    return Decimal(repr(valeur) if isinstance(valeur, float) else str(valeur))


def _vers_date(valeur: Any) -> Any:
    return date.fromisoformat(valeur) if isinstance(valeur, str) else valeur


def _vers_datetime(valeur: Any) -> Any:
    return datetime.fromisoformat(valeur) if isinstance(valeur, str) else valeur


def _convertisseur(type_declare: str) -> Convertisseur | None:
    """Imite les types riches d'Access à partir du type déclaré SQLite."""
    t = type_declare.upper()
    if t.startswith(("DECIMAL", "CURRENCY", "NUMERIC", "MONEY")):
        return _vers_decimal
    if t in ("DATETIME", "TIMESTAMP"):
        return _vers_datetime
    if t == "DATE":
        return _vers_date
    return None


def _citer(identifiant: str) -> str:
    return '"' + identifiant.replace('"', '""') + '"'


class SourceSqlite:
    def __init__(self, connexion: sqlite3.Connection) -> None:
        self._connexion = connexion

    @classmethod
    def ouvrir(cls, chemin: str | Path) -> SourceSqlite:
        """Ouvre un fichier SQLite en lecture seule."""
        uri = Path(chemin).resolve().as_uri() + "?mode=ro"
        return cls(sqlite3.connect(uri, uri=True))

    def lister_tables(self) -> list[str]:
        curseur = self._connexion.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        return [ligne[0] for ligne in curseur]

    def schema(self, table: str) -> SchemaTable:
        infos = self._connexion.execute(f"PRAGMA table_info({_citer(table)})").fetchall()
        colonnes = tuple(Colonne(i[1], i[2] or "") for i in infos)
        cle = tuple(i[1] for i in sorted((i for i in infos if i[5] > 0), key=lambda i: i[5]))
        return SchemaTable(colonnes, cle)

    def lire_lignes(self, table: str) -> Iterator[tuple[Any, ...]]:
        conversions = [_convertisseur(c.type_declare) for c in self.schema(table).colonnes]
        curseur = self._connexion.execute(f"SELECT * FROM {_citer(table)}")
        if not any(conversions):
            yield from curseur
            return
        for ligne in curseur:
            yield tuple(
                conv(v) if conv is not None else v for conv, v in zip(conversions, ligne)
            )
