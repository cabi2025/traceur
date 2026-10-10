"""Réanalyse hors ligne d'un `trace.json` (AMB-042) : `traceur.exe --reanalyser <trace.json>`.

Recalcule `liens`, `ecarts_saisie` et `champs_calcules` avec les règles courantes, **sans aucun accès à la
base** (ni pyodbc, ni configuration). La trace d'origine n'est jamais modifiée : le résultat est écrit à côté,
dans `trace_reanalysee.json` et `rapport_reanalyse.html`.

Limite : `trace.json` ne contient que les changements, pas les photos. Les hypothèses qui en dépendent
(`compteur` d'une insertion, `copie`, `constante`, `somme_lignes`) sont reprises de l'original, filtrées par
les règles courantes, avec l'avertissement « non recalculable hors ligne ».
"""

from __future__ import annotations

import copy
import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from traceur.moteur.calcules import (
    TABLES_IGNOREES_ANALYSE_DEFAUT,
    detecter_champs_calcules_hors_ligne,
)
from traceur.moteur.cellules import Cellule
from traceur.moteur.diff import Avertissement
from traceur.moteur.liens import ValeurSaisie, chercher_liens
from traceur.rapports.rapport import generer_rapport_html
from traceur.rapports.trace import FORMAT_VERSION

NOM_TRACE_REANALYSEE = "trace_reanalysee.json"
NOM_RAPPORT_REANALYSE = "rapport_reanalyse.html"
CODES_INTERPRETATION = ("profil_absent", "valeur_saisie_invalide", "non_recalculable_hors_ligne", "reanalyse")

_MONTANT_JSON = re.compile(r"^-?\d+\.\d{4}$")  # un Decimal est écrit en chaîne avec 4 décimales (monnaie)
_DATE_HEURE_JSON = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$")
_DATE_JSON = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ErreurReanalyse(Exception):
    """Trace illisible ou de version inconnue (message en français)."""


def typer_valeur_json(valeur: Any) -> Any:
    """Retrouve le type d'origine d'une valeur de `trace.json` (montant, date) ; le reste est inchangé.

    Le fichier n'écrit pas les types : un montant est une chaîne `x.xxxx` (Decimal), une date une chaîne ISO.
    """
    if isinstance(valeur, str):
        if _MONTANT_JSON.match(valeur):
            return Decimal(valeur)
        try:
            if _DATE_HEURE_JSON.match(valeur):
                return datetime.fromisoformat(valeur)
            if _DATE_JSON.match(valeur):
                return date.fromisoformat(valeur)
        except ValueError:
            return valeur
    return valeur


def _typer_ligne(ligne: Mapping[str, Any]) -> dict[str, Any]:
    return {k: typer_valeur_json(v) for k, v in ligne.items()}


def cellules_de_la_trace(changements: Sequence[Mapping[str, Any]]) -> list[Cellule]:
    """Mêmes cellules que `extraire_cellules` (même numérotation), reconstruites depuis `changements`."""
    cellules: list[Cellule] = []
    numero = 0
    for t in changements:
        table = str(t["table"])
        sans_cle = t.get("cle_utilisee", {}).get("type") == "aucune"
        origine = "ligne_ajoutee" if sans_cle else "insert"
        for brut in (*t.get("inserts", []), *t.get("lignes_ajoutees", [])):
            ligne = _typer_ligne(brut["valeurs"])
            for colonne, valeur in ligne.items():
                cellules.append(Cellule(table, colonne, valeur, origine, None, ligne, (table, numero, colonne)))
            numero += 1
        for u in t.get("updates", []):
            cle = _typer_ligne(u["cle"])
            champs = [(c["colonne"], typer_valeur_json(c["avant"]), typer_valeur_json(c["apres"])) for c in u["champs"]]
            complete = {**cle, **{colonne: apres for colonne, _, apres in champs}}
            for colonne, avant, apres in champs:
                cellules.append(Cellule(table, colonne, apres, "update", avant, complete, (table, numero, colonne)))
            numero += 1
        for p in t.get("updates_probables", []):
            apres_ligne = _typer_ligne(p["apres"])
            for c in p["champs"]:
                cellules.append(Cellule(table, c["colonne"], typer_valeur_json(c["apres"]), "update_probable",
                                        typer_valeur_json(c["avant"]), apres_ligne, (table, numero, c["colonne"])))
            numero += 1
    return cellules


