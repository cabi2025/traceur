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
        infos = self._c.sqlite.execute(f'PRAGMA table_info("{table}")').fetchall()
        return [CleODBC(i[1], i[5]) for i in infos if i[5] > 0]

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
                 erreur_connexion: str | None = None) -> None:
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
        self.connexions.append(connexion)
        return connexion
