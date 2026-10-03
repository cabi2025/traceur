"""Chargement et validation de `config.json` (F1, SPEC §4).

Les mots de passe ne figurent jamais dans `repr()` ni dans les messages d'erreur.
"""

from __future__ import annotations

import codecs
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CLES_OBLIGATOIRES = ("base_test", "instantane_reference", "chemins_interdits", "dossier_sorties")
# AMB-023 : `fichier_fiches` est optionnel ; `instantane_reference` reste obligatoire.
MESSAGE_FICHES_INDISPONIBLES = (
    "Aucun fichier de fiches n'est configuré (paramètre « fichier_fiches » de config.json) : "
    "seuls le profilage et la calibration sont disponibles."
)


class ErreurConfiguration(Exception):
    """Configuration absente ou invalide (message en français, sans mot de passe)."""


@dataclass(frozen=True)
class Configuration:
    base_test: str
    instantane_reference: str
    chemins_interdits: tuple[str, ...]
    dossier_sorties: str
    fichier_fiches: str | None = None
    mot_de_passe: str | None = field(default=None, repr=False)
    fichier_mdw: str | None = None
    utilisateur: str | None = None
    mot_de_passe_mdw: str | None = field(default=None, repr=False)
    tables_ignorees: tuple[str, ...] = ()
    encodage_texte: str = "cp1252"
    delai_stabilisation_s: float = 3

    @property
    def fiches_disponibles(self) -> bool:
        """Sans fichier de fiches, les boutons de fiche sont désactivés (message ci-dessus)."""
        return self.fichier_fiches is not None

    def secrets(self) -> list[str]:
        """Valeurs à masquer dans tout journal ou rapport."""
        return [s for s in (self.mot_de_passe, self.mot_de_passe_mdw) if s]


def _texte(donnees: dict[str, Any], cle: str, obligatoire: bool = False) -> str | None:
    valeur = donnees.get(cle)
    if valeur is None or (isinstance(valeur, str) and not valeur.strip()):
        if obligatoire:
            raise ErreurConfiguration(f"Le paramètre « {cle} » est obligatoire dans config.json.")
        return None
    if not isinstance(valeur, str):
        raise ErreurConfiguration(f"Le paramètre « {cle} » doit être un texte.")
    return valeur


def _liste(donnees: dict[str, Any], cle: str, obligatoire: bool = False) -> tuple[str, ...]:
    valeur = donnees.get(cle)
    if valeur is None:
        if obligatoire:
            raise ErreurConfiguration(f"Le paramètre « {cle} » est obligatoire dans config.json.")
        return ()
    if not isinstance(valeur, list) or not all(isinstance(v, str) for v in valeur):
        raise ErreurConfiguration(f"Le paramètre « {cle} » doit être une liste de textes.")
    if obligatoire and not any(v.strip() for v in valeur):
        raise ErreurConfiguration(
            f"Le paramètre « {cle} » ne doit pas être vide : indiquez au moins la base de production."
        )
    return tuple(v for v in valeur if v.strip())


def configuration_depuis_dict(donnees: dict[str, Any]) -> Configuration:
    """Valide un dictionnaire (contenu de config.json)."""
    encodage = _texte(donnees, "encodage_texte") or "cp1252"
    try:
        codecs.lookup(encodage)
    except LookupError:
        raise ErreurConfiguration(f"Encodage inconnu : « {encodage} » (paramètre encodage_texte).") from None
    delai = donnees.get("delai_stabilisation_s", 3)
    if isinstance(delai, bool) or not isinstance(delai, (int, float)) or delai < 0:
        raise ErreurConfiguration("Le paramètre « delai_stabilisation_s » doit être un nombre positif.")
    config = Configuration(
        base_test=_texte(donnees, "base_test", True) or "",
        instantane_reference=_texte(donnees, "instantane_reference", True) or "",
        chemins_interdits=_liste(donnees, "chemins_interdits", True),
        dossier_sorties=_texte(donnees, "dossier_sorties", True) or "",
        fichier_fiches=_texte(donnees, "fichier_fiches"),
        mot_de_passe=_texte(donnees, "mot_de_passe"),
        fichier_mdw=_texte(donnees, "fichier_mdw"),
        utilisateur=_texte(donnees, "utilisateur"),
        mot_de_passe_mdw=_texte(donnees, "mot_de_passe_mdw"),
        tables_ignorees=_liste(donnees, "tables_ignorees"),
        encodage_texte=encodage,
        delai_stabilisation_s=delai,
    )
    if config.mot_de_passe and config.fichier_mdw:  # AMB-026
        raise ErreurConfiguration(
            "Un mot de passe de base (« mot_de_passe ») et un groupe de travail (« fichier_mdw ») "
            "ne peuvent pas être utilisés ensemble. Gardez l'un des deux.\n"
            "Conseil : retirez le mot de passe de la copie de TEST (ouvrez la copie dans Access en "
            "mode exclusif, menu Outils > Sécurité, puis supprimez le mot de passe de la base de données)."
        )
    if config.fichier_mdw and not config.utilisateur:
        raise ErreurConfiguration("Un « fichier_mdw » demande aussi le paramètre « utilisateur ».")
    return config


def charger_configuration(chemin: str | Path) -> Configuration:
    """Lit `config.json` (UTF-8, BOM toléré)."""
    chemin = Path(chemin)
    try:
        texte = chemin.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise ErreurConfiguration(f"Fichier de configuration introuvable : {chemin}") from None
    except (OSError, UnicodeDecodeError) as erreur:
        raise ErreurConfiguration(f"Impossible de lire {chemin} (enregistrez-le en UTF-8) : {erreur}") from None
    try:
        donnees = json.loads(texte)
    except json.JSONDecodeError as erreur:
        raise ErreurConfiguration(
            f"config.json n'est pas un JSON valide (ligne {erreur.lineno}, colonne {erreur.colno}) : "
            f"{erreur.msg}. Pensez à doubler les antislashs dans les chemins (\\\\)."
        ) from None
    if not isinstance(donnees, dict):
        raise ErreurConfiguration("config.json doit contenir un objet JSON { ... }.")
    return configuration_depuis_dict(donnees)
