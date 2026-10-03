"""Faux module pyodbc au-dessus de SQLite : permet de tester SourceAccess sans Windows ni Access."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from collections import namedtuple
from typing import Any

SQL_CHAR = 1
SQL_WCHAR = -8
Table = namedtuple("Table", "table_name table_type")
ColonneODBC = namedtuple("ColonneODBC", "column_name type_name ordinal_position")
CleODBC = namedtuple("CleODBC", "column_name key_seq")
Statistique = namedtuple("Statistique", "index_name ordinal_position column_name non_unique")


class Error(Exception):
    pass


class FauxCurseur:
    def __init__(self, connexion: FausseConnexion) -> None:
        self._c = connexion
        self._resultat: list[tuple[Any, ...]] = []
        self.ferme = False

    def tables(self, tableType: str = "TABLE") -> list[Table]:
        lignes = self._c.sqlite.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        tables = [Table(n, "TABLE") for (n,) in lignes] + [Table("MSysObjects", "SYSTEM TABLE")]
        return [t for t in tables if t.table_type == tableType]

    def columns(self, table: str) -> list[ColonneODBC]:
        infos = self._c.sqlite.execute(f'PRAGMA table_info("{table}")').fetchall()
        return [ColonneODBC(i[1], i[2], i[0] + 1) for i in infos]

    def primaryKeys(self, table: str) -> list[CleODBC]:
        self._c.appels_primary_keys += 1
        if not self._c.pk_supportee:
            raise Error("('IM001', '[IM001] [Microsoft][Gestionnaire de pilotes ODBC] Le pilote ne prend pas "
                        "cette fonction en charge (0) (SQLPrimaryKeys)')")
        infos = self._c.sqlite.execute(f'PRAGMA table_info("{table}")').fetchall()
        return [CleODBC(i[1], i[5]) for i in infos if i[5] > 0]

    def statistics(self, table: str, unique: bool = False, quick: bool = True) -> list[Statistique]:
        """Imite le pilote Jet : l'index de clé primaire s'appelle « PrimaryKey »."""
        if not self._c.statistiques_supportees:
            raise Error("('IM001', '[IM001] SQLStatistics non pris en charge')")
        lignes: list[Statistique] = [Statistique(None, 0, None, None)]  # ligne d'effectif de table
        infos = self._c.sqlite.execute(f'PRAGMA table_info("{table}")').fetchall()
        lignes += [Statistique("PrimaryKey", i[5], i[1], 0) for i in infos if i[5] > 0]
        for _, nom, unique_, *_ in self._c.sqlite.execute(f'PRAGMA index_list("{table}")').fetchall():
            if unique_ and not nom.startswith("sqlite_autoindex"):
                colonnes = self._c.sqlite.execute(f'PRAGMA index_info("{nom}")').fetchall()
                lignes += [Statistique(nom, c[0] + 1, c[2], 0) for c in colonnes]
        return lignes

    def execute(self, sql: str, *parametres: Any) -> FauxCurseur:
        if self._c.readonly and not sql.lstrip().upper().startswith("SELECT"):
            raise Error("HY000: ODBC Microsoft Access Driver : la requête doit utiliser une base modifiable.")
        sqlite_sql = re.sub(r"\[((?:[^\]]|\]\])+)\]", lambda m: '"' + m.group(1).replace("]]", "]") + '"', sql)
        if len(parametres) == 1 and isinstance(parametres[0], (tuple, list)):
            parametres = tuple(parametres[0])
        parametres = tuple(p.isoformat() if isinstance(p, datetime) else p for p in parametres)
        self._resultat = self._c.sqlite.execute(sqlite_sql, parametres).fetchall()
        return self

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._resultat.pop(0) if self._resultat else None

    def fetchmany(self, n: int) -> list[tuple[Any, ...]]:
        lot, self._resultat = self._resultat[:n], self._resultat[n:]
        return lot

    def close(self) -> None:
        self.ferme = True


class FausseConnexion:
    def __init__(self, sqlite_conn: sqlite3.Connection, chaine: str, readonly: bool, autocommit: bool) -> None:
        self.sqlite = sqlite_conn
        self.chaine = chaine
        self.readonly = readonly
        self.autocommit = autocommit
        self.decodages: list[tuple[int, str]] = []
        self.encodage: str | None = None
        self.fermee = False
        self.pk_supportee = True
        self.statistiques_supportees = True
        self.appels_primary_keys = 0

    def setdecoding(self, type_sql: int, encoding: str) -> None:
        self.decodages.append((type_sql, encoding))

    def setencoding(self, encoding: str) -> None:
        self.encodage = encoding

    def cursor(self) -> FauxCurseur:
        return FauxCurseur(self)

    def commit(self) -> None:
        self.sqlite.commit()

    def rollback(self) -> None:
        self.sqlite.rollback()

    def close(self) -> None:
        self.fermee = True


class FauxPyodbc:
    """Même interface que le module `pyodbc` pour ce qu'utilise SourceAccess."""

    Error = Error
    SQL_CHAR = SQL_CHAR
    SQL_WCHAR = SQL_WCHAR

    def __init__(self, sqlite_conn: sqlite3.Connection, pilotes: list[str] | None = None,
                 erreur_connexion: str | None = None, pk_supportee: bool = True,
                 statistiques_supportees: bool = True) -> None:
        self._pk_supportee = pk_supportee
        self._statistiques_supportees = statistiques_supportees
        self._sqlite = sqlite_conn
        self._pilotes = ["SQL Server", "Microsoft Access Driver (*.mdb)"] if pilotes is None else pilotes
        self._erreur = erreur_connexion
        self.connexions: list[FausseConnexion] = []

    def drivers(self) -> list[str]:
        return list(self._pilotes)

    def connect(self, chaine: str, readonly: bool = False, autocommit: bool = False) -> FausseConnexion:
        if self._erreur is not None:
            raise Error(self._erreur.replace("{chaine}", chaine))
        connexion = FausseConnexion(self._sqlite, chaine, readonly, autocommit)
        connexion.pk_supportee = self._pk_supportee
        connexion.statistiques_supportees = self._statistiques_supportees
        self.connexions.append(connexion)
        return connexion
