"""Fiches de scénarios : chargement (SPEC §9) et statut dérivé des traces (SPEC §5.1, §8.2)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from traceur.moteur.liens import TYPES_SAISIE, ValeurSaisie

journal = logging.getLogger("traceur.fiches")

A_FAIRE, FAITE, ECART, ANNULEE = "à faire", "faite", "écart", "annulée"
STATUT_DEPUIS_TRACE = {"terminee": FAITE, "ecart_saisie": ECART, "annulee": ANNULEE}


class ErreurFiches(Exception):
    """Fichier de fiches illisible ou invalide (message en français)."""


@dataclass(frozen=True)
class Etape:
    n: int
    texte: str
    capture_ref: str | None = None


@dataclass(frozen=True)
class Fiche:
    id: str
    titre: str
    lot: int | None
    duree_min: int | None
    prerequis: tuple[str, ...]
    reinitialiser_avant: bool
    etapes: tuple[Etape, ...]
    valeurs_saisies: tuple[ValeurSaisie, ...]
    a_noter: tuple[str, ...]


def _texte(valeur: Any, quoi: str) -> str:
    if not isinstance(valeur, str) or not valeur.strip():
        raise ErreurFiches(f"{quoi} doit être un texte non vide.")
    return valeur


def _entier_optionnel(valeur: Any, quoi: str) -> int | None:
    if valeur is None:
        return None
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise ErreurFiches(f"{quoi} doit être un nombre entier.")
    return valeur


def _liste_textes(valeur: Any, quoi: str) -> tuple[str, ...]:
    if valeur is None:
        return ()
    if not isinstance(valeur, list) or not all(isinstance(v, str) for v in valeur):
        raise ErreurFiches(f"{quoi} doit être une liste de textes.")
    return tuple(valeur)


def _fiche(donnees: Any, position: int) -> Fiche:
    if not isinstance(donnees, dict):
        raise ErreurFiches(f"La fiche n° {position} doit être un objet JSON.")
    ident = _texte(donnees.get("id"), f"L'identifiant de la fiche n° {position}")
    quoi = f"Fiche {ident} :"
    etapes = []
    for i, e in enumerate(donnees.get("etapes") or [], 1):
        if not isinstance(e, dict):
            raise ErreurFiches(f"{quoi} l'étape n° {i} doit être un objet JSON.")
        n = _entier_optionnel(e.get("n", i), f"{quoi} le numéro de l'étape n° {i}")
        ref = e.get("capture_ref")
        etapes.append(Etape(n if n is not None else i, _texte(e.get("texte"), f"{quoi} le texte de l'étape n° {i}"),
                            str(ref) if ref is not None else None))
    saisies = []
    for i, v in enumerate(donnees.get("valeurs_saisies") or [], 1):
        if not isinstance(v, dict) or v.get("type") not in TYPES_SAISIE:
            raise ErreurFiches(
                f"{quoi} la valeur saisie n° {i} doit avoir un type parmi : {', '.join(TYPES_SAISIE)}.")
        saisies.append(ValeurSaisie(_texte(v.get("champ_ecran"), f"{quoi} le champ d'écran n° {i}"),
                                    str(v.get("ecran", "")), str(v.get("valeur", "")), v["type"]))
    reinit = donnees.get("reinitialiser_avant", False)
    if not isinstance(reinit, bool):
        raise ErreurFiches(f"{quoi} « reinitialiser_avant » doit valoir true ou false.")
    return Fiche(ident, _texte(donnees.get("titre"), f"{quoi} le titre"),
                 _entier_optionnel(donnees.get("lot"), f"{quoi} le lot"),
                 _entier_optionnel(donnees.get("duree_min"), f"{quoi} la durée"),
                 _liste_textes(donnees.get("prerequis"), f"{quoi} « prerequis »"), reinit, tuple(etapes),
                 tuple(saisies), _liste_textes(donnees.get("a_noter"), f"{quoi} « a_noter »"))


def charger_fiches(chemin: str | Path) -> list[Fiche]:
    """Lit le fichier de fiches (UTF-8, BOM toléré) ; chaque erreur nomme la fiche concernée."""
    chemin = Path(chemin)
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise ErreurFiches(f"Fichier de fiches introuvable : {chemin}") from None
    except (OSError, UnicodeDecodeError) as erreur:
        raise ErreurFiches(f"Impossible de lire {chemin} (enregistrez-le en UTF-8) : {erreur}") from None
    except json.JSONDecodeError as erreur:
        raise ErreurFiches(f"Le fichier de fiches n'est pas un JSON valide (ligne {erreur.lineno}, colonne "
                           f"{erreur.colno}) : {erreur.msg}.") from None
    brutes = donnees.get("fiches") if isinstance(donnees, dict) else None
    if not isinstance(brutes, list) or not brutes:
        raise ErreurFiches("Le fichier de fiches doit contenir une liste « fiches » non vide.")
    fiches = [_fiche(f, i) for i, f in enumerate(brutes, 1)]
    doublons = sorted({f.id for f in fiches if sum(g.id == f.id for g in fiches) > 1})
    if doublons:
        raise ErreurFiches(f"Identifiants de fiche en double : {', '.join(doublons)}.")
    lot_du_fichier = _entier_optionnel(donnees.get("lot"), "Le lot du fichier")
    return [f if f.lot is not None or lot_du_fichier is None else _avec_lot(f, lot_du_fichier) for f in fiches]


def _avec_lot(fiche: Fiche, lot: int) -> Fiche:
    return Fiche(fiche.id, fiche.titre, lot, fiche.duree_min, fiche.prerequis, fiche.reinitialiser_avant,
                 fiche.etapes, fiche.valeurs_saisies, fiche.a_noter)


def statuts_fiches(fiches: Sequence[Fiche], dossiers_de_traces: Sequence[Path]) -> dict[str, str]:
    """Statut de chaque fiche d'après sa **dernière** trace (SPEC §8.2). Sans trace : « à faire ».

    `dossiers_de_traces` : dossiers contenant un sous-dossier par trace (partage et dossier local).
    Un dossier inaccessible ou une trace illisible est ignoré (avertissement au journal).
    """
    derniere: dict[str, tuple[str, str]] = {}
    for dossier in dossiers_de_traces:
        try:
            sous_dossiers = [d for d in dossier.iterdir() if d.is_dir() and not d.name.startswith(".")]
        except FileNotFoundError:
            continue  # aucune trace encore déposée : normal au premier lancement
        except OSError as erreur:
            journal.warning("Dossier de traces inaccessible (%s) : %s", dossier, erreur)
            continue
        for sous in sous_dossiers:
            try:
                trace = json.loads((sous / "trace.json").read_text(encoding="utf-8"))
                ident, debut, statut = trace["fiche"]["id"], trace["execution"]["debut"], trace["execution"]["statut"]
            except (OSError, ValueError, KeyError):
                journal.warning("Trace illisible ignorée pour les statuts : %s", sous)
                continue
            if ident not in derniere or debut > derniere[ident][0]:
                derniere[ident] = (debut, statut)
    return {f.id: STATUT_DEPUIS_TRACE.get(derniere.get(f.id, ("", ""))[1], A_FAIRE) for f in fiches}
