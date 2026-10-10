"""AMB-041 / AMB-042 : réanalyse hors ligne d'un trace.json (jeu anonymisé + trace réelle locale)."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

import traceur.__main__ as principal
from traceur.config import configuration_depuis_dict
from traceur.moteur.calcules import TABLES_IGNOREES_ANALYSE_DEFAUT, est_valeur_triviale
from traceur.reanalyse import (
    ErreurReanalyse,
    NOM_RAPPORT_REANALYSE,
    NOM_TRACE_REANALYSEE,
    cellules_de_la_trace,
    lire_trace,
    reanalyser_fichier,
    reanalyser_trace,
    typer_valeur_json,
)

ANONYMISEE = Path(__file__).parent / "data" / "trace_S201_anonymisee.json"
REELLE = Path(__file__).parent.parent / "donnees_reelles" / "S-201" / "trace.json"  # locale, non versionnée


def _charger(chemin: Path) -> dict[str, Any]:
    return json.loads(chemin.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


@pytest.fixture(scope="module")
def trace() -> dict[str, Any]:
    return _charger(ANONYMISEE)


@pytest.fixture(scope="module")
def reanalysee(trace: dict[str, Any]) -> dict[str, Any]:
    return reanalyser_trace(trace)


def _verifier_acceptation(origine: dict[str, Any], nouvelle: dict[str, Any]) -> None:
    """Test d'acceptation de la demande (AMB-041 / AMB-042), valable pour la trace réelle et l'anonymisée."""
    # 1. plus d'écart de saisie sur Document ni Libellé (et statut recalculé)
    assert origine["execution"]["statut"] == "ecart_saisie"
    assert {e["champ_ecran"] for e in origine["ecarts_saisie"]} == {"Document", "Libellé"}
    assert nouvelle["ecarts_saisie"] == []
    assert nouvelle["execution"]["statut"] == "terminee"
    types = {(x["champ_ecran"], x["valeur"], x["table"], x["colonne"]): x["type_correspondance"]
             for x in nouvelle["liens"]}
    assert types[("Document", "TEST-S201", "ecrit", "Document")] == "espaces_fin"
    assert types[("Libellé", "TEST-S201", "ecrit", "Libelle")] == "espaces_fin"
    assert types[("Compte", "61263", "ecrit", "Compte")] == "espaces_fin"  # '61263    '
    # 2. plus aucune copie triviale ni issue des tables parasites
    for x in nouvelle["champs_calcules"]:
        assert "Tableau20" not in x["details"] or "copie" not in x["hypotheses"], x
        assert "Table des erreurs" not in x["details"], x
        assert "Erreurs de conversion" not in x["details"], x
        if "copie" in x["hypotheses"]:
            assert not est_valeur_triviale(x["valeur"]), x
    # 3. plus de « compteur » sur les montants
    for x in nouvelle["champs_calcules"]:
        if "compteur" in x["hypotheses"]:
            assert isinstance(x["valeur"], int) or (isinstance(x["valeur"], str) and x["valeur"].isdigit()), x
    assert not [x for x in nouvelle["champs_calcules"]
                if x["table"] in ("compte", "scompte") and "compteur" in x["hypotheses"]]
    # 4. cumul_hierarchique sur les trois chaînes de comptes (61263, 34552, 441110024)
    chaines = [x["details"] for x in nouvelle["champs_calcules"] if "cumul_hierarchique" in x["hypotheses"]]
    for attendu in ("61, 612, 6126, 61263", "34, 345, 3455, 34552", "44, 441, 4411, 44111, 441110024"):
        assert any(attendu in d for d in chaines), attendu
    # 13 comptes de `compte` touchés, tous expliqués
    compte = [x for x in nouvelle["champs_calcules"] if x["table"] == "compte"]
    assert compte and all("cumul_hierarchique" in x["hypotheses"] for x in compte)
    # le niveau classe n'apparaît jamais dans une chaîne
    for d in chaines:
        comptes = d.split(" : ")[-1].split(", ")
        assert all(len(c) >= 2 for c in comptes), d


def test_acceptation_sur_la_trace_anonymisee(trace: dict[str, Any], reanalysee: dict[str, Any]) -> None:
    _verifier_acceptation(trace, reanalysee)


@pytest.mark.skipif(not REELLE.exists(), reason="trace réelle locale absente (non versionnée)")
def test_acceptation_sur_la_trace_reelle_locale() -> None:
    reelle = _charger(REELLE)
    _verifier_acceptation(reelle, reanalyser_trace(reelle))


def test_l_original_n_est_pas_modifie(trace: dict[str, Any]) -> None:
    avant = copy.deepcopy(trace)
    reanalyser_trace(trace)
    assert trace == avant


def test_valeurs_brutes_inchangees(trace: dict[str, Any], reanalysee: dict[str, Any]) -> None:
    assert reanalysee["changements"] == trace["changements"]  # « 'TEST-S201     ' » et montants intacts
    assert reanalysee["fiche"] == trace["fiche"]
    textes = json.dumps(reanalysee["changements"], ensure_ascii=False)
    assert "TEST-S201     " in textes and "61263    " in textes


def test_reanalyse_idempotente(reanalysee: dict[str, Any]) -> None:
    deuxieme = reanalyser_trace(reanalysee)
    for cle in ("liens", "ecarts_saisie", "champs_calcules"):
        assert deuxieme[cle] == reanalysee[cle], cle


def test_hypotheses_non_recalculables_reprises_avec_avertissement(
    trace: dict[str, Any], reanalysee: dict[str, Any]
) -> None:
    codes = [a for a in reanalysee["avertissements"] if a["code"] == "non_recalculable_hors_ligne"]
    assert codes and all("non recalculable hors ligne" in a["message"] for a in codes)
    hypotheses_reprises = {a["hypothese"] for a in codes}
    assert hypotheses_reprises <= {"compteur", "copie", "constante", "somme_lignes"}
    assert "compteur" in hypotheses_reprises  # ecrit.Compteur / Lien : insertions, entiers
    compteurs = [x for x in reanalysee["champs_calcules"] if x["table"] == "ecrit" and x["colonne"] == "Compteur"]
    assert [x["details"] for x in compteurs] == ["max avant = 26601"] * len(compteurs)
    # les hypothèses recalculables ne sont jamais signalées comme reprises
    assert not hypotheses_reprises & {"cumul_mis_a_jour", "cumul_hierarchique", "horodatage_systeme"}


def test_filtre_de_reprise_copie_et_compteur(trace: dict[str, Any]) -> None:
    """Les hypothèses bruitées de l'original sont écartées à la reprise."""
    bruit = copy.deepcopy(trace)
    bruit["champs_calcules"].append({
        "table": "ecrit", "colonne": "Debit", "valeur": "0.0000", "hypotheses": ["copie"],
        "details": "copie de Tableau20.Brut (ligne code = 10)"})
    bruit["champs_calcules"].append({
        "table": "ecrit", "colonne": "Externe", "valeur": "x", "hypotheses": ["copie"],
        "details": "copie de Table des erreurs.Compte (ligne Code = 10)"})
    nouvelle = reanalyser_trace(bruit)
    assert not [x for x in nouvelle["champs_calcules"] if "copie" in x["hypotheses"]
                and ("Tableau20" in x["details"] or "Table des erreurs" in x["details"])]


