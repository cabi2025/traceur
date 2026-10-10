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


def test_relations_faibles_listees_mais_non_dessinees(base: sqlite3.Connection) -> None:
    base.execute("CREATE TABLE CLIENTS (ID INTEGER PRIMARY KEY)")
    base.executemany("INSERT INTO CLIENTS VALUES (?)", [(i,) for i in range(1, 21)])
    base.execute("CREATE TABLE DEUX (FLAG INTEGER)")
    base.executemany("INSERT INTO DEUX VALUES (?)", [(1,), (2,), (1,)])
    html = generer_html(profiler(SourceSqlite(base)).vers_dict())
    assert "DEUX.FLAG" in html and "faible" in html  # dans le tableau
    assert "<svg" not in html  # aucune relation à dessiner
    assert "1 relation(s) à confiance faible" in html
    assert "Aucune relation candidate" in html


def test_avertissement_petite_table_sans_cle_primaire(base: sqlite3.Connection) -> None:
    """AMB-037 : une clé candidate sur moins de 50 lignes est signalée comme peu fiable."""
    base.execute("CREATE TABLE COMPTEURS (CODE TEXT, DERNIER INTEGER)")
    base.executemany("INSERT INTO COMPTEURS VALUES (?,?)", [("ACH", 3), ("VTE", 5), ("OD", 42)])
    base.execute("CREATE TABLE GROSSE (A INTEGER, B INTEGER)")
    base.executemany("INSERT INTO GROSSE VALUES (?,?)", [(i, 0) for i in range(60)])
    base.execute("CREATE TABLE PETITE_PK (ID INTEGER PRIMARY KEY, V INTEGER)")
    base.executemany("INSERT INTO PETITE_PK VALUES (?,?)", [(1, 0), (2, 0)])
    html = generer_html(profiler(SourceSqlite(base), version_jet="Jet 4").vers_dict())
    assert html.count("cette table a moins de 50 lignes") == 1  # ni GROSSE (60 lignes) ni PETITE_PK (clé primaire)
    debut = html.index("COMPTEURS <small>")
    fin = html.find("<h3", debut + 1)
    bloc = html[debut:] if fin < 0 else html[debut:fin]
    assert "cette table a moins de 50 lignes" in bloc and "peu fiable" in bloc
    assert "juste après une réinitialisation" in bloc
