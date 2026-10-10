import logging
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from traceur.captures import capturer_ecran


class _Image:
    def save(self, chemin: Path, format: str) -> None:
        Path(chemin).write_bytes(b"\x89PNG-" + format.encode())


def test_capture_reussie(tmp_path: Path) -> None:
    cible = tmp_path / "sous" / "capture_debut.png"
    assert capturer_ecran(cible, _Image) is True
    assert cible.read_bytes() == b"\x89PNG-PNG"


def test_echec_de_capture_non_bloquant(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    def pas_d_ecran() -> Any:
        raise OSError("pas d'affichage")

    caplog.set_level(logging.WARNING, "traceur")
    cible = tmp_path / "c.png"
    assert capturer_ecran(cible, pas_d_ecran) is False and not cible.exists()
    assert "Capture d'écran impossible (c.png) : pas d'affichage" in caplog.text


def test_echec_pendant_l_enregistrement_ne_laisse_pas_de_fichier(tmp_path: Path) -> None:
    class Cassee:
        def save(self, chemin: Path, format: str) -> None:
            Path(chemin).write_bytes(b"partiel")
            raise OSError("disque plein")

    cible = tmp_path / "c.png"
    assert capturer_ecran(cible, Cassee) is False and not cible.exists()


def test_pillow_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "PIL", None)
    assert capturer_ecran(tmp_path / "c.png") is False


def _faux_pil(monkeypatch: pytest.MonkeyPatch, grab: Any) -> None:
    pil = types.ModuleType("PIL")
    module = types.ModuleType("PIL.ImageGrab")
    module.grab = grab  # type: ignore[attr-defined]
    pil.ImageGrab = module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "PIL", pil)
    monkeypatch.setitem(sys.modules, "PIL.ImageGrab", module)


def test_capture_par_defaut_prend_tous_les_ecrans(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    appels: list[dict[str, Any]] = []
    _faux_pil(monkeypatch, lambda **options: appels.append(options) or _Image())
    assert capturer_ecran(tmp_path / "c.png") is True and appels == [{"all_screens": True}]


def test_repli_sur_l_ecran_principal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    appels: list[dict[str, Any]] = []

    def grab(**options: Any) -> Any:
        appels.append(options)
        if options:
            raise OSError("all_screens non pris en charge")
        return _Image()

    caplog.set_level(logging.INFO, "traceur")
    _faux_pil(monkeypatch, grab)
    assert capturer_ecran(tmp_path / "c.png") is True and appels == [{"all_screens": True}, {}]
    assert "repli sur l'écran principal" in caplog.text


def test_echec_total_des_deux_captures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def grab(**options: Any) -> Any:
        raise OSError("pas d'écran")

    _faux_pil(monkeypatch, grab)
    assert capturer_ecran(tmp_path / "c.png") is False
