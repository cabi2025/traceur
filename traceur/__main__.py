"""Point d'entrée : `python -m traceur [--config config.json]` (puis `traceur.exe`, J7)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from traceur.config import ErreurConfiguration, charger_configuration
from traceur.controleur import Controleur, FabriqueSource
from traceur.securite import ErreurSecurite, configurer_journal, dossier_application, verifier_demarrage
from traceur.sources.access import (
    ErreurAccess,
    ParametresAccess,
    SourceAccess,
    choisir_pilote,
    importer_pyodbc,
)


def fabrique_access(config) -> FabriqueSource:  # type: ignore[no-untyped-def]
    """Chaque photo ouvre une connexion neuve. pyodbc et le pilote sont contrôlés ici, dès le démarrage
    et dans le fil principal : une installation incomplète donne un message clair avant l'ouverture."""
    parametres = ParametresAccess.depuis_configuration(config)
    module = importer_pyodbc()
    pilote = choisir_pilote(list(module.drivers()))
    return lambda: SourceAccess(parametres, module, pilote)


def _erreur_fatale(message: str) -> None:
    """Message d'erreur affiché dans une boîte (ou sur la console si Tkinter est indisponible)."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        racine = tk.Tk()
        racine.withdraw()
        messagebox.showerror("Traceur", message)
        racine.destroy()
    except Exception:  # noqa: BLE001 - pas d'écran : on écrit sur la console
        print(message, file=sys.stderr)


def _message_info(message: str) -> None:
    """Résultat affiché dans une boîte (l'exécutable n'a pas de console) et sur la sortie standard."""
    print(message)
    try:
        import tkinter as tk
        from tkinter import messagebox

        racine = tk.Tk()
        racine.withdraw()
        messagebox.showinfo("Traceur", message)
        racine.destroy()
    except Exception:  # noqa: BLE001 - pas d'écran : la sortie standard suffit
        pass


def _reanalyser(args: argparse.Namespace) -> int:
    """`--reanalyser trace.json` : recalcul hors ligne, sans configuration, sans base (AMB-042)."""
    from traceur.moteur.calcules import TABLES_IGNOREES_ANALYSE_DEFAUT
    from traceur.reanalyse import ErreurReanalyse, reanalyser_fichier

    motifs: Sequence[str] = TABLES_IGNOREES_ANALYSE_DEFAUT
    try:
        if args.config:
            motifs = charger_configuration(Path(args.config)).tables_ignorees_analyse
        sortie_json, sortie_html, resume = reanalyser_fichier(
            Path(args.reanalyser), Path(args.sortie) if args.sortie else None, motifs)
    except (ErreurReanalyse, ErreurConfiguration) as erreur:
        _erreur_fatale(str(erreur))
        return 1
    _message_info(f"{resume}\n\nÉcrit : {sortie_json}\n          {sortie_html}")
    return 0


def lancer(argv: Sequence[str] | None = None, fabrique: FabriqueSource | None = None, dialogues=None,  # type: ignore[no-untyped-def]
           dossier: Path | None = None, boucle: bool = True):  # type: ignore[no-untyped-def]
    """Démarre l'application. Retourne l'`Application` (boucle=False, pour les tests) ou un code de sortie."""
    parseur = argparse.ArgumentParser(prog="traceur", description="Traceur d'écritures Access.")
    parseur.add_argument("--config", default=None, help="chemin de config.json (défaut : à côté du programme)")
    parseur.add_argument("--reanalyser", metavar="TRACE_JSON", default=None,
                         help="recalcule liens, écarts et champs calculés d'un trace.json, sans accès à la base")
    parseur.add_argument("--sortie", metavar="DOSSIER", default=None,
                         help="avec --reanalyser : dossier d'écriture (défaut : celui du trace.json)")
    args = parseur.parse_args(argv)
    if args.reanalyser:
        return _reanalyser(args)
    dossier = dossier or dossier_application()
    configurer_journal([], dossier)  # journal.log dès le départ (sans secret connu)
    chemin = Path(args.config) if args.config else dossier / "config.json"
    try:
        config = charger_configuration(chemin)
        configurer_journal(config.secrets(), dossier)  # masque désormais les mots de passe
        verifier_demarrage(config)  # F1 : refus si base de production ou instantané
    except (ErreurConfiguration, ErreurSecurite) as erreur:
        _erreur_fatale(str(erreur))
        return 1
    if sys.platform == "win32":  # texte net sur les écrans à forte densité
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    try:
        fabrique = fabrique or fabrique_access(config)
    except ErreurAccess as erreur:
        _erreur_fatale(str(erreur))
        return 1
    from traceur.ui.application import Application

    controleur = Controleur(config, fabrique, dossier / "traces_locales",
                            dossier / "donnees_locales", ecouteur=None)  # type: ignore[arg-type]
    application = Application(controleur, dialogues)
    application.demarrer()
    if not boucle:
        return application
    try:
        application.mainloop()
    except KeyboardInterrupt:  # Ctrl+C dans le terminal : arrêt propre, sans trace d'erreur
        logging.getLogger("traceur").info("Arrêt demandé par Ctrl+C.")
        application.arreter()
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(lancer())