def lire_trace(chemin: Path) -> dict[str, Any]:
    try:
        trace = json.loads(chemin.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise ErreurReanalyse(f"Fichier introuvable : {chemin}") from None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erreur:
        raise ErreurReanalyse(f"Impossible de lire {chemin} comme trace.json : {erreur}") from None
    if not isinstance(trace, dict) or "changements" not in trace or "fiche" not in trace:
        raise ErreurReanalyse(f"{chemin} n'est pas un trace.json du Traceur (rubriques « fiche » et « changements »).")
    if trace.get("format_version") != FORMAT_VERSION:
        raise ErreurReanalyse(
            f"Version de format inconnue : {trace.get('format_version')!r} (attendue : {FORMAT_VERSION!r})."
        )
    return trace


def reanalyser_trace(
    trace: Mapping[str, Any],
    tables_ignorees_analyse: Sequence[str] = TABLES_IGNOREES_ANALYSE_DEFAUT,
) -> dict[str, Any]:
    """Nouvelle trace (copie) dont `liens`, `ecarts_saisie`, `champs_calcules` sont recalculés."""
    resultat: dict[str, Any] = copy.deepcopy(dict(trace))
    avertissements: list[Avertissement] = []
    saisies = tuple(
        ValeurSaisie(v["champ_ecran"], v["ecran"], v["valeur"], v["type"])
        for v in trace["fiche"].get("valeurs_saisies", [])
    )
    execution = trace.get("execution", {})
    if not saisies:
        avertissements.append(Avertissement(None, "reanalyse", "La trace ne contient aucune valeur saisie : "
                                            "aucun lien ni écart de saisie ne peut être recalculé."))
    cellules = cellules_de_la_trace(trace["changements"])
    liens, ecarts, expliquees = chercher_liens(saisies, cellules, avertissements)
    try:
        debut = datetime.fromisoformat(execution["debut"])
        fin = datetime.fromisoformat(execution["fin"])
    except (KeyError, ValueError):
        debut = fin = datetime.min
        avertissements.append(Avertissement(None, "reanalyse", "Début ou fin d'exécution illisible : "
                                            "l'hypothèse « horodatage_systeme » est ignorée."))
    calcules = detecter_champs_calcules_hors_ligne(
        cellules, expliquees, saisies, debut, fin, trace.get("champs_calcules", []),
        tables_ignorees_analyse, avertissements,
    )
    conserves = [a for a in trace.get("avertissements", []) if a.get("code") not in CODES_INTERPRETATION]
    resultat["liens"] = [x.vers_dict() for x in liens]
    resultat["ecarts_saisie"] = [x.vers_dict() for x in ecarts]
    resultat["champs_calcules"] = [x.vers_dict() for x in calcules]
    resultat["avertissements"] = [
        *conserves, *(a.vers_dict() for a in avertissements),
        Avertissement(None, "reanalyse", "Trace réanalysée hors ligne avec les règles courantes "
                      "(trace d'origine inchangée).").vers_dict(),
    ]
    if resultat.get("execution", {}).get("statut") != "annulee":
        resultat["execution"]["statut"] = "ecart_saisie" if ecarts else "terminee"
    return resultat


def resume_reanalyse(avant: Mapping[str, Any], apres: Mapping[str, Any]) -> str:
    """Texte court des changements, affiché à l'utilisateur."""
    def n(trace: Mapping[str, Any], cle: str) -> int:
        return len(trace.get(cle, []))

    non_recalculables = sum(1 for a in apres["avertissements"] if a.get("code") == "non_recalculable_hors_ligne")
    return "\n".join([
        f"Liens : {n(avant, 'liens')} → {n(apres, 'liens')}",
        f"Écarts de saisie : {n(avant, 'ecarts_saisie')} → {n(apres, 'ecarts_saisie')}",
        f"Champs calculés : {n(avant, 'champs_calcules')} → {n(apres, 'champs_calcules')}",
        f"Hypothèses reprises de l'original (non recalculables hors ligne) : {non_recalculables}",
        f"Statut : {avant.get('execution', {}).get('statut')} → {apres.get('execution', {}).get('statut')}",
    ])


def reanalyser_fichier(
    chemin: Path,
    dossier_sortie: Path | None = None,
    tables_ignorees_analyse: Sequence[str] = TABLES_IGNOREES_ANALYSE_DEFAUT,
) -> tuple[Path, Path, str]:
    """Lit `chemin`, réanalyse, écrit `trace_reanalysee.json` et `rapport_reanalyse.html`. Retourne
    (json, html, résumé). Le fichier d'origine n'est jamais écrit."""
    trace = lire_trace(chemin)
    nouvelle = reanalyser_trace(trace, tables_ignorees_analyse)
    dossier = dossier_sortie or chemin.parent
    dossier.mkdir(parents=True, exist_ok=True)
    sortie_json, sortie_html = dossier / NOM_TRACE_REANALYSEE, dossier / NOM_RAPPORT_REANALYSE
    if sortie_json.resolve() == chemin.resolve():
        raise ErreurReanalyse("Le fichier d'entrée porte le nom du fichier de sortie : choisissez un autre dossier.")
    sortie_json.write_text(json.dumps(nouvelle, ensure_ascii=False, indent=2), encoding="utf-8")
    sortie_html.write_text(generer_rapport_html(nouvelle), encoding="utf-8")
    return sortie_json, sortie_html, resume_reanalyse(trace, nouvelle)
