"""Champs calculés : hypothèses sur les valeurs non expliquées par F6 (F7, SPEC §7.2).

Chaque résultat est une **hypothèse**, jamais une règle. Aucune autre heuristique que celles
de la SPEC (§7.3). Détails : AMB-022 (validée).
"""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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
    "cumul_hierarchique",
)
HYPOTHESES_DU_PROFIL = ("somme_lignes", "copie", "constante")  # désactivées sans profil (AMB-010)
MARGE_HORODATAGE = timedelta(minutes=2)  # AMB-022 : écart d'horloge poste / serveur
_SUFFIXE = re.compile(r"^(.*?)(\d+)$", re.DOTALL)
_MONTANT_TEXTE = re.compile(r"^-?\d+[.,]\d+$")  # AMB-041.3 : un montant écrit en texte n'est pas un code

# AMB-041.2 : tables parasites d'Access, jamais prises comme source d'une `copie` (motifs `*` acceptés).
TABLES_IGNOREES_ANALYSE_DEFAUT = ("Table des erreurs", "Erreurs de conversion*")

# AMB-041.4 / R-003 (CARTE_ECRANS §16) : cumul stocké sur le compte et sur ses comptes parents.
TABLES_CUMUL_HIERARCHIQUE = ("compte", "scompte")
COLONNE_COMPTE = "Compte"
COLONNE_PERIODE = "Mois"
LONGUEUR_MIN_COMPTE_PARENT = 2  # jamais le niveau classe (1 caractère)


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
    tables_ignorees_analyse: Sequence[str] = TABLES_IGNOREES_ANALYSE_DEFAUT
    inserees: dict[str, list[Mapping[str, Any]]] = field(default_factory=dict)
    deltas: dict[tuple[str, str], list[Decimal]] = field(default_factory=dict)
    cumuls: dict[tuple[str, str, str | None], list[tuple[str, Decimal]]] = field(default_factory=dict)
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


def est_valeur_triviale(valeur: Any) -> bool:
    """Vide, blanche ou nulle (0, 0.0000) : trouvée dans n'importe quelle table, donc sans valeur de preuve."""
    if valeur is None:
        return True
    if isinstance(valeur, str):
        return not valeur.strip()
    nb = nombre(valeur)
    return nb is not None and nb == 0


def table_ignoree_pour_analyse(table: str, motifs: Sequence[str]) -> bool:
    """`table` correspond-elle à un motif de `tables_ignorees_analyse` (casse ignorée, `*` accepté) ?"""
    nom = table.casefold()
    return any(fnmatch.fnmatchcase(nom, motif.casefold()) for motif in motifs)


def _entier(valeur: Any) -> Decimal | None:
    """Valeur d'une colonne entière seulement : un Decimal, un flottant ou un texte n'en sont pas (AMB-041.3)."""
    if isinstance(valeur, int) and not isinstance(valeur, bool):
        return Decimal(valeur)
    return None


def _fmt(valeur: Any) -> str:
    return format(valeur, "f") if isinstance(valeur, Decimal) else str(valeur)


def _pas(valeurs: Sequence[Decimal]) -> Decimal:
    """Pas constant entre les valeurs distinctes triées d'avant, sinon 1 (AMB-022)."""
    triees = sorted(set(valeurs))
    ecarts = {b - a for a, b in zip(triees, triees[1:])}
    return ecarts.pop() if len(ecarts) == 1 and next(iter(ecarts), 0) > 0 else Decimal(1)


def _decouper(valeur: Any) -> tuple[str, str] | None:
    if not isinstance(valeur, str) or _MONTANT_TEXTE.match(valeur.strip()):
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
        valeur = _entier(c.valeur)
        if valeur is not None:
            nombres = [x for x in map(_entier, avant) if x is not None]
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
    avant_v, apres_v = _entier(c.avant), _entier(c.valeur)
    if avant_v is not None and apres_v is not None:
        delta = apres_v - avant_v
    elif nombre(c.avant) is not None or nombre(c.valeur) is not None:
        return None  # montant ou flottant : jamais un compteur (AMB-041.3)
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
    debut, fin = ctx.debut - MARGE_HORODATAGE, ctx.fin + MARGE_HORODATAGE
    if isinstance(v, datetime) and (v.hour, v.minute, v.second, v.microsecond) != (0, 0, 0, 0):
        dans = debut <= v <= fin
    elif isinstance(v, datetime):
        dans = debut.date() <= v.date() <= fin.date()
    elif isinstance(v, date):
        dans = debut.date() <= v <= fin.date()
    else:
        return None
    if not dans:
        return None
    return f"{v.isoformat()} dans [{ctx.debut.isoformat()}, {ctx.fin.isoformat()}] ±2 min"


