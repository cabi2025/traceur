"""Logique de l'application (J6) : aucune dépendance à Tkinter ; la base est un SQLite en mémoire."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pytest

from conftest import DEBUT, SAISIES_FACTURE, _creer_base_facture, _requetes_facture
from traceur.config import MESSAGE_FICHES_INDISPONIBLES, Configuration
from traceur.controleur import (
    MESSAGE_ERREUR_INATTENDUE,
    MESSAGE_OCCUPE,
    Controleur,
    ErreurAffichable,
    Etat,
    ExecuteurTaches,
    OperationAnnulee,
    Progression,
    ResultatFiche,
    ResultatProfilage,
)
from traceur.sources.access import ErreurConnexion
from traceur.sources.sqlite import SourceSqlite


class Enregistreur:
    """Écouteur de test : garde tout ce que l'interface recevrait."""

    def __init__(self) -> None:
        self.progressions: list[Progression] = []
        self.erreurs: list[ErreurAffichable] = []
        self.resultats: list[tuple[str, Any]] = []
        self.annulations: list[str] = []
        self.nb_etats = 0

    def progression(self, progression: Progression) -> None:
        self.progressions.append(progression)

    def erreur(self, erreur: ErreurAffichable) -> None:
        self.erreurs.append(erreur)

    def etat_change(self) -> None:
        self.nb_etats += 1

    def resultat(self, nom: str, valeur: Any) -> None:
        self.resultats.append((nom, valeur))

    def annule(self, nom: str) -> None:
        self.annulations.append(nom)

    def dernier(self, nom: str) -> Any:
        return next(v for n, v in reversed(self.resultats) if n == nom)

    def messages(self) -> list[str]:
        return [e.message for e in self.erreurs]