def test_motifs_vides_conservent_les_copies_non_triviales(trace: dict[str, Any]) -> None:
    ajout = copy.deepcopy(trace)
    cellule = next(c for c in cellules_de_la_trace(ajout["changements"])
                   if c.table == "ecrit" and c.colonne == "Piece")
    ajout["champs_calcules"] = [x for x in ajout["champs_calcules"] if x["colonne"] != "Piece"] + [{
        "table": "ecrit", "colonne": "Piece", "valeur": cellule.valeur, "hypotheses": ["copie"],
        "details": "copie de Table des erreurs.Compte (ligne Code = 10)"}]
    avec_defaut = reanalyser_trace(ajout)
    sans_filtre = reanalyser_trace(ajout, tables_ignorees_analyse=())
    piece = lambda t: [x for x in t["champs_calcules"] if x["colonne"] == "Piece"][0]  # noqa: E731
    assert "copie" not in piece(avec_defaut)["hypotheses"]
    assert "copie" in piece(sans_filtre)["hypotheses"]


def test_typage_des_valeurs_json() -> None:
    from datetime import date, datetime
    from decimal import Decimal

    assert typer_valeur_json("1481.4700") == Decimal("1481.4700")
    assert typer_valeur_json("-5.0000") == Decimal("-5.0000")
    assert typer_valeur_json("26") == "26"  # code texte
    assert typer_valeur_json("990201") == "990201"
    assert typer_valeur_json("12.5") == "12.5"  # pas 4 décimales : texte
    assert typer_valeur_json(26602) == 26602
    assert typer_valeur_json("2026-10-07T13:42:49") == datetime(2026, 10, 7, 13, 42, 49)
    assert typer_valeur_json("2026-10-07") == date(2026, 10, 7)
    assert typer_valeur_json("2026-13-45") == "2026-13-45"
    assert typer_valeur_json(None) is None


