"""Démonstration de J5 : fabrique une trace d'exemple (base SQLite en mémoire, aucune base Access),
fait les captures d'écran si demandé, puis l'écrit en local et la dépose dans un dossier de sortie.
Rejoue d'abord les dépôts en attente (comme au démarrage du traceur).

    python outils\\demo_j5.py --sorties C:\\Traceur\\sorties
    python outils\\demo_j5.py --sorties \\\\SERVEUR\\Partage\\Traceur\\sorties --capture
    python outils\\demo_j5.py --sorties Z:\\inexistant              (partage indisponible : reste en local)

Rien n'est écrit ailleurs que dans `--local` (défaut : traces_locales) et `--sorties`.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Sequence

from traceur.captures import capturer_ecran
from traceur.moteur.diff import comparer_instantanes
from traceur.moteur.instantane import prendre_instantane
from traceur.moteur.interpretation import interpreter
from traceur.moteur.liens import ValeurSaisie
from traceur.moteur.profilage import cles_candidates_du_profil, profiler
from traceur.rapports.depot import DEPOSEE, enregistrer_trace, reprendre_depots_en_attente
from traceur.rapports.trace import Execution, FicheTrace, construire_trace
from traceur.sources.sqlite import SourceSqlite

SAISIES = (ValeurSaisie("Journal", "001", "ACH", "code"), ValeurSaisie("Date", "001", "2025-01-15", "date"),
           ValeurSaisie("Compte", "001", "6111", "code"), ValeurSaisie("Libellé", "001", "TEST-DEMO", "texte"),
           ValeurSaisie("Débit", "001", "1234.56", "montant"))


def _trace_exemple(ecart: bool, debut: datetime, fin: datetime):  # type: ignore[no-untyped-def]
    base = sqlite3.connect(":memory:")
    base.executescript("""
        CREATE TABLE ECRITURES (NUM_ECR INTEGER PRIMARY KEY, JOURNAL TEXT, DATE_ECR DATETIME, PIECE TEXT);
        CREATE TABLE LIGNES (NUM_ECR INTEGER, COMPTE TEXT, LIBELLE TEXT, DEBIT DECIMAL(12,2), CREDIT DECIMAL(12,2));
        CREATE TABLE COMPTEURS (CODE_JOURNAL TEXT PRIMARY KEY, DERNIER_NUM INTEGER);
        INSERT INTO ECRITURES VALUES (18341, 'ACH', '2025-01-10T00:00:00', '0041');
        INSERT INTO COMPTEURS VALUES ('ACH', 41);""")
    source = SourceSqlite(base)
    profil = profiler(source)
    avant = prendre_instantane(source)
    debit = "1243.56" if ecart else "1234.56"
    base.executescript(f"""
        INSERT INTO ECRITURES VALUES (18342, 'ACH', '2025-01-15T00:00:00', '0042');
        INSERT INTO LIGNES VALUES (18342, '6111', 'TEST-DEMO', '{debit}', '0.00');
        UPDATE COMPTEURS SET DERNIER_NUM = 42 WHERE CODE_JOURNAL = 'ACH';""")
    apres = prendre_instantane(source)
    diff = comparer_instantanes(avant, apres, cles_candidates_du_profil(profil))
    interpretation = interpreter(diff, avant, apres, SAISIES, debut, fin, profil)
    execution = Execution(debut, fin, remarques="Message : Écriture enregistrée sous le n° 2025-ACH-0042 (démonstration)")
    return construire_trace(FicheTrace("S-DEMO", "Démonstration J5 (données fictives)", SAISIES), execution,
                            "(base fictive en mémoire)", diff, interpretation)


def executer(argv: Sequence[str] | None = None, sortie: Callable[[str], None] = print) -> int:
    parseur = argparse.ArgumentParser(description="Démonstration du rapport et du dépôt (J5).")
    parseur.add_argument("--sorties", required=True, help="dossier de dépôt (local ou partage réseau)")
    parseur.add_argument("--local", default="traces_locales", help="dossier local de travail")
    parseur.add_argument("--capture", action="store_true", help="prend les 2 captures d'écran (Pillow requis)")
    parseur.add_argument("--ecart", action="store_true", help="simule un écart de saisie (1243.56 au lieu de 1234.56)")
    args = parseur.parse_args(argv)
    local, sorties = Path(args.local), Path(args.sorties)

    for r in reprendre_depots_en_attente(local, sorties):
        sortie(f"Reprise d'un dépôt en attente : {r.nom} → {r.statut}" + (f" ({r.erreur})" if r.erreur else ""))

    fin = datetime.now().replace(microsecond=0)
    debut = fin - timedelta(seconds=30)
    captures: dict[str, Path | None] = {}
    with tempfile.TemporaryDirectory() as temporaire:
        if args.capture:
            for cle in ("debut", "fin"):
                chemin = Path(temporaire) / f"{cle}.png"
                captures[cle] = chemin if capturer_ecran(chemin) else None
                sortie(f"Capture {cle} : {'faite' if captures[cle] else 'IMPOSSIBLE (voir journal)'}")
        resultat = enregistrer_trace(_trace_exemple(args.ecart, debut, fin), local, sorties, captures)
    if resultat.statut == DEPOSEE:
        sortie(f"Trace déposée : {resultat.destination}")
        sortie(f"Index : {sorties / 'index.html'}" + ("" if resultat.index_a_jour else " (NON mis à jour)"))
    else:
        sortie(f"Partage indisponible ({resultat.erreur}) : la trace reste en local, en_attente_depot.")
        sortie(f"Relancez cette commande quand le partage est revenu : la reprise est automatique.")
    return 0


if __name__ == "__main__":
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(executer())