class Monde:
    """Poste de test : base SQLite, config, fiches, contrôleur et écouteur."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.base = sqlite3.connect(":memory:", check_same_thread=False)
        _creer_base_facture(self.base)
        self.echecs_connexion: list[Exception] = []
        self.bloquer = threading.Event()  # si posé à False par un test, la connexion attend
        self.bloquer.set()
        self.ouvertures = 0
        (tmp / "test.mdb").write_bytes(b"BASE DE TEST")
        (tmp / "ref.mdb").write_bytes(b"REFERENCE")
        self.fiches = tmp / "fiches.json"
        self.fiches.write_text(json.dumps({"format_version": "1.0", "lot": 2, "fiches": [{
            "id": "S-003", "titre": "Saisie facture achat", "duree_min": 3, "prerequis": ["Logiciel ouvert"],
            "reinitialiser_avant": False,
            "etapes": [{"n": 1, "texte": "Ouvrir l'écran", "capture_ref": "001"}, {"n": 2, "texte": "Valider"}],
            "valeurs_saisies": [{"champ_ecran": v.champ_ecran, "ecran": v.ecran, "valeur": v.valeur, "type": v.type}
                                for v in SAISIES_FACTURE],
            "a_noter": ["Numéro de pièce"]}, {"id": "S-004", "titre": "Autre", "etapes": [], "valeurs_saisies": []}]}),
            encoding="utf-8")
        self.config = Configuration(
            str(tmp / "test.mdb"), str(tmp / "ref.mdb"), (r"\\SERVEUR\Compta\compta.mdb",), str(tmp / "partage"),
            fichier_fiches=str(self.fiches), mot_de_passe="S3cr3t!Test", delai_stabilisation_s=3)
        self.ecouteur = Enregistreur()
        self.pauses: list[float] = []
        self.captures: list[Path] = []
        self.capture_ok = True
        self.controleur = self._controleur()

    @contextmanager
    def fabrique(self) -> Iterator[SourceSqlite]:
        self.bloquer.wait(10)
        if self.echecs_connexion:
            raise self.echecs_connexion.pop(0)
        self.ouvertures += 1
        yield SourceSqlite(self.base)

    def _capturer(self, chemin: Path) -> bool:
        self.captures.append(chemin)
        if self.capture_ok:
            chemin.write_bytes(b"PNG")
        return self.capture_ok

    def _controleur(self, **options: Any) -> Controleur:
        return Controleur(
            self.config, self.fabrique, self.tmp / "traces_locales", self.tmp / "donnees", self.ecouteur,
            maintenant=lambda: DEBUT, dormir=self.pauses.append, capturer=self._capturer,
            version_jet=lambda chemin: "Jet 4", **options)

    def faire(self, action: Any, *args: Any) -> None:
        action(*args)
        self.controleur.executeur.attendre()

    def action_du_comptable(self, debit: str = "1234.56") -> None:
        for requete in _requetes_facture(debit):
            self.base.execute(requete)


@pytest.fixture
def monde(tmp_path: Path) -> Monde:
    return Monde(tmp_path)


def _demarre(monde: Monde) -> Controleur:
    monde.faire(monde.controleur.demarrer)
    return monde.controleur


def _fiche_complete(monde: Monde, remarques: str = "Message : n° 2025-ACH-0042", debit: str = "1234.56") -> ResultatFiche:
    c = monde.controleur
    c.choisir_fiche("S-003")
    monde.faire(c.debut)
    monde.action_du_comptable(debit)
    monde.faire(c.fin, remarques)
    assert not monde.ecouteur.erreurs, monde.ecouteur.messages()
    resultat: ResultatFiche = monde.ecouteur.dernier("fiche")
    return resultat


# --- démarrage -------------------------------------------------------------------------------

def test_demarrage_charge_fiches_teste_la_connexion_et_reprend_les_depots(monde: Monde) -> None:
    c = _demarre(monde)
    assert [f.id for f in c.fiches] == ["S-003", "S-004"] and c.message_fiches is None
    assert c.connexion_ok is True and c.connexion_message == "Connectée en lecture seule (4 tables)"
    assert c.statuts == {"S-003": "à faire", "S-004": "à faire"}
    assert [n for n, _ in monde.ecouteur.resultats] == ["connexion", "depots"] and not monde.ecouteur.erreurs
    b = c.bandeau()
    assert (b.base_test, b.profil, b.profil_present) == (monde.config.base_test, "Profil absent — lancer le profilage", False)


def test_sans_fichier_de_fiches_profilage_et_calibration_seulement(monde: Monde) -> None:
    """AMB-023 : boutons de fiche désactivés avec un message ; le reste fonctionne."""
    from dataclasses import replace

    monde.config = replace(monde.config, fichier_fiches=None)
    monde.controleur = monde._controleur()
    c = _demarre(monde)
    assert c.fiches == [] and c.message_fiches == MESSAGE_FICHES_INDISPONIBLES
    with pytest.raises(ErreurAffichable, match="seuls le profilage et la calibration"):
        c.choisir_fiche("S-003")
    monde.faire(c.profiler)
    assert isinstance(monde.ecouteur.dernier("profilage"), ResultatProfilage)


def test_fichier_de_fiches_invalide_message_en_francais(monde: Monde) -> None:
    monde.fiches.write_text('{"fiches": [{"id": "S-1", "titre": "t", "valeurs_saisies": [{"champ_ecran": "x", "type": "inconnu"}]}]}', encoding="utf-8")
    c = _demarre(monde)
    assert c.fiches == [] and "Fiche S-1" in (c.message_fiches or "") and "type parmi" in (c.message_fiches or "")


def test_connexion_impossible(monde: Monde) -> None:
    monde.echecs_connexion.append(ErreurConnexion("Connexion à la base impossible. Mot de passe incorrect pour la base."))
    c = _demarre(monde)
    assert c.connexion_ok is False and c.connexion_message == "Connexion impossible"
    assert monde.ecouteur.messages() == ["Connexion à la base impossible. Mot de passe incorrect pour la base."]
    assert "depots" in [n for n, _ in monde.ecouteur.resultats]  # le démarrage continue


# --- profilage -------------------------------------------------------------------------------

def test_profilage_ecrit_localement_et_sur_le_partage_et_se_recharge(monde: Monde) -> None:
    c = _demarre(monde)
    monde.faire(c.profiler)
    resultat: ResultatProfilage = monde.ecouteur.dernier("profilage")
    assert resultat.avertissement is None and resultat.chemin_html.name == "profil.html"
    assert (monde.tmp / "donnees" / "profil" / "profil.json").is_file() and (monde.tmp / "partage" / "profil" / "profil.html").is_file()
    assert resultat.profil.version_jet == "Jet 4" and c.bandeau().profil_present
    assert c.bandeau().profil == "Dernier profilage : 05/10/2026 10:15"
    assert any("Lecture" in p.message or "Profilage" in p.message for p in monde.ecouteur.progressions)
    autre = monde._controleur()  # nouveau démarrage : le profil enregistré est rechargé (typé)
    monde.controleur = autre
    monde.faire(autre.demarrer)
    assert autre.profil is not None and autre.bandeau().profil_present


def test_profilage_partage_indisponible_enregistre_en_local_avec_avertissement(monde: Monde) -> None:
    (monde.tmp / "partage").write_text("bloc", encoding="utf-8")  # le « partage » est un fichier : inaccessible
    c = _demarre(monde)
    monde.faire(c.profiler)
    resultat: ResultatProfilage = monde.ecouteur.dernier("profilage")
    assert "indisponible" in (resultat.avertissement or "") and (monde.tmp / "donnees" / "profil" / "profil.json").is_file()
    assert c.profil is not None


def test_profilage_annulable(monde: Monde) -> None:
    c = _demarre(monde)
    monde.bloquer.clear()
    c.profiler()
    c.annuler_operation()
    monde.bloquer.set()
    c.executeur.attendre()
    assert monde.ecouteur.annulations == ["profilage"] and c.profil is None
    assert not (monde.tmp / "donnees" / "profil").exists()


# --- calibration -----------------------------------------------------------------------------

def test_calibration_proposition_validation_et_usage_dans_le_diff(monde: Monde) -> None:
    c = _demarre(monde)
    c._dormir = lambda duree: monde.base.execute("UPDATE SESSIONS SET DERNIER = ?", (str(duree),))
    monde.faire(c.calibrer, 5.0)
    calibration = monde.ecouteur.dernier("calibration")
    assert calibration.proposees == {"SESSIONS": "1 ligne modifiée"} and calibration.intervalle_s == 5.0
    assert c.tables_bruit == []  # rien n'est retenu avant la validation de l'utilisateur
    assert c.valider_calibration(["SESSIONS"]) is None
    assert c.tables_bruit == ["SESSIONS"]
    assert json.loads((monde.tmp / "partage" / "calibration" / "bruit.json").read_text("utf-8"))["tables_bruit"] == ["SESSIONS"]
    assert (monde.tmp / "donnees" / "calibration" / "bruit.json").is_file()
    c._dormir = monde.pauses.append
    resultat = _fiche_complete(monde)
    assert [b["table"] for b in resultat.trace["bruit"]] == ["SESSIONS"]  # la table de bruit est rapportée à part
    assert "SESSIONS" not in [t["table"] for t in resultat.trace["changements"]]


def test_calibration_validation_inconnue_ou_absente(monde: Monde) -> None:
    c = _demarre(monde)
    with pytest.raises(ErreurAffichable, match="Aucune calibration à valider"):
        c.valider_calibration([])
    monde.faire(c.calibrer, 1.0)
    with pytest.raises(ErreurAffichable, match="non proposées"):
        c.valider_calibration(["ECRITURES"])


def test_calibration_annulable_pendant_l_attente(monde: Monde) -> None:
    c = _demarre(monde)

    def dormir_puis_annuler(duree: float) -> None:
        c.annuler_operation()

    c._dormir = dormir_puis_annuler
    monde.faire(c.calibrer, 30.0)
    assert monde.ecouteur.annulations == ["calibration"]
    assert any("encore" in p.message and "ne touchez pas" in p.message for p in monde.ecouteur.progressions)


# --- réinitialisation ------------------------------------------------------------------------

def test_reinitialisation_confirmee(monde: Monde) -> None:
    c = _demarre(monde)
    texte = c.preparer_reinitialisation()
    assert monde.config.base_test in texte and "ÉCRASER" in texte
    monde.faire(c.reinitialiser, True)
    assert not monde.ecouteur.erreurs
    assert (monde.tmp / "test.mdb").read_bytes() == b"REFERENCE"
    assert monde.ecouteur.dernier("reinitialisation").octets == len(b"REFERENCE")


def test_reinitialisation_non_confirmee_ne_touche_a_rien(monde: Monde) -> None:
    c = _demarre(monde)
    monde.faire(c.reinitialiser, False)
    assert (monde.tmp / "test.mdb").read_bytes() == b"BASE DE TEST" and "annulée" in monde.ecouteur.messages()[-1]


def test_reinitialisation_refusee_si_logiciel_ouvert_ou_base_interdite(monde: Monde) -> None:
    c = _demarre(monde)
    (monde.tmp / "test.ldb").write_bytes(b"")
    with pytest.raises(ErreurAffichable, match="RÉINITIALISATION REFUSÉE"):
        c.preparer_reinitialisation()
    (monde.tmp / "test.ldb").unlink()
    from dataclasses import replace

    c.config = replace(monde.config, chemins_interdits=(monde.config.base_test,))
    with pytest.raises(ErreurAffichable, match="PRODUCTION"):
        c.preparer_reinitialisation()


def test_reinitialisation_refusee_pendant_une_fiche(monde: Monde) -> None:
    c = _demarre(monde)
    c.choisir_fiche("S-003")
    monde.faire(c.debut)
    with pytest.raises(ErreurAffichable, match="fiche en cours"):
        c.preparer_reinitialisation()


# --- une fiche, de bout en bout ---------------------------------------------------------------

def test_parcours_complet_d_une_fiche(monde: Monde) -> None:
    c = _demarre(monde)
    fiche = c.choisir_fiche("S-003")
    assert (fiche.id, c.etat) == ("S-003", Etat.FICHE_CHOISIE)
    monde.faire(c.debut)
    assert c.etat == Etat.EN_COURS and c.session is not None
    assert c.session.empreinte_fichier_avant is not None and c.session.empreinte_fichier_avant.startswith("sha256:")
    assert c.session.captures["debut"] is not None and c.session.avant.nb_lignes == 3
    c.cocher(1, True)
    c.cocher(2, True)
    c.cocher(2, False)
    assert c.session.cochees == {1}
    monde.action_du_comptable()
    monde.faire(c.fin, "Message : Écriture enregistrée sous le n° 2025-ACH-0042")
    assert not monde.ecouteur.erreurs and c.etat == Etat.REPOS and c.session is None and c.fiche is None

    r: ResultatFiche = monde.ecouteur.dernier("fiche")
    assert r.statut == "terminee" and not r.ecart_de_saisie and not r.depot_en_attente
    assert r.resume == "4 tables modifiées, 2 lignes ajoutées, 2 modifiées"  # SESSIONS n'est pas encore en bruit
    assert r.rapport.is_file() and r.rapport.name == "rapport.html" and (monde.tmp / "partage" / "traces") in r.rapport.parents
    assert (r.rapport.parent / "capture_debut.png").is_file() and (r.rapport.parent / "capture_fin.png").is_file()
    trace = json.loads((r.rapport.parent / "trace.json").read_text(encoding="utf-8"))
    assert trace["execution"]["debut"] == "2026-10-05T10:15:22" and trace["execution"]["remarques"].startswith("Message")
    assert trace["base"]["chemin"] == monde.config.base_test and {x["colonne"] for x in trace["liens"]} >= {"DEBIT", "COMPTE"}
    assert c.statuts["S-003"] == "faite" and c.statuts["S-004"] == "à faire"
    assert "Ouvrir le rapport" in (monde.tmp / "partage" / "index.html").read_text(encoding="utf-8")
    assert sum(monde.pauses) == pytest.approx(3.0)  # délai de stabilisation avant la photo après
    assert list((monde.tmp / "donnees" / "temp").iterdir()) == []  # captures temporaires nettoyées
    assert monde.ouvertures >= 3  # une connexion neuve par photo (AMB-027)
    assert any("Attente de 3 s" in p.message for p in monde.ecouteur.progressions)
    assert [p.message for p in monde.ecouteur.progressions if "Lecture" in p.message]


def test_ecart_de_saisie_detecte_et_statut_ecart(monde: Monde) -> None:
    c = _demarre(monde)
    r = _fiche_complete(monde, debit="1243.56")
    assert r.statut == "ecart_saisie" and r.ecart_de_saisie
    assert [e["type_ecart"] for e in r.trace["ecarts_saisie"]] == ["introuvable"]
    assert c.statuts["S-003"] == "écart" and "Écart de saisie" in r.rapport.read_text(encoding="utf-8")


def test_le_profil_enrichit_l_interpretation_et_les_cles(monde: Monde) -> None:
    c = _demarre(monde)
    monde.faire(c.profiler)
    r = _fiche_complete(monde)
    assert not any(a["code"] == "profil_absent" for a in r.trace["avertissements"])
    comptes = next(t for t in r.trace["changements"] if t["table"] == "COMPTEURS")
    assert comptes["cle_utilisee"]["type"] == "primaire"


def test_sans_profil_avertissement_dans_la_trace(monde: Monde) -> None:
    _demarre(monde)
    r = _fiche_complete(monde)
    assert any(a["code"] == "profil_absent" for a in r.trace["avertissements"])


def test_annulation_entre_debut_et_fin_trace_conservee(monde: Monde) -> None:
    c = _demarre(monde)
    c.choisir_fiche("S-003")
    monde.faire(c.debut)
    monde.faire(c.annuler, "Logiciel planté")
    r: ResultatFiche = monde.ecouteur.dernier("fiche")
    assert r.statut == "annulee" and c.etat == Etat.REPOS and c.session is None
    trace = json.loads(r.rapport.with_name("trace.json").read_text(encoding="utf-8"))
    assert trace["execution"]["statut"] == "annulee" and trace["execution"]["remarques"] == "Logiciel planté"
    assert trace["changements"] == [] and "Fiche annulée" in r.resume
    assert c.statuts["S-003"] == "annulée"


def test_annulation_pendant_la_photo_de_debut(monde: Monde) -> None:
    c = _demarre(monde)
    c.choisir_fiche("S-003")
    monde.bloquer.clear()
    c.debut()
    assert c.etat == Etat.DEBUT_EN_COURS
    c.annuler()  # « Annuler » pendant la photo : demande d'annulation
    monde.bloquer.set()
    c.executeur.attendre()
    assert c.etat == Etat.FICHE_CHOISIE and c.session is None and monde.ecouteur.annulations == ["debut"]
    assert list((monde.tmp / "donnees" / "temp").iterdir()) == [] and c.statuts["S-003"] == "à faire"
    assert not (monde.tmp / "partage" / "traces").exists()  # rien d'enregistré


def test_remarques_doivent_etre_proposees(monde: Monde) -> None:
    c = _demarre(monde)
    c.choisir_fiche("S-003")
    monde.faire(c.debut)
    c.fin(None)
    assert "proposées avant de clôturer" in monde.ecouteur.messages()[-1] and c.etat == Etat.EN_COURS
    monde.faire(c.fin, "")  # « aucune remarque », confirmée explicitement
    assert c.etat == Etat.REPOS and monde.ecouteur.dernier("fiche").trace["execution"]["remarques"] == ""


def test_echec_pendant_fin_conserve_la_fiche_et_permet_de_recommencer(monde: Monde) -> None:
    c = _demarre(monde)
    c.choisir_fiche("S-003")
    monde.faire(c.debut)
    monde.action_du_comptable()
    monde.echecs_connexion.append(ErreurConnexion("Connexion à la base impossible. La base est ouverte en mode exclusif."))
    monde.faire(c.fin, "x")
    assert c.etat == Etat.EN_COURS and c.session is not None  # la photo avant est conservée
    assert "mode exclusif" in monde.ecouteur.messages()[-1]
    monde.faire(c.fin, "x")  # nouvel essai
    assert c.etat == Etat.REPOS and monde.ecouteur.dernier("fiche").statut == "terminee"


def test_partage_indisponible_a_la_fin_trace_en_attente_puis_reprise(monde: Monde) -> None:
    c = _demarre(monde)
    blocage = monde.tmp / "partage"
    blocage.write_text("bloc", encoding="utf-8")
    r = _fiche_complete(monde)
    assert r.depot_en_attente and r.rapport.is_file() and monde.tmp / "traces_locales" in r.rapport.parents
    assert c.statuts["S-003"] == "faite"  # le statut vient aussi des traces locales
    blocage.unlink()
    monde.faire(c.reprendre_depots)
    assert not (monde.tmp / "traces_locales").exists() or not list((monde.tmp / "traces_locales").iterdir())
    assert len(list((monde.tmp / "partage" / "traces").iterdir())) == 1


def test_capture_impossible_ne_bloque_pas_la_fiche(monde: Monde) -> None:
    monde.capture_ok = False
    _demarre(monde)
    r = _fiche_complete(monde)
    assert r.statut == "terminee" and not (r.rapport.parent / "capture_debut.png").exists()
    assert {a["code"] for a in r.trace["avertissements"]} >= {"capture_impossible"}
    assert "Aucune capture disponible." in r.rapport.read_text(encoding="utf-8")


def test_aucun_mot_de_passe_dans_la_trace(monde: Monde) -> None:
    _demarre(monde)
    r = _fiche_complete(monde, remarques="le mot de passe est S3cr3t!Test")
    for fichier in ("trace.json", "rapport.html", "remarques.txt"):
        assert "S3cr3t!Test" not in (r.rapport.parent / fichier).read_text(encoding="utf-8")


# --- états, erreurs, tâches ------------------------------------------------------------------

def test_etats_interdits(monde: Monde) -> None:
    c = _demarre(monde)
    with pytest.raises(ErreurAffichable, match="Fiche inconnue"):
        c.choisir_fiche("S-999")
    c.debut()
    c.fin("x")
    c.annuler()
    assert monde.ecouteur.messages()[-3:] == ["Choisissez d'abord une fiche.",
                                              "Aucune fiche en cours : cliquez d'abord sur « Début ».",
                                              "Aucune fiche à annuler."]
    c.choisir_fiche("S-003")
    c.abandonner_choix()
    assert c.etat == Etat.REPOS and c.fiche is None
    c.choisir_fiche("S-003")
    monde.faire(c.debut)
    with pytest.raises(ErreurAffichable, match="déjà en cours"):
        c.choisir_fiche("S-004")


def test_une_seule_operation_a_la_fois(monde: Monde) -> None:
    c = _demarre(monde)
    monde.bloquer.clear()
    c.profiler()
    c.calibrer()
    c.profiler()
    assert monde.ecouteur.messages() == [MESSAGE_OCCUPE, MESSAGE_OCCUPE]
    monde.bloquer.set()
    c.executeur.attendre()
    assert c.profil is not None


def test_peut_quitter(monde: Monde) -> None:
    c = _demarre(monde)
    assert c.peut_quitter_sans_perte()
    c.choisir_fiche("S-003")
    assert c.peut_quitter_sans_perte()
    monde.faire(c.debut)
    assert not c.peut_quitter_sans_perte()


def test_erreur_inattendue_message_general_et_detail_au_journal(monde: Monde, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR, "traceur")
    c = _demarre(monde)
    monde.echecs_connexion.append(RuntimeError("détail technique secret-interne"))
    monde.faire(c.profiler)
    assert monde.ecouteur.messages() == [MESSAGE_ERREUR_INATTENDUE]
    assert "secret-interne" not in monde.ecouteur.messages()[0] and "secret-interne" in caplog.text


def test_erreur_d_acces_fichier_message_clair(monde: Monde) -> None:
    c = _demarre(monde)
    monde.echecs_connexion.append(PermissionError("[WinError 5] Accès refusé"))
    monde.faire(c.profiler)
    assert "Problème d'accès à un fichier ou au réseau" in monde.ecouteur.messages()[0]


# --- exécuteur de tâches ---------------------------------------------------------------------

def test_executeur_progression_resultat_et_annulation() -> None:
    ex = ExecuteurTaches()
    recus: list[Any] = []

    def travail(ctx: Any) -> int:
        ctx.progression("étape 1", 1, 4)
        ctx.progression_annulable("étape 2", 2, 4)
        return 42

    ex.lancer(travail, recus.append, recus.append, lambda p: recus.append(p.message))
    ex.attendre()
    assert recus == ["étape 1", "étape 2", 42] and not ex.occupe

    def boucle(ctx: Any) -> None:
        while True:
            ctx.verifier_annulation()

    ex.lancer(boucle, recus.append, recus.append, None, lambda: recus.append("annulé"))
    ex.annuler()
    ex.attendre()
    assert recus[-1] == "annulé"


def test_executeur_refuse_deux_travaux_et_survit_a_un_rappel_fautif(caplog: pytest.LogCaptureFixture) -> None:
    ex = ExecuteurTaches()
    gel = threading.Event()
    ex.lancer(lambda ctx: gel.wait(5), lambda v: None, lambda e: None)
    with pytest.raises(ErreurAffichable, match="déjà en cours"):
        ex.lancer(lambda ctx: 1, lambda v: None, lambda e: None)
    gel.set()
    ex.attendre()

    def rappel_fautif(valeur: Any) -> None:
        raise RuntimeError("bug dans l'interface")

    ex.lancer(lambda ctx: 1, rappel_fautif, lambda e: None)
    ex.attendre()
    assert not ex.occupe and "Erreur dans un rappel de l'interface" in caplog.text
    assert Progression("x", 1, 4).fraction == 0.25 and Progression("x").fraction is None and Progression("x", 5, 4).fraction == 1.0
    assert issubclass(OperationAnnulee, Exception)
