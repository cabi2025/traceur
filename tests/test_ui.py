"""Tests de l'interface Tkinter. Sautés sans Tkinter ni écran (sous Linux : `xvfb-run -a pytest tests/test_ui.py`)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import pytest

tkinter = pytest.importorskip("tkinter")  # sans Tkinter, tout le fichier est sauté
import tkinter.ttk  # noqa: E402,F401

try:
    _essai = tkinter.Tk()
    _essai.destroy()
    ECRAN = True
except tkinter.TclError:  # pas d'affichage
    ECRAN = False

pytestmark = [pytest.mark.ui, pytest.mark.skipif(not ECRAN, reason="aucun écran disponible pour Tkinter")]

from test_controleur import Monde  # noqa: E402

from traceur.controleur import ErreurAffichable, Etat, Progression  # noqa: E402
from traceur.sources.access import ErreurConnexion  # noqa: E402
from traceur.ui.application import COULEUR_ALERTE, COULEUR_OK, Application  # noqa: E402
from traceur.ui.dialogues import DialoguesTk  # noqa: E402


class FauxDialogues:
    """Dialogues scriptés : enregistrent les appels et rendent les réponses programmées."""

    def __init__(self) -> None:
        self.erreurs: list[str] = []
        self.infos: list[tuple[str, str]] = []
        self.confirmations: list[tuple[str, str]] = []
        self.avertissements: dict[str, bool] = {}  # titre -> icône « attention » demandée
        self.reponses: dict[str, bool] = {}  # par titre ; défaut True
        self.tables_bruit: list[str] | None = None
        self.propositions: list[dict[str, str]] = []
        self.resultats: list[Any] = []
        self.action_resultat = "fermer"
        self.ouvertures: list[Path] = []

    def erreur(self, message: str) -> None:
        self.erreurs.append(message)

    def info(self, titre: str, message: str) -> None:
        self.infos.append((titre, message))

    def confirmer(self, titre: str, message: str, avertissement: bool = False) -> bool:
        self.confirmations.append((titre, message))
        self.avertissements[titre] = avertissement
        return self.reponses.get(titre, True)

    def choisir_tables_bruit(self, propositions: Any) -> list[str] | None:
        self.propositions.append(dict(propositions))
        return list(propositions) if self.tables_bruit is None else self.tables_bruit

    def resultat_fiche(self, resultat: Any, ouvrir: Callable[[Path], None]) -> str:
        self.resultats.append(resultat)
        return self.action_resultat

    def ouvrir(self, chemin: Path) -> None:
        self.ouvertures.append(chemin)


class Poste:
    """Un monde de test + une vraie fenêtre Tk pilotée par ses boutons."""

    def __init__(self, tmp: Path) -> None:
        self.monde = Monde(tmp)
        self.dialogues = FauxDialogues()
        self.app = Application(self.monde.controleur, self.dialogues)
        self.c = self.monde.controleur

    def attendre(self) -> None:
        self.app.update()
        self.c.executeur.attendre()
        self.app.update()

    def demarrer(self) -> None:
        self.app.demarrer()
        self.attendre()

    def cliquer(self, bouton: Any) -> None:
        assert self.actif(bouton), f"bouton inactif : {bouton}"
        bouton.invoke()
        self.attendre()

    def actif(self, bouton: Any) -> bool:
        return "disabled" not in bouton.state()

    def choisir(self, identifiant: str = "S-003") -> None:
        self.app.arbre.selection_set(identifiant)
        self.cliquer(self.app.btn_choisir)

    def fermer(self) -> None:
        try:
            self.app.destroy()
        except tkinter.TclError:
            pass


@pytest.fixture
def poste(tmp_path: Path) -> Any:
    p = Poste(tmp_path)
    yield p
    p.fermer()


def _texte_arbre(app: Application) -> list[tuple[str, ...]]:
    return [tuple(str(v) for v in app.arbre.item(i, "values")) for i in app.arbre.get_children()]


# --- écran principal -------------------------------------------------------------------------

def test_ecran_principal_apres_demarrage(poste: Poste) -> None:
    poste.demarrer()
    a = poste.app
    assert a.lbl_base.cget("text") == f"Base de TEST active : {poste.monde.config.base_test}"
    assert a.lbl_connexion.cget("text") == "Connexion : Connectée en lecture seule (4 tables)"
    assert str(a.lbl_connexion.cget("foreground")) == COULEUR_OK
    assert a.lbl_profil.cget("text") == "Profil absent — lancer le profilage"  # AMB-010
    assert str(a.lbl_profil.cget("foreground")) == COULEUR_ALERTE
    assert _texte_arbre(a) == [("S-003", "Saisie facture achat", "2", "3 min", "à faire"), ("S-004", "Autre", "2", "", "à faire")]
    assert [b.cget("text") for b in (a.btn_choisir, a.btn_reinit, a.btn_profil, a.btn_calibrer)] == [
        "Choisir une fiche", "Réinitialiser la base", "Profiler la base", "Calibrer le bruit"]
    assert all(poste.actif(b) for b in (a.btn_choisir, a.btn_reinit, a.btn_profil, a.btn_calibrer))
    assert a.ecran_principal.winfo_manager() == "pack" and a.ecran_fiche.winfo_manager() == ""
    assert not poste.dialogues.erreurs and not poste.c.occupe


def test_sans_fichier_de_fiches_boutons_desactives_avec_message(tmp_path: Path) -> None:
    from dataclasses import replace

    monde = Monde(tmp_path)
    monde.config = replace(monde.config, fichier_fiches=None)
    monde.controleur = monde._controleur()
    p = Poste.__new__(Poste)
    p.monde, p.dialogues = monde, FauxDialogues()
    p.app, p.c = Application(monde.controleur, p.dialogues), monde.controleur
    try:
        p.demarrer()
        assert not p.actif(p.app.btn_choisir) and p.actif(p.app.btn_profil) and p.actif(p.app.btn_calibrer)
        assert "seuls le profilage et la calibration sont disponibles" in p.app.lbl_fiches.cget("text")
        p.app._choisir()
        assert p.dialogues.infos[-1][0] == "Fiches" and "profilage" in p.dialogues.infos[-1][1]
    finally:
        p.fermer()


def test_message_si_fichier_de_fiches_invalide(tmp_path: Path) -> None:
    monde = Monde(tmp_path)
    monde.fiches.write_text("{pas du json", encoding="utf-8")
    p = Poste.__new__(Poste)
    p.monde, p.dialogues, p.c = monde, FauxDialogues(), monde.controleur
    p.app = Application(monde.controleur, p.dialogues)
    try:
        p.demarrer()
        assert "pas un JSON valide" in p.app.lbl_fiches.cget("text") and not p.actif(p.app.btn_choisir)
    finally:
        p.fermer()


def test_choisir_sans_selection(poste: Poste) -> None:
    poste.demarrer()
    poste.app.arbre.selection_set(())
    poste.app._choisir()
    assert poste.dialogues.infos[-1][0] == "Choisir une fiche" and poste.c.etat == Etat.REPOS


# --- profilage, calibration, réinitialisation ------------------------------------------------

def test_profiler(poste: Poste) -> None:
    poste.demarrer()
    poste.cliquer(poste.app.btn_profil)
    titre, texte = poste.dialogues.confirmations[-1]
    assert titre == "Profilage terminé" and "4 tables, 3 lignes" in texte and "Ouvrir le profil" in texte
    assert [p.name for p in poste.dialogues.ouvertures] == ["profil.html"]
    assert poste.app.lbl_profil.cget("text") == "Dernier profilage : 05/10/2026 10:15"
    assert str(poste.app.lbl_profil.cget("foreground")) != COULEUR_ALERTE and not poste.dialogues.erreurs


def test_calibrer_valider_les_tables_proposees(poste: Poste) -> None:
    poste.demarrer()
    poste.c._dormir = lambda duree: poste.monde.base.execute("UPDATE SESSIONS SET DERNIER = ?", (str(duree),))
    poste.cliquer(poste.app.btn_calibrer)
    assert poste.dialogues.propositions == [{"SESSIONS": "1 ligne modifiée"}]
    assert poste.c.tables_bruit == ["SESSIONS"] and poste.dialogues.infos[-1] == ("Calibration enregistrée", "1 table(s) de bruit enregistrée(s).")


def test_calibrer_sans_aucune_table_qui_bouge(poste: Poste) -> None:
    poste.demarrer()
    poste.cliquer(poste.app.btn_calibrer)
    assert poste.dialogues.propositions == [] and poste.c.tables_bruit == []
    assert "Aucune table ne change toute seule" in poste.dialogues.infos[-1][1]
    assert (poste.monde.tmp / "donnees" / "calibration" / "bruit.json").is_file()


def test_calibration_abandonnee_par_l_utilisateur(poste: Poste) -> None:
    poste.demarrer()
    poste.c._dormir = lambda duree: poste.monde.base.execute("UPDATE SESSIONS SET DERNIER = 'x'")
    poste.dialogues.tables_bruit = None
    poste.dialogues.choisir_tables_bruit = lambda propositions: None  # type: ignore[method-assign]
    poste.cliquer(poste.app.btn_calibrer)
    assert poste.c.tables_bruit == [] and poste.app.lbl_etat.cget("text") == "Calibration non enregistrée."


def test_reinitialiser_confirme_puis_refuse(poste: Poste) -> None:
    poste.demarrer()
    poste.dialogues.reponses["Réinitialiser la base de TEST"] = False
    poste.cliquer(poste.app.btn_reinit)
    assert poste.dialogues.confirmations[-1][0] == "Réinitialiser la base de TEST"
    assert poste.monde.config.base_test in poste.dialogues.confirmations[-1][1] and "ÉCRASER" in poste.dialogues.confirmations[-1][1]
    assert (poste.monde.tmp / "test.mdb").read_bytes() == b"BASE DE TEST"  # refus : rien n'est touché
    poste.dialogues.reponses["Réinitialiser la base de TEST"] = True
    poste.cliquer(poste.app.btn_reinit)
    assert (poste.monde.tmp / "test.mdb").read_bytes() == b"REFERENCE"
    assert poste.dialogues.infos[-1][0] == "Base réinitialisée" and not poste.dialogues.erreurs


def test_reinitialisation_impossible_logiciel_ouvert(poste: Poste) -> None:
    poste.demarrer()
    (poste.monde.tmp / "test.ldb").write_bytes(b"")
    poste.cliquer(poste.app.btn_reinit)
    assert "RÉINITIALISATION REFUSÉE" in poste.dialogues.erreurs[-1]
    assert not [t for t, _ in poste.dialogues.confirmations if t == "Réinitialiser la base de TEST"]  # pas de confirmation inutile


# --- une fiche -------------------------------------------------------------------------------

def test_parcours_d_une_fiche(poste: Poste) -> None:
    poste.demarrer()
    a = poste.app
    poste.choisir()
    assert a.ecran_fiche.winfo_manager() == "pack" and a.ecran_principal.winfo_manager() == ""
    assert a.lbl_titre.cget("text") == "S-003 — Saisie facture achat"
    assert "Durée prévue : 3 min" in a.lbl_infos.cget("text") and "Logiciel ouvert" in a.lbl_infos.cget("text")
    assert [c.cget("text") for c in a._boutons_cases] == ["1. Ouvrir l'écran   (capture 001)", "2. Valider"]
    assert a.lbl_a_noter.cget("text") == "À noter : Numéro de pièce"
    # avant « Début » : cases et remarques inactives
    assert poste.actif(a.btn_debut) and not poste.actif(a.btn_fin) and not poste.actif(a.btn_annuler)
    assert not any(poste.actif(c) for c in a._boutons_cases) and str(a.txt_remarques.cget("state")) == "disabled"

    poste.cliquer(a.btn_debut)
    assert poste.c.etat == Etat.EN_COURS
    assert all(poste.actif(c) for c in a._boutons_cases) and str(a.txt_remarques.cget("state")) == "normal"
    assert poste.actif(a.btn_fin) and poste.actif(a.btn_annuler) and not poste.actif(a.btn_debut) and not poste.actif(a.btn_retour)

    a._boutons_cases[0].invoke()
    assert poste.c.session.cochees == {1}  # type: ignore[union-attr]
    poste.monde.action_du_comptable()
    a.txt_remarques.insert("1.0", "Message : Écriture enregistrée sous le n° 2025-ACH-0042")
    poste.cliquer(a.btn_fin)
    (resultat,) = poste.dialogues.resultats
    assert resultat.statut == "terminee" and resultat.trace["execution"]["remarques"].startswith("Message : Écriture")
    assert resultat.rapport.is_file() and not [t for t, _ in poste.dialogues.confirmations if t.startswith("Remarques")]
    assert a.ecran_principal.winfo_manager() == "pack" and poste.c.etat == Etat.REPOS
    assert _texte_arbre(a)[0][-1] == "faite" and a.arbre.item("S-003", "tags") == ("faite",)
    assert poste.actif(a.btn_choisir) and a.lbl_etat.cget("text") == "Prêt."


def test_remarques_vides_demandent_une_confirmation_explicite(poste: Poste) -> None:
    poste.demarrer()
    poste.choisir()
    poste.cliquer(poste.app.btn_debut)
    poste.monde.action_du_comptable()
    poste.dialogues.reponses["Remarques / messages affichés"] = False
    poste.cliquer(poste.app.btn_fin)
    assert poste.c.etat == Etat.EN_COURS and not poste.dialogues.resultats  # l'utilisateur veut encore écrire
    assert "Terminer la fiche sans remarque ?" in poste.dialogues.confirmations[-1][1]
    poste.dialogues.reponses["Remarques / messages affichés"] = True
    poste.cliquer(poste.app.btn_fin)
    assert poste.c.etat == Etat.REPOS and poste.dialogues.resultats[0].trace["execution"]["remarques"] == ""


def test_ecart_de_saisie_puis_reinitialiser_et_rejouer(poste: Poste) -> None:
    poste.demarrer()
    poste.choisir()
    poste.cliquer(poste.app.btn_debut)
    poste.monde.action_du_comptable("1243.56")
    poste.app.txt_remarques.insert("1.0", "x")
    poste.dialogues.action_resultat = "rejouer"
    poste.cliquer(poste.app.btn_fin)
    assert poste.dialogues.resultats[0].ecart_de_saisie and _texte_arbre(poste.app)[0][-1] == "écart"
    # « Réinitialiser puis rejouer » : confirmation, copie de la référence, puis la fiche est de nouveau proposée
    assert poste.dialogues.confirmations[-1][0] == "Réinitialiser la base de TEST"
    assert (poste.monde.tmp / "test.mdb").read_bytes() == b"REFERENCE"
    assert poste.c.etat == Etat.FICHE_CHOISIE and poste.c.fiche.id == "S-003"  # type: ignore[union-attr]
    assert poste.app.ecran_fiche.winfo_manager() == "pack" and poste.actif(poste.app.btn_debut)


def test_annuler_la_fiche(poste: Poste) -> None:
    poste.demarrer()
    poste.choisir()
    poste.cliquer(poste.app.btn_debut)
    poste.app.txt_remarques.insert("1.0", "Logiciel planté")
    poste.dialogues.reponses["Annuler la fiche"] = False
    poste.cliquer(poste.app.btn_annuler)
    assert poste.c.etat == Etat.EN_COURS  # refus : la fiche continue
    poste.dialogues.reponses["Annuler la fiche"] = True
    poste.cliquer(poste.app.btn_annuler)
    assert poste.c.etat == Etat.REPOS and _texte_arbre(poste.app)[0][-1] == "annulée"
    trace = json.loads(poste.dialogues.resultats[0].rapport.with_name("trace.json").read_text(encoding="utf-8"))
    assert trace["execution"]["statut"] == "annulee" and trace["execution"]["remarques"] == "Logiciel planté"


def test_retour_a_la_liste_avant_debut(poste: Poste) -> None:
    poste.demarrer()
    poste.choisir()
    poste.cliquer(poste.app.btn_retour)
    assert poste.c.etat == Etat.REPOS and poste.app.ecran_principal.winfo_manager() == "pack"


def test_fiche_qui_demande_une_reinitialisation_avant(poste: Poste) -> None:
    poste.demarrer()
    ancienne = poste.c.fiches[0]
    from dataclasses import replace

    poste.c.fiches[0] = replace(ancienne, reinitialiser_avant=True)
    poste.dialogues.reponses["Réinitialiser avant de commencer ?"] = True
    poste.choisir()
    assert (poste.monde.tmp / "test.mdb").read_bytes() == b"REFERENCE" and poste.c.etat == Etat.FICHE_CHOISIE


# --- jamais figée ----------------------------------------------------------------------------

def test_l_interface_reste_reactive_pendant_un_travail_long(poste: Poste) -> None:
    poste.demarrer()
    poste.monde.bloquer.clear()  # la connexion à la base « traîne »
    poste.app.btn_profil.invoke()
    marques: list[str] = []
    poste.app.after(10, lambda: marques.append("a"))
    poste.app.after(40, lambda: marques.append("b"))
    t0 = time.monotonic()
    while len(marques) < 2 and time.monotonic() - t0 < 2:
        poste.app.update()
        time.sleep(0.005)
    assert marques == ["a", "b"]  # la boucle d'événements tourne pendant que le travail est bloqué
    assert poste.c.occupe and not poste.actif(poste.app.btn_profil) and not poste.actif(poste.app.btn_choisir)
    assert poste.actif(poste.app.btn_annuler_op)
    poste.monde.bloquer.set()
    poste.attendre()
    assert not poste.c.occupe and poste.actif(poste.app.btn_profil) and not poste.actif(poste.app.btn_annuler_op)


def test_annuler_l_operation_en_cours(poste: Poste) -> None:
    poste.demarrer()
    poste.monde.bloquer.clear()
    poste.app.btn_profil.invoke()
    poste.app.update()
    poste.app.btn_annuler_op.invoke()
    poste.monde.bloquer.set()
    poste.attendre()
    assert poste.app.lbl_etat.cget("text") == "Opération annulée : rien n'a été enregistré." and poste.c.profil is None


def test_pendant_fin_tout_est_inactif(poste: Poste) -> None:
    poste.demarrer()
    poste.choisir()
    poste.cliquer(poste.app.btn_debut)
    poste.monde.bloquer.clear()
    poste.app.txt_remarques.insert("1.0", "x")
    poste.app.btn_fin.invoke()
    poste.app.update()
    assert poste.c.etat == Etat.FIN_EN_COURS
    assert not any(poste.actif(b) for b in (poste.app.btn_fin, poste.app.btn_annuler, poste.app.btn_debut, poste.app.btn_retour,
                                            poste.app.btn_annuler_op))
    assert not any(poste.actif(c) for c in poste.app._boutons_cases)
    poste.monde.bloquer.set()
    poste.attendre()
    assert poste.c.etat == Etat.REPOS


def test_barre_de_progression(poste: Poste) -> None:
    a = poste.app
    a.progression(Progression("Lecture de la table LIGNES", 2, 4))
    assert a.lbl_etat.cget("text") == "Lecture de la table LIGNES" and float(a.barre.cget("value")) == 50.0
    a.progression(Progression("Attente…"))
    assert str(a.barre.cget("mode")) == "indeterminate"
    a.progression(Progression("Presque fini", 4, 4))
    assert str(a.barre.cget("mode")) == "determinate" and float(a.barre.cget("value")) == 100.0


# --- erreurs et fermeture --------------------------------------------------------------------

def test_erreur_affichee_en_francais_sans_figer(poste: Poste) -> None:
    poste.demarrer()
    poste.monde.echecs_connexion.append(ErreurConnexion("Connexion à la base impossible. Mot de passe incorrect pour la base."))
    poste.cliquer(poste.app.btn_profil)
    assert poste.dialogues.erreurs == ["Connexion à la base impossible. Mot de passe incorrect pour la base."]
    assert poste.actif(poste.app.btn_profil) and poste.app.lbl_etat.cget("text") == "Opération interrompue."


def test_connexion_impossible_au_demarrage(tmp_path: Path) -> None:
    monde = Monde(tmp_path)
    monde.echecs_connexion.append(ErreurConnexion("Connexion à la base impossible. Fichier de base introuvable."))
    p = Poste.__new__(Poste)
    p.monde, p.dialogues, p.c = monde, FauxDialogues(), monde.controleur
    p.app = Application(monde.controleur, p.dialogues)
    try:
        p.demarrer()
        assert p.app.lbl_connexion.cget("text") == "Connexion : Connexion impossible"
        assert "introuvable" in p.dialogues.erreurs[0]
        assert p.actif(p.app.btn_profil)  # l'application reste utilisable (nouvelle tentative possible)
    finally:
        p.fermer()


def test_fermeture_pendant_une_fiche(poste: Poste) -> None:
    poste.demarrer()
    poste.choisir()
    poste.cliquer(poste.app.btn_debut)
    poste.dialogues.reponses["Quitter"] = False
    poste.app._quitter()
    assert poste.app.winfo_exists() and poste.c.etat == Etat.EN_COURS
    poste.dialogues.reponses["Quitter"] = True
    poste.app._quitter()  # l'abandon de la fiche est enregistré en tâche de fond, puis la fenêtre se ferme
    fin = time.monotonic() + 5
    while time.monotonic() < fin:
        try:
            poste.app.update()
        except tkinter.TclError:
            break
        time.sleep(0.01)
    with pytest.raises(tkinter.TclError):
        poste.app.winfo_exists()
    (dossier,) = (poste.monde.tmp / "partage" / "traces").iterdir()
    assert json.loads((dossier / "trace.json").read_text(encoding="utf-8"))["execution"]["statut"] == "annulee"


def test_fermeture_au_repos(poste: Poste) -> None:
    poste.demarrer()
    poste.app._quitter()
    with pytest.raises(tkinter.TclError):
        poste.app.winfo_exists()
    assert not poste.dialogues.confirmations


# --- vraies boîtes de dialogue ---------------------------------------------------------------

def _trouver(widget: Any, nom: str) -> Any:
    for enfant in widget.winfo_children():
        if str(enfant).endswith("." + nom):
            return enfant
        trouve = _trouver(enfant, nom)
        if trouve is not None:
            return trouve
    return None


def _fenetre(app: Application) -> Any:
    return next(w for w in app.winfo_children() if isinstance(w, tkinter.Toplevel))


def test_dialogue_choix_des_tables_de_bruit(poste: Poste) -> None:
    dialogues = DialoguesTk(poste.app)
    poste.app.after(150, lambda: _trouver(_fenetre(poste.app), "valider").invoke())
    assert dialogues.choisir_tables_bruit({"SESSIONS": "1 ligne modifiée", "JOURNAL": "2 lignes ajoutées"}) == ["SESSIONS", "JOURNAL"]
    poste.app.after(150, lambda: _trouver(_fenetre(poste.app), "annuler").invoke())
    assert dialogues.choisir_tables_bruit({"SESSIONS": "x"}) is None

    def decocher_puis_valider() -> None:
        fen = _fenetre(poste.app)
        cases = [w for w in _tous(fen) if isinstance(w, tkinter.ttk.Checkbutton)]
        cases[1].invoke()
        _trouver(fen, "valider").invoke()

    poste.app.after(150, decocher_puis_valider)
    assert dialogues.choisir_tables_bruit({"A": "x", "B": "y", "C": "z"}) == ["A", "C"]


def _tous(widget: Any) -> list[Any]:
    sortie = []
    for enfant in widget.winfo_children():
        sortie.append(enfant)
        sortie += _tous(enfant)
    return sortie


def _faux_resultat(statut: str, ecarts: list[dict[str, Any]] | None = None, en_attente: bool = False) -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(statut=statut, resume="3 tables modifiées, 4 lignes ajoutées, 1 modifiée",
                           ecart_de_saisie=statut == "ecart_saisie", depot_en_attente=en_attente,
                           trace={"ecarts_saisie": ecarts or []}, rapport=Path("/tmp/rapport.html"))


def test_dialogue_resultat_normal_ouvrir_le_rapport_puis_fermer(poste: Poste) -> None:
    ouvertures: list[Path] = []
    dialogues = DialoguesTk(poste.app)

    def agir() -> None:
        fen = _fenetre(poste.app)
        assert _trouver(fen, "alerte") is None and _trouver(fen, "depot") is None and _trouver(fen, "rejouer") is None
        textes = [w.cget("text") for w in _tous(fen) if isinstance(w, tkinter.ttk.Label)]
        assert "Fiche terminée" in textes and "3 tables modifiées, 4 lignes ajoutées, 1 modifiée" in textes
        _trouver(fen, "rapport").invoke()
        _trouver(fen, "fermer").invoke()

    poste.app.after(150, agir)
    assert dialogues.resultat_fiche(_faux_resultat("terminee"), ouvertures.append) == "fermer"
    assert ouvertures == [Path("/tmp/rapport.html")]


def test_dialogue_resultat_avec_ecart_et_depot_en_attente(poste: Poste) -> None:
    dialogues = DialoguesTk(poste.app)
    ecarts = [{"champ_ecran": "Débit", "valeur_attendue": "1234.56", "type_ecart": "valeur_differente", "valeur_trouvee": "1243.56"},
              {"champ_ecran": "Compte", "valeur_attendue": "6111", "type_ecart": "introuvable"}]

    def agir() -> None:
        fen = _fenetre(poste.app)
        alerte = _trouver(fen, "alerte").cget("text")
        assert "ATTENTION" in alerte and "Débit : valeur attendue 1234.56, trouvée 1243.56" in alerte
        assert "Compte : valeur attendue 6111 — introuvable" in alerte and "réinitialiser la base de TEST puis rejouer" in alerte
        assert "gardée sur ce poste" in _trouver(fen, "depot").cget("text")
        _trouver(fen, "rejouer").invoke()

    poste.app.after(150, agir)
    assert dialogues.resultat_fiche(_faux_resultat("ecart_saisie", ecarts, en_attente=True), lambda p: None) == "rejouer"


def test_barre_vide_au_repos_apres_chaque_operation(poste: Poste) -> None:
    def au_repos() -> None:
        assert str(poste.app.barre.cget("mode")) == "determinate" and float(poste.app.barre.cget("value")) == 0.0

    poste.demarrer()  # test de connexion puis reprise des dépôts : deux opérations indéterminées d'affilée
    au_repos()
    poste.cliquer(poste.app.btn_profil)
    au_repos()
    poste.monde.echecs_connexion.append(ErreurConnexion("Connexion à la base impossible."))
    poste.cliquer(poste.app.btn_profil)  # une erreur laisse aussi la barre vide
    au_repos()


def test_icones_des_confirmations(poste: Poste) -> None:
    """Question simple pour une information (profilage), « attention » pour ce qui est destructeur."""
    poste.demarrer()
    poste.cliquer(poste.app.btn_profil)
    poste.cliquer(poste.app.btn_reinit)
    poste.choisir()
    poste.cliquer(poste.app.btn_debut)
    poste.cliquer(poste.app.btn_annuler)
    poste.choisir()
    poste.cliquer(poste.app.btn_debut)
    poste.app._quitter()  # fiche en cours : confirmation puis fermeture
    fin = time.monotonic() + 5
    while time.monotonic() < fin:
        try:
            poste.app.update()
        except tkinter.TclError:
            break
        time.sleep(0.01)
    assert poste.dialogues.avertissements["Profilage terminé"] is False
    for titre in ("Réinitialiser la base de TEST", "Annuler la fiche", "Quitter"):
        assert poste.dialogues.avertissements[titre] is True, titre
