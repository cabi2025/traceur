from pathlib import Path

from outils.demo_j5 import executer
from traceur.captures import capturer_ecran  # noqa: F401  (importé par la démo)


def _lancer(*args: str) -> tuple[int, str]:
    sorties: list[str] = []
    code = executer(list(args), sorties.append)
    return code, "\n".join(sorties)


def test_demo_depot_puis_partage_indisponible_puis_retabli(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    code, texte = _lancer("--sorties", str(tmp_path / "sorties"))
    assert code == 0 and "Trace déposée" in texte and (tmp_path / "sorties" / "index.html").is_file()
    bloc = tmp_path / "reseau"
    bloc.write_text("bloc", encoding="utf-8")
    code, texte = _lancer("--sorties", str(bloc / "sorties"), "--ecart")
    assert code == 0 and "en_attente_depot" in texte
    bloc.unlink()
    code, texte = _lancer("--sorties", str(bloc / "sorties"))
    assert "Reprise d'un dépôt en attente" in texte and "deposee" in texte
    assert len(list((bloc / "sorties" / "traces").iterdir())) == 2  # reprise + nouvelle trace
    assert list((tmp_path / "traces_locales").iterdir()) == []


def test_demo_capture_impossible_ne_bloque_pas(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    code, texte = _lancer("--sorties", str(tmp_path / "s"), "--capture")  # pas d'écran sous Linux : captures impossibles
    assert code == 0 and "Trace déposée" in texte
    assert "Capture debut :" in texte and "Capture fin :" in texte
