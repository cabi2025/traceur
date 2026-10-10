"""`bruit.json` (F3) : écriture de la calibration et relecture des tables de bruit validées."""

from __future__ import annotations

import json
from pathlib import Path

from traceur.moteur.calibration import Calibration


def ecrire_bruit(calibration: Calibration, dossier: Path) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / "bruit.json"
    chemin.write_text(
        json.dumps(calibration.vers_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return chemin


def lire_tables_bruit(chemin: Path) -> list[str]:
    """Tables de bruit validées, à passer à `comparer_instantanes(tables_bruit=...)`."""
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    tables = donnees["tables_bruit"]
    if not isinstance(tables, list):
        raise ValueError("bruit.json : `tables_bruit` doit être une liste")
    return [str(t) for t in tables]