def _relations(ctx: _Contexte) -> list[RelationCandidate]:
    """Relations utilisables : confiance `normale` uniquement (AMB-022 : `faible` exclue)."""
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
    if ctx.profil is None or est_valeur_triviale(c.valeur):  # AMB-041.2
        return None
    for r in _relations(ctx):
        if r.table_source != c.table or r.table_cible == c.table:
            continue
        if table_ignoree_pour_analyse(r.table_cible, ctx.tables_ignorees_analyse):
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


def _compte(ligne: Mapping[str, Any]) -> str | None:
    valeur = ligne.get(COLONNE_COMPTE)
    return valeur.rstrip(" ") if isinstance(valeur, str) and valeur.strip() else None


def _indexer_cumuls(cellules: Sequence[Cellule]) -> dict[tuple[str, str, str | None], list[tuple[str, Decimal]]]:
    """Variations numériques des tables de cumul par (table, colonne, période) : [(compte, delta)]."""
    index: dict[tuple[str, str, str | None], list[tuple[str, Decimal]]] = {}
    for c in cellules:
        if c.table.casefold() not in TABLES_CUMUL_HIERARCHIQUE or c.colonne in (COLONNE_COMPTE, COLONNE_PERIODE):
            continue
        compte = _compte(c.ligne)
        apres = nombre(c.valeur)
        if compte is None or apres is None:
            continue
        avant = Decimal(0) if c.est_insertion else nombre(c.avant)
        if avant is None or apres == avant:
            continue
        periode = c.ligne.get(COLONNE_PERIODE)
        cle = (c.table.casefold(), c.colonne, None if periode is None else str(periode).rstrip(" "))
        index.setdefault(cle, []).append((compte, apres - avant))
    return index


def _cumul_hierarchique(c: Cellule, ctx: _Contexte) -> str | None:
    """Même variation sur un compte et sur ses comptes parents (R-003) ; jamais le niveau classe."""
    if c.table.casefold() not in TABLES_CUMUL_HIERARCHIQUE or c.colonne in (COLONNE_COMPTE, COLONNE_PERIODE):
        return None
    compte, apres = _compte(c.ligne), nombre(c.valeur)
    if compte is None or apres is None or len(compte) < LONGUEUR_MIN_COMPTE_PARENT:
        return None
    avant = Decimal(0) if c.est_insertion else nombre(c.avant)
    if avant is None or apres == avant:
        return None
    delta = apres - avant
    periode = c.ligne.get(COLONNE_PERIODE)
    cle = (c.table.casefold(), c.colonne, None if periode is None else str(periode).rstrip(" "))
    liees = sorted(
        {b for b, d in ctx.cumuls.get(cle, [])
         if d == delta and b != compte and len(b) >= LONGUEUR_MIN_COMPTE_PARENT
         and (b.startswith(compte) or compte.startswith(b))},
        key=lambda x: (len(x), x),
    )
    if not liees:
        return None
    chaine = sorted({compte, *liees}, key=lambda x: (len(x), x))
    return f"delta {_fmt(delta)} identique sur {len(chaine)} comptes liés par préfixe : {', '.join(chaine)}"


_TESTS: dict[str, Callable[[Cellule, _Contexte], str | None]] = {
    "compteur": _compteur,
    "horodatage_systeme": _horodatage,
    "somme_lignes": _somme_lignes,
    "copie": _copie,
    "constante": _constante,
    "cumul_mis_a_jour": _cumul,
    "cumul_hierarchique": _cumul_hierarchique,
}


def _contexte(
    diff: ResultatDiff,
    avant: Instantane,
    apres: Instantane,
    saisies: Sequence[ValeurSaisie],
    debut: datetime,
    fin: datetime,
    profil: Profil | None,
    cellules: Sequence[Cellule],
    tables_ignorees_analyse: Sequence[str],
) -> _Contexte:
    montants = [
        (s, m) for s in saisies if s.type == "montant" and (m := analyser_montant(s.valeur)) is not None
    ]
    ctx = _Contexte(diff, avant, apres, debut, fin, profil, montants, cellules, tuple(tables_ignorees_analyse))
    ctx.inserees = lignes_inserees(diff)
    ctx.cumuls = _indexer_cumuls(cellules)
    for c in cellules:
        a, b = nombre(c.avant), nombre(c.valeur)
        if not c.est_insertion and a is not None and b is not None:
            ctx.deltas.setdefault((c.table, c.colonne), []).append(b - a)
    return ctx


