import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from conftest import DEBUT, FIN
from traceur.moteur.diff import Avertissement
from traceur.rapports.trace import (
    Execution,
    FicheTrace,
    compter_changements,
    construire_trace,
    nom_dossier_trace,
    resume_trace,
    statut_execution,
)

EXEMPLE = json.loads((Path(__file__).parent.parent / "docs" / "formats" / "trace.example.json").read_text(encoding="utf-8"))


def _contient_flottant(x: Any) -> bool:
    if isinstance(x, float):
        return True
    if isinstance(x, dict):
        return any(_contient_flottant(v) for v in x.values())
    return isinstance(x, list) and any(_contient_flottant(v) for v in x)


def test_forme_conforme_a_l_exemple_de_reference(trace_facture: dict[str, Any]) -> None:
    t = trace_facture
    assert list(t) == list(EXEMPLE) and t["format_version"] == "1.0"
    assert set(t["fiche"]) == set(EXEMPLE["fiche"])
    assert set(t["execution"]) == set(EXEMPLE["execution"])
    assert set(t["base"]) == set(EXEMPLE["base"])
    for cle in ("liens", "champs_calcules"):
        assert set(t[cle][0]) == set(EXEMPLE[cle][0]), cle
    assert set(t["bruit"][0]) == set(EXEMPLE["bruit"][0])
    attendu = {c["table"]: set(c) for c in EXEMPLE["changements"]}
    assert {c["table"]: set(c) for c in t["changements"] if c["table"] in attendu} == attendu
    assert set(t["fiche"]["valeurs_saisies"][0]) == set(EXEMPLE["fiche"]["valeurs_saisies"][0])


def test_contenu_de_la_trace(trace_facture: dict[str, Any]) -> None:
    t = trace_facture
    assert t["execution"] == {"debut": "2026-10-05T10:15:22", "fin": "2026-10-05T10:18:04", "poste": "PC-COMPTA",
                              "utilisateur_windows": "comptable", "statut": "terminee",
                              "remarques": "Message : Écriture enregistrée sous le n° 2025-ACH-0042"}
    assert t["base"] == {"chemin": "\\\\SERVEUR\\Compta_TEST\\compta_test.mdb", "empreinte_fichier_avant": "sha256:abc"}
    assert {c["table"] for c in t["changements"]} == {"ECRITURES", "LIGNES", "COMPTEURS"}
    assert [b["table"] for b in t["bruit"]] == ["SESSIONS"]
    assert t["ecarts_saisie"] == [] and t["schema_modifie"] == []
    assert any(c["colonne"] == "PIECE" and c["details"] == "max avant = 0041" for c in t["champs_calcules"])
    assert all(isinstance(v, (str, int, type(None), list, dict)) for v in t.values())
    assert not _contient_flottant(t)
    assert json.loads(json.dumps(t, ensure_ascii=False)) == t


def test_ecart_de_saisie_donne_le_statut_ecart_saisie(trace_avec_ecart: dict[str, Any]) -> None:
    t = trace_avec_ecart
    assert t["execution"]["statut"] == "ecart_saisie"
    assert [(e["type_ecart"], e["valeur_attendue"]) for e in t["ecarts_saisie"]] == [("introuvable", "1234.56")]


def test_fiche_annulee_conservee_sans_comparaison(trace_facture: dict[str, Any]) -> None:
    fiche = FicheTrace("S-003", "Saisie", ())
    t = construire_trace(fiche, Execution(DEBUT, FIN, "PC", "u", "abandon", annulee=True), "base.mdb", None, None)
    assert t["execution"]["statut"] == "annulee" and t["execution"]["remarques"] == "abandon"
    assert t["changements"] == t["liens"] == t["champs_calcules"] == t["bruit"] == []
    assert resume_trace(t) == "Fiche annulée : aucune comparaison n'a été faite."


def test_annulee_l_emporte_sur_ecart(trace_avec_ecart: dict[str, Any], base: Any, jouer: Any) -> None:
    from traceur.moteur.interpretation import ResultatInterpretation
    from traceur.moteur.liens import EcartSaisie

    interp = ResultatInterpretation(ecarts_saisie=[EcartSaisie("Débit", "001", "1", "introuvable")])
    assert statut_execution(Execution(DEBUT, FIN, annulee=True), interp) == "annulee"
    assert statut_execution(Execution(DEBUT, FIN), interp) == "ecart_saisie"
    assert statut_execution(Execution(DEBUT, FIN), None) == "terminee"


def test_avertissements_regroupes() -> None:
    from traceur.moteur.diff import ResultatDiff
    from traceur.moteur.interpretation import ResultatInterpretation

    diff = ResultatDiff(avertissements=[Avertissement("A", "x", "du diff")])
    interp = ResultatInterpretation(avertissements=[Avertissement(None, "profil_absent", "de l'interprétation")])
    t = construire_trace(FicheTrace("S", "t"), Execution(DEBUT, FIN, "p", "u"), "b.mdb", diff, interp,
                         avertissements=[Avertissement(None, "capture", "pas de capture")])
    assert [a["message"] for a in t["avertissements"]] == ["du diff", "de l'interprétation", "pas de capture"]


def test_poste_et_utilisateur_par_defaut() -> None:
    t = construire_trace(FicheTrace("S", "t"), Execution(DEBUT, FIN), "b.mdb", None, None)
    assert t["execution"]["poste"] and isinstance(t["execution"]["utilisateur_windows"], str)


def test_nom_du_dossier_de_trace() -> None:
    assert nom_dossier_trace("S-003", datetime(2026, 10, 5, 10, 15, 22)) == "S-003_20261005-101522"
    assert nom_dossier_trace("S 003/é:*", datetime(2026, 10, 5, 10, 15, 22)) == "S_003_20261005-101522"
    assert nom_dossier_trace("///", datetime(2026, 10, 5, 10, 15, 22)) == "fiche_20261005-101522"


def test_resume_et_totaux(trace_facture: dict[str, Any]) -> None:
    assert compter_changements(trace_facture) == {"tables": 3, "ajoutees": 2, "modifiees": 1, "supprimees": 0}
    assert resume_trace(trace_facture) == "3 tables modifiées, 2 lignes ajoutées, 1 modifiée"
    vide = {"execution": {"statut": "terminee"}, "changements": []}
    assert resume_trace(vide) == "Aucune modification détectée dans la base."
    un = {"execution": {"statut": "terminee"}, "changements": [{"table": "T", "deletes": [{}], "inserts": [{}]}]}
    assert resume_trace(un) == "1 table modifiée, 1 ligne ajoutée, 1 supprimée"
    deux = {"execution": {"statut": "terminee"}, "changements": [{"table": "T", "updates": [{}, {}], "deletes": [{}, {}]}]}
    assert resume_trace(deux) == "1 table modifiée, 2 modifiées, 2 supprimées"
