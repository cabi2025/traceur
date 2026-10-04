"""`profil.json` et `profil.html` (F2, SPEC §6.4). Le HTML est autonome : CSS et SVG en ligne."""

from __future__ import annotations

import json
import math
from decimal import Decimal
from html import escape
from pathlib import Path
from typing import Any

from traceur.moteur.diff import SEUIL_PETITE_TABLE
from traceur.moteur.profilage import Profil

_CSS = """
body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#1b1b1b;background:#fff}
h1{margin:0 0 4px}h2{margin-top:32px;border-bottom:2px solid #1f4e79;padding-bottom:4px}
.meta{color:#444;margin-bottom:16px}.meta b{color:#000}
table{border-collapse:collapse;margin:8px 0 4px;font-size:14px}
th,td{border:1px solid #bbb;padding:3px 8px;text-align:left}th{background:#e8eef5}
td.n{text-align:right;font-variant-numeric:tabular-nums}
.cles{font-size:14px;margin:2px 0 14px}.vide{color:#777;font-style:italic}
.bandeau{border-left:6px solid;padding:8px 12px;margin:6px 0 14px;font-size:14px}.alerte{background:#fff4e0;border-color:#e08a00}
svg{max-width:100%;height:auto;border:1px solid #ccc;background:#fafafa}
svg text{font-family:Segoe UI,Arial,sans-serif}
"""


def _fr(nombre: str) -> str:
    return nombre.replace(".", ",")


def _pct(taux: str) -> str:
    """« 0.9950 » → « 99,50 % » (affichage uniquement)."""
    return _fr(format((Decimal(taux) * 100).quantize(Decimal("0.01")), "f")) + " %"


def _texte(valeur: Any) -> str:
    return "" if valeur is None else escape(str(valeur))


def _svg_relations(relations: list[dict[str, Any]]) -> str:
    noeuds = sorted({r["table_source"] for r in relations} | {r["table_cible"] for r in relations})
    if not noeuds:
        return '<p class="vide">Aucune relation candidate détectée.</p>'
    rayon = max(120.0, 45.0 * len(noeuds))
    largeur = hauteur = int(2 * rayon + 260)
    cx = cy = largeur / 2
    pos: dict[str, tuple[float, float]] = {}
    for i, nom in enumerate(noeuds):
        angle = 2 * math.pi * i / len(noeuds) - math.pi / 2
        pos[nom] = (cx + rayon * math.cos(angle), cy + rayon * math.sin(angle))
    morceaux = [
        f'<svg viewBox="0 0 {largeur} {hauteur}" width="{largeur}" role="img" '
        'aria-label="Graphe des relations candidates">',
        '<defs><marker id="fl" markerWidth="10" markerHeight="8" refX="9" refY="4" '
        'orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#1f4e79"/></marker></defs>',
    ]
    for r in relations:
        x1, y1 = pos[r["table_source"]]
        x2, y2 = pos[r["table_cible"]]
        etiquette = escape(
            f"{r['colonne_source']} → {r['colonne_cible']} ({_pct(r['taux_inclusion'])})"
        )
        if (x1, y1) == (x2, y2):
            morceaux.append(
                f'<path d="M{x1 - 12:.0f},{y1 - 14:.0f} C{x1 - 50:.0f},{y1 - 70:.0f} '
                f'{x1 + 50:.0f},{y1 - 70:.0f} {x1 + 12:.0f},{y1 - 14:.0f}" fill="none" '
                'stroke="#1f4e79" marker-end="url(#fl)"/>'
            )
            mx, my = x1, y1 - 62
        else:
            dx, dy = x2 - x1, y2 - y1
            longueur = math.hypot(dx, dy)
            # Raccourcit la flèche pour qu'elle s'arrête au bord du cadre de la table cible.
            fin_x, fin_y = x2 - dx / longueur * 28, y2 - dy / longueur * 28
            morceaux.append(
                f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{fin_x:.0f}" y2="{fin_y:.0f}" '
                'stroke="#1f4e79" marker-end="url(#fl)"/>'
            )
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        morceaux.append(
            f'<text x="{mx:.0f}" y="{my:.0f}" font-size="11" text-anchor="middle" '
            f'fill="#7a2e00" stroke="#fafafa" stroke-width="3" paint-order="stroke">{etiquette}</text>'
        )
    for nom in noeuds:
        x, y = pos[nom]
        w = len(nom) * 8 + 24
        morceaux.append(
            f'<rect x="{x - w / 2:.0f}" y="{y - 14:.0f}" width="{w}" height="28" rx="4" '
            'fill="#e8eef5" stroke="#1f4e79"/>'
            f'<text x="{x:.0f}" y="{y + 5:.0f}" font-size="13" font-weight="bold" '
            f'text-anchor="middle">{escape(nom)}</text>'
        )
    morceaux.append("</svg>")
    return "\n".join(morceaux)


