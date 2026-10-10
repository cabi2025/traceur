"""Fenêtre principale du traceur (SPEC §5) : écran principal, exécution d'une fiche, fin de fiche.

Cette couche ne calcule rien : elle appelle le contrôleur et se redessine quand il le demande.
Les opérations longues tournent dans un fil de travail ; `_tick` vide la file toutes les 100 ms,
la fenêtre ne se fige donc jamais.
"""

from __future__ import annotations

import gc
import logging
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Any

from traceur.controleur import Controleur, ErreurAffichable, Etat, Progression, ResultatFiche, ResultatProfilage

from .dialogues import Dialogues, DialoguesTk

COULEUR_OK, COULEUR_ERREUR, COULEUR_ALERTE, COULEUR_NEUTRE = "#2e7d32", "#c62828", "#b36b00", "#555555"
INTERVALLE_MS = 100
journal = logging.getLogger("traceur.ui")


class Application(tk.Tk):
    def __init__(self, controleur: Controleur, dialogues: Dialogues | None = None) -> None:
        super().__init__()
        self.controleur = controleur
        self.dialogues: Dialogues = dialogues or DialoguesTk(self)
        controleur.ecouteur = self
        self.title("Traceur — observation des écritures")
        self.minsize(940, 700)
        self._rejouer: str | None = None  # fiche à rejouer après une réinitialisation
        self._apres_reinit: Any = None
        # Les objets Tk ne doivent jamais être détruits par le ramasse-miettes depuis le fil de travail
        # (Tcl abandonne le processus). Le GC automatique est donc suspendu : `_tick` le lance, depuis
        # le fil de l'interface, toutes les 5 secondes ; les variables Tk sont réutilisées (`_reserve`).
        gc.disable()
        self._reserve: list[tk.BooleanVar] = []
        self._ticks = 0
        self._cases: dict[int, tk.BooleanVar] = {}
        self._boutons_cases: list[ttk.Checkbutton] = []
        self._fermeture_demandee = False
        self._fiche_affichee: str | None = None
        self._styles()
        self._construire()
        self.protocol("WM_DELETE_WINDOW", self._quitter)
        self._id_tick = self.after(INTERVALLE_MS, self._tick)

    # -- construction ---------------------------------------------------------------------------

    def _styles(self) -> None:
        police = tkfont.nametofont("TkDefaultFont")
        police.configure(size=11)
        tkfont.nametofont("TkTextFont").configure(size=11)
        style = ttk.Style(self)
        style.configure("Gros.TButton", font=("Segoe UI", 13, "bold"), padding=(14, 12))
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 11))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))

    def _construire(self) -> None:
        bandeau = ttk.Frame(self, padding=(14, 10), relief="groove", name="bandeau")
        bandeau.pack(fill="x", padx=10, pady=(10, 4))
        self.lbl_base = ttk.Label(bandeau, name="lbl_base", font=("Segoe UI", 11, "bold"))
        self.lbl_connexion = ttk.Label(bandeau, name="lbl_connexion")
        self.lbl_profil = ttk.Label(bandeau, name="lbl_profil")
        for lbl in (self.lbl_base, self.lbl_connexion, self.lbl_profil):
            lbl.pack(anchor="w")

        self.zone = ttk.Frame(self, padding=10)
        self.zone.pack(fill="both", expand=True)
        self._construire_principal()
        self._construire_fiche()

        pied = ttk.Frame(self, padding=(14, 6, 14, 12), name="pied")
        pied.pack(fill="x")
        self.lbl_etat = ttk.Label(pied, name="lbl_etat", text="Prêt.")
        self.lbl_etat.pack(anchor="w")
        ligne = ttk.Frame(pied)
        ligne.pack(fill="x", pady=(4, 0))
        self.barre = ttk.Progressbar(ligne, name="barre", maximum=100, mode="determinate")
        self.barre.pack(side="left", fill="x", expand=True)
        self.btn_annuler_op = ttk.Button(ligne, text="Annuler l'opération", name="btn_annuler_op",
                                         command=self.controleur.annuler_operation)
        self.btn_annuler_op.pack(side="left", padx=(10, 0))

    def _construire_principal(self) -> None:
        self.ecran_principal = ttk.Frame(self.zone, name="ecran_principal")
        ttk.Label(self.ecran_principal, text="Fiches de scénarios", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        cadre = ttk.Frame(self.ecran_principal)
        cadre.pack(fill="both", expand=True, pady=(6, 6))
        colonnes = ("id", "titre", "lot", "duree", "statut")
        self.arbre = ttk.Treeview(cadre, columns=colonnes, show="headings", selectmode="browse", name="arbre")
        for colonne, titre, largeur in (("id", "Fiche", 90), ("titre", "Titre", 430), ("lot", "Lot", 50),
                                        ("duree", "Durée", 80), ("statut", "Statut", 110)):
            self.arbre.heading(colonne, text=titre)
            self.arbre.column(colonne, width=largeur, anchor="w")
        self.arbre.pack(side="left", fill="both", expand=True)
        defilement = ttk.Scrollbar(cadre, orient="vertical", command=self.arbre.yview)
        self.arbre.configure(yscrollcommand=defilement.set)
        defilement.pack(side="right", fill="y")
        self.arbre.bind("<Double-1>", lambda _: self._choisir())
        self.arbre.tag_configure("faite", foreground=COULEUR_OK)
        self.arbre.tag_configure("écart", foreground=COULEUR_ALERTE)
        self.arbre.tag_configure("annulée", foreground=COULEUR_ERREUR)
        self.lbl_fiches = ttk.Label(self.ecran_principal, name="lbl_fiches", wraplength=860, foreground=COULEUR_ALERTE)
        self.lbl_fiches.pack(anchor="w")
        boutons = ttk.Frame(self.ecran_principal, name="boutons")
        boutons.pack(fill="x", pady=(10, 0))
        self.btn_choisir = ttk.Button(boutons, text="Choisir une fiche", style="Gros.TButton", name="btn_choisir", command=self._choisir)
        self.btn_reinit = ttk.Button(boutons, text="Réinitialiser la base", style="Gros.TButton", name="btn_reinit", command=self._reinitialiser)
        self.btn_profil = ttk.Button(boutons, text="Profiler la base", style="Gros.TButton", name="btn_profil", command=self.controleur.profiler)
        self.btn_calibrer = ttk.Button(boutons, text="Calibrer le bruit", style="Gros.TButton", name="btn_calibrer", command=self.controleur.calibrer)
        for i, b in enumerate((self.btn_choisir, self.btn_reinit, self.btn_profil, self.btn_calibrer)):
            b.grid(row=0, column=i, padx=6, sticky="ew")
            boutons.columnconfigure(i, weight=1)

    def _construire_fiche(self) -> None:
        self.ecran_fiche = ttk.Frame(self.zone, name="ecran_fiche")
        self.lbl_titre = ttk.Label(self.ecran_fiche, name="lbl_titre", font=("Segoe UI", 16, "bold"), wraplength=860)
        self.lbl_titre.pack(anchor="w")
        self.lbl_infos = ttk.Label(self.ecran_fiche, name="lbl_infos", wraplength=860, justify="left")
        self.lbl_infos.pack(anchor="w", pady=(2, 6))
        self.cadre_etapes = ttk.LabelFrame(self.ecran_fiche, text="Étapes (cochez au fur et à mesure)", padding=8, name="cadre_etapes")
        self.cadre_etapes.pack(fill="x")
        self.lbl_a_noter = ttk.Label(self.ecran_fiche, name="lbl_a_noter", wraplength=860, justify="left", foreground=COULEUR_ALERTE)
        self.lbl_a_noter.pack(anchor="w", pady=(6, 0))
        ttk.Label(self.ecran_fiche, text="Remarques / messages affichés", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8, 0))
        self.txt_remarques = tk.Text(self.ecran_fiche, height=5, wrap="word", name="txt_remarques", font=("Segoe UI", 11))
        self.txt_remarques.pack(fill="x")
        boutons = ttk.Frame(self.ecran_fiche, name="boutons_fiche")
        boutons.pack(fill="x", pady=(10, 0))
        self.btn_retour = ttk.Button(boutons, text="← Retour à la liste", name="btn_retour", command=self.controleur.abandonner_choix)
        self.btn_debut = ttk.Button(boutons, text="Début", style="Gros.TButton", name="btn_debut", command=self._debut)
        self.btn_fin = ttk.Button(boutons, text="Fin", style="Gros.TButton", name="btn_fin", command=self._fin)
        self.btn_annuler = ttk.Button(boutons, text="Annuler la fiche", style="Gros.TButton", name="btn_annuler", command=self._annuler_fiche)
        self.btn_retour.pack(side="left")
        for b in (self.btn_annuler, self.btn_fin, self.btn_debut):
            b.pack(side="right", padx=6)

    # -- affichage ------------------------------------------------------------------------------

    def _afficher_ecran(self, nom: str) -> None:
        for cadre in (self.ecran_principal, self.ecran_fiche):
            cadre.pack_forget()
        (self.ecran_fiche if nom == "fiche" else self.ecran_principal).pack(fill="both", expand=True)

    def _remplir_bandeau(self) -> None:
        b = self.controleur.bandeau()
        self.lbl_base.configure(text=f"Base de TEST active : {b.base_test}")
        couleur = {True: COULEUR_OK, False: COULEUR_ERREUR, None: COULEUR_NEUTRE}[b.connexion_ok]
        self.lbl_connexion.configure(text=f"Connexion : {b.connexion}", foreground=couleur)
        self.lbl_profil.configure(text=b.profil, foreground=COULEUR_NEUTRE if b.profil_present else COULEUR_ALERTE,
                                  font=("Segoe UI", 11) if b.profil_present else ("Segoe UI", 11, "bold"))

    def _remplir_fiches(self) -> None:
        c = self.controleur
        selection = self.arbre.selection()
        self.arbre.delete(*self.arbre.get_children())
        for f in c.fiches:
            statut = c.statuts.get(f.id, "à faire")
            self.arbre.insert("", "end", iid=f.id, tags=(statut,), values=(
                f.id, f.titre, "" if f.lot is None else f.lot, "" if f.duree_min is None else f"{f.duree_min} min", statut))
        if selection and self.arbre.exists(selection[0]):
            self.arbre.selection_set(selection[0])
        elif c.fiches:
            self.arbre.selection_set(c.fiches[0].id)
        self.lbl_fiches.configure(text=c.message_fiches or "")

    def _remplir_fiche(self) -> None:
        fiche = self.controleur.fiche
        self._fiche_affichee = fiche.id if fiche is not None else None
        for enfant in self.cadre_etapes.winfo_children():
            enfant.destroy()
        self._cases.clear()
        self._boutons_cases.clear()
        if fiche is None:
            return
        self.lbl_titre.configure(text=f"{fiche.id} — {fiche.titre}")
        infos = []
        if fiche.duree_min is not None:
            infos.append(f"Durée prévue : {fiche.duree_min} min")
        if fiche.prerequis:
            infos.append("Prérequis : " + " ; ".join(fiche.prerequis))
        self.lbl_infos.configure(text="\n".join(infos))
        for position, etape in enumerate(fiche.etapes):
            if position >= len(self._reserve):
                self._reserve.append(tk.BooleanVar(master=self, value=False))
            variable = self._reserve[position]
            variable.set(False)
            self._cases[etape.n] = variable
            texte = f"{etape.n}. {etape.texte}" + (f"   (capture {etape.capture_ref})" if etape.capture_ref else "")
            case = ttk.Checkbutton(self.cadre_etapes, text=texte, variable=variable, name=f"etape_{etape.n}",
                                   command=lambda n=etape.n: self.controleur.cocher(n, self._cases[n].get()))
            case.pack(anchor="w", pady=2)
            self._boutons_cases.append(case)
        self.lbl_a_noter.configure(text=("À noter : " + " ; ".join(fiche.a_noter)) if fiche.a_noter else "")
        self.txt_remarques.configure(state="normal")
        self.txt_remarques.delete("1.0", "end")

    def _rafraichir(self) -> None:
        c = self.controleur
        self._remplir_bandeau()
        libre = not c.occupe
        repos = c.etat == Etat.REPOS and libre
        a_des_fiches = c.config.fiches_disponibles and bool(c.fiches)
        self.btn_choisir.state(["!disabled"] if repos and a_des_fiches else ["disabled"])
        for bouton in (self.btn_reinit, self.btn_profil, self.btn_calibrer):
            bouton.state(["!disabled"] if repos else ["disabled"])
        etat = c.etat
        self.btn_retour.state(["!disabled"] if etat == Etat.FICHE_CHOISIE and libre else ["disabled"])
        self.btn_debut.state(["!disabled"] if etat == Etat.FICHE_CHOISIE and libre else ["disabled"])
        en_cours = etat == Etat.EN_COURS and libre
        self.btn_fin.state(["!disabled"] if en_cours else ["disabled"])
        self.btn_annuler.state(["!disabled"] if en_cours or etat == Etat.DEBUT_EN_COURS else ["disabled"])
        for case in self._boutons_cases:
            case.state(["!disabled"] if en_cours else ["disabled"])
        self.txt_remarques.configure(state="normal" if en_cours else "disabled")
        peut_annuler_op = c.occupe and etat != Etat.FIN_EN_COURS
        self.btn_annuler_op.state(["!disabled"] if peut_annuler_op else ["disabled"])
        if not c.occupe:  # au repos : barre vide (jamais de curseur « en attente » figé)
            self.barre.stop()
            if self.barre["mode"] != "determinate":
                self.barre.configure(mode="determinate")
            self.barre.configure(value=0)

    # -- écouteur du contrôleur (appelé dans le fil de l'interface) ------------------------------

    def progression(self, progression: Progression) -> None:
        self.lbl_etat.configure(text=progression.message)
        fraction = progression.fraction
        if fraction is None:
            if self.barre["mode"] != "indeterminate":
                self.barre.configure(mode="indeterminate")
                self.barre.start(60)
        else:
            if self.barre["mode"] != "determinate":
                self.barre.stop()
                self.barre.configure(mode="determinate")
            self.barre.configure(value=fraction * 100)

    def erreur(self, erreur: ErreurAffichable) -> None:
        if self._fermeture_demandee:  # on quitte : pas de boîte de dialogue
            journal.info("Erreur pendant la fermeture : %s", erreur.message)
            return
        self.lbl_etat.configure(text="Opération interrompue.")
        self._rejouer = self._apres_reinit = None
        self._rafraichir()
        self.dialogues.erreur(erreur.message)

    def annule(self, nom: str) -> None:
        if self._fermeture_demandee:
            return
        self.lbl_etat.configure(text="Opération annulée : rien n'a été enregistré.")
        self._rafraichir()

    def etat_change(self) -> None:
        if self._fermeture_demandee:
            return
        c = self.controleur
        self._remplir_fiches()
        if c.etat == Etat.REPOS:
            self._fiche_affichee = None
            self._afficher_ecran("principal")
        else:
            if c.fiche is not None and self._fiche_affichee != c.fiche.id:
                self._remplir_fiche()
            self._afficher_ecran("fiche")
        self._rafraichir()

    def resultat(self, nom: str, valeur: Any) -> None:
        if self._fermeture_demandee:  # on quitte : le résultat est enregistré, mais rien n'est affiché
            return
        self._rafraichir()
        self.lbl_etat.configure(text="Prêt.")
        self.barre.configure(value=0)
        if nom == "profilage":
            self._fin_profilage(valeur)
        elif nom == "calibration":
            self._fin_calibration(valeur)
        elif nom == "reinitialisation":
            self._fin_reinitialisation()
        elif nom == "fiche":
            self._fin_fiche(valeur)

    # -- actions de l'utilisateur ----------------------------------------------------------------

    def _fiche_selectionnee(self) -> str | None:
        selection = self.arbre.selection()
        return selection[0] if selection else None

    def _choisir(self) -> None:
        c = self.controleur
        if not c.fiches:
            self.dialogues.info("Fiches", c.message_fiches or "Aucune fiche disponible.")
            return
        identifiant = self._fiche_selectionnee()
        if identifiant is None:
            self.dialogues.info("Choisir une fiche", "Cliquez d'abord sur une fiche dans la liste.")
            return
        try:
            fiche = c.choisir_fiche(identifiant)
        except ErreurAffichable as erreur:
            self.dialogues.erreur(erreur.message)
            return
        self.etat_change()
        if fiche.reinitialiser_avant and self.dialogues.confirmer(
                "Réinitialiser avant de commencer ?",
                "Cette fiche demande de réinitialiser la base de TEST avant de commencer.\nRéinitialiser maintenant ?",
                avertissement=True):
            self._reinitialiser(rejouer=None)

    def _reinitialiser(self, rejouer: str | None = None) -> None:
        c = self.controleur
        try:
            texte = c.preparer_reinitialisation()
        except ErreurAffichable as erreur:
            self.dialogues.erreur(erreur.message)
            return
        if self.dialogues.confirmer("Réinitialiser la base de TEST", texte, avertissement=True):
            self._rejouer = rejouer
            c.reinitialiser(True)

    def _debut(self) -> None:
        self.controleur.debut()

    def _fin(self) -> None:
        remarques = self.txt_remarques.get("1.0", "end").strip()
        if not remarques and not self.dialogues.confirmer(
                "Remarques / messages affichés",
                "Vous n'avez saisi aucune remarque.\nLe logiciel a-t-il affiché un message ? Si oui, notez-le "
                "dans le champ « Remarques » avant de terminer.\n\nTerminer la fiche sans remarque ?"):
            self.txt_remarques.focus_set()
            return
        self.controleur.fin(remarques)

    def _annuler_fiche(self) -> None:
        c = self.controleur
        if c.etat == Etat.DEBUT_EN_COURS:
            c.annuler()
            return
        if self.dialogues.confirmer("Annuler la fiche", "Annuler la fiche en cours ?\nLa trace sera conservée, marquée « annulée ».",
                                    avertissement=True):
            c.annuler(self.txt_remarques.get("1.0", "end").strip())

    # -- fins d'opérations -----------------------------------------------------------------------

    def _fin_profilage(self, resultat: ResultatProfilage) -> None:
        p = resultat.profil
        texte = (f"Profilage terminé : {len(p.tables)} tables, {sum(t.nb_lignes for t in p.tables)} lignes, "
                 f"{len(p.relations)} relations candidates.")
        if resultat.avertissement:
            texte += f"\n\n{resultat.avertissement}"
        if self.dialogues.confirmer("Profilage terminé", texte + "\n\nOuvrir le profil dans le navigateur ?"):
            self.dialogues.ouvrir(resultat.chemin_html)

    def _fin_calibration(self, calibration: Any) -> None:
        if calibration.proposees:
            choix = self.dialogues.choisir_tables_bruit(calibration.proposees)
            if choix is None:
                self.lbl_etat.configure(text="Calibration non enregistrée.")
                return
        else:
            choix = []
        try:
            avertissement = self.controleur.valider_calibration(choix)
        except ErreurAffichable as erreur:
            self.dialogues.erreur(erreur.message)
            return
        texte = (f"{len(choix)} table(s) de bruit enregistrée(s)." if choix
                 else "Aucune table ne change toute seule : rien à ignorer.")
        self.dialogues.info("Calibration enregistrée", texte + (f"\n\n{avertissement}" if avertissement else ""))

    def _fin_reinitialisation(self) -> None:
        self.dialogues.info("Base réinitialisée", "La base de TEST a été remplacée par la copie de référence "
                                                   "(copie vérifiée par empreinte).")
        rejouer, self._rejouer = self._rejouer, None
        if rejouer is not None:
            try:
                self.controleur.choisir_fiche(rejouer)
            except ErreurAffichable as erreur:
                self.dialogues.erreur(erreur.message)
                return
            self.etat_change()

    def _fin_fiche(self, resultat: ResultatFiche) -> None:
        self._remplir_fiches()
        action = self.dialogues.resultat_fiche(resultat, self.dialogues.ouvrir)
        if action == "rejouer":
            self._reinitialiser(rejouer=resultat.trace["fiche"]["id"])

    # -- boucle et fermeture ---------------------------------------------------------------------

    def _tick(self) -> None:
        self.controleur.executeur.traiter()
        self._ticks += 1
        if self._ticks % 50 == 0:
            gc.collect()
        if not self._fermeture_demandee:
            self._id_tick = self.after(INTERVALLE_MS, self._tick)

    def demarrer(self) -> None:
        self.controleur.demarrer()
        self.etat_change()

    def _quitter(self) -> None:
        c = self.controleur
        if c.etat == Etat.EN_COURS and not self.dialogues.confirmer(
                "Quitter", "Une fiche est en cours : quitter l'abandonnera (la trace sera marquée « annulée »).\nQuitter ?",
                avertissement=True):
            return
        if c.occupe and c.etat != Etat.EN_COURS and not self.dialogues.confirmer(
                "Quitter", "Une opération est en cours : elle sera interrompue.\nQuitter ?", avertissement=True):
            return
        self._fermeture_demandee = True
        if c.etat == Etat.EN_COURS:
            c.annuler("Abandonnée : fermeture du traceur.")
        else:
            c.annuler_operation()
        self._attendre_puis_fermer(50)

    def arreter(self) -> None:
        """Arrêt sans dialogue (Ctrl+C dans le terminal) : une fiche en cours est enregistrée comme
        annulée, une opération en cours est interrompue, puis la fenêtre se ferme."""
        c = self.controleur
        self._fermeture_demandee = True
        try:
            if c.etat == Etat.EN_COURS:
                c.annuler("Abandonnée : arrêt du traceur (Ctrl+C).")
            else:
                c.annuler_operation()
            c.executeur.attendre(10)
        except Exception:  # noqa: BLE001 - on ferme quoi qu'il arrive
            journal.exception("Erreur pendant l'arrêt du traceur")
        finally:
            self.destroy()

    def destroy(self) -> None:
        try:
            self.barre.stop()
            self.after_cancel(self._id_tick)
        except tk.TclError:
            pass
        super().destroy()
        gc.collect()  # dans le fil de l'interface
        gc.enable()

    def _attendre_puis_fermer(self, essais: int) -> None:
        self.controleur.executeur.traiter()
        if self.controleur.occupe and essais > 0:
            self.after(100, lambda: self._attendre_puis_fermer(essais - 1))
        else:
            self.destroy()
