"""Construction de `trace.json` (SPEC §8.1, format de référence : docs/formats/trace.example.json)."""

from __future__ import annotations

import getpass
import re
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from traceur.moteur.diff import Avertissement, ResultatDiff
from traceur.moteur.interpretation import ResultatInterpretation
from traceur.moteur.liens import ValeurSaisie

FORMAT_VERSION = "1.0"
STATUTS_EXECUTION = ("terminee", "annulee", "ecart_saisie")  # SPEC §8.2


@dataclass(frozen=True)
class FicheTrace:
    id: str
    titre: str
    valeurs_saisies: tuple[ValeurSaisie, ...] = ()


@dataclass(frozen=True)
class Execution:
    debut: datetime
    fin: datetime
    poste: str = ""
    utilisateur_windows: str = ""
    remarques: str = ""
    annulee: bool = False


def poste_courant() -> str:
    return socket.gethostname()


def utilisateur_courant() -> str:
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001 - variables d'environnement absentes, compte de service…
        return ""


def nom_dossier_trace(fiche_id: str, debut: datetime) -> str:
    """`S-003_20261005-101522` (SPEC §8) ; les caractères interdits dans un nom de dossier sont remplacés."""
    sur = re.sub(r"[^A-Za-z0-9._-]+", "_", fiche_id).strip("._") or "fiche"
    return f"{sur}_{debut:%Y%m%d-%H%M%S}"


def statut_execution(execution: Execution, interpretation: ResultatInterpretation | None) -> str:
    """`annulee` > `ecart_saisie` > `terminee` (SPEC §8.2)."""
    if execution.annulee:
        return "annulee"
    if interpretation is not None and interpretation.a_un_ecart_de_saisie:
        return "ecart_saisie"
    return "terminee"


def construire_trace(
    fiche: FicheTrace,
    execution: Execution,
    base_chemin: str,
    diff: ResultatDiff | None,
    interpretation: ResultatInterpretation | None,
    empreinte_fichier_avant: str | None = None,
    avertissements: Sequence[Avertissement] = (),
) -> dict[str, Any]:
    """Dictionnaire JSON d'une trace. Une fiche annulée est conservée sans comparaison."""
    if execution.annulee:
        diff, interpretation = None, None
    diff_dict = diff.vers_dict() if diff is not None else {
        "changements": [], "schema_modifie": [], "bruit": [], "avertissements": []}
    interp = interpretation.vers_dict() if interpretation is not None else {
        "liens": [], "champs_calcules": [], "ecarts_saisie": [], "avertissements": []}
    tous_avertissements = [*diff_dict["avertissements"], *interp["avertissements"],
                           *(a.vers_dict() for a in avertissements)]
    return {
        "format_version": FORMAT_VERSION,
        "fiche": {
            "id": fiche.id,
            "titre": fiche.titre,
            "valeurs_saisies": [
                {"champ_ecran": v.champ_ecran, "ecran": v.ecran, "valeur": v.valeur, "type": v.type}
                for v in fiche.valeurs_saisies
            ],
        },
        "execution": {
            "debut": execution.debut.isoformat(timespec="seconds"),
            "fin": execution.fin.isoformat(timespec="seconds"),
            "poste": execution.poste or poste_courant(),
            "utilisateur_windows": execution.utilisateur_windows or utilisateur_courant(),
            "statut": statut_execution(execution, interpretation),
            "remarques": execution.remarques,
        },
        "base": {"chemin": base_chemin, "empreinte_fichier_avant": empreinte_fichier_avant},
        "changements": diff_dict["changements"],
        "bruit": diff_dict["bruit"],
        "liens": interp["liens"],
        "champs_calcules": interp["champs_calcules"],
        "ecarts_saisie": interp["ecarts_saisie"],
        "schema_modifie": diff_dict["schema_modifie"],
        "avertissements": tous_avertissements,
    }


def _pluriel(n: int, singulier: str, pluriel: str) -> str:
    return f"{n} {singulier if n <= 1 else pluriel}"


def compter_changements(trace: dict[str, Any]) -> dict[str, int]:
    """Totaux par nature : tables, lignes ajoutées / modifiées / supprimées."""
    ajoutees = modifiees = supprimees = 0
    for t in trace["changements"]:
        ajoutees += len(t.get("inserts", [])) + len(t.get("lignes_ajoutees", []))
        modifiees += len(t.get("updates", [])) + len(t.get("updates_probables", []))
        supprimees += len(t.get("deletes", [])) + len(t.get("lignes_supprimees", []))
    return {"tables": len(trace["changements"]), "ajoutees": ajoutees,
            "modifiees": modifiees, "supprimees": supprimees}


def resume_trace(trace: dict[str, Any]) -> str:
    """« 3 tables modifiées, 4 lignes ajoutées, 1 modifiée » (SPEC §5.3)."""
    if trace["execution"]["statut"] == "annulee":
        return "Fiche annulée : aucune comparaison n'a été faite."
    n = compter_changements(trace)
    if not n["tables"]:
        return "Aucune modification détectée dans la base."
    morceaux = [_pluriel(n["tables"], "table modifiée", "tables modifiées")]
    if n["ajoutees"]:
        morceaux.append(_pluriel(n["ajoutees"], "ligne ajoutée", "lignes ajoutées"))
    if n["modifiees"]:
        morceaux.append(_pluriel(n["modifiees"], "modifiée", "modifiées"))
    if n["supprimees"]:
        morceaux.append(_pluriel(n["supprimees"], "supprimée", "supprimées"))
    return ", ".join(morceaux)
