import copy
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from traceur.rapports import depot
from traceur.rapports.depot import (
    DEPOSEE,
    EN_ATTENTE,
    creer_trace_locale,
    deposer_trace,
    enregistrer_trace,
    lister_en_attente,
    reprendre_depots_en_attente,
)

NOM = "S-003_20261005-101522"


@pytest.fixture
def captures(tmp_path: Path) -> dict[str, Path | None]:
    debut, fin = tmp_path / "tmp_debut.png", tmp_path / "tmp_fin.png"
    debut.write_bytes(b"PNG-DEBUT")
    fin.write_bytes(b"PNG-FIN")
    return {"debut": debut, "fin": fin}


@pytest.fixture
def locale(tmp_path: Path) -> Path:
    return tmp_path / "traces_locales"


@pytest.fixture
def partage(tmp_path: Path) -> Path:
    return tmp_path / "partage" / "sorties"


def _fichiers(dossier: Path) -> list[str]:
    return sorted(p.name for p in dossier.iterdir())


# --- écriture locale -------------------------------------------------------------------------

def test_ecriture_locale_complete(trace_facture: dict[str, Any], locale: Path, captures: dict[str, Path | None]) -> None:
    dossier = creer_trace_locale(trace_facture, locale, captures)
    assert dossier == locale / NOM
    assert _fichiers(dossier) == ["capture_debut.png", "capture_fin.png", "depot.json", "rapport.html", "remarques.txt", "trace.json"]
    assert json.loads((dossier / "trace.json").read_text(encoding="utf-8")) == trace_facture
    assert "Écriture enregistrée sous le n° 2025-ACH-0042" in (dossier / "remarques.txt").read_text(encoding="utf-8")
    assert 'src="capture_debut.png"' in (dossier / "rapport.html").read_text(encoding="utf-8")
    assert (dossier / "capture_fin.png").read_bytes() == b"PNG-FIN"
    marqueur = json.loads((dossier / "depot.json").read_text(encoding="utf-8"))
    assert (marqueur["depot"], marqueur["tentatives"], marqueur["derniere_erreur"]) == (EN_ATTENTE, 0, None)
    assert _fichiers(locale) == [NOM]  # aucun dossier de travail caché ne reste


def test_ecriture_locale_sans_captures(trace_facture: dict[str, Any], locale: Path) -> None:
    dossier = creer_trace_locale(trace_facture, locale, {"debut": None, "fin": locale / "absente.png"})
    assert "capture_debut.png" not in _fichiers(dossier)
    assert "Aucune capture disponible." in (dossier / "rapport.html").read_text(encoding="utf-8")


def test_trace_locale_deja_presente_jamais_ecrasee(trace_facture: dict[str, Any], locale: Path) -> None:
    premiere = creer_trace_locale(trace_facture, locale)
    seconde = creer_trace_locale(trace_facture, locale)
    assert (premiere.name, seconde.name) == (NOM, f"{NOM}_2") and _fichiers(locale) == [NOM, f"{NOM}_2"]


def test_aucun_mot_de_passe_dans_les_fichiers(trace_facture: dict[str, Any], locale: Path) -> None:
    trace_facture["execution"]["remarques"] = "J'ai tapé S3cr3t!Test dans la case"
    trace_facture["avertissements"].append({"table": None, "code": "x", "message": "connexion avec S3cr3t!Test"})
    dossier = creer_trace_locale(trace_facture, locale, secrets=("S3cr3t!Test",))
    for fichier in ("trace.json", "rapport.html", "remarques.txt"):
        texte = (dossier / fichier).read_text(encoding="utf-8")
        assert "S3cr3t!Test" not in texte, fichier
    assert "***" in (dossier / "remarques.txt").read_text(encoding="utf-8")
    assert json.loads((dossier / "trace.json").read_text(encoding="utf-8"))["execution"]["remarques"].count("***") == 1


# --- dépôt -----------------------------------------------------------------------------------

