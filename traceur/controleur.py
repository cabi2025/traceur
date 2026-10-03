"""Contrôleur de l'application (SPEC §5) : toute la logique, sans Tkinter.

L'interface (`traceur/ui/`) n'appelle que ce module. Les opérations longues (profilage, calibration,
photos, diff, dépôt, réinitialisation) s'exécutent dans un fil de travail ; leurs résultats, erreurs
et progressions reviennent par une file que le fil de l'interface vide avec `executeur.traiter()` :
l'interface ne calcule jamais et ne se fige donc jamais.

Chaque photo ouvre une **connexion neuve** (`fabrique_source`) : le cache du pilote Jet ne peut pas
rendre une photo « après » périmée (AMB-027).
"""

from __future__ import annotations

import logging
import queue
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, ContextManager, Protocol

from traceur.captures import capturer_ecran
from traceur.config import MESSAGE_FICHES_INDISPONIBLES, Configuration, ErreurConfiguration
from traceur.fiches import ErreurFiches, Fiche, charger_fiches, statuts_fiches
from traceur.moteur.calibration import Calibration, calibrer
from traceur.moteur.diff import Avertissement, comparer_instantanes
from traceur.moteur.instantane import Instantane, prendre_instantane
from traceur.moteur.interpretation import interpreter
from traceur.moteur.profilage import Profil, cles_candidates_du_profil, profiler
from traceur.moteur.source import SourceDonnees
from traceur.rapports.calibration import ecrire_bruit, lire_tables_bruit
from traceur.rapports.depot import EN_ATTENTE, ResultatDepot, enregistrer_trace, reprendre_depots_en_attente
from traceur.rapports.profil import ecrire_profil
from traceur.rapports.trace import Execution, FicheTrace, construire_trace, resume_trace
from traceur.securite import (
    ErreurSecurite,
    ResultatReinitialisation,
    empreinte_sha256,
    reinitialiser_base_test,
    texte_confirmation,
    verifier_reinitialisation_possible,
)
from traceur.sources.access import ErreurAccess, version_jet_de

journal = logging.getLogger("traceur.controleur")

FabriqueSource = Callable[[], ContextManager[SourceDonnees]]
MESSAGE_OCCUPE = "Une opération est déjà en cours : attendez qu'elle se termine ou annulez-la."
MESSAGE_ERREUR_INATTENDUE = "Une erreur inattendue s'est produite. Le détail est écrit dans journal.log."
MESSAGE_ERREUR_ACCES = ("Problème d'accès à un fichier ou au réseau. Vérifiez que le dossier ou le partage est "
                        "joignable, puis recommencez. Le détail est écrit dans journal.log.")


class OperationAnnulee(Exception):
    """L'utilisateur a annulé l'opération en cours."""


class ErreurAffichable(Exception):
    """Erreur à montrer à l'utilisateur : `message` en français, `detail` réservé au journal."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


def traduire_erreur(erreur: BaseException) -> ErreurAffichable:
    """Message en français pour n'importe quelle exception. Le détail va dans `journal.log`."""
    if isinstance(erreur, ErreurAffichable):
        return erreur
    if isinstance(erreur, (ErreurAccess, ErreurSecurite, ErreurConfiguration, ErreurFiches)):
        return ErreurAffichable(str(erreur), repr(erreur))
    if isinstance(erreur, OSError):
        return ErreurAffichable(MESSAGE_ERREUR_ACCES, repr(erreur))
    return ErreurAffichable(MESSAGE_ERREUR_INATTENDUE, repr(erreur))


@dataclass(frozen=True)
class Progression:
    message: str
    fait: int | None = None
    total: int | None = None

    @property
    def fraction(self) -> float | None:
        if self.fait is None or not self.total:
            return None
        return min(1.0, self.fait / self.total)


class Contexte:
    """Fourni à chaque travail : progression et annulation."""

    def __init__(self, executeur: ExecuteurTaches) -> None:
        self._executeur = executeur

    def progression(self, message: str, fait: int | None = None, total: int | None = None) -> None:
        self._executeur._poster("progression", Progression(message, fait, total))

    def verifier_annulation(self) -> None:
        if self._executeur._annulation.is_set():
            raise OperationAnnulee()

    def progression_annulable(self, message: str, fait: int, total: int) -> None:
        """À passer au moteur : notifie puis lève `OperationAnnulee` si l'utilisateur a annulé."""
        self.progression(message, fait, total)
        self.verifier_annulation()


