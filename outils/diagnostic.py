"""Diagnostic du traceur sur un poste (J4) : Python, pilote ODBC, configuration, contrôles de
sécurité, version Jet, connexion en lecture seule, temps de photo, profil, réinitialisation.

    python outils\\diagnostic.py --config config.json            vérifications (aucune écriture)
    python outils\\diagnostic.py --config config.json --photo    + temps de photo (AMB-002)
    python outils\\diagnostic.py --config config.json --profil   + profil.json / profil.html
    python outils\\diagnostic.py --config config.json --reinitialiser   (écrase la base de TEST !)

Hors `--reinitialiser`, le script ne modifie aucun fichier de la base (lecture seule) ; il n'essaie
jamais d'écrire dans la base. Le mot de passe n'est ni affiché ni écrit dans journal.log.
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

from traceur.config import Configuration, ErreurConfiguration, charger_configuration
from traceur.moteur.instantane import prendre_instantane
from traceur.moteur.profilage import profiler
from traceur.rapports.profil import ecrire_profil
from traceur.securite import (
    ErreurSecurite,
    ReinitialisationAnnulee,
    chemin_verrou,
    configurer_journal,
    reinitialiser_base_test,
    verifier_demarrage,
)
from traceur.sources.access import (
    ErreurAccess,
    ParametresAccess,
    SourceAccess,
    choisir_pilote,
    importer_pyodbc,
    version_jet_de,
)

OBJECTIF_PHOTO_S = 60.0
TOTAL_ETAPES = 6


class _Arret(Exception):
    pass


def executer(
    argv: Sequence[str] | None = None,
    pyodbc_module: Any | None = None,
    entree: Callable[[str], str] = input,
    sortie: Callable[[str], None] = print,
) -> int:
    parseur = argparse.ArgumentParser(description="Diagnostic du traceur sur ce poste.")
    parseur.add_argument("--config", default="config.json")
    parseur.add_argument("--photo", action="store_true", help="mesure le temps d'une photo complète")
    parseur.add_argument("--profil", action="store_true", help="écrit profil.json et profil.html")
    parseur.add_argument("--reinitialiser", action="store_true", help="ÉCRASE la base de TEST")
    parseur.add_argument("--sorties", default="diagnostic_sorties", help="dossier des fichiers produits")
    args = parseur.parse_args(argv)

    def etape(n: int, titre: str) -> None:
        sortie(f"\n[{n}/{TOTAL_ETAPES}] {titre}")

    def ok(texte: str) -> None:
        sortie(f"      OK      {texte}")

    def echec(texte: str) -> _Arret:
        sortie(f"      ÉCHEC   {texte}")
        return _Arret(texte)

    gestionnaire = None
    try:
        etape(1, "Python")
        bits = struct.calcsize("P") * 8
        ok(f"Python {sys.version.split()[0]}, {bits} bits")
        if bits != 32:
            sortie("      ATTENTION : le pilote ODBC Access de Windows est 32 bits. "
                   "Avec Python 64 bits il ne sera pas vu (étape 2).")

        etape(2, "pyodbc et pilote ODBC Access")
        try:
            module = pyodbc_module if pyodbc_module is not None else importer_pyodbc()
            pilotes = list(module.drivers())
            pilote = choisir_pilote(pilotes)
        except ErreurAccess as erreur:
            raise echec(str(erreur)) from None
        ok(f"pyodbc {getattr(module, 'version', '?')} — pilote retenu : {pilote}")

        etape(3, f"Configuration ({args.config})")
        try:
            config: Configuration = charger_configuration(args.config)
        except ErreurConfiguration as erreur:
            raise echec(str(erreur)) from None
        gestionnaire = configurer_journal(config.secrets(), Path.cwd())
        ok(f"base_test            : {config.base_test}")
        ok(f"instantane_reference : {config.instantane_reference}")
        ok(f"mot de passe         : {'fourni (non affiché)' if config.mot_de_passe else 'aucun'}"
           + (f" — groupe de travail : {config.fichier_mdw}" if config.fichier_mdw else ""))

        etape(4, "Contrôles de sécurité au démarrage (F1)")
        try:
            verifier_demarrage(config)
        except ErreurSecurite as erreur:
            raise echec(str(erreur)) from None
        ok("la base de TEST n'est ni une base interdite, ni l'instantané de référence")

        etape(5, "Fichier de la base de TEST")
        if not os.path.isfile(config.base_test):
            raise echec(f"fichier introuvable : {config.base_test}")
        taille = os.path.getsize(config.base_test)
        version = version_jet_de(config.base_test)
        ok(f"{taille / 1_048_576:.1f} Mo — format : {version or 'non reconnu'}")
        try:
            verrou = chemin_verrou(config.base_test)
            sortie(f"      info    fichier de verrou {'PRÉSENT' if os.path.exists(verrou) else 'absent'} : {verrou}")
        except ErreurSecurite as erreur:
            sortie(f"      info    {erreur}")

        etape(6, "Connexion en lecture seule et lecture des tables")
        try:
            source = SourceAccess(ParametresAccess.depuis_configuration(config), module, pilote)
        except ErreurAccess as erreur:
            raise echec(str(erreur)) from None
        try:
            tables = [t for t in source.lister_tables() if t.lower() not in {x.lower() for x in config.tables_ignorees}]
            ok(f"{len(tables)} tables lisibles (connexion ReadOnly=1)")
            profil = profiler(source, config.tables_ignorees, version_jet=version)
            total = sum(t.nb_lignes for t in profil.tables)
            for t in sorted(profil.tables, key=lambda t: -t.nb_lignes)[:15]:
                cle = ", ".join(t.cle_primaire) or "aucune"
                sortie(f"              {t.nom:<28}{t.nb_lignes:>10} lignes   clé primaire : {cle}")
            ok(f"{total} lignes au total ; {len(profil.relations)} relations candidates ; profilage en {profil.duree_s:.1f} s")
            if args.profil:
                dossier = Path(args.sorties) / "profil"
                _, html = ecrire_profil(profil, dossier)
                ok(f"profil écrit : {html}")
            if args.photo:
                source.rafraichir()
                photo = prendre_instantane(source, config.tables_ignorees)
                sortie("\n      " + photo.resume().replace("\n", "\n      "))
                verdict = "OK" if photo.duree_s < OBJECTIF_PHOTO_S else "DÉPASSÉ (AMB-002 à traiter)"
                ok(f"temps de photo : {photo.duree_s:.1f} s (objectif < {OBJECTIF_PHOTO_S:.0f} s) — {verdict}")
        finally:
            source.fermer()
        ok("connexion fermée")

        if args.reinitialiser:
            sortie("\n[+] Réinitialisation de la base de TEST (F10)")
            try:
                resultat = reinitialiser_base_test(config, lambda t: entree(t + "\n  Tapez OUI pour confirmer : ").strip() == "OUI")
            except ReinitialisationAnnulee as erreur:
                sortie(f"      {erreur}")
            except ErreurSecurite as erreur:
                raise echec(str(erreur)) from None
            else:
                ok(f"copie vérifiée ({resultat.octets} octets, {resultat.empreinte[:23]}…, {resultat.duree_s:.1f} s)")
        sortie("\nDiagnostic terminé : tout est OK.")
        return 0
    except _Arret:
        sortie("\nDiagnostic interrompu : corrigez le point en échec puis relancez.")
        return 1
    finally:
        if gestionnaire is not None:
            import logging

            logging.getLogger("traceur").removeHandler(gestionnaire)
            gestionnaire.close()


def main() -> int:
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")
    return executer()


if __name__ == "__main__":
    sys.exit(main())
