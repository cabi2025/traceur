"""Champs calculés : hypothèses sur les valeurs non expliquées par F6 (F7, SPEC §7.2).

Chaque résultat est une **hypothèse**, jamais une règle. Aucune autre heuristique que celles
de la SPEC (§7.3). Détails provisoires : AMB-022.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Mapping, Sequence

from .cellules import Cellule, lignes_inserees
from .diff import Avertissement, ResultatDiff
from .instantane import Instantane
from .liens import ValeurSaisie, analyser_montant, nombre
from .normalisation import normaliser_valeur, valeur_json
from .profilage import Profil, RelationCandidate, cle_comparaison

HYPOTHESES = (
    "compteur", "horodatage_systeme", "somme_lignes", "copie", "constante", "cumul_mis_a_jour",
)
HYPOTHESES_DU_PROFIL = ("somme_lignes", "copie", "constante")  # désactivées sans profil (AMB-010)
_SUFFIXE = re.compile(r"^(.*?)(\d+)$", re.DOTALL)


@dataclass(frozen=True)
class ChampCalcule:
    table: str
    colonne: str
    valeur: Any
    hypotheses: tuple[str, ...]
    details: str

    def vers_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "colonne": self.colonne,
            "valeur": valeur_json(self.valeur),
            "hypotheses": list(self.hypotheses),
            "details": self.details,
        }


@dataclass
class _Contexte:
    diff: ResultatDiff
    avant: Instantane
    apres: Instantane
    debut: datetime
    fin: datetime
    profil: Profil | None
    montants_saisis: list[tuple[ValeurSaisie, Decimal]]
    cellules: Sequence[Cellule]
    inserees: dict[str, list[Mapping[str, Any]]] = field(default_factory=dict)
    deltas: dict[tuple[str, str], list[Decimal]] = field(default_factory=dict)
    _index_avant: dict[tuple[str, str], dict[str, Mapping[str, Any]]] = field(default_factory=dict)

    def ligne_avant(self, table: str, colonne: str, valeur: Any) -> Mapping[str, Any] | None:
        """Ligne de la photo avant dont `colonne` vaut `valeur` (première trouvée)."""
        cle = (table, colonne)
        if cle not in self._index_avant:
            photo = self.avant.tables.get(table)
            index: dict[str, Mapping[str, Any]] = {}
            if photo is not None and colonne in photo.schema.noms():
                noms = photo.schema.noms()
                i = noms.index(colonne)
                for ligne in photo.lignes:
                    index.setdefault(normaliser_valeur(ligne.valeurs[i]), dict(zip(noms, ligne.valeurs)))
            self._index_avant[cle] = index
        return self._index_avant[cle].get(normaliser_valeur(valeur))


def _fmt(valeur: Any) -> str:
    return format(valeur, "f") if isinstance(valeur, Decimal) else str(valeur)


def _pas(valeurs: Sequence[Decimal]) -> Decimal:
    """Pas constant entre les valeurs distinctes triées d'avant, sinon 1 (AMB-022)."""
    triees = sorted(set(valeurs))
    ecarts = {b - a for a, b in zip(triees, triees[1:])}
    return ecarts.pop() if len(ecarts) == 1 and next(iter(ecarts), 0) > 0 else Decimal(1)


def _decouper(valeur: Any) -> tuple[str, str] | None:
    if not isinstance(valeur, str):
        return None
    m = _SUFFIXE.match(valeur)
    return (m.group(1), m.group(2)) if m else None


def _valeurs_avant(ctx: _Contexte, table: str, colonne: str) -> list[Any]:
    photo = ctx.avant.tables.get(table)
    if photo is None or colonne not in photo.schema.noms():
        return []
    i = photo.schema.noms().index(colonne)
    return [ligne.valeurs[i] for ligne in photo.lignes if ligne.valeurs[i] is not None]


