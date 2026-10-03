"""Boîtes de dialogue de l'interface (Tkinter). Isolées pour être remplacées dans les tests."""

from __future__ import annotations

import os
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable, Mapping, Protocol

TITRE = "Traceur"


class Dialogues(Protocol):
    def erreur(self, message: str) -> None: ...
    def info(self, titre: str, message: str) -> None: ...
    def confirmer(self, titre: str, message: str) -> bool: ...
    def choisir_tables_bruit(self, propositions: Mapping[str, str]) -> list[str] | None: ...
    def resultat_fiche(self, resultat: Any, ouvrir: Callable[[Path], None]) -> str: ...
    def ouvrir(self, chemin: Path) -> None: ...


def _centrer(fenetre: tk.Toplevel, parent: tk.Misc) -> None:
    fenetre.update_idletasks()
    x = parent.winfo_rootx() + max(0, (parent.winfo_width() - fenetre.winfo_width()) // 2)
    y = parent.winfo_rooty() + max(0, (parent.winfo_height() - fenetre.winfo_height()) // 3)
    fenetre.geometry(f"+{x}+{y}")


class DialoguesTk:
    def __init__(self, racine: tk.Misc) -> None:
        self.racine = racine

    def erreur(self, message: str) -> None:
        messagebox.showerror(TITRE, message, parent=self.racine)

    def info(self, titre: str, message: str) -> None:
        messagebox.showinfo(titre, message, parent=self.racine)

    def confirmer(self, titre: str, message: str) -> bool:
        return bool(messagebox.askyesno(titre, message, parent=self.racine, icon="warning"))

    def ouvrir(self, chemin: Path) -> None:
        """Ouvre un rapport HTML dans le navigateur par défaut."""
        if sys.platform == "win32":
            os.startfile(str(chemin))  # type: ignore[attr-defined]  # noqa: S606
        else:
            webbrowser.open(chemin.as_uri())

    def choisir_tables_bruit(self, propositions: Mapping[str, str]) -> list[str] | None:
        """Liste les tables qui ont bougé sans action ; l'utilisateur décoche celles à garder en détail."""
        fenetre = tk.Toplevel(self.racine)
        fenetre.title("Calibration du bruit")
        fenetre.transient(self.racine)  # type: ignore[arg-type]
        fenetre.grab_set()
        ttk.Label(fenetre, wraplength=520, justify="left", padding=12, text=(
            "Ces tables ont changé alors que personne n'utilisait le logiciel. Elles seront rapportées "
            "à part, sans être mêlées aux changements d'une fiche.\nDécochez une table que vous voulez "
            "au contraire suivre normalement.")).pack(anchor="w")
        variables: dict[str, tk.BooleanVar] = {}
        cadre = ttk.Frame(fenetre, padding=(12, 0))
        cadre.pack(fill="x")
        for table, resume in propositions.items():
            variables[table] = tk.BooleanVar(master=fenetre, value=True)
            ttk.Checkbutton(cadre, text=f"{table} — {resume}", variable=variables[table]).pack(anchor="w", pady=2)
        reponse: list[list[str] | None] = [None]

        def valider() -> None:
            reponse[0] = [t for t, v in variables.items() if v.get()]
            fenetre.destroy()

        boutons = ttk.Frame(fenetre, padding=12)
        boutons.pack(fill="x")
        ttk.Button(boutons, text="Valider", style="Gros.TButton", command=valider, name="valider").pack(side="right")
        ttk.Button(boutons, text="Annuler", style="Gros.TButton", command=fenetre.destroy, name="annuler").pack(side="right", padx=8)
        _centrer(fenetre, self.racine)
        fenetre.wait_window()
        variables.clear()  # libère les variables Tk ici, dans le fil de l'interface
        return reponse[0]

    def resultat_fiche(self, resultat: Any, ouvrir: Callable[[Path], None]) -> str:
        """Résumé de fin de fiche (SPEC §5.3). Retourne « rejouer » ou « fermer »."""
        titres = {"terminee": "Fiche terminée", "annulee": "Fiche annulée", "ecart_saisie": "Écart de saisie"}
        fenetre = tk.Toplevel(self.racine)
        fenetre.title(titres.get(resultat.statut, "Fiche"))
        fenetre.transient(self.racine)  # type: ignore[arg-type]
        fenetre.grab_set()
        cadre = ttk.Frame(fenetre, padding=16)
        cadre.pack(fill="both", expand=True)
        ttk.Label(cadre, text=titres.get(resultat.statut, ""), font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(cadre, text=resultat.resume, font=("Segoe UI", 13), wraplength=560, justify="left").pack(anchor="w", pady=(8, 8))
        if resultat.ecart_de_saisie:
            ecarts = "\n".join(
                f"• {e['champ_ecran']} : valeur attendue {e['valeur_attendue']}"
                + (f", trouvée {e['valeur_trouvee']}" if e["type_ecart"] == "valeur_differente" else " — introuvable")
                for e in resultat.trace["ecarts_saisie"])
            tk.Label(cadre, name="alerte", bg="#fff4e0", fg="#6b3f00", justify="left", wraplength=560, padx=10, pady=8,
                     font=("Segoe UI", 11), text=("ATTENTION : une valeur saisie semble différer de la fiche.\n"
                                                 f"{ecarts}\nProposition : réinitialiser la base de TEST puis rejouer la fiche.")).pack(fill="x")
        if resultat.depot_en_attente:
            ttk.Label(cadre, name="depot", wraplength=560, foreground="#b36b00", text=(
                "Le partage est indisponible : la trace est gardée sur ce poste et sera déposée "
                "automatiquement au prochain démarrage.")).pack(anchor="w", pady=(8, 0))
        choix = ["fermer"]

        def rejouer() -> None:
            choix[0] = "rejouer"
            fenetre.destroy()

        boutons = ttk.Frame(cadre)
        boutons.pack(fill="x", pady=(14, 0))
        ttk.Button(boutons, text="Fermer", style="Gros.TButton", command=fenetre.destroy, name="fermer").pack(side="right")
        ttk.Button(boutons, text="Ouvrir le rapport", style="Gros.TButton", name="rapport",
                   command=lambda: ouvrir(resultat.rapport)).pack(side="right", padx=8)
        if resultat.ecart_de_saisie:
            ttk.Button(boutons, text="Réinitialiser puis rejouer", style="Gros.TButton", command=rejouer, name="rejouer").pack(side="right")
        _centrer(fenetre, self.racine)
        fenetre.wait_window()
        return choix[0]
