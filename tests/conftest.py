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