def _compteur(c: Cellule, ctx: _Contexte) -> str | None:
    if c.est_insertion:
        n = len(ctx.inserees.get(c.table, []))
        avant = _valeurs_avant(ctx, c.table, c.colonne)
        valeur = nombre(c.valeur)
        if valeur is not None:
            nombres = [x for x in map(nombre, avant) if x is not None]
            if not nombres:
                return None
            maximum, pas = max(nombres), _pas(nombres)
            delta = valeur - maximum
            if delta > 0 and delta % pas == 0 and delta // pas <= n:
                return f"max avant = {_fmt(maximum)}"
            return None
        decoupe = _decouper(c.valeur)
        if decoupe is None:
            return None
        prefixe, chiffres = decoupe
        candidats = [d for d in map(_decouper, avant) if d is not None and d[0] == prefixe]
        if not candidats:
            return None
        prefixe_max, chiffres_max = max(candidats, key=lambda d: (int(d[1]), len(d[1])))
        delta_texte = int(chiffres) - int(chiffres_max)
        largeur = max(len(chiffres_max), len(str(int(chiffres))))
        if 1 <= delta_texte <= n and len(chiffres) == largeur:
            return f"max avant = {prefixe_max}{chiffres_max}"
        return None
    # ligne modifiée : delta de +1, ou pas constant entre les lignes modifiées de la colonne
    avant_v, apres_v = nombre(c.avant), nombre(c.valeur)
    if avant_v is not None and apres_v is not None:
        delta = apres_v - avant_v
    else:
        d1, d2 = _decouper(c.avant), _decouper(c.valeur)
        if d1 is None or d2 is None or d1[0] != d2[0] or len(d1[1]) != len(d2[1]):
            return None
        delta = Decimal(int(d2[1]) - int(d1[1]))
    deltas = ctx.deltas.get((c.table, c.colonne), [])
    constant = len(deltas) >= 2 and len(set(deltas)) == 1
    if delta > 0 and (delta == 1 or constant):
        return f"{c.avant} → {c.valeur}"
    return None


def _horodatage(c: Cellule, ctx: _Contexte) -> str | None:
    v = c.valeur
    if isinstance(v, datetime) and (v.hour, v.minute, v.second, v.microsecond) != (0, 0, 0, 0):
        dans = ctx.debut <= v <= ctx.fin
    elif isinstance(v, datetime):
        dans = ctx.debut.date() <= v.date() <= ctx.fin.date()
    elif isinstance(v, date):
        dans = ctx.debut.date() <= v <= ctx.fin.date()
    else:
        return None
    if not dans:
        return None
    return f"{v.isoformat()} dans [{ctx.debut.isoformat()}, {ctx.fin.isoformat()}]"


def _relations(ctx: _Contexte) -> list[RelationCandidate]:
    return [] if ctx.profil is None else [r for r in ctx.profil.relations if r.confiance == "normale"]


def _somme_lignes(c: Cellule, ctx: _Contexte) -> str | None:
    valeur = nombre(c.valeur)
    if ctx.profil is None or valeur is None or valeur == 0:
        return None
    for r in _relations(ctx):
        if r.table_cible != c.table or r.table_source == c.table:
            continue
        cle = c.ligne.get(r.colonne_cible)
        enfants = [
            e for e in ctx.inserees.get(r.table_source, [])
            if cle is not None and normaliser_valeur(e.get(r.colonne_source)) == normaliser_valeur(cle)
        ]
        if not enfants:
            continue
        for colonne in enfants[0]:
            if colonne == r.colonne_source:
                continue
            montants = [nombre(e.get(colonne)) for e in enfants]
            if all(m is not None for m in montants) and sum(m for m in montants if m is not None) == valeur:
                return f"somme de {r.table_source}.{colonne} ({len(enfants)} lignes liées)"
    return None


def _copie(c: Cellule, ctx: _Contexte) -> str | None:
    if ctx.profil is None or c.valeur is None:
        return None
    for r in _relations(ctx):
        if r.table_source != c.table or r.table_cible == c.table:
            continue
        reference = ctx.ligne_avant(r.table_cible, r.colonne_cible, c.ligne.get(r.colonne_source))
        if reference is None:
            continue
        for colonne, autre in reference.items():
            if colonne != r.colonne_cible and normaliser_valeur(autre) == normaliser_valeur(c.valeur):
                return (f"copie de {r.table_cible}.{colonne} "
                        f"(ligne {r.colonne_cible} = {_fmt(c.ligne.get(r.colonne_source))})")
    return None


