from pathlib import Path

import pytest

from outils.version_jet import FormatInconnu, main, version_jet


def _fichier(chemin: Path, octet: int, signature: bytes = b"Standard Jet DB") -> Path:
    entete = bytearray(64)
    entete[0:4] = b"\x00\x01\x00\x00"
    entete[4 : 4 + len(signature)] = signature
    entete[0x14] = octet
    chemin.write_bytes(bytes(entete))
    return chemin


def test_jet3(tmp_path: Path) -> None:
    assert version_jet(_fichier(tmp_path / "a.mdb", 0)).libelle == "Jet 3"


def test_jet4(tmp_path: Path) -> None:
    assert version_jet(_fichier(tmp_path / "a.mdb", 1)).libelle == "Jet 4"


def test_version_inconnue(tmp_path: Path) -> None:
    resultat = version_jet(_fichier(tmp_path / "a.mdb", 7))
    assert resultat.octet == 7 and "inconnue" in resultat.libelle


def test_fichier_non_access(tmp_path: Path) -> None:
    f = tmp_path / "x.mdb"
    f.write_bytes(b"x" * 100)
    with pytest.raises(FormatInconnu):
        version_jet(f)


def test_fichier_trop_court(tmp_path: Path) -> None:
    f = tmp_path / "x.mdb"
    f.write_bytes(b"\x00\x01")
    with pytest.raises(FormatInconnu):
        version_jet(f)


def test_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version_jet", str(_fichier(tmp_path / "a.mdb", 1))]) == 0
    assert "Jet 4" in capsys.readouterr().out
    assert main(["version_jet", str(tmp_path / "absent.mdb")]) == 1
