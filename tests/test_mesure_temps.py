"""Mesure du temps de photo (AMB-002) : affichée dans la sortie de pytest (option -s ou -rP)."""

import sqlite3
import time
from typing import Callable

import pytest

from traceur.moteur.diff import comparer_instantanes
from traceur.moteur.instantane import prendre_instantane
from traceur.sources.sqlite import SourceSqlite

NB_LIGNES = 100_000
OBJECTIF_S = 60.0  # SPEC §3, valable pour la vraie volumétrie ; ici simple garde-fou


def test_temps_de_photo_et_de_diff(
    base: sqlite3.Connection, source: SourceSqlite, record_property: Callable[[str, object], None]
) -> None:
    base.execute("CREATE TABLE GROS (ID INTEGER PRIMARY KEY, C TEXT, M DECIMAL(12,2), D DATE, N TEXT)")
    base.executemany(
        "INSERT INTO GROS VALUES (?,?,?,?,?)",
        ((i, f"C{i % 500}", f"{i}.25", "2025-01-15", None if i % 7 else "x") for i in range(NB_LIGNES)),
    )
    base.execute("CREATE TABLE SANS_PK (A TEXT, B TEXT)")
    base.executemany("INSERT INTO SANS_PK VALUES (?,?)", ((f"a{i % 50}", "b") for i in range(20_000)))

    avant = prendre_instantane(source)
    print("\n" + avant.resume())
    base.execute("INSERT INTO GROS VALUES (?,?,?,?,?)", (NB_LIGNES, "NEW", "1234.56", "2025-01-15", None))
    debut = time.perf_counter()
    apres = prendre_instantane(source)
    diff = comparer_instantanes(avant, apres)
    duree_diff = time.perf_counter() - debut
    print(f"Photo + diff : {duree_diff:.2f} s pour {apres.nb_lignes} lignes")

    record_property("duree_photo_s", f"{avant.duree_s:.3f}")
    record_property("nb_lignes", avant.nb_lignes)
    assert avant.nb_lignes == NB_LIGNES + 20_000
    assert avant.duree_s < OBJECTIF_S
    assert [t.table for t in diff.changements] == ["GROS"]
