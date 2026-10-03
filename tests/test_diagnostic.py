import json
import sqlite3
from pathlib import Path

import pytest

from fake_pyodbc import FauxPyodbc
from outils.diagnostic import executer


@pytest.fixture
def poste(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    monkeypatch.chdir(tmp_path)
    base = tmp_path / "test.mdb"
    entete = bytearray(64)
    entete[4:19] = b"Standard Jet DB"
    entete[0x14] = 1
    base.write_bytes(bytes(entete))
    (tmp_path / "reference.mdb").write_bytes(bytes(entete))
    config = {
        "base_test": str(base), "instantane_reference": str(tmp_path / "reference.mdb"),
        "chemins_interdits": [r"\\SERVEUR\Compta\compta.mdb"], "fichier_fiches": "f.json",
        "dossier_sorties": str(tmp_path / "sorties"), "mot_de_passe": "S3cr3t!",
    }
    (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
    sqlite = sqlite3.connect(":memory:")
    sqlite.execute("CREATE TABLE A (ID INTEGER PRIMARY KEY, M CURRENCY)")
    sqlite.executemany("INSERT INTO A VALUES (?,?)", [(i, str(i)) for i in range(1, 6)])
    return {"config": config, "sqlite": sqlite, "dossier": tmp_path, "base": base}


def _lancer(poste: dict[str, object], *args: str, pilotes: list[str] | None = None,
            reponse: str = "OUI") -> tuple[int, str]:
    sorties: list[str] = []
    faux = FauxPyodbc(poste["sqlite"], pilotes=pilotes)  # type: ignore[arg-type]
    code = executer(["--config", "config.json", *args], faux, lambda _: reponse, sorties.append)
    return code, "\n".join(sorties)


def test_diagnostic_complet_ok_sans_mot_de_passe_dans_les_sorties(poste: dict[str, object]) -> None:
    code, texte = _lancer(poste, "--photo", "--profil")
    assert code == 0 and "Diagnostic terminé : tout est OK." in texte
    for attendu in ("[1/6] Python", "pilote retenu : Microsoft Access Driver (*.mdb)", "format : Jet 4",
                    "5 lignes au total", "temps de photo", "profil écrit", "connexion fermée"):
        assert attendu in texte, attendu
    assert "S3cr3t!" not in texte and "fourni (non affiché)" in texte
    dossier = poste["dossier"]
    assert (dossier / "diagnostic_sorties" / "profil" / "profil.html").exists()  # type: ignore[operator]
    assert "S3cr3t!" not in (dossier / "journal.log").read_text(encoding="utf-8")  # type: ignore[operator]


def test_pas_de_pilote(poste: dict[str, object]) -> None:
    code, texte = _lancer(poste, pilotes=["SQL Server"])
    assert code == 1 and "ÉCHEC" in texte and "Aucun pilote ODBC Access" in texte and "[3/6]" not in texte


def test_refus_si_base_de_production(poste: dict[str, object]) -> None:
    config = dict(poste["config"])  # type: ignore[call-overload]
    config["chemins_interdits"] = [config["base_test"]]
    (poste["dossier"] / "config.json").write_text(json.dumps(config), encoding="utf-8")  # type: ignore[operator]
    code, texte = _lancer(poste)
    assert code == 1 and "DÉMARRAGE REFUSÉ" in texte and "[5/6]" not in texte


def test_configuration_absente(poste: dict[str, object]) -> None:
    (poste["dossier"] / "config.json").unlink()  # type: ignore[operator]
    code, texte = _lancer(poste)
    assert code == 1 and "introuvable" in texte


def test_reinitialisation_confirmee_et_annulee(poste: dict[str, object]) -> None:
    base = poste["base"]
    base.write_bytes(b"MODIFIEE")  # type: ignore[attr-defined]
    code, texte = _lancer(poste, "--reinitialiser", reponse="non")
    assert code == 0 and "annulée" in texte and base.read_bytes() == b"MODIFIEE"  # type: ignore[attr-defined]
    code, texte = _lancer(poste, "--reinitialiser", reponse="OUI")
    assert code == 0 and "copie vérifiée" in texte
    assert base.read_bytes() == (poste["dossier"] / "reference.mdb").read_bytes()  # type: ignore[attr-defined,operator]