class ExecuteurTaches:
    """Un seul travail à la fois, dans un fil ; les rappels s'exécutent dans le fil appelant `traiter()`."""

    def __init__(self) -> None:
        self._evenements: queue.Queue[tuple[str, Callable[[], None]]] = queue.Queue()
        self._annulation = threading.Event()
        self._en_cours = False
        self._rappel_progression: Callable[[Progression], None] | None = None

    @property
    def occupe(self) -> bool:
        return self._en_cours

    def _poster(self, genre: str, valeur: Any) -> None:
        if genre == "progression":
            self._evenements.put((genre, lambda: self._rappel_progression and self._rappel_progression(valeur)))

    def lancer(
        self,
        travail: Callable[[Contexte], Any],
        au_resultat: Callable[[Any], None],
        en_erreur: Callable[[ErreurAffichable], None],
        a_la_progression: Callable[[Progression], None] | None = None,
        a_l_annulation: Callable[[], None] | None = None,
    ) -> None:
        if self._en_cours:
            raise ErreurAffichable(MESSAGE_OCCUPE)
        self._en_cours = True
        self._annulation.clear()
        self._rappel_progression = a_la_progression
        contexte = Contexte(self)

        def executer() -> None:
            try:
                valeur = travail(contexte)
            except OperationAnnulee:
                self._evenements.put(("fin", lambda: a_l_annulation and a_l_annulation()))
            except BaseException as erreur:  # noqa: BLE001 - jamais d'exception non gérée vers l'utilisateur
                traduite = traduire_erreur(erreur)
                if traduite is not erreur or traduite.detail:
                    journal.error("Opération échouée : %s", traduite.detail or repr(erreur), exc_info=erreur)
                self._evenements.put(("fin", lambda: en_erreur(traduite)))
            else:
                self._evenements.put(("fin", lambda: au_resultat(valeur)))

        threading.Thread(target=executer, name="traceur-travail", daemon=True).start()

    def annuler(self) -> None:
        self._annulation.set()

    def traiter(self) -> int:
        """À appeler régulièrement par le fil de l'interface : exécute les rappels en attente."""
        traites = 0
        while True:
            try:
                genre, rappel = self._evenements.get_nowait()
            except queue.Empty:
                return traites
            if genre == "fin":
                self._en_cours = False  # avant le rappel : il peut lancer la suite
            try:
                rappel()
            except Exception:  # noqa: BLE001 - un rappel fautif ne doit pas tuer l'interface
                journal.exception("Erreur dans un rappel de l'interface")
            traites += 1

    def attendre(self, delai_s: float = 20.0) -> None:
        """Pour les tests et la fermeture : traite les événements jusqu'à la fin du travail."""
        fin = time.monotonic() + delai_s
        while time.monotonic() < fin:
            self.traiter()
            if not self._en_cours and self._evenements.empty():
                return
            time.sleep(0.002)
        raise TimeoutError("Le travail en cours n'a pas fini à temps")


class Etat(Enum):
    REPOS = "repos"
    FICHE_CHOISIE = "fiche_choisie"
    DEBUT_EN_COURS = "debut_en_cours"  # photo avant en cours
    EN_COURS = "en_cours"  # entre Début et Fin : l'utilisateur travaille dans le logiciel
    FIN_EN_COURS = "fin_en_cours"  # attente, photo après, diff, rapport, dépôt


class Ecouteur(Protocol):
    def progression(self, progression: Progression) -> None: ...
    def erreur(self, erreur: ErreurAffichable) -> None: ...
    def etat_change(self) -> None: ...
    def resultat(self, nom: str, valeur: Any) -> None: ...
    def annule(self, nom: str) -> None: ...


@dataclass(frozen=True)
class Bandeau:
    base_test: str
    connexion: str
    connexion_ok: bool | None
    profil: str
    profil_present: bool


