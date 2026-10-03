"""Lien valeur saisie → colonne (F6, SPEC §7.1) et écarts de saisie (SPEC §7.4)."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, Sequence

from .cellules import Cellule
from .diff import Avertissement
from .normalisation import valeur_json

TYPES_SAISIE = ("montant", "date", "texte", "code")
FORMATS_DATE = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")
LONGUEUR_MIN_TRONQUE = 3  # AMB-020 (validée)
LONGUEUR_MIN_ECART_TEXTE = 4  # AMB-021

# AMB-019 (validée) : échelle de confiance.
CONFIANCE = {
    "exacte": "haute",
    "date_heure": "haute",
    "signe_inverse": "moyenne",
    "majuscules": "moyenne",
    "tronque": "moyenne",
    "x100": "faible",
    "div100": "faible",
}


@dataclass(frozen=True)
class ValeurSaisie:
    champ_ecran: str
    ecran: str
    valeur: str
    type: str


@dataclass(frozen=True)
class Lien:
    champ_ecran: str
    ecran: str
    valeur: str
    table: str
    colonne: str
    type_correspondance: str
    confiance: str

    def vers_dict(self) -> dict[str, Any]:
        return {
            "champ_ecran": self.champ_ecran,
            "ecran": self.ecran,
            "valeur": self.valeur,
            "table": self.table,
            "colonne": self.colonne,
            "type_correspondance": self.type_correspondance,
            "confiance": self.confiance,
        }


@dataclass(frozen=True)
class EcartSaisie:
    champ_ecran: str
    ecran: str
    valeur_attendue: str
    type_ecart: str  # "introuvable" | "valeur_differente"
    table: str | None = None
    colonne: str | None = None
    valeur_trouvee: Any = None

    def vers_dict(self) -> dict[str, Any]:
        return {
            "champ_ecran": self.champ_ecran,
            "ecran": self.ecran,
            "valeur_attendue": self.valeur_attendue,
            "type_ecart": self.type_ecart,
            "table": self.table,
            "colonne": self.colonne,
            "valeur_trouvee": valeur_json(self.valeur_trouvee),
        }


@dataclass(frozen=True)
class _Attendu:
    type: str
    texte: str
    montant: Decimal | None = None
    jour: date | None = None


def analyser_montant(texte: str) -> Decimal | None:
    """« 1 234,56 », « 1234.56 » → Decimal ; None si ce n'est pas un montant."""
    nettoye = "".join(c for c in texte if not c.isspace()).replace(",", ".")
    try:
        montant = Decimal(nettoye)
    except InvalidOperation:
        return None
    return montant if montant.is_finite() else None


def analyser_date(texte: str) -> date | None:
    for format_ in FORMATS_DATE:
        try:
            return datetime.strptime(texte.strip(), format_).date()
        except ValueError:
            continue
    return None


def nombre(valeur: Any) -> Decimal | None:
    """Valeur numérique d'une cellule (entier, Decimal, flottant) ; None sinon."""
    if isinstance(valeur, bool):
        return None
    if isinstance(valeur, (int, Decimal)):
        return Decimal(valeur)
    if isinstance(valeur, float):
        return Decimal(repr(valeur)) if valeur == valeur else None
    return None


def _preparer(saisie: ValeurSaisie) -> _Attendu | None:
    if saisie.type == "montant":
        montant = analyser_montant(saisie.valeur)
        return None if montant is None else _Attendu("montant", saisie.valeur, montant=montant)
    if saisie.type == "date":
        jour = analyser_date(saisie.valeur)
        return None if jour is None else _Attendu("date", saisie.valeur, jour=jour)
    if saisie.type in ("texte", "code"):
        return _Attendu(saisie.type, unicodedata.normalize("NFC", saisie.valeur))
    return None


def _comparer(attendu: _Attendu, valeur: Any) -> str | None:
    """Type de correspondance entre la valeur saisie et une cellule, ou None."""
    if valeur is None:
        return None
    if attendu.type == "montant" and attendu.montant is not None:
        cellule = nombre(valeur)
        if cellule is None:
            return None
        m = attendu.montant
        if cellule == m:
            return "exacte"
        if m == 0:  # AMB-020 : aucune tolérance pour 0
            return None
        if cellule == -m:
            return "signe_inverse"
        if cellule == m.scaleb(2):
            return "x100"
        if cellule == m.scaleb(-2):
            return "div100"
        return None
    if attendu.type == "date" and attendu.jour is not None:
        if isinstance(valeur, datetime):
            if valeur.date() != attendu.jour:
                return None
            # AMB-020 : minuit pile = exacte ; `date_heure` seulement avec une heure non nulle.
            return "exacte" if valeur.time() == time(0, 0) else "date_heure"
        if isinstance(valeur, date):
            return "exacte" if valeur == attendu.jour else None
        if isinstance(valeur, str):
            return "exacte" if analyser_date(valeur) == attendu.jour else None
        return None
    if attendu.type == "code":
        cellule = nombre(valeur)
        if cellule is not None and cellule == cellule.to_integral_value():
            return "exacte" if str(int(cellule)) == attendu.texte else None
        if isinstance(valeur, str):
            return "exacte" if unicodedata.normalize("NFC", valeur) == attendu.texte else None
        return None
    if attendu.type == "texte" and isinstance(valeur, str):
        texte = unicodedata.normalize("NFC", valeur)
        if texte == attendu.texte:
            return "exacte"
        if texte == attendu.texte.upper():
            return "majuscules"
        if LONGUEUR_MIN_TRONQUE <= len(texte) < len(attendu.texte) and attendu.texte.startswith(texte):
            return "tronque"
    return None


