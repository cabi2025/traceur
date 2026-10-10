"""Captures d'écran automatiques (F9) via Pillow `ImageGrab`. Jamais bloquantes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

journal = logging.getLogger("traceur.captures")


def _grab_tous_les_ecrans() -> Any:
    """Tous les écrans (Windows : `all_screens=True`) ; repli sur l'écran principal en cas d'échec
    (AMB-030)."""
    from PIL import ImageGrab  # import tardif : Pillow n'est requis que pour cette fonction

    try:
        return ImageGrab.grab(all_screens=True)
    except Exception as erreur:  # noqa: BLE001 - paramètre ou système non pris en charge
        journal.info("Capture de tous les écrans impossible (%s) : repli sur l'écran principal.", erreur)
        return ImageGrab.grab()


def capturer_ecran(chemin: Path, grab: Callable[[], Any] | None = None) -> bool:
    """Enregistre une capture PNG. Retourne False (avec un avertissement) en cas d'échec :
    Pillow absent, pas d'écran, disque plein… La fiche continue sans capture."""
    try:
        image = (grab or _grab_tous_les_ecrans)()
        chemin.parent.mkdir(parents=True, exist_ok=True)
        image.save(chemin, format="PNG")
    except Exception as erreur:  # noqa: BLE001 - la capture ne doit jamais interrompre la fiche
        journal.warning("Capture d'écran impossible (%s) : %s", chemin.name, erreur)
        chemin.unlink(missing_ok=True)
        return False
    return True