@dataclass
class SessionFiche:
    fiche: Fiche
    debut: datetime
    avant: Instantane
    dossier_temp: Path
    captures: dict[str, Path | None]
    empreinte_fichier_avant: str | None
    avertissements: list[Avertissement] = field(default_factory=list)
    cochees: set[int] = field(default_factory=set)


@dataclass(frozen=True)
class ResultatProfilage:
    profil: Profil
    chemin_html: Path
    avertissement: str | None


@dataclass(frozen=True)
class ResultatFiche:
    trace: dict[str, Any]
    resume: str
    statut: str  # statut d'exécution : terminee | annulee | ecart_saisie
    depot: ResultatDepot
    rapport: Path

    @property
    def ecart_de_saisie(self) -> bool:
        return self.statut == "ecart_saisie"

    @property
    def depot_en_attente(self) -> bool:
        return self.depot.statut == EN_ATTENTE


class Controleur:
    def __init__(
        self,
        config: Configuration,
        fabrique_source: FabriqueSource,
        dossier_local: Path,
        dossier_donnees: Path,
        ecouteur: Ecouteur,
        executeur: ExecuteurTaches | None = None,
        maintenant: Callable[[], datetime] = datetime.now,
        dormir: Callable[[float], None] = time.sleep,
        capturer: Callable[[Path], bool] = capturer_ecran,
        reinitialiseur: Callable[[Configuration, Callable[[str], bool]], ResultatReinitialisation] = reinitialiser_base_test,
        empreinte: Callable[[str], str] = empreinte_sha256,
        version_jet: Callable[[str], str | None] = version_jet_de,
    ) -> None:
        self.config = config
        self._fabrique = fabrique_source
        self.dossier_local, self.dossier_donnees = dossier_local, dossier_donnees
        self.ecouteur = ecouteur
        self.executeur = executeur or ExecuteurTaches()
        self._maintenant, self._dormir, self._capturer = maintenant, dormir, capturer
        self._reinitialiseur, self._empreinte, self._version_jet = reinitialiseur, empreinte, version_jet
        self.etat = Etat.REPOS
        self.fiches: list[Fiche] = []
        self.message_fiches: str | None = None
        self.statuts: dict[str, str] = {}
        self.fiche: Fiche | None = None
        self.session: SessionFiche | None = None
        self.profil: Profil | None = None
        self.tables_bruit: list[str] = []
        self.connexion_ok: bool | None = None
        self.connexion_message = "Connexion non testée"
        self._calibration: Calibration | None = None

    # -- démarrage ------------------------------------------------------------------------------

    def demarrer(self) -> None:
        """Charge fiches, profil et bruit enregistrés ; teste la connexion ; reprend les dépôts en attente."""
        self._charger_etat_local()
        self._charger_fiches()
        self.tester_connexion(suite=self.reprendre_depots)

    def _charger_fiches(self) -> None:
        self.fiches, self.message_fiches = [], None
        if not self.config.fiches_disponibles:  # AMB-023
            self.message_fiches = MESSAGE_FICHES_INDISPONIBLES
            return
        try:
            self.fiches = charger_fiches(self.config.fichier_fiches or "")
        except ErreurFiches as erreur:
            self.message_fiches = str(erreur)
            journal.error("Fiches illisibles : %s", erreur)

    def _charger_etat_local(self) -> None:
        import json

        try:
            self.profil = Profil.depuis_dict(json.loads(
                (self.dossier_donnees / "profil" / "profil.json").read_text(encoding="utf-8")))
        except FileNotFoundError:
            self.profil = None
        except (OSError, ValueError, KeyError) as erreur:
            self.profil = None
            journal.warning("Profil enregistré illisible, à refaire : %s", erreur)
        try:
            self.tables_bruit = lire_tables_bruit(self.dossier_donnees / "calibration" / "bruit.json")
        except FileNotFoundError:
            self.tables_bruit = []
        except (OSError, ValueError, KeyError) as erreur:
            self.tables_bruit = []
            journal.warning("Calibration enregistrée illisible, à refaire : %s", erreur)

    def bandeau(self) -> Bandeau:
        if self.profil is None:
            profil = "Profil absent — lancer le profilage"  # AMB-010
        else:
            profil = f"Dernier profilage : {self.profil.date:%d/%m/%Y %H:%M}"
        return Bandeau(self.config.base_test, self.connexion_message, self.connexion_ok, profil, self.profil is not None)

    @property
    def occupe(self) -> bool:
        return self.executeur.occupe

    def _changer_etat(self, etat: Etat) -> None:
        self.etat = etat
        self.ecouteur.etat_change()

    # -- plomberie des tâches -------------------------------------------------------------------

    def _lancer(
        self,
        nom: str,
        travail: Callable[[Contexte], Any],
        au_resultat: Callable[[Any], None] | None = None,
        en_erreur: Callable[[ErreurAffichable], None] | None = None,
        a_l_annulation: Callable[[], None] | None = None,
    ) -> None:
        def reussi(valeur: Any) -> None:
            if au_resultat is not None:
                au_resultat(valeur)
            self.ecouteur.resultat(nom, valeur)

        def echoue(erreur: ErreurAffichable) -> None:
            if en_erreur is not None:
                en_erreur(erreur)
            self.ecouteur.erreur(erreur)

        def annule() -> None:
            if a_l_annulation is not None:
                a_l_annulation()
            self.ecouteur.annule(nom)

        try:
            self.executeur.lancer(travail, reussi, echoue, self.ecouteur.progression, annule)
        except ErreurAffichable as erreur:
            self.ecouteur.erreur(erreur)
            return
        self.ecouteur.etat_change()  # l'interface désactive les boutons pendant l'opération

    def _libre(self) -> bool:
        """Refuse (avec un message) de lancer une opération si une autre est en cours."""
        if self.occupe:
            self.ecouteur.erreur(ErreurAffichable(MESSAGE_OCCUPE))
            return False
        return True

    def annuler_operation(self) -> None:
        """Annule l'opération annulable en cours (profilage, calibration, photo de début)."""
        if self.etat != Etat.FIN_EN_COURS:
            self.executeur.annuler()

    # -- connexion et dépôts en attente ---------------------------------------------------------

    def tester_connexion(self, suite: Callable[[], None] | None = None) -> None:
        if not self._libre():
            return
        def travail(ctx: Contexte) -> int:
            ctx.progression("Test de la connexion à la base de TEST…")
            with self._fabrique() as source:
                return len(source.lister_tables())

        def reussi(nb_tables: int) -> None:
            self.connexion_ok, self.connexion_message = True, f"Connectée en lecture seule ({nb_tables} tables)"
            self.ecouteur.etat_change()
            if suite is not None:
                suite()

        def echoue(erreur: ErreurAffichable) -> None:
            self.connexion_ok, self.connexion_message = False, "Connexion impossible"
            self.ecouteur.etat_change()
            if suite is not None:
                suite()

        self._lancer("connexion", travail, reussi, echoue)

    def reprendre_depots(self) -> None:
        """Nouvelle tentative de dépôt des traces en attente (au démarrage) ; rafraîchit les statuts."""

        def travail(ctx: Contexte) -> tuple[list[ResultatDepot], dict[str, str]]:
            ctx.progression("Vérification des traces en attente de dépôt…")
            resultats = reprendre_depots_en_attente(self.dossier_local, Path(self.config.dossier_sorties))
            return resultats, self._calculer_statuts()

        def reussi(valeur: tuple[list[ResultatDepot], dict[str, str]]) -> None:
            self.statuts = valeur[1]
            self.ecouteur.etat_change()

        self._lancer("depots", travail, reussi)

    def _calculer_statuts(self) -> dict[str, str]:
        return statuts_fiches(self.fiches, [Path(self.config.dossier_sorties) / "traces", self.dossier_local])

    # -- profilage et calibration ---------------------------------------------------------------

    def profiler(self) -> None:
        if not self._libre():
            return

        def travail(ctx: Contexte) -> ResultatProfilage:
            with self._fabrique() as source:
                profil = profiler(source, self.config.tables_ignorees, self._version_jet(self.config.base_test),
                                  self._maintenant, progression=ctx.progression_annulable)
            ctx.progression("Écriture du profil…")
            chemin, avertissement = self._publier("profil", lambda dossier: ecrire_profil(profil, dossier)[1])
            return ResultatProfilage(profil, chemin, avertissement)

        def reussi(resultat: ResultatProfilage) -> None:
            self.profil = resultat.profil
            self.ecouteur.etat_change()

        self._lancer("profilage", travail, reussi)

    def _publier(self, sous_dossier: str, ecrire: Callable[[Path], Path]) -> tuple[Path, str | None]:
        """Écrit d'abord en local, puis sur le partage (AMB-029) ; un partage absent n'est pas une erreur."""
        chemin_local = ecrire(self.dossier_donnees / sous_dossier)
        try:
            ecrire(Path(self.config.dossier_sorties) / sous_dossier)
        except OSError as erreur:
            journal.warning("Partage indisponible pour « %s » : %s", sous_dossier, erreur)
            return chemin_local, "Le partage est indisponible : le résultat n'est enregistré que sur ce poste."
        return chemin_local, None

    def calibrer(self, intervalle_s: float = 30.0) -> None:
        if not self._libre():
            return

        def travail(ctx: Contexte) -> Calibration:
            def dormir(duree: float) -> None:
                reste = duree
                while reste > 0:
                    ctx.progression(f"Attente avant la 2e photo : encore {reste:.0f} s — ne touchez pas au logiciel",
                                    int(duree - reste), int(duree))
                    ctx.verifier_annulation()
                    pas = min(0.25, reste)
                    self._dormir(pas)
                    reste -= pas

            with self._fabrique() as source:
                return calibrer(source, intervalle_s, self.config.tables_ignorees, dormir, self._maintenant,
                                getattr(source, "rafraichir", None), ctx.progression_annulable)

        def reussi(calibration: Calibration) -> None:
            self._calibration = calibration

        self._lancer("calibration", travail, reussi)

    def valider_calibration(self, tables_bruit: list[str]) -> str | None:
        """Enregistre le choix de l'utilisateur (`bruit.json`). Retourne un avertissement éventuel."""
        if self._calibration is None:
            raise ErreurAffichable("Aucune calibration à valider : lancez d'abord « Calibrer le bruit ».")
        calibration = self._calibration
        try:
            calibration.valider(tables_bruit)
            _, avertissement = self._publier("calibration", lambda dossier: ecrire_bruit(calibration, dossier))
        except ValueError as erreur:
            raise ErreurAffichable(str(erreur)) from None
        except OSError as erreur:
            raise traduire_erreur(erreur) from None
        self.tables_bruit = list(calibration.tables_bruit)
        self._calibration = None
        self.ecouteur.etat_change()
        return avertissement

    # -- réinitialisation -----------------------------------------------------------------------

    def preparer_reinitialisation(self) -> str:
        """Contrôles préalables ; retourne le texte à faire confirmer (rappelle la base visée)."""
        if self.etat not in (Etat.REPOS, Etat.FICHE_CHOISIE):
            raise ErreurAffichable("Terminez ou annulez d'abord la fiche en cours.")
        if self.occupe:
            raise ErreurAffichable(MESSAGE_OCCUPE)
        try:
            verifier_reinitialisation_possible(self.config)
        except ErreurSecurite as erreur:
            raise ErreurAffichable(str(erreur), repr(erreur)) from None
        return texte_confirmation(self.config)

    def reinitialiser(self, confirme: bool) -> None:
        """À appeler seulement après la confirmation explicite de l'utilisateur (`confirme=True`)."""
        if not confirme:
            self.ecouteur.erreur(ErreurAffichable("Réinitialisation annulée : rien n'a été modifié."))
            return
        if not self._libre():
            return

        def travail(ctx: Contexte) -> ResultatReinitialisation:
            ctx.progression("Copie de l'instantané de référence et vérification…")
            return self._reinitialiseur(self.config, lambda texte: True)

        self._lancer("reinitialisation", travail)

    # -- fiches ---------------------------------------------------------------------------------

    def choisir_fiche(self, fiche_id: str) -> Fiche:
        if not self.config.fiches_disponibles:
            raise ErreurAffichable(MESSAGE_FICHES_INDISPONIBLES)
        if self.etat not in (Etat.REPOS, Etat.FICHE_CHOISIE):
            raise ErreurAffichable("Une fiche est déjà en cours.")
        fiche = next((f for f in self.fiches if f.id == fiche_id), None)
        if fiche is None:
            raise ErreurAffichable(f"Fiche inconnue : {fiche_id}")
        self.fiche = fiche
        self._changer_etat(Etat.FICHE_CHOISIE)
        return fiche

    def abandonner_choix(self) -> None:
        """Retour à l'écran principal avant « Début » : rien n'est enregistré."""
        if self.etat == Etat.FICHE_CHOISIE:
            self.fiche = None
            self._changer_etat(Etat.REPOS)

    def debut(self) -> None:
        """« Début » : photo avant, capture d'écran, empreinte du fichier ; active ensuite les cases."""
        if self.etat != Etat.FICHE_CHOISIE or self.fiche is None:
            self.ecouteur.erreur(ErreurAffichable("Choisissez d'abord une fiche."))
            return
        if not self._libre():
            return
        fiche = self.fiche
        self.dossier_donnees.joinpath("temp").mkdir(parents=True, exist_ok=True)

        def travail(ctx: Contexte) -> SessionFiche:
            dossier_temp = Path(tempfile.mkdtemp(prefix="trace_", dir=self.dossier_donnees / "temp"))
            avertissements: list[Avertissement] = []
            try:
                with self._fabrique() as source:
                    avant = prendre_instantane(source, self.config.tables_ignorees, progression=ctx.progression_annulable)
                ctx.progression("Capture d'écran…")
                capture = dossier_temp / "capture_debut.png"
                if not self._capturer(capture):
                    avertissements.append(Avertissement(None, "capture_impossible",
                                                        "La capture d'écran du début n'a pas pu être prise."))
                ctx.progression("Empreinte du fichier de la base…")
                try:
                    empreinte: str | None = self._empreinte(self.config.base_test)
                except OSError as erreur:
                    journal.warning("Empreinte du fichier impossible : %s", erreur)
                    empreinte = None
                    avertissements.append(Avertissement(None, "empreinte_impossible",
                                                        "L'empreinte du fichier de la base n'a pas pu être calculée."))
                ctx.verifier_annulation()
                return SessionFiche(fiche, self._maintenant(), avant, dossier_temp,
                                    {"debut": capture if capture.is_file() else None, "fin": None}, empreinte, avertissements)
            except BaseException:
                shutil.rmtree(dossier_temp, ignore_errors=True)
                raise

        def reussi(session: SessionFiche) -> None:
            self.session = session
            self._changer_etat(Etat.EN_COURS)

        def retour() -> None:
            self._changer_etat(Etat.FICHE_CHOISIE)

        self._changer_etat(Etat.DEBUT_EN_COURS)
        self._lancer("debut", travail, reussi, lambda erreur: retour(), retour)

    def cocher(self, numero: int, coche: bool) -> None:
        if self.session is None:
            return
        (self.session.cochees.add if coche else self.session.cochees.discard)(numero)

    def annuler(self, remarques: str = "") -> None:
        """« Annuler » (entre Début et Fin) : la trace est marquée annulée et conservée (SPEC §5.2)."""
        if self.etat == Etat.DEBUT_EN_COURS:
            self.annuler_operation()
            return
        if self.etat != Etat.EN_COURS or self.session is None:
            self.ecouteur.erreur(ErreurAffichable("Aucune fiche à annuler."))
            return
        if not self._libre():
            return
        session = self.session

        def travail(ctx: Contexte) -> ResultatFiche:
            ctx.progression("Enregistrement de la trace annulée…")
            trace = construire_trace(
                FicheTrace(session.fiche.id, session.fiche.titre, session.fiche.valeurs_saisies),
                Execution(session.debut, self._maintenant(), remarques=remarques, annulee=True),
                self.config.base_test, None, None, session.empreinte_fichier_avant, session.avertissements)
            return self._enregistrer(trace, session)

        self._changer_etat(Etat.FIN_EN_COURS)
        self._lancer("fiche", travail, self._fiche_terminee, self._fiche_a_reprendre)

    def fin(self, remarques: str | None) -> None:
        """« Fin » : attente de stabilisation, photo après, diff, interprétation, rapport, dépôt.

        `remarques` doit avoir été proposé à l'utilisateur : `None` est refusé ; `""` signifie
        « aucune remarque », confirmée explicitement (SPEC §5.2).
        """
        if self.etat != Etat.EN_COURS or self.session is None:
            self.ecouteur.erreur(ErreurAffichable("Aucune fiche en cours : cliquez d'abord sur « Début »."))
            return
        if remarques is None:
            self.ecouteur.erreur(ErreurAffichable(
                "Les remarques doivent être proposées avant de clôturer la fiche (laissez le champ vide si "
                "vous n'avez rien à signaler)."))
            return
        if not self._libre():
            return
        session, fin_clic = self.session, self._maintenant()

        def travail(ctx: Contexte) -> ResultatFiche:
            self._attendre_stabilisation(ctx)
            with self._fabrique() as source:  # connexion neuve : pas de cache périmé (AMB-027)
                apres = prendre_instantane(source, self.config.tables_ignorees, progression=ctx.progression)
            ctx.progression("Capture d'écran…")
            capture = session.dossier_temp / "capture_fin.png"
            avertissements = list(session.avertissements)
            if self._capturer(capture):
                session.captures["fin"] = capture
            else:
                avertissements.append(Avertissement(None, "capture_impossible", "La capture d'écran de fin n'a pas pu être prise."))
            ctx.progression("Calcul des différences…")
            cles = cles_candidates_du_profil(self.profil) if self.profil is not None else None
            diff = comparer_instantanes(session.avant, apres, cles, self.tables_bruit)
            interpretation = interpreter(diff, session.avant, apres, session.fiche.valeurs_saisies, session.debut,
                                         fin_clic, self.profil)
            ctx.progression("Écriture du rapport et dépôt…")
            trace = construire_trace(
                FicheTrace(session.fiche.id, session.fiche.titre, session.fiche.valeurs_saisies),
                Execution(session.debut, fin_clic, remarques=remarques), self.config.base_test, diff, interpretation,
                session.empreinte_fichier_avant, avertissements)
            return self._enregistrer(trace, session)

        self._changer_etat(Etat.FIN_EN_COURS)
        self._lancer("fiche", travail, self._fiche_terminee, self._fiche_a_reprendre)

    def _attendre_stabilisation(self, ctx: Contexte) -> None:
        total = int(self.config.delai_stabilisation_s)
        reste = float(self.config.delai_stabilisation_s)
        while reste > 0:
            ctx.progression(f"Attente de {total} s pour laisser le logiciel finir ses écritures…",
                            int(self.config.delai_stabilisation_s - reste), total)
            pas = min(0.25, reste)
            self._dormir(pas)
            reste -= pas

    def _enregistrer(self, trace: dict[str, Any], session: SessionFiche) -> ResultatFiche:
        depot = enregistrer_trace(trace, self.dossier_local, Path(self.config.dossier_sorties), session.captures,
                                  tuple(self.config.secrets()))
        dossier = depot.destination if depot.destination is not None else self.dossier_local / depot.nom
        self.statuts = self._calculer_statuts()
        return ResultatFiche(trace, resume_trace(trace), trace["execution"]["statut"], depot, dossier / "rapport.html")

    def _fiche_terminee(self, resultat: ResultatFiche) -> None:
        if self.session is not None:
            shutil.rmtree(self.session.dossier_temp, ignore_errors=True)
        self.session, self.fiche = None, None
        self._changer_etat(Etat.REPOS)

    def _fiche_a_reprendre(self, *_: Any) -> None:
        """Échec pendant « Fin » : la photo avant est conservée, l'utilisateur peut recliquer sur « Fin »."""
        self._changer_etat(Etat.EN_COURS if self.session is not None else Etat.REPOS)

    def peut_quitter_sans_perte(self) -> bool:
        return self.etat in (Etat.REPOS, Etat.FICHE_CHOISIE) and not self.occupe