def test_depot_atomique_reussi(trace_facture: dict[str, Any], locale: Path, partage: Path, captures: dict[str, Path | None]) -> None:
    dossier = creer_trace_locale(trace_facture, locale, captures)
    resultat = deposer_trace(dossier, partage)
    assert (resultat.statut, resultat.nom, resultat.index_a_jour) == (DEPOSEE, NOM, True)
    final = partage / "traces" / NOM
    assert resultat.destination == final
    assert _fichiers(final) == ["capture_debut.png", "capture_fin.png", "rapport.html", "remarques.txt", "trace.json"]  # pas depot.json
    assert (final / "trace.json").read_bytes() == (dossier / "trace.json").read_bytes() if dossier.exists() else True
    assert not dossier.exists()  # dossier local supprimé après succès
    assert _fichiers(partage / "traces") == [NOM]  # aucun dossier temporaire caché
    index = (partage / "index.html").read_text(encoding="utf-8")
    assert f'href="traces/{NOM}/rapport.html"' in index and "3 tables modifiées" in index
    assert _fichiers(partage) == ["index.html", "traces"]


def test_partage_indisponible_puis_retabli(trace_facture: dict[str, Any], locale: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Critère d'acceptation J5 : le partage est inaccessible, la trace reste en local ; il revient, elle est déposée."""
    caplog.set_level(logging.INFO, "traceur")
    bloc = tmp_path / "reseau"
    bloc.write_text("ce fichier remplace le dossier : le partage est « inaccessible »", encoding="utf-8")
    partage = bloc / "sorties"  # créer ce dossier échoue (NotADirectoryError)
    dossier = creer_trace_locale(trace_facture, locale)

    resultat = deposer_trace(dossier, partage)  # ne lève aucune exception
    assert resultat.statut == EN_ATTENTE and resultat.destination is None and resultat.erreur
    assert (dossier / "trace.json").is_file() and (dossier / "rapport.html").is_file()  # trace intacte en local
    marqueur = json.loads((dossier / "depot.json").read_text(encoding="utf-8"))
    assert marqueur["depot"] == EN_ATTENTE and marqueur["tentatives"] == 1 and marqueur["derniere_erreur"]
    assert "reste en local (en_attente_depot)" in caplog.text
    assert lister_en_attente(locale) == [dossier]

    deposer_trace(dossier, partage)  # 2e échec : le compteur de tentatives avance
    assert json.loads((dossier / "depot.json").read_text(encoding="utf-8"))["tentatives"] == 2

    bloc.unlink()  # le partage est rétabli
    (resultats := reprendre_depots_en_attente(locale, partage))
    assert [(r.statut, r.nom) for r in resultats] == [(DEPOSEE, NOM)]
    assert (partage / "traces" / NOM / "trace.json").is_file() and not dossier.exists()
    assert NOM in (partage / "index.html").read_text(encoding="utf-8")
    assert reprendre_depots_en_attente(locale, partage) == [] and lister_en_attente(locale) == []


def test_copie_interrompue_ne_laisse_rien_de_visible_sur_le_partage(trace_facture: dict[str, Any], locale: Path, partage: Path) -> None:
    dossier = creer_trace_locale(trace_facture, locale)
    copies: list[str] = []

    def coupure_reseau(source: Path, destination: Path) -> None:
        if copies:
            raise ConnectionResetError("connexion réseau perdue")
        copies.append(source.name)
        shutil.copyfile(source, destination)

    resultat = deposer_trace(dossier, partage, copier=coupure_reseau)
    assert resultat.statut == EN_ATTENTE and "connexion réseau perdue" in (resultat.erreur or "")
    assert _fichiers(partage / "traces") == []  # ni dossier final ni dossier temporaire
    assert dossier.exists() and not (partage / "index.html").exists()
    assert deposer_trace(dossier, partage).statut == DEPOSEE  # la reprise aboutit


def test_copie_corrompue_detectee_par_le_hash(trace_facture: dict[str, Any], locale: Path, partage: Path) -> None:
    dossier = creer_trace_locale(trace_facture, locale)

    def corrompue(source: Path, destination: Path) -> None:
        destination.write_bytes(source.read_bytes()[:-1] + b"X")

    resultat = deposer_trace(dossier, partage, copier=corrompue)
    assert resultat.statut == EN_ATTENTE and "copie corrompue" in (resultat.erreur or "")
    assert _fichiers(partage / "traces") == [] and dossier.exists()


def test_reste_d_une_tentative_interrompue_nettoye(trace_facture: dict[str, Any], locale: Path, partage: Path) -> None:
    dossier = creer_trace_locale(trace_facture, locale)
    reste = partage / "traces" / f".{NOM}.depot-tmp"
    reste.mkdir(parents=True)
    (reste / "vieux.txt").write_text("reste d'un plantage", encoding="utf-8")
    assert deposer_trace(dossier, partage).statut == DEPOSEE
    assert _fichiers(partage / "traces") == [NOM] and "vieux.txt" not in _fichiers(partage / "traces" / NOM)


def test_trace_deja_deposee_identique_pas_de_doublon(trace_facture: dict[str, Any], locale: Path, partage: Path) -> None:
    """Le dépôt avait réussi mais le nettoyage local a échoué : la reprise ne duplique rien."""
    dossier = creer_trace_locale(trace_facture, locale)
    shutil.copytree(dossier, partage / "traces" / NOM, ignore=shutil.ignore_patterns("depot.json"))
    assert deposer_trace(dossier, partage).statut == DEPOSEE
    assert _fichiers(partage / "traces") == [NOM] and not dossier.exists()


def test_collision_de_nom_avec_une_autre_trace_suffixe(trace_facture: dict[str, Any], locale: Path, partage: Path) -> None:
    (partage / "traces" / NOM).mkdir(parents=True)
    (partage / "traces" / NOM / "trace.json").write_text('{"autre": true}', encoding="utf-8")
    dossier = creer_trace_locale(trace_facture, locale)
    resultat = deposer_trace(dossier, partage)
    assert resultat.statut == DEPOSEE and resultat.nom == f"{NOM}_2"
    assert json.loads((partage / "traces" / NOM / "trace.json").read_text(encoding="utf-8")) == {"autre": True}  # intact


def test_index_non_mis_a_jour_n_annule_pas_le_depot(trace_facture: dict[str, Any], locale: Path, partage: Path,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    def echec(*args: Any, **kwargs: Any) -> None:
        raise PermissionError("index verrouillé")

    monkeypatch.setattr(depot, "ecrire_index", echec)
    resultat = deposer_trace(creer_trace_locale(trace_facture, locale), partage)
    assert (resultat.statut, resultat.index_a_jour) == (DEPOSEE, False)
    assert (partage / "traces" / NOM / "trace.json").is_file()


def test_reprise_ignore_les_dossiers_caches_et_deja_deposes(trace_facture: dict[str, Any], locale: Path, partage: Path) -> None:
    (locale / f".{NOM}.en_cours").mkdir(parents=True)  # écriture locale interrompue : jamais reprise
    (locale / "sans_marqueur").mkdir()
    deposee = creer_trace_locale(trace_facture, locale)
    marqueur = json.loads((deposee / "depot.json").read_text(encoding="utf-8"))
    marqueur["depot"] = DEPOSEE
    (deposee / "depot.json").write_text(json.dumps(marqueur), encoding="utf-8")
    assert lister_en_attente(locale) == [] and reprendre_depots_en_attente(locale, partage) == []
    assert lister_en_attente(locale / "n_existe_pas") == []


def test_enregistrement_de_bout_en_bout(trace_facture: dict[str, Any], locale: Path,
                                         partage: Path, captures: dict[str, Path | None]) -> None:
    assert enregistrer_trace(trace_facture, locale, partage, captures).statut == DEPOSEE
    seconde = copy.deepcopy(trace_facture)
    seconde["execution"].update(debut="2026-10-05T11:00:00", statut="ecart_saisie")
    assert enregistrer_trace(seconde, locale, partage).statut == DEPOSEE
    index = (partage / "index.html").read_text(encoding="utf-8")
    assert index.count("Ouvrir le rapport") == 2 and "Écart de saisie" in index and "Terminée" in index
    assert _fichiers(locale) == []


def test_partage_indisponible_a_l_enregistrement(trace_facture: dict[str, Any], locale: Path, tmp_path: Path) -> None:
    (tmp_path / "x").write_text("bloc", encoding="utf-8")
    resultat = enregistrer_trace(trace_facture, locale, tmp_path / "x" / "sorties")
    assert resultat.statut == EN_ATTENTE and _fichiers(locale) == [NOM]
