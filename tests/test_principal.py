"""Point d'entrée : démarrage, refus de la sécurité (F1), journal sans mot de passe."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

import traceur.__main__ as principal
from test_controleur import Monde


def _ecran() -> bool:
    try:
        import tkinter

        tkinter.Tk().destroy()
        return True
    except (ImportError, Exception):  # noqa: BLE001 - pas de Tkinter ou pas d'écran
        return False


@pytest.fixture(autouse=True)
def journal_propre() -> Any:
    racine = logging.getLogger("traceur")
    avant = list(racine.handlers)
    yield
    for gestionnaire in racine.handlers[:]:
        if gestionnaire not in avant:
            racine.removeHandler(gestionnaire)
            gestionnaire.close()


@pytest.fixture
def dossier(tmp_path: Path) -> Path:
    monde = Monde(tmp_path)
    config = {"base_test": monde.config.base_test, "instantane_reference": monde.config.instantane_reference,
              "chemins_interdits": [r"\\SERVEUR\Compta\compta.mdb"], "fichier_fiches": str(monde.fiches),
              "dossier_sorties": str(tmp_path / "partage"), "mot_de_passe": "S3cr3t!Test"}
    (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
    return tmp_path


def test_configuration_absente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(principal, "_erreur_fatale", messages.append)
    assert principal.lancer([], dossier=tmp_path) == 1
    assert len(messages) == 1 and "introuvable" in messages[0] and (tmp_path / "journal.log").is_file()


def test_refus_de_demarrer_sur_une_base_de_production(dossier: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(principal, "_erreur_fatale", messages.append)
    config = json.loads((dossier / "config.json").read_text(encoding="utf-8"))
    config["chemins_interdits"] = [config["base_test"].upper()]
    (dossier / "config.json").write_text(json.dumps(config), encoding="utf-8")
    assert principal.lancer([], dossier=dossier) == 1
    assert "DÉMARRAGE REFUSÉ" in messages[0] and "PRODUCTION" in messages[0]
    assert "S3cr3t!Test" not in (dossier / "journal.log").read_text(encoding="utf-8")


def test_refus_si_test_et_reference_identiques(dossier: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(principal, "_erreur_fatale", messages.append)
    config = json.loads((dossier / "config.json").read_text(encoding="utf-8"))
    config["instantane_reference"] = config["base_test"]
    (dossier / "config.json").write_text(json.dumps(config), encoding="utf-8")
    assert principal.lancer(["--config", str(dossier / "config.json")], dossier=dossier) == 1
    assert "même fichier que l'instantané" in messages[0]


def test_configuration_invalide(dossier: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(principal, "_erreur_fatale", messages.append)
    (dossier / "config.json").write_text('{"base_test": "x"}', encoding="utf-8")
    assert principal.lancer([], dossier=dossier) == 1 and "instantane_reference" in messages[0]


def test_pyodbc_inutilisable_message_clair_avant_d_ouvrir_la_fenetre(dossier: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(principal, "_erreur_fatale", messages.append)
    monkeypatch.setitem(__import__("sys").modules, "pyodbc", None)  # import impossible
    assert principal.lancer([], dossier=dossier) == 1
    assert "pyodbc" in messages[0] and "Cause :" in messages[0] and "pip install pyodbc" in messages[0]
    assert "même environnement" in messages[0]


def test_pilote_access_absent_message_clair(dossier: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import types

    messages: list[str] = []
    monkeypatch.setattr(principal, "_erreur_fatale", messages.append)
    faux = types.ModuleType("pyodbc")
    faux.drivers = lambda: ["SQL Server"]  # type: ignore[attr-defined]
    monkeypatch.setitem(__import__("sys").modules, "pyodbc", faux)
    assert principal.lancer([], dossier=dossier) == 1
    assert "Aucun pilote ODBC Access" in messages[0] and "32 bits" in messages[0]


@pytest.mark.skipif(not _ecran(), reason="aucun écran disponible pour Tkinter")
def test_demarrage_complet(dossier: Path) -> None:
    from test_ui import FauxDialogues

    (dossier / "monde").mkdir()
    monde = Monde(dossier / "monde")
    dialogues = FauxDialogues()
    app = principal.lancer([], fabrique=monde.fabrique, dialogues=dialogues, dossier=dossier, boucle=False)
    try:
        app.controleur.executeur.attendre()
        app.update()
        assert app.controleur.connexion_ok is True and [f.id for f in app.controleur.fiches] == ["S-003", "S-004"]
        assert app.lbl_profil.cget("text") == "Profil absent — lancer le profilage"
        # journal.log local à côté du programme, mot de passe masqué dès qu'il est connu
        logging.getLogger("traceur.test").info("connexion avec S3cr3t!Test")
        contenu = (dossier / "journal.log").read_text(encoding="utf-8")
        assert "connexion avec ***" in contenu and "S3cr3t!Test" not in contenu
        assert app.controleur.dossier_local == dossier / "traces_locales" and app.controleur.dossier_donnees == dossier / "donnees_locales"
    finally:
        app.destroy()


@pytest.mark.skipif(not _ecran(), reason="aucun écran disponible pour Tkinter")
def test_ctrl_c_arret_propre_sans_trace(dossier: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from test_ui import FauxDialogues
    from traceur.ui.application import Application

    (dossier / "monde").mkdir()
    monde = Monde(dossier / "monde")

    def mainloop_interrompu(self: Any, *args: Any) -> None:
        self.controleur.executeur.attendre()
        raise KeyboardInterrupt

    monkeypatch.setattr(Application, "mainloop", mainloop_interrompu)
    code = principal.lancer([], fabrique=monde.fabrique, dialogues=FauxDialogues(), dossier=dossier)
    assert code == 130  # convention : 128 + SIGINT
    assert "Arrêt demandé par Ctrl+C" in (dossier / "journal.log").read_text(encoding="utf-8")
