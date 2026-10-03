"""Sonde ce que le pilote ODBC Access répond pour chaque table (diagnostic des clés primaires).
Lecture seule. À lancer si les clés primaires ne sont pas reconnues (étape 10 de LISEZMOI_J4) :

    python outils\\sonder_pilote.py C:\\Traceur\\test\\synthetique.mdb [--mot-de-passe XXX]
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from traceur.sources.access import ErreurAccess, ParametresAccess, SourceAccess, importer_pyodbc


def sonder(chemin: str, mot_de_passe: str | None = None, sortie=print) -> int:  # type: ignore[no-untyped-def]
    try:
        pyodbc = importer_pyodbc()
        source = SourceAccess(ParametresAccess(chemin, mot_de_passe=mot_de_passe), pyodbc)
    except ErreurAccess as erreur:
        sortie(f"Erreur : {erreur}")
        return 1
    try:
        for table in source.lister_tables():
            curseur = source._connexion.cursor()
            sortie(f"\n== {table}")
            try:
                cles = [(k.key_seq, k.column_name) for k in curseur.primaryKeys(table=table)]
                sortie(f"  primaryKeys : {cles}")
            except pyodbc.Error as erreur:
                sortie(f"  primaryKeys : NON PRIS EN CHARGE ({str(erreur)[:90]})")
            try:
                for ligne in curseur.statistics(table=table, unique=True):
                    sortie(f"  statistics  : index={ligne.index_name!r} type={ligne.type} "
                           f"position={ligne.ordinal_position} colonne={ligne.column_name!r} "
                           f"non_unique={ligne.non_unique}")
            except pyodbc.Error as erreur:
                sortie(f"  statistics  : NON PRIS EN CHARGE ({str(erreur)[:90]})")
            sortie(f"  clé retenue par le traceur : {source.schema(table).cle_primaire or 'aucune'}")
            curseur.close()
    finally:
        source.fermer()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description="Sonde les clés primaires vues par le pilote.")
    parseur.add_argument("chemin")
    parseur.add_argument("--mot-de-passe")
    args = parseur.parse_args(argv)
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")
    return sonder(args.chemin, args.mot_de_passe)


if __name__ == "__main__":
    sys.exit(main())
