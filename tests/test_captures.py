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


def test_capture_par_defaut_utilise_imagegrab(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    appels: list[str] = []
    pil = types.ModuleType("PIL")
    grab = types.ModuleType("PIL.ImageGrab")
    grab.grab = lambda: appels.append("grab") or _Image()  # type: ignore[attr-defined]
    pil.ImageGrab = grab  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "PIL", pil)
    monkeypatch.setitem(sys.modules, "PIL.ImageGrab", grab)
    assert capturer_ecran(tmp_path / "c.png") is True and appels == ["grab"]
