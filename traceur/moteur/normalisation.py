"""Normalisation des valeurs et empreintes (SPEC §6.2).

Chaque valeur est écrite avec un préfixe de type pour que `1` (entier), `"1"` (texte)
et `Decimal("1")` ne puissent jamais produire la même empreinte.
"""

from __future__ import annotations

import hashlib
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Sequence

MARQUEUR_NUL = "N:"


def normaliser_valeur(valeur: Any) -> str:
    """Forme textuelle stable d'une valeur. Le texte est en NFC, sans trim."""
    if valeur is None:
        return MARQUEUR_NUL
    if isinstance(valeur, bool):
        return "L:1" if valeur else "L:0"
    if isinstance(valeur, int):
        return f"I:{valeur}"
    if isinstance(valeur, Decimal):
        return f"M:{format(valeur, 'f')}"
    if isinstance(valeur, float):
        return f"F:{valeur!r}"
    if isinstance(valeur, datetime):
        return f"D:{valeur.isoformat()}"
    if isinstance(valeur, date):
        return f"J:{valeur.isoformat()}"
    if isinstance(valeur, (bytes, bytearray, memoryview)):
        return f"B:{hashlib.sha256(bytes(valeur)).hexdigest()}"
    if isinstance(valeur, str):
        return f"T:{unicodedata.normalize('NFC', valeur)}"
    raise TypeError(f"Type de valeur non géré : {type(valeur).__name__}")


def empreinte_ligne(valeurs: Sequence[Any]) -> str:
    """Empreinte d'une ligne (sensible à l'ordre des colonnes)."""
    h = hashlib.sha256()
    for valeur in valeurs:
        octets = normaliser_valeur(valeur).encode("utf-8")
        h.update(f"{len(octets)}:".encode("ascii"))
        h.update(octets)
    return h.hexdigest()


def empreinte_table(empreintes_lignes: Iterable[str]) -> str:
    """Empreinte d'une table : indépendante de l'ordre des lignes, sensible aux doublons."""
    h = hashlib.sha256()
    for empreinte in sorted(empreintes_lignes):
        h.update(empreinte.encode("ascii"))
    return h.hexdigest()


def valeur_json(valeur: Any) -> Any:
    """Valeur écrite dans `trace.json` : montants en chaîne exacte, dates ISO, jamais de flottant."""
    if valeur is None or isinstance(valeur, str):
        return valeur
    if isinstance(valeur, bool):
        return int(valeur)
    if isinstance(valeur, int):
        return valeur
    if isinstance(valeur, Decimal):
        return format(valeur, "f")
    if isinstance(valeur, float):
        return repr(valeur)
    if isinstance(valeur, (date, datetime)):
        return valeur.isoformat()
    if isinstance(valeur, (bytes, bytearray, memoryview)):
        return f"sha256:{hashlib.sha256(bytes(valeur)).hexdigest()}"
    raise TypeError(f"Type de valeur non géré : {type(valeur).__name__}")
