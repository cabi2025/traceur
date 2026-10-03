"""Point d'entrée : `python -m traceur [--config config.json]` (puis `traceur.exe`, J7)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from traceur.config import ErreurConfiguration, charger_configuration
from traceur.controleur import Controleur, FabriqueSource
from traceur.securite import ErreurSecurite, configurer_journal, dossier_application, verifier_demarrage
from traceur.sources.access import ParametresAccess, SourceAccess


def fabrique_access(config) -> FabriqueSource:  # type: ignore[no-untyped-def]
    parametres = ParametresAccess.depuis_configuration(config)
    return lambda: SourceAccess(parametres)


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


def lancer(argv: Sequence[str] | None = None, fabrique: FabriqueSource | None = None, dialogues=None,  # type: ignore[no-untyped-def]
           dossier: Path | None = None, boucle: bool = True):  # type: ignore[no-untyped-def]
    """Démarre l'application. Retourne l'`Application` (boucle=False, pour les tests) ou un code de sortie."""
    parseur = argparse.ArgumentParser(prog="traceur", description="Traceur d'écritures Access.")
    parseur.add_argument("--config", default=None, help="chemin de config.json (défaut : à côté du programme)")
    args = parseur.parse_args(argv)
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
    from traceur.ui.application import Application

    controleur = Controleur(config, fabrique or fabrique_access(config), dossier / "traces_locales",
                            dossier / "donnees_locales", ecouteur=None)  # type: ignore[arg-type]
    application = Application(controleur, dialogues)
    application.demarrer()
    if not boucle:
        return application
    application.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(lancer())
