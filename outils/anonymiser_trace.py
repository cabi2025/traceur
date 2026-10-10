"""Anonymise un `trace.json` réel pour en faire un jeu de test versionnable (AMB-042).

    python outils/anonymiser_trace.py donnees_reelles/S-201/trace.json tests/data/trace_S201_anonymisee.json

Remplacés : montants des cumuls (tables `compte`, `scompte`, `journal`, `sjournal` : avant / après, en
conservant exactement les **variations**, donc les hypothèses de cumul), nom du tiers, poste, utilisateur,
chemin de la base, empreinte du fichier. Conservés : structure, valeurs saisies de la fiche (fictives),
numéros de compte, compteurs, textes complétés par des espaces. Le script vérifie en sortie qu'aucune valeur
d'origine remplacée ne subsiste.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

TABLES_CUMUL = ("compte", "scompte", "journal", "sjournal")
_MONTANT = re.compile(r"\d+\.\d{4}")
TIERS_REEL = "AUTOROUTES DU MAROC"
TIERS_FICTIF = "TIERS FICTIF"
CHEMIN_FICTIF = "\\\\SERVEUR\\partage\\ZZ_TEST\\2026\\dossier.mdb"


def _fictif(reel: str) -> Decimal:
    """Montant fictif déterministe (mêmes entrées, mêmes sorties) entre 1 000,00 et 99 999 999,99."""
    n = int(hashlib.sha256(reel.encode()).hexdigest()[:10], 16)
    return Decimal(1000 * 100 + n % (99_999_999 * 100)) / Decimal(100)


def _construire_correspondances(trace: dict[str, Any]) -> dict[str, str]:
    table: dict[str, str] = {}
    for t in trace["changements"]:
        if t["table"] not in TABLES_CUMUL:
            continue
        for u in t.get("updates", []):
            for c in u["champs"]:
                if not (isinstance(c["avant"], str) and _MONTANT.fullmatch(c["avant"])
                        and isinstance(c["apres"], str) and _MONTANT.fullmatch(c["apres"])):
                    continue  # Piece (texte) : conservé
                delta = Decimal(c["apres"]) - Decimal(c["avant"])
                fictif_avant = _fictif(c["avant"])
                for reel, fictif in ((c["avant"], fictif_avant), (c["apres"], fictif_avant + delta)):
                    valeur = f"{fictif:.4f}"
                    if table.setdefault(reel, valeur) != valeur:
                        raise SystemExit(f"Conflit d'anonymisation sur la valeur {reel} (variations différentes).")
    return table


def _remplacer_texte(texte: str, correspondances: dict[str, str]) -> str:
    return _MONTANT.sub(lambda m: correspondances.get(m.group(0), m.group(0)), texte)


def anonymiser(trace: dict[str, Any]) -> dict[str, Any]:
    correspondances = _construire_correspondances(trace)
    for t in trace["changements"]:
        if t["table"] in TABLES_CUMUL:
            for u in t.get("updates", []):
                for c in u["champs"]:
                    c["avant"] = correspondances.get(c["avant"], c["avant"])
                    c["apres"] = correspondances.get(c["apres"], c["apres"])
    for champ in trace.get("champs_calcules", []):
        if champ["table"] in TABLES_CUMUL and isinstance(champ["valeur"], str):
            champ["valeur"] = correspondances.get(champ["valeur"], champ["valeur"])
        champ["details"] = _remplacer_texte(champ.get("details", ""), correspondances)
    texte = json.dumps(trace, ensure_ascii=False, indent=2)
    texte = texte.replace(TIERS_REEL.ljust(40), TIERS_FICTIF.ljust(40)).replace(TIERS_REEL, TIERS_FICTIF)
    sortie = json.loads(texte)
    sortie["execution"]["poste"] = "POSTE-TEST"
    sortie["execution"]["utilisateur_windows"] = "UTILISATEUR-TEST"
    sortie["execution"]["remarques"] = ""
    sortie["base"] = {"chemin": CHEMIN_FICTIF, "empreinte_fichier_avant": "sha256:" + "0" * 64}
    final = json.dumps(sortie, ensure_ascii=False)
    restes = [reel for reel in correspondances if reel in final and correspondances[reel] != reel]
    if restes or TIERS_REEL in final:
        raise SystemExit(f"Anonymisation incomplète : {restes[:3]}")
    return sortie  # type: ignore[no-any-return]


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    source, destination = Path(argv[1]), Path(argv[2])
    trace = json.loads(source.read_text(encoding="utf-8-sig"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(anonymiser(trace), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Écrit : {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