# --- fichiers, erreurs, ligne de commande ------------------------------------------------------------

def test_reanalyser_fichier_ecrit_a_cote_sans_toucher_l_original(tmp_path: Path) -> None:
    source = tmp_path / "trace.json"
    source.write_bytes(ANONYMISEE.read_bytes())
    sortie_json, sortie_html, resume = reanalyser_fichier(source)
    assert (sortie_json.name, sortie_html.name) == (NOM_TRACE_REANALYSEE, NOM_RAPPORT_REANALYSE)
    assert sortie_json.parent == tmp_path and sortie_json.exists() and sortie_html.exists()
    assert source.read_bytes() == ANONYMISEE.read_bytes()
    assert "Écarts de saisie : 2 → 0" in resume and "ecart_saisie → terminee" in resume
    assert "cumul sur le compte et ses comptes parents" in sortie_html.read_text(encoding="utf-8")


def test_reanalyser_fichier_dossier_de_sortie(tmp_path: Path) -> None:
    sortie_json, _, _ = reanalyser_fichier(ANONYMISEE, tmp_path / "sous" / "dossier")
    assert sortie_json == tmp_path / "sous" / "dossier" / NOM_TRACE_REANALYSEE


def test_erreurs_de_lecture(tmp_path: Path) -> None:
    with pytest.raises(ErreurReanalyse, match="introuvable"):
        lire_trace(tmp_path / "absent.json")
    mauvais = tmp_path / "mauvais.json"
    mauvais.write_text("{pas du json", encoding="utf-8")
    with pytest.raises(ErreurReanalyse, match="Impossible de lire"):
        lire_trace(mauvais)
    autre = tmp_path / "autre.json"
    autre.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ErreurReanalyse, match="n'est pas un trace.json"):
        lire_trace(autre)
    futur = _charger(ANONYMISEE)
    futur["format_version"] = "9.9"
    chemin = tmp_path / "futur.json"
    chemin.write_text(json.dumps(futur), encoding="utf-8")
    with pytest.raises(ErreurReanalyse, match="Version de format inconnue"):
        lire_trace(chemin)


def test_trace_sans_valeur_saisie_avertit(trace: dict[str, Any]) -> None:
    sans = copy.deepcopy(trace)
    sans["fiche"]["valeurs_saisies"] = []
    nouvelle = reanalyser_trace(sans)
    assert nouvelle["liens"] == [] and nouvelle["ecarts_saisie"] == []
    assert any("aucune valeur saisie" in a["message"] for a in nouvelle["avertissements"])


def test_trace_annulee_garde_son_statut() -> None:
    annulee = {"format_version": "1.0", "fiche": {"id": "X", "titre": "t", "valeurs_saisies": []},
               "execution": {"debut": "2026-10-07T10:00:00", "fin": "2026-10-07T10:01:00", "statut": "annulee"},
               "changements": [], "bruit": [], "liens": [], "champs_calcules": [], "ecarts_saisie": [],
               "schema_modifie": [], "avertissements": []}
    assert reanalyser_trace(annulee)["execution"]["statut"] == "annulee"


