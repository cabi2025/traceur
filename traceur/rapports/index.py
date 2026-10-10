"""`index.html` : liste des traces déposées, avec statut et lien vers chaque rapport (SPEC §8)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote

from .trace import resume_trace

journal = logging.getLogger("traceur.index")

STATUTS = {"terminee": ("Terminée", "ok"), "annulee": ("Annulée", "ko"), "ecart_saisie": ("Écart de saisie", "alerte")}
_CSS = """
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f6f8;color:#1b1b1b}
main{max-width:1000px;margin:0 auto;padding:20px}h1{margin:0 0 4px}
table{border-collapse:collapse;width:100%;background:#fff}
th,td{border:1px solid #c5ccd3;padding:6px 10px;text-align:left}th{background:#e3ebf3}
td:nth-child(1),td:nth-child(2),td:nth-child(6){white-space:nowrap}
.ok{color:#2e7d32;font-weight:600}.alerte{color:#b36b00;font-weight:600}.ko{color:#c62828;font-weight:600}
.note{color:#555;font-size:14px}a{color:#1f4e79}
"""


@dataclass(frozen=True)
class EntreeIndex:
    dossier: str
    fiche_id: str
    titre: str
    debut: str
    statut: str
    resume: str


def lire_entrees(dossier_traces: Path) -> tuple[list[EntreeIndex], list[str]]:
    """Entrées lisibles (plus récentes d'abord) et noms des dossiers dont `trace.json` est illisible."""
    entrees: list[EntreeIndex] = []
    illisibles: list[str] = []
    if not dossier_traces.is_dir():
        return entrees, illisibles
    for dossier in sorted(dossier_traces.iterdir()):
        if not dossier.is_dir() or dossier.name.startswith("."):
            continue
        try:
            trace = json.loads((dossier / "trace.json").read_text(encoding="utf-8"))
            entrees.append(EntreeIndex(dossier.name, trace["fiche"]["id"], trace["fiche"]["titre"],
                                       trace["execution"]["debut"], trace["execution"]["statut"], resume_trace(trace)))
        except (OSError, ValueError, KeyError) as erreur:
            journal.warning("Trace illisible dans l'index (%s) : %s", dossier.name, erreur)
            illisibles.append(dossier.name)
    entrees.sort(key=lambda e: e.debut, reverse=True)
    return entrees, illisibles


def generer_index_html(entrees: list[EntreeIndex], illisibles: list[str], maintenant: datetime) -> str:
    lignes = []
    for e in entrees:
        libelle, classe = STATUTS.get(e.statut, (e.statut, ""))
        try:
            date = datetime.fromisoformat(e.debut).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            date = e.debut
        lien = f"traces/{quote(e.dossier)}/rapport.html"
        lignes.append(
            f"<tr><td>{escape(date)}</td><td>{escape(e.fiche_id)}</td><td>{escape(e.titre)}</td>"
            f'<td class="{classe}">{escape(libelle)}</td><td>{escape(e.resume)}</td>'
            f'<td><a href="{lien}">Ouvrir le rapport</a></td></tr>')
    corps = ('<table><tr><th>Date</th><th>Fiche</th><th>Titre</th><th>Statut</th><th>Résumé</th><th>Rapport</th></tr>'
             + "".join(lignes) + "</table>") if lignes else '<p class="note">Aucune trace déposée pour le moment.</p>'
    avert = "".join(f"<li>{escape(n)}</li>" for n in illisibles)
    bloc = f'<h2>Traces illisibles</h2><ul>{avert}</ul>' if avert else ""
    return "\n".join([
        '<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Traces du traceur</title>',
        f"<style>{_CSS}</style></head><body><main><h1>Traces</h1>",
        f'<p class="note">{len(entrees)} trace(s) · mis à jour le {maintenant:%d/%m/%Y à %H:%M}</p>',
        corps, bloc, "</main></body></html>"])


def ecrire_index(dossier_sorties: Path, maintenant: datetime | None = None) -> Path:
    """Reconstruit `index.html` à la racine de `dossier_sorties` (écriture puis remplacement atomique)."""
    entrees, illisibles = lire_entrees(dossier_sorties / "traces")
    html = generer_index_html(entrees, illisibles, maintenant or datetime.now())
    cible = dossier_sorties / "index.html"
    temporaire = dossier_sorties / ".index.html.tmp"
    temporaire.write_text(html, encoding="utf-8")
    os.replace(temporaire, cible)
    return cible