def _constante(c: Cellule, ctx: _Contexte) -> str | None:
    if ctx.profil is None or c.valeur is None:
        return None
    table = next((t for t in ctx.profil.tables if t.nom == c.table), None)
    if table is None or table.nb_lignes < 2:
        return None
    colonne = next((x for x in table.colonnes if x.nom == c.colonne), None)
    if colonne is None or colonne.nb_distincts != 1 or colonne.nb_nuls or colonne.min is None:
        return None
    try:
        egale = cle_comparaison(colonne.min) == cle_comparaison(c.valeur)
    except TypeError:
        return None
    return f"valeur constante sur toute la table ({_fmt(c.valeur)})" if egale else None


def _cumul(c: Cellule, ctx: _Contexte) -> str | None:
    avant, apres = nombre(c.avant), nombre(c.valeur)
    if c.est_insertion or avant is None or apres is None or apres == avant:
        return None
    delta = apres - avant
    for saisie, montant in ctx.montants_saisis:
        if delta == montant:
            return f"delta {_fmt(delta)} = montant saisi {saisie.champ_ecran} ({saisie.valeur})"
        if delta == -montant:
            return f"delta {_fmt(delta)} = opposé du montant saisi {saisie.champ_ecran} ({saisie.valeur})"
    return None


_TESTS: dict[str, Callable[[Cellule, _Contexte], str | None]] = {
    "compteur": _compteur,
    "horodatage_systeme": _horodatage,
    "somme_lignes": _somme_lignes,
    "copie": _copie,
    "constante": _constante,
    "cumul_mis_a_jour": _cumul,
}


def detecter_champs_calcules(
    diff: ResultatDiff,
    cellules: Sequence[Cellule],
    expliquees: set[tuple[str, int, str]],
    avant: Instantane,
    apres: Instantane,
    saisies: Sequence[ValeurSaisie],
    debut: datetime,
    fin: datetime,
    profil: Profil | None,
    avertissements: list[Avertissement],
) -> list[ChampCalcule]:
    """Hypothèses pour chaque cellule non nulle non expliquée par F6 (TODO(AMB-022) : détails)."""
    if profil is None:
        avertissements.append(
            Avertissement(
                None,
                "profil_absent",
                "Profil absent : les hypothèses " + ", ".join(HYPOTHESES_DU_PROFIL)
                + " sont désactivées. Lancer le profilage de la base.",
                {"hypotheses_desactivees": list(HYPOTHESES_DU_PROFIL)},
            )
        )
    montants = [
        (s, m) for s in saisies if s.type == "montant" and (m := analyser_montant(s.valeur)) is not None
    ]
    ctx = _Contexte(diff, avant, apres, debut, fin, profil, montants, cellules)
    ctx.inserees = lignes_inserees(diff)
    for c in cellules:
        a, b = nombre(c.avant), nombre(c.valeur)
        if not c.est_insertion and a is not None and b is not None:
            ctx.deltas.setdefault((c.table, c.colonne), []).append(b - a)
    resultats: list[ChampCalcule] = []
    vus: set[tuple[str, str, str, tuple[str, ...], str]] = set()
    for c in cellules:
        if c.ref in expliquees or c.valeur is None:
            continue
        trouvees = [(h, d) for h in HYPOTHESES if (d := _TESTS[h](c, ctx)) is not None]
        hypotheses: tuple[str, ...]
        if not trouvees:
            hypotheses, details = ("inconnu",), ""
        else:
            hypotheses = tuple(h for h, _ in trouvees)
            details = trouvees[0][1] if len(trouvees) == 1 else " ; ".join(f"{h} : {d}" for h, d in trouvees)
        cle = (c.table, c.colonne, normaliser_valeur(c.valeur), hypotheses, details)
        if cle not in vus:
            vus.add(cle)
            resultats.append(ChampCalcule(c.table, c.colonne, c.valeur, hypotheses, details))
    return resultats
