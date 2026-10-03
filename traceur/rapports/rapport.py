"""`rapport.html` : rapport d'une trace, lisible par un non-technicien, en français (SPEC §8).

Page autonome : CSS en ligne, aucun script, aucune ressource réseau. Les valeurs sont affichées
telles que dans `trace.json` (AMB-031) ; seuls les en-têtes de date sont en format français.
Les captures sont des fichiers voisins (`capture_debut.png`, `capture_fin.png`).
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any, Mapping, Sequence

from .trace import compter_changements, resume_trace

STATUTS = {
    "terminee": ("Terminée", "ok", "La fiche s'est déroulée jusqu'au bout."),
    "annulee": ("Annulée", "ko", "La fiche a été annulée avant la fin : la trace est conservée, sans comparaison."),
    "ecart_saisie": ("Écart de saisie", "alerte",
                     "Une valeur de la fiche n'a pas été retrouvée telle quelle dans la base. "
                     "Réinitialisez la base de TEST puis rejouez la fiche."),
}
CORRESPONDANCES = {
    "exacte": "valeur identique", "signe_inverse": "signe inversé", "x100": "multipliée par 100",
    "div100": "divisée par 100", "date_heure": "date avec une heure", "tronque": "texte tronqué",
    "majuscules": "texte en majuscules",
}
HYPOTHESES = {
    "compteur": "compteur (numéro qui augmente)", "horodatage_systeme": "date ou heure du système",
    "somme_lignes": "somme de lignes liées", "copie": "copie d'une valeur d'une autre table",
    "constante": "valeur constante", "cumul_mis_a_jour": "cumul mis à jour", "inconnu": "origine inconnue",
}
SEUIL_REPLIAGE = 30  # au-delà de ce nombre de lignes, le détail d'une table est replié

_CSS = """
body{font-family:Segoe UI,Arial,sans-serif;margin:0;color:#1b1b1b;background:#f4f6f8;line-height:1.45}
main{max-width:1000px;margin:0 auto;padding:20px}
h1{margin:0 0 4px;font-size:26px}h2{margin:30px 0 8px;border-bottom:2px solid #1f4e79;padding-bottom:4px;font-size:20px}
h3{margin:16px 0 6px;font-size:16px}
.meta{color:#444}.meta b{color:#000}
.bandeau{border-radius:6px;padding:12px 16px;margin:14px 0;font-size:18px;border-left:8px solid}
.ok{background:#e6f4ea;border-color:#2e7d32}.alerte{background:#fff4e0;border-color:#e08a00}.ko{background:#fdeaea;border-color:#c62828}
.resume{font-size:20px;margin:12px 0;font-weight:600}
table{border-collapse:collapse;margin:6px 0 12px;font-size:14px;background:#fff}
th,td{border:1px solid #c5ccd3;padding:4px 9px;text-align:left;vertical-align:top}th{background:#e3ebf3}
td.nul{color:#888;font-style:italic}.avant{background:#fdeaea}.apres{background:#e6f4ea}
details{background:#fff;border:1px solid #c5ccd3;border-radius:6px;margin:10px 0;padding:6px 12px}
summary{cursor:pointer;font-weight:600;font-size:16px}
.vide{color:#777;font-style:italic}.note{color:#555;font-size:14px}
.hyp{background:#fffbe6}
pre{white-space:pre-wrap;background:#fff;border:1px solid #c5ccd3;border-radius:6px;padding:8px 12px}
figure{display:inline-block;margin:6px 12px 6px 0;vertical-align:top}figure img{max-width:480px;border:1px solid #888}
figcaption{font-size:13px;color:#555}
"""


def _t(valeur: Any) -> str:
    return escape(str(valeur))


def _cellule(valeur: Any) -> str:
    if valeur is None:
        return '<td class="nul">(vide)</td>'
    return f"<td>{_t(valeur)}</td>"


def _date_fr(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return iso


def _duree(debut: str, fin: str) -> str:
    try:
        secondes = int((datetime.fromisoformat(fin) - datetime.fromisoformat(debut)).total_seconds())
    except ValueError:
        return ""
    minutes, secondes = divmod(max(secondes, 0), 60)
    return f"{minutes} min {secondes:02d} s"


def _tableau_lignes(lignes: Sequence[Mapping[str, Any]]) -> str:
    colonnes: list[str] = []
    for ligne in lignes:
        colonnes += [c for c in ligne if c not in colonnes]
    tete = "".join(f"<th>{_t(c)}</th>" for c in colonnes)
    corps = "".join("<tr>" + "".join(_cellule(l.get(c)) for c in colonnes) + "</tr>" for l in lignes)
    return f"<table><tr>{tete}</tr>{corps}</table>"


def _cle_texte(cle: Mapping[str, Any]) -> str:
    return ", ".join(f"{c} = {v}" for c, v in cle.items())


def _tableau_champs(champs: Sequence[Mapping[str, Any]]) -> str:
    lignes = "".join(
        f"<tr><td>{_t(c['colonne'])}</td><td class=\"avant\">{_t('(vide)' if c['avant'] is None else c['avant'])}</td>"
        f"<td class=\"apres\">{_t('(vide)' if c['apres'] is None else c['apres'])}</td></tr>"
        for c in champs
    )
    return f"<table><tr><th>Champ</th><th>Avant</th><th>Après</th></tr>{lignes}</table>"


def _section_table(t: Mapping[str, Any]) -> str:
    morceaux: list[str] = []
    nb = 0
    a_cle = t["cle_utilisee"]["type"] != "aucune"
    ajoutees = [i["valeurs"] for i in t.get("inserts", [])] if a_cle else [x["valeurs"] for x in t.get("lignes_ajoutees", [])]
    supprimees = [d["valeurs"] for d in t.get("deletes", [])] if a_cle else [x["valeurs"] for x in t.get("lignes_supprimees", [])]
    if ajoutees:
        nb += len(ajoutees)
        morceaux.append(f"<h3>{len(ajoutees)} ligne(s) ajoutée(s)</h3>{_tableau_lignes(ajoutees)}")
    for u in t.get("updates", []):
        nb += 1
        morceaux.append(f"<h3>Ligne modifiée ({_t(_cle_texte(u['cle']))})</h3>{_tableau_champs(u['champs'])}")
    for u in t.get("updates_probables", []):
        nb += 1
        morceaux.append(
            "<h3>Modification probable <span class=\"note\">(une ligne supprimée et une ligne ajoutée très "
            "semblables : à confirmer)</span></h3>" + _tableau_champs(u["champs"]))
    if supprimees:
        nb += len(supprimees)
        morceaux.append(f"<h3>{len(supprimees)} ligne(s) supprimée(s)</h3>{_tableau_lignes(supprimees)}")
    cle = t["cle_utilisee"]
    libelle_cle = {"primaire": "clé primaire", "candidate": "clé déduite du profil", "aucune": "aucune clé"}[cle["type"]]
    detail = f"{libelle_cle}{' : ' + ', '.join(cle['colonnes']) if cle['colonnes'] else ''}"
    ouvert = " open" if nb <= SEUIL_REPLIAGE else ""
    return (f"<details{ouvert}><summary>Table {_t(t['table'])} — {nb} changement(s) "
            f"<span class=\"note\">({_t(detail)})</span></summary>{''.join(morceaux)}</details>")


def _section_liens(trace: Mapping[str, Any]) -> str:
    if not trace["fiche"]["valeurs_saisies"]:
        return '<p class="vide">Cette fiche ne déclare aucune valeur saisie.</p>'
    if not trace["liens"]:
        return '<p class="vide">Aucune valeur saisie n\'a été retrouvée dans la base.</p>'
    lignes = "".join(
        f"<tr><td>{_t(x['champ_ecran'])}</td><td>{_t(x['valeur'])}</td>"
        f"<td>{_t(x['table'])}.{_t(x['colonne'])}</td>"
        f"<td>{_t(CORRESPONDANCES.get(x['type_correspondance'], x['type_correspondance']))}</td>"
        f"<td>{_t(x['confiance'])}</td></tr>" for x in trace["liens"])
    return ("<p>Où chaque valeur saisie par le comptable a été retrouvée dans la base.</p>"
            "<table><tr><th>Champ à l'écran</th><th>Valeur saisie</th><th>Colonne de la base</th>"
            f"<th>Correspondance</th><th>Confiance</th></tr>{lignes}</table>")


def _section_ecarts(trace: Mapping[str, Any]) -> str:
    if not trace["ecarts_saisie"]:
        return ""
    lignes = []
    for e in trace["ecarts_saisie"]:
        if e["type_ecart"] == "valeur_differente":
            texte = (f"Valeur attendue <b>{_t(e['valeur_attendue'])}</b>, valeur trouvée "
                     f"<b>{_t(e['valeur_trouvee'])}</b> dans {_t(e['table'])}.{_t(e['colonne'])}.")
        else:
            texte = f"Valeur attendue <b>{_t(e['valeur_attendue'])}</b> : introuvable dans la base."
        lignes.append(f"<li><b>{_t(e['champ_ecran'])}</b> (écran {_t(e['ecran'])}) — {texte}</li>")
    return ('<h2>Écarts de saisie</h2><div class="bandeau alerte">Une valeur saisie semble différer de la fiche. '
            "Proposition : réinitialiser la base de TEST puis rejouer la fiche.</div>"
            f"<ul>{''.join(lignes)}</ul>")


def _section_calcules(trace: Mapping[str, Any]) -> str:
    if not trace["champs_calcules"]:
        return ""
    lignes = "".join(
        f"<tr class=\"hyp\"><td>{_t(c['table'])}.{_t(c['colonne'])}</td><td>{_t(c['valeur'])}</td>"
        f"<td>{_t(' ; '.join(HYPOTHESES.get(h, h) for h in c['hypotheses']))}</td><td>{_t(c['details'])}</td></tr>"
        for c in trace["champs_calcules"])
    return ("<h2>Valeurs calculées par le logiciel (hypothèses)</h2>"
            "<p class=\"note\">Ces valeurs n'ont pas été saisies : le logiciel les a produites. Les explications "
            "proposées sont des <b>hypothèses</b> à confirmer, pas des règles.</p>"
            "<table><tr><th>Colonne</th><th>Valeur</th><th>Origine possible</th><th>Détail</th></tr>"
            f"{lignes}</table>")


def _section_bruit(trace: Mapping[str, Any]) -> str:
    if not trace["bruit"]:
        return ""
    items = "".join(f"<li>{_t(b['table'])} : {_t(b['resume'])}</li>" for b in trace["bruit"])
    return ("<h2>Tables qui bougent toutes seules (ignorées)</h2>"
            f"<p class=\"note\">Ces tables changent même sans action : elles ne sont pas comptées ci-dessus.</p><ul>{items}</ul>")


def _section_schema(trace: Mapping[str, Any]) -> str:
    if not trace["schema_modifie"]:
        return ""
    natures = {"colonnes_modifiees": "colonnes modifiées", "table_ajoutee": "table ajoutée", "table_supprimee": "table supprimée"}
    items = "".join(f"<li>{_t(s['table'])} : {_t(natures.get(s['nature'], s['nature']))}</li>" for s in trace["schema_modifie"])
    return f"<h2>Structure de la base modifiée</h2><ul>{items}</ul>"


def _section_avertissements(trace: Mapping[str, Any]) -> str:
    if not trace["avertissements"]:
        return ""
    items = "".join(f"<li>{_t(a['message'])}</li>" for a in trace["avertissements"])
    return f'<h2>Avertissements</h2><div class="bandeau alerte"><ul>{items}</ul></div>'


def generer_rapport_html(trace: dict[str, Any], captures: Mapping[str, str | None] | None = None) -> str:
    """Page HTML autonome pour `trace` (dictionnaire de `construire_trace`)."""
    captures = captures or {}
    ex, fiche = trace["execution"], trace["fiche"]
    libelle, classe, explication = STATUTS[ex["statut"]]
    n = compter_changements(trace)
    p = [
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">',
        f"<title>Rapport {_t(fiche['id'])} — {_t(fiche['titre'])}</title>",
        f"<style>{_CSS}</style></head><body><main>",
        f"<h1>{_t(fiche['id'])} — {_t(fiche['titre'])}</h1>",
        f'<div class="meta">Du <b>{_t(_date_fr(ex["debut"]))}</b> au <b>{_t(_date_fr(ex["fin"]))}</b> '
        f"(durée {_t(_duree(ex['debut'], ex['fin']))}) · poste <b>{_t(ex['poste'])}</b> · "
        f"utilisateur <b>{_t(ex['utilisateur_windows'])}</b></div>",
        f'<div class="bandeau {classe}"><b>{libelle}.</b> {_t(explication)}</div>',
        f'<p class="resume">{_t(resume_trace(trace))}</p>',
    ]
    if ex["remarques"].strip():
        p += ["<h2>Remarques et messages affichés</h2>", f"<pre>{_t(ex['remarques'])}</pre>"]
    p.append("<h2>Ce que la fiche a écrit dans la base</h2>")
    if ex["statut"] == "annulee":
        p.append('<p class="vide">Fiche annulée : rien à comparer.</p>')
    elif not n["tables"]:
        p.append('<p class="vide">Aucune modification détectée.</p>')
    else:
        p += [_section_table(t) for t in trace["changements"]]
    p += ["<h2>Valeurs saisies retrouvées</h2>", _section_liens(trace) if ex["statut"] != "annulee" else ""]
    p += [_section_ecarts(trace), _section_calcules(trace), _section_bruit(trace),
          _section_schema(trace), _section_avertissements(trace)]
    figures = "".join(
        f'<figure><img src="{_t(nom)}" alt="Capture d\'écran {titre}"><figcaption>Capture {titre}</figcaption></figure>'
        for cle, titre in (("debut", "au début"), ("fin", "à la fin")) if (nom := captures.get(cle)))
    p += ["<h2>Captures d'écran</h2>", figures or '<p class="vide">Aucune capture disponible.</p>']
    p.append(f'<p class="note">Base tracée : {_t(trace["base"]["chemin"])} · format de trace {_t(trace["format_version"])}</p>')
    p.append("</main></body></html>")
    return "\n".join(p)
