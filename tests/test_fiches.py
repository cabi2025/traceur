import json
from pathlib import Path
from typing import Any

import pytest

from traceur.fiches import A_FAIRE, ANNULEE, ECART, FAITE, ErreurFiches, charger_fiches, statuts_fiches

EXEMPLE = Path(__file__).parent.parent / "docs" / "formats" / "fiches.example.json"


def _ecrire(tmp_path: Path, contenu: Any) -> Path:
    chemin = tmp_path / "fiches.json"
    chemin.write_text(contenu if isinstance(contenu, str) else json.dumps(contenu), encoding="utf-8")
    return chemin


def test_chargement_de_l_exemple_de_reference() -> None:
    (f,) = charger_fiches(EXEMPLE)
    assert (f.id, f.titre, f.lot, f.duree_min, f.reinitialiser_avant) == ("S-003", "Saisie facture achat avec TVA", 2, 3, False)
    assert f.prerequis == ("Logiciel ouvert sur la base TEST", "Traceur ouvert") and len(f.etapes) == 6
    assert (f.etapes[0].n, f.etapes[0].capture_ref, f.etapes[1].capture_ref) == (1, "001", None)
    assert [(v.champ_ecran, v.valeur, v.type) for v in f.valeurs_saisies][:2] == [("Journal", "ACH", "code"), ("Date", "2025-01-15", "date")]
    assert len(f.valeurs_saisies) == 7 and f.a_noter == ("Numéro de pièce attribué", "Message affiché après Valider")


def test_valeurs_par_defaut_et_lot_du_fichier(tmp_path: Path) -> None:
    (f,) = charger_fiches(_ecrire(tmp_path, {"lot": 5, "fiches": [{"id": "S-1", "titre": "t"}]}))
    assert (f.lot, f.duree_min, f.prerequis, f.etapes, f.valeurs_saisies, f.a_noter, f.reinitialiser_avant) == (
        5, None, (), (), (), (), False)
    (g,) = charger_fiches(_ecrire(tmp_path, {"lot": 5, "fiches": [{"id": "S-1", "titre": "t", "lot": 2}]}))
    assert g.lot == 2


def test_bom_utf8_et_accents(tmp_path: Path) -> None:
    chemin = tmp_path / "f.json"
    chemin.write_bytes(b"\xef\xbb\xbf" + json.dumps({"fiches": [{"id": "S-1", "titre": "Écriture été"}]}, ensure_ascii=False).encode("utf-8"))
    assert charger_fiches(chemin)[0].titre == "Écriture été"


@pytest.mark.parametrize(("contenu", "message"), [
    ("{pas du json", "pas un JSON valide"),
    ({"fiches": []}, "liste « fiches » non vide"),
    ({}, "liste « fiches » non vide"),
    ([], "liste « fiches » non vide"),
    ({"fiches": [{"titre": "t"}]}, "L'identifiant de la fiche n° 1"),
    ({"fiches": [{"id": "S-1"}]}, "Fiche S-1 : le titre"),
    ({"fiches": [{"id": "S-1", "titre": "t", "duree_min": "3"}]}, "Fiche S-1 : la durée doit être un nombre entier"),
    ({"fiches": [{"id": "S-1", "titre": "t", "prerequis": "a"}]}, "« prerequis » doit être une liste de textes"),
    ({"fiches": [{"id": "S-1", "titre": "t", "reinitialiser_avant": "oui"}]}, "« reinitialiser_avant » doit valoir true ou false"),
    ({"fiches": [{"id": "S-1", "titre": "t", "etapes": [{"n": 1}]}]}, "Fiche S-1 : le texte de l'étape n° 1"),
    ({"fiches": [{"id": "S-1", "titre": "t", "valeurs_saisies": [{"champ_ecran": "x", "type": "nombre"}]}]},
     "type parmi : montant, date, texte, code"),
    ({"fiches": [{"id": "S-1", "titre": "a"}, {"id": "S-1", "titre": "b"}]}, "Identifiants de fiche en double : S-1"),
    ({"fiches": ["S-1"]}, "La fiche n° 1 doit être un objet JSON"),
])
def test_erreurs_en_francais_qui_nomment_la_fiche(tmp_path: Path, contenu: Any, message: str) -> None:
    with pytest.raises(ErreurFiches, match=message):
        charger_fiches(_ecrire(tmp_path, contenu))


def test_fichier_absent(tmp_path: Path) -> None:
    with pytest.raises(ErreurFiches, match="introuvable"):
        charger_fiches(tmp_path / "absent.json")


# --- statut dérivé de la dernière trace ------------------------------------------------------

def _trace(dossier: Path, nom: str, fiche: str, debut: str, statut: str) -> None:
    (dossier / nom).mkdir(parents=True)
    (dossier / nom / "trace.json").write_text(json.dumps(
        {"fiche": {"id": fiche}, "execution": {"debut": debut, "statut": statut}}), encoding="utf-8")


def test_statut_de_la_derniere_trace(tmp_path: Path) -> None:
    fiches = charger_fiches(_ecrire(tmp_path, {"fiches": [{"id": f"S-{i}", "titre": "t"} for i in range(1, 6)]}))
    partage, local = tmp_path / "partage" / "traces", tmp_path / "locales"
    _trace(partage, "S-1_a", "S-1", "2026-10-05T09:00:00", "ecart_saisie")
    _trace(partage, "S-1_b", "S-1", "2026-10-05T10:00:00", "terminee")  # plus récente : fait foi
    _trace(partage, "S-2_a", "S-2", "2026-10-05T09:00:00", "terminee")
    _trace(local, "S-2_b", "S-2", "2026-10-05T11:00:00", "annulee")  # trace locale en attente, plus récente
    _trace(partage, "S-3_a", "S-3", "2026-10-05T09:00:00", "ecart_saisie")
    assert statuts_fiches(fiches, [partage, local]) == {
        "S-1": FAITE, "S-2": ANNULEE, "S-3": ECART, "S-4": A_FAIRE, "S-5": A_FAIRE}


def test_statuts_dossiers_absents_et_traces_illisibles(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    fiches = charger_fiches(_ecrire(tmp_path, {"fiches": [{"id": "S-1", "titre": "t"}]}))
    (tmp_path / "t" / "S-1_x").mkdir(parents=True)
    (tmp_path / "t" / "S-1_x" / "trace.json").write_text("{cassé", encoding="utf-8")
    (tmp_path / "t" / ".S-1.depot-tmp").mkdir()  # copie en cours : ignorée
    assert statuts_fiches(fiches, [tmp_path / "t", tmp_path / "absent"]) == {"S-1": A_FAIRE}
    assert "Trace illisible ignorée" in caplog.text and "inaccessible" not in caplog.text


def test_fiche_de_validation_s000() -> None:
    """La fiche S-000 du guide (AMB-027) se charge et propose la réinitialisation avant."""
    (f,) = charger_fiches(Path(__file__).parent.parent / "docs" / "formats" / "fiche_S000.json")
    assert (f.id, f.lot, f.reinitialiser_avant, len(f.etapes)) == ("S-000", 0, True, 3)
    assert [(v.champ_ecran, v.valeur) for v in f.valeurs_saisies] == [("Nom", "TEST-S000")]