def _evaluer(
    cellules: Sequence[Cellule],
    expliquees: set[tuple[str, int, str]],
    ctx: _Contexte,
    reprises: Callable[[Cellule], list[tuple[str, str]]] | None = None,
) -> list[ChampCalcule]:
    """Teste les hypothèses sur chaque cellule non expliquée. `reprises` (réanalyse hors ligne) fournit
    les hypothèses de l'original que la trace seule ne permet pas de recalculer."""
    resultats: list[ChampCalcule] = []
    vus: set[tuple[str, str, str, tuple[str, ...], str]] = set()
    for c in cellules:
        if c.ref in expliquees or c.valeur is None:
            continue
        trouvees = [(h, d) for h in HYPOTHESES if (d := _TESTS[h](c, ctx)) is not None]
        if reprises is not None:
            deja = {h for h, _ in trouvees}
            trouvees += [(h, d) for h, d in reprises(c) if h not in deja]
            trouvees.sort(key=lambda hd: HYPOTHESES.index(hd[0]))
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
    tables_ignorees_analyse: Sequence[str] = TABLES_IGNOREES_ANALYSE_DEFAUT,
) -> list[ChampCalcule]:
    """Hypothèses pour chaque cellule non nulle non expliquée par F6 (détails : AMB-022)."""
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
    ctx = _contexte(diff, avant, apres, saisies, debut, fin, profil, cellules, tables_ignorees_analyse)
    return _evaluer(cellules, expliquees, ctx)


# --- Réanalyse hors ligne d'un trace.json (AMB-042) ------------------------------------------------

HYPOTHESES_NON_RECALCULABLES = ("compteur", "somme_lignes", "copie", "constante")
_COPIE_DE = re.compile(r"^copie de (?P<table>.+)\.(?P<colonne>[^.]+) \(ligne ", re.DOTALL)


def hypotheses_de_l_original(champ: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(hypothèse, détail) d'un `champs_calcules[]` de trace.json (détails séparés par « ; »)."""
    hypotheses = [h for h in champ.get("hypotheses", []) if h in HYPOTHESES]
    details = str(champ.get("details", ""))
    if len(hypotheses) == 1:
        return [(hypotheses[0], details)]
    morceaux: dict[str, str] = {}
    for morceau in details.split(" ; "):
        nom, separateur, reste = morceau.partition(" : ")
        if separateur and nom in hypotheses:
            morceaux[nom] = reste
    return [(h, morceaux.get(h, "")) for h in hypotheses]


def reprise_admise(hypothese: str, detail: str, c: Cellule, tables_ignorees_analyse: Sequence[str]) -> bool:
    """Une hypothèse de l'original reprise hors ligne est filtrée par les règles courantes (AMB-041)."""
    if hypothese == "copie":
        if est_valeur_triviale(c.valeur):
            return False
        m = _COPIE_DE.match(detail)
        return not (m and table_ignoree_pour_analyse(m.group("table"), tables_ignorees_analyse))
    if hypothese == "compteur":
        return _entier(c.valeur) is not None or _decouper(c.valeur) is not None
    return hypothese in HYPOTHESES_NON_RECALCULABLES


def detecter_champs_calcules_hors_ligne(
    cellules: Sequence[Cellule],
    expliquees: set[tuple[str, int, str]],
    saisies: Sequence[ValeurSaisie],
    debut: datetime,
    fin: datetime,
    originaux: Sequence[Mapping[str, Any]],
    tables_ignorees_analyse: Sequence[str],
    avertissements: list[Avertissement],
) -> list[ChampCalcule]:
    """Recalcule les hypothèses sans accès à la base.

    Recalculables : `horodatage_systeme`, `cumul_mis_a_jour`, `cumul_hierarchique` et `compteur` d'une ligne
    modifiée. Les autres (`compteur` d'une insertion, `copie`, `constante`, `somme_lignes`) exigent la photo
    ou le profil : elles sont reprises de l'original, filtrées par les règles courantes, avec un avertissement
    « non recalculable hors ligne ».
    """
    ctx = _contexte(ResultatDiff(), Instantane(), Instantane(), saisies, debut, fin, None, cellules,
                    tables_ignorees_analyse)
    index: dict[tuple[str, str, str], list[tuple[str, str]]] = {}
    for champ in originaux:
        cle = (str(champ.get("table")), str(champ.get("colonne")), json.dumps(champ.get("valeur"), sort_keys=True))
        index.setdefault(cle, []).extend(
            (h, d) for h, d in hypotheses_de_l_original(champ) if h in HYPOTHESES_NON_RECALCULABLES)
    signales: set[tuple[str, str, str]] = set()

    def reprises(c: Cellule) -> list[tuple[str, str]]:
        cle = (c.table, c.colonne, json.dumps(valeur_json(c.valeur), sort_keys=True))
        reprises_cellule: list[tuple[str, str]] = []
        for h, d in index.get(cle, []):
            if h == "compteur" and not c.est_insertion:
                continue  # recalculé à partir de avant → après
            if not reprise_admise(h, d, c, tables_ignorees_analyse):
                continue
            reprises_cellule.append((h, d))
            if (h, c.table, c.colonne) not in signales:
                signales.add((h, c.table, c.colonne))
                avertissements.append(Avertissement(
                    c.table, "non_recalculable_hors_ligne",
                    f"Hypothèse « {h} » sur {c.table}.{c.colonne} : non recalculable hors ligne, "
                    "reprise de la trace d'origine (filtrée par les règles courantes).",
                    {"colonne": c.colonne, "hypothese": h}))
        return reprises_cellule

    return _evaluer(cellules, expliquees, ctx, reprises)