def test_ligne_de_commande_sans_base_ni_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--reanalyser` n'ouvre ni configuration, ni pyodbc, ni fenêtre principale."""
    import traceur.sources.access as access

    def interdit(*_a: object, **_k: object) -> None:
        raise AssertionError("accès à la base ou à pyodbc interdit en réanalyse")

    monkeypatch.setattr(access, "importer_pyodbc", interdit)
    monkeypatch.setattr(principal, "fabrique_access", interdit)
    monkeypatch.setattr(principal, "verifier_demarrage", interdit)
    monkeypatch.setattr(principal, "_message_info", lambda message: print(message))
    code = principal.lancer(["--reanalyser", str(ANONYMISEE), "--sortie", str(tmp_path)])
    assert code == 0
    assert (tmp_path / NOM_TRACE_REANALYSEE).exists()
    assert "Écarts de saisie : 2 → 0" in capsys.readouterr().out


def test_ligne_de_commande_erreur(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(principal, "_erreur_fatale", messages.append)
    assert principal.lancer(["--reanalyser", str(tmp_path / "absent.json")]) == 1
    assert messages and "introuvable" in messages[0]


def test_ligne_de_commande_motifs_de_la_configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "base_test": "C:\\\\t.mdb", "instantane_reference": "C:\\\\r.mdb", "chemins_interdits": ["C:\\\\p.mdb"],
        "dossier_sorties": "C:\\\\s", "tables_ignorees_analyse": ["Autre"]}), encoding="utf-8")
    vus: list[Any] = []
    import traceur.reanalyse as module

    original = module.reanalyser_fichier
    monkeypatch.setattr(module, "reanalyser_fichier",
                        lambda chemin, sortie, motifs: (vus.append(motifs), original(chemin, sortie, motifs))[1])
    monkeypatch.setattr(principal, "_message_info", lambda message: None)
    assert principal.lancer(["--reanalyser", str(ANONYMISEE), "--sortie", str(tmp_path), "--config", str(config)]) == 0
    assert vus == [("Autre",)]


# --- configuration : tables_ignorees_analyse (AMB-041.2) ----------------------------------------------

BASE_CONFIG = {"base_test": "C:\\t.mdb", "instantane_reference": "C:\\r.mdb",
               "chemins_interdits": ["C:\\p.mdb"], "dossier_sorties": "C:\\s"}


def test_config_defaut_dans_le_code() -> None:
    assert configuration_depuis_dict(dict(BASE_CONFIG)).tables_ignorees_analyse == TABLES_IGNOREES_ANALYSE_DEFAUT
    assert TABLES_IGNOREES_ANALYSE_DEFAUT == ("Table des erreurs", "Erreurs de conversion*")


def test_config_cle_facultative_remplace_le_defaut() -> None:
    assert configuration_depuis_dict({**BASE_CONFIG, "tables_ignorees_analyse": ["A*", "B"]}) \
        .tables_ignorees_analyse == ("A*", "B")
    assert configuration_depuis_dict({**BASE_CONFIG, "tables_ignorees_analyse": []}).tables_ignorees_analyse == ()


def test_config_cle_invalide() -> None:
    from traceur.config import ErreurConfiguration

    with pytest.raises(ErreurConfiguration, match="tables_ignorees_analyse"):
        configuration_depuis_dict({**BASE_CONFIG, "tables_ignorees_analyse": "Table des erreurs"})


def test_aucun_pyodbc_charge_par_la_reanalyse() -> None:
    import subprocess

    code = ("import sys, traceur.reanalyse; "
            "sys.exit(1 if 'pyodbc' in sys.modules else 0)")
    racine = Path(__file__).parent.parent
    assert subprocess.run([sys.executable, "-c", code], cwd=racine, env={"PYTHONPATH": str(racine)}).returncode == 0