def generer_html(profil: dict[str, Any]) -> str:
    """Page autonome (aucune ressource externe) à partir de `Profil.vers_dict()`."""
    tables = profil["tables"]
    total = sum(t["nb_lignes"] for t in tables)
    jet = profil["version_jet"] or "non détectée"
    visibles = [r for r in profil["relations_candidates"] if r["confiance"] != "faible"]
    nb_faibles = len(profil["relations_candidates"]) - len(visibles)
    p = [
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">',
        "<title>Profil de la base</title>",
        f"<style>{_CSS}</style></head><body>",
        "<h1>Profil de la base</h1>",
        f'<div class="meta">Généré le <b>{escape(profil["date"])}</b> · Version Jet : '
        f"<b>{escape(jet)}</b> · <b>{len(tables)}</b> tables · <b>{total}</b> lignes</div>",
        "<h2>Relations candidates</h2>",
        "<p>Une relation est candidate quand au moins 99 % des valeurs non nulles d'une colonne "
        "se retrouvent dans une colonne clé candidate de même type. C'est une hypothèse, "
        "pas une règle.</p>",
        _svg_relations(visibles),
    ]
    if nb_faibles:
        p.append(
            f"<p>{nb_faibles} relation(s) à confiance faible (colonne source booléenne ou à "
            "moins de 3 valeurs distinctes) ne sont pas dessinées ; elles figurent dans le "
            "tableau ci-dessous.</p>"
        )
    if profil["relations_candidates"]:
        p.append("<table><tr><th>Colonne source</th><th>Colonne cible</th><th>Confiance</th>"
                 "<th>Inclusion (lignes)</th><th>Lignes</th>"
                 "<th>Inclusion (valeurs distinctes)</th><th>Valeurs distinctes</th></tr>")
        for r in profil["relations_candidates"]:
            p.append(
                f"<tr><td>{escape(r['table_source'])}.{escape(r['colonne_source'])}</td>"
                f"<td>{escape(r['table_cible'])}.{escape(r['colonne_cible'])}</td>"
                f"<td>{escape(r['confiance'])}</td>"
                f'<td class="n">{_pct(r["taux_inclusion"])}</td>'
                f'<td class="n">{r["nb_incluses"]} / {r["nb_valeurs"]}</td>'
                f'<td class="n">{_pct(r["taux_inclusion_distincts"])}</td>'
                f'<td class="n">{r["nb_distincts_inclus"]} / {r["nb_distincts_source"]}</td></tr>'
            )
        p.append("</table>")
    p.append("<h2>Dictionnaire des tables</h2>")
    for t in tables:
        p.append(f'<h3 id="t-{escape(t["nom"])}">{escape(t["nom"])} '
                 f'<small>({t["nb_lignes"]} lignes)</small></h3>')
        pk = ", ".join(t["cle_primaire"]) or "aucune déclarée"
        candidates = " ; ".join("(" + ", ".join(c) + ")" for c in t["cles_candidates"]) or "aucune"
        p.append(f'<div class="cles">Clé primaire : <b>{escape(pk)}</b> · '
                 f"Clés candidates : <b>{escape(candidates)}</b></div>")
        if not t["cle_primaire"] and t["cles_candidates"] and t["nb_lignes"] < SEUIL_PETITE_TABLE:
            p.append(f'<div class="bandeau alerte">Attention : cette table a moins de {SEUIL_PETITE_TABLE} lignes. '
                     "Une clé candidate peut y être unique par hasard (par exemple un compteur dont les valeurs "
                     "sont toutes différentes à cet instant) : elle est peu fiable. Profilez de préférence juste "
                     "après une réinitialisation de la base.</div>")
        p.append("<table><tr><th>Colonne</th><th>Type déclaré</th><th>Types observés</th>"
                 "<th>% nuls</th><th>Distincts</th><th>Min</th><th>Max</th></tr>")
        for c in t["colonnes"]:
            p.append(
                f"<tr><td>{escape(c['nom'])}</td><td>{escape(c['type_declare'])}</td>"
                f"<td>{escape(', '.join(c['types_observes']))}</td>"
                f'<td class="n">{_fr(c["pct_nuls"])}</td><td class="n">{c["nb_distincts"]}</td>'
                f"<td>{_texte(c['min'])}</td><td>{_texte(c['max'])}</td></tr>"
            )
        p.append("</table>")
    p.append("</body></html>")
    return "\n".join(p)


def ecrire_profil(profil: Profil, dossier: Path) -> tuple[Path, Path]:
    """Écrit `profil.json` et `profil.html` (UTF-8) dans `dossier`."""
    dossier.mkdir(parents=True, exist_ok=True)
    donnees = profil.vers_dict()
    chemin_json = dossier / "profil.json"
    chemin_html = dossier / "profil.html"
    chemin_json.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    chemin_html.write_text(generer_html(donnees), encoding="utf-8")
    return chemin_json, chemin_html
