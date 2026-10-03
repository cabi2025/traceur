import json
import re
import sqlite3
from html.parser import HTMLParser
from pathlib import Path

from traceur.moteur.profilage import profiler
from traceur.rapports.profil import ecrire_profil, generer_html
from traceur.sources.sqlite import SourceSqlite


def _base(base: sqlite3.Connection) -> sqlite3.Connection:
    base.execute("CREATE TABLE CLIENTS (ID INTEGER PRIMARY KEY, LIBELLÉ TEXT)")
    base.execute("CREATE TABLE FACTURES (NUM INTEGER PRIMARY KEY, CLIENT_ID INTEGER)")
    base.executemany("INSERT INTO CLIENTS VALUES (?,?)", [(i, f"é{i}") for i in range(1, 6)])
    base.executemany("INSERT INTO FACTURES VALUES (?,?)", [(100 + i, 1 + i % 5) for i in range(20)])
    return base


class _Compteur(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.balises: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.balises.append(tag)


def test_html_autonome_sans_reseau(base: sqlite3.Connection) -> None:
    profil = profiler(SourceSqlite(_base(base)), version_jet="Jet 3")
    html = generer_html(profil.vers_dict())
    for interdit in ("http:", "https:", "//", "<script", "<link", "src=", "href=", "@import"):
        assert interdit not in html, interdit
    assert not re.search(r"url\((?!#)", html)  # seules les références internes (#id)
    p = _Compteur()
    p.feed(html)
    assert "svg" in p.balises and "style" in p.balises
    assert "Version Jet : <b>Jet 3</b>" in html
    assert "CLIENT_ID → ID (100,00 %)" in html
    assert "FACTURES" in html and "LIBELLÉ" in html


def test_html_sans_relation(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE A (X INTEGER)")
    html = generer_html(profiler(SourceSqlite(base)).vers_dict())
    assert "Aucune relation candidate" in html and "non détectée" in html


def test_html_echappe_les_noms(base: sqlite3.Connection) -> None:
    base.execute('CREATE TABLE "A<B>" (X INTEGER)')
    html = generer_html(profiler(SourceSqlite(base)).vers_dict())
    assert "A<B>" not in html and "A&lt;B&gt;" in html


def test_ecriture_utf8(base: sqlite3.Connection, tmp_path: Path) -> None:
    profil = profiler(SourceSqlite(_base(base)))
    chemin_json, chemin_html = ecrire_profil(profil, tmp_path / "profil")
    assert json.loads(chemin_json.read_text(encoding="utf-8")) == profil.vers_dict()
    assert "LIBELLÉ" in chemin_html.read_text(encoding="utf-8")
    assert "LIBELLÉ" in chemin_json.read_text(encoding="utf-8")  # pas d'échappement \u


def test_profil_json_sans_flottant(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE A (M DECIMAL(10,2))")
    base.executemany("INSERT INTO A VALUES (?)", [("1.10",), ("2.25",)])
    d = profiler(SourceSqlite(base)).vers_dict()
    assert d["tables"][0]["colonnes"][0]["min"] == "1.1"
    assert not any(isinstance(v, float) for v in json.loads(json.dumps(d)).values())
