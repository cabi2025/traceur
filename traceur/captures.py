"""Captures d'écran automatiques (F9) via Pillow `ImageGrab`. Jamais bloquantes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

journal = logging.getLogger("traceur.captures")


def _grab_ecran_principal() -> Any:
    from PIL import ImageGrab  # import tardif : Pillow n'est requis que pour cette fonction

    return ImageGrab.grab()  # AMB-030 : écran principal


def capturer_ecran(chemin: Path, grab: Callable[[], Any] | None = None) -> bool:
    """Enregistre une capture PNG. Retourne False (avec un avertissement) en cas d'échec :
    Pillow absent, pas d'écran, disque plein… La fiche continue sans capture."""
    try:
        image = (grab or _grab_ecran_principal)()
        chemin.parent.mkdir(parents=True, exist_ok=True)
        image.save(chemin, format="PNG")
    except Exception as erreur:  # noqa: BLE001 - la capture ne doit jamais interrompre la fiche
        journal.warning("Capture d'écran impossible (%s) : %s", chemin.name, erreur)
        chemin.unlink(missing_ok=True)
        return False
    return True
