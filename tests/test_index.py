import json
from datetime import datetime
from pathlib import Path

from traceur.rapports.index import ecrire_index, lire_entrees


def _trace(dossier: Path, nom: str, fiche: str, titre: str, debut: str, statut: str, changements: list | None = None) -> None:
    (dossier / nom).mkdir(parents=True)
    (dossier / nom / "trace.json").write_text(json.dumps({
        "fiche": {"id": fiche, "titre": titre}, "execution": {"debut": debut, "statut": statut},
        "changements": changements or []}, ensure_ascii=False), encoding="utf-8")


def test_index_liste_les_traces_les_plus_recentes_d_abord(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    _trace(traces, "S-001_20261005-090000", "S-001", "Créer un compte", "2026-10-05T09:00:00", "terminee",
           [{"table": "COMPTES", "inserts": [{}]}])
    _trace(traces, "S-003_20261005-101522", "S-003", "Facture <achat>", "2026-10-05T10:15:22", "ecart_saisie")
    _trace(traces, "S-002_20261004-160000", "S-002", "Annulée", "2026-10-04T16:00:00", "annulee")
    chemin = ecrire_index(tmp_path, datetime(2026, 10, 5, 12, 30))
    html = chemin.read_text(encoding="utf-8")
    assert chemin == tmp_path / "index.html"
    ordre = [html.index(x) for x in ("S-003", "S-001", "S-002")]
    assert ordre == sorted(ordre)
    for attendu in ("3 trace(s) · mis à jour le 05/10/2026 à 12:30", "05/10/2026 10:15", "Écart de saisie", "Terminée", "Annulée",
                    'href="traces/S-003_20261005-101522/rapport.html"', "1 table modifiée, 1 ligne ajoutée",
                    "Facture &lt;achat&gt;"):
        assert attendu in html, attendu
    assert "<script" not in html and "http:" not in html and "Facture <achat>" not in html


def test_index_vide_et_lien_encode(tmp_path: Path) -> None:
    assert "Aucune trace déposée pour le moment." in ecrire_index(tmp_path).read_text(encoding="utf-8")
    _trace(tmp_path / "traces", "S 004 é_20261005-100000", "S 004", "t", "2026-10-05T10:00:00", "terminee")
    assert 'href="traces/S%20004%20%C3%A9_20261005-100000/rapport.html"' in ecrire_index(tmp_path).read_text(encoding="utf-8")


def test_trace_illisible_signalee_et_dossiers_caches_ignores(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    _trace(traces, "S-001_20261005-090000", "S-001", "ok", "2026-10-05T09:00:00", "terminee")
    (traces / "S-002_cassee").mkdir()
    (traces / "S-002_cassee" / "trace.json").write_text("{pas du json", encoding="utf-8")
    (traces / ".S-003.depot-tmp").mkdir()  # copie en cours : ignorée
    entrees, illisibles = lire_entrees(traces)
    assert [e.fiche_id for e in entrees] == ["S-001"] and illisibles == ["S-002_cassee"]
    html = ecrire_index(tmp_path).read_text(encoding="utf-8")
    assert "Traces illisibles" in html and "S-002_cassee" in html and ".S-003" not in html


def test_ecriture_atomique_sans_fichier_temporaire_restant(tmp_path: Path) -> None:
    ecrire_index(tmp_path)
    ecrire_index(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["index.html"]
