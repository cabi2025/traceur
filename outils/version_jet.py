"""Détecte la version Jet d'un fichier .mdb (AMB-001) en lisant son en-tête.

Usage : python outils/version_jet.py chemin\\vers\\base.mdb
Le fichier est ouvert en lecture seule et seuls les premiers octets sont lus.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

DECALAGE_SIGNATURE = 0x04
DECALAGE_VERSION = 0x14
SIGNATURES = (b"Standard Jet DB", b"Standard ACE DB")
VERSIONS = {0: "Jet 3", 1: "Jet 4"}


@dataclass(frozen=True)
class VersionJet:
    octet: int
    libelle: str


class FormatInconnu(ValueError):
    """Le fichier n'a pas l'en-tête d'une base Jet."""


def version_jet(chemin: str | Path) -> VersionJet:
    with open(chemin, "rb") as f:
        entete = f.read(DECALAGE_VERSION + 1)
    if len(entete) <= DECALAGE_VERSION:
        raise FormatInconnu("Fichier trop court pour être une base Access.")
    signature = entete[DECALAGE_SIGNATURE : DECALAGE_SIGNATURE + 15]
    if signature not in SIGNATURES:
        raise FormatInconnu("Signature Jet absente : ce n'est pas une base Access .mdb.")
    octet = entete[DECALAGE_VERSION]
    return VersionJet(octet, VERSIONS.get(octet, f"inconnue (octet 0x14 = {octet})"))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    try:
        resultat = version_jet(argv[1])
    except (OSError, FormatInconnu) as erreur:
        print(f"Erreur : {erreur}")
        return 1
    print(f"{resultat.libelle} (octet 0x14 = {resultat.octet})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