def _forme_normalisee(attendu: _Attendu, valeur: Any) -> str | None:
    """Forme comparable pour la distance de l'écart de saisie (AMB-021)."""
    if attendu.type == "montant":
        nb = nombre(valeur)
        return None if nb is None else format(nb.normalize(), "f")
    if attendu.type == "date":
        if isinstance(valeur, (date, datetime)):
            return valeur.date().isoformat() if isinstance(valeur, datetime) else valeur.isoformat()
        jour = analyser_date(valeur) if isinstance(valeur, str) else None
        return None if jour is None else jour.isoformat()
    if isinstance(valeur, str):
        return unicodedata.normalize("NFC", valeur)
    nb = nombre(valeur)
    return None if nb is None else str(int(nb)) if nb == nb.to_integral_value() else None


def _attendu_normalise(attendu: _Attendu) -> str:
    if attendu.montant is not None:
        return format(attendu.montant.normalize(), "f")
    if attendu.jour is not None:
        return attendu.jour.isoformat()
    return attendu.texte


def distance(a: str, b: str) -> int:
    """Distance de Damerau-Levenshtein (une transposition de deux caractères voisins compte 1).

    Variante « OSA » : identique à la distance complète pour le seuil ≤ 1 utilisé ici.
    """
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cout = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cout)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


def chercher_liens(
    saisies: Sequence[ValeurSaisie],
    cellules: Sequence[Cellule],
    avertissements: list[Avertissement],
) -> tuple[list[Lien], list[EcartSaisie], set[tuple[str, int, str]]]:
    """Liens saisie → colonne, écarts de saisie, et références des cellules expliquées.

    Le lien se fait par valeur (AMB-009). Les correspondances tolérées ne sont cherchées que
    s'il n'existe aucune correspondance exacte pour la saisie (AMB-020).
    """
    liens: list[Lien] = []
    vus: set[Lien] = set()
    expliquees: set[tuple[str, int, str]] = set()
    sans_lien: list[tuple[ValeurSaisie, _Attendu]] = []
    colonnes_du_champ: dict[tuple[str, str], list[tuple[str, str]]] = {}

    for saisie in saisies:
        attendu = _preparer(saisie)
        if attendu is None:
            avertissements.append(
                Avertissement(
                    None,
                    "valeur_saisie_invalide",
                    f"La valeur « {saisie.valeur} » du champ « {saisie.champ_ecran} » n'est pas "
                    f"un(e) {saisie.type} valide : elle ne peut pas être recherchée.",
                    {"champ_ecran": saisie.champ_ecran, "ecran": saisie.ecran},
                )
            )
            continue
        trouvees = [(c, t) for c in cellules if (t := _comparer(attendu, c.valeur)) is not None]
        exactes = [(c, t) for c, t in trouvees if t == "exacte"]
        retenues = exactes or trouvees
        if not retenues:
            sans_lien.append((saisie, attendu))
            continue
        for cellule, type_ in retenues:
            expliquees.add(cellule.ref)
            lien = Lien(saisie.champ_ecran, saisie.ecran, saisie.valeur, cellule.table,
                        cellule.colonne, type_, CONFIANCE[type_])
            if lien not in vus:
                vus.add(lien)
                liens.append(lien)
            cle = (saisie.champ_ecran, saisie.ecran)
            paire = (cellule.table, cellule.colonne)
            if paire not in colonnes_du_champ.setdefault(cle, []):
                colonnes_du_champ[cle].append(paire)

    ecarts = [
        _ecart(saisie, attendu, colonnes_du_champ, cellules, expliquees)
        for saisie, attendu in sans_lien
    ]
    return liens, ecarts, expliquees


def _ecart(
    saisie: ValeurSaisie,
    attendu: _Attendu,
    colonnes_du_champ: dict[tuple[str, str], list[tuple[str, str]]],
    cellules: Sequence[Cellule],
    expliquees: set[tuple[str, int, str]],
) -> EcartSaisie:
    """AMB-021 : « manifestement différent » = Damerau-Levenshtein ≤ 1, dans la colonne des saisies sœurs."""
    colonnes = colonnes_du_champ.get((saisie.champ_ecran, saisie.ecran), [])
    cible = _attendu_normalise(attendu)
    if attendu.type in ("texte", "code") and len(cible) < LONGUEUR_MIN_ECART_TEXTE:
        colonnes = []
    for cellule in cellules:
        if (cellule.table, cellule.colonne) not in colonnes or cellule.ref in expliquees:
            continue
        forme = _forme_normalisee(attendu, cellule.valeur)
        if forme is not None and forme != cible and distance(forme, cible) <= 1:
            return EcartSaisie(saisie.champ_ecran, saisie.ecran, saisie.valeur,
                               "valeur_differente", cellule.table, cellule.colonne, cellule.valeur)
    return EcartSaisie(saisie.champ_ecran, saisie.ecran, saisie.valeur, "introuvable")
