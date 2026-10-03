"""Profilage initial de la base (F2, SPEC §6.4) : statistiques, clés et relations candidates."""

from __future__ import annotations

import time
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from itertools import combinations
from typing import Any, Callable, Collection, Hashable, Mapping

from .normalisation import valeur_json
from .source import SourceDonnees

SEUIL_INCLUSION = Decimal("0.99")
NB_LIGNES_MIN_CLE = 2  # TODO(AMB-015) : seuil minimal provisoire
_DEUX_DECIMALES = Decimal("0.01")
_QUATRE_DECIMALES = Decimal("0.0001")


def famille(valeur: Any) -> str:
    """Famille de types servant à décider de la compatibilité (SPEC §6.4)."""
    if isinstance(valeur, bool):
        return "booleen"
    if isinstance(valeur, (int, Decimal, float)):
        return "numerique"
    if isinstance(valeur, str):
        return "texte"
    if isinstance(valeur, (date, datetime)):
        return "date"
    if isinstance(valeur, (bytes, bytearray, memoryview)):
        return "binaire"
    raise TypeError(f"Type de valeur non géré : {type(valeur).__name__}")


def cle_comparaison(valeur: Any) -> Hashable:
    """Valeur comparable à travers les types d'une même famille (1 == 1.0 == Decimal('1.00'))."""
    f = famille(valeur)
    if f == "numerique":
        if isinstance(valeur, float):
            return Decimal(repr(valeur))
        return Decimal(valeur)
    if f == "texte":
        return unicodedata.normalize("NFC", valeur)
    if f == "date":
        if isinstance(valeur, datetime):
            return valeur
        return datetime(valeur.year, valeur.month, valeur.day)
    if f == "binaire":
        return bytes(valeur)
    return bool(valeur)


@dataclass(frozen=True)
class ColonneProfil:
    nom: str
    type_declare: str
    types_observes: tuple[str, ...]
    nb_nuls: int
    pct_nuls: Decimal
    nb_distincts: int
    min: Any
    max: Any


@dataclass(frozen=True)
class TableProfil:
    nom: str
    nb_lignes: int
    cle_primaire: tuple[str, ...]
    colonnes: tuple[ColonneProfil, ...]
    cles_candidates: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class RelationCandidate:
    table_source: str
    colonne_source: str
    table_cible: str
    colonne_cible: str
    taux_inclusion: Decimal
    nb_valeurs: int
    nb_incluses: int


@dataclass
class Profil:
    date: datetime
    version_jet: str | None
    tables: list[TableProfil] = field(default_factory=list)
    relations: list[RelationCandidate] = field(default_factory=list)
    duree_s: float = 0.0

    def table(self, nom: str) -> TableProfil:
        return next(t for t in self.tables if t.nom == nom)

    def vers_dict(self) -> dict[str, Any]:
        return {
            "format_version": "1.0",
            "date": self.date.isoformat(timespec="seconds"),
            "version_jet": self.version_jet,
            "tables": [
                {
                    "nom": t.nom,
                    "nb_lignes": t.nb_lignes,
                    "cle_primaire": list(t.cle_primaire),
                    "cles_candidates": [list(c) for c in t.cles_candidates],
                    "colonnes": [
                        {
                            "nom": c.nom,
                            "type_declare": c.type_declare,
                            "types_observes": list(c.types_observes),
                            "nb_nuls": c.nb_nuls,
                            "pct_nuls": format(c.pct_nuls, "f"),
                            "nb_distincts": c.nb_distincts,
                            "min": valeur_json(c.min),
                            "max": valeur_json(c.max),
                        }
                        for c in t.colonnes
                    ],
                }
                for t in self.tables
            ],
            "relations_candidates": [
                {
                    "table_source": r.table_source,
                    "colonne_source": r.colonne_source,
                    "table_cible": r.table_cible,
                    "colonne_cible": r.colonne_cible,
                    "taux_inclusion": format(r.taux_inclusion, "f"),
                    "nb_valeurs": r.nb_valeurs,
                    "nb_incluses": r.nb_incluses,
                }
                for r in self.relations
            ],
        }


class _Accumulateur:
    """Statistiques d'une colonne, calculées en une passe."""

    def __init__(self) -> None:
        self.cles: list[Hashable | None] = []
        self.compteur: Counter[Hashable] = Counter()
        self.nb_nuls = 0
        self.familles: set[str] = set()
        self.types: set[str] = set()
        self.ordre_valide = True
        self.minimum: tuple[Hashable, Any] | None = None
        self.maximum: tuple[Hashable, Any] | None = None

    def ajouter(self, valeur: Any) -> None:
        if valeur is None:
            self.nb_nuls += 1
            self.cles.append(None)
            return
        cle = cle_comparaison(valeur)
        self.cles.append(cle)
        self.compteur[cle] += 1
        self.familles.add(famille(valeur))
        self.types.add(type(valeur).__name__)
        if not self.ordre_valide:
            return
        try:
            if self.minimum is None or cle < self.minimum[0]:  # type: ignore[operator]
                self.minimum = (cle, valeur)
            if self.maximum is None or cle > self.maximum[0]:  # type: ignore[operator]
                self.maximum = (cle, valeur)
        except (TypeError, ArithmeticError):
            self.ordre_valide = False

    @property
    def nb_valeurs(self) -> int:
        return len(self.cles) - self.nb_nuls

    def bornes(self) -> tuple[Any, Any]:
        """Min/max seulement pour une famille ordonnée unique (pas de binaire, pas de mélange)."""
        if not self.ordre_valide or len(self.familles) != 1 or "binaire" in self.familles:
            return None, None
        if self.minimum is None or self.maximum is None:
            return None, None
        return self.minimum[1], self.maximum[1]


def _profiler_table(
    nom: str, source: SourceDonnees
) -> tuple[TableProfil, dict[str, _Accumulateur]]:
    schema = source.schema(nom)
    noms = schema.noms()
    acc = {n: _Accumulateur() for n in noms}
    nb_lignes = 0
    for ligne in source.lire_lignes(nom):
        nb_lignes += 1
        for n, valeur in zip(noms, ligne):
            acc[n].ajouter(valeur)
    colonnes = []
    for colonne in schema.colonnes:
        a = acc[colonne.nom]
        pct = (
            (Decimal(a.nb_nuls) * 100 / nb_lignes).quantize(_DEUX_DECIMALES)
            if nb_lignes
            else Decimal(0).quantize(_DEUX_DECIMALES)
        )
        minimum, maximum = a.bornes()
        colonnes.append(
            ColonneProfil(
                colonne.nom,
                colonne.type_declare,
                tuple(sorted(a.types)),
                a.nb_nuls,
                pct,
                len(a.compteur),
                minimum,
                maximum,
            )
        )
    table = TableProfil(
        nom, nb_lignes, schema.cle_primaire, tuple(colonnes), _cles_candidates(noms, acc, nb_lignes)
    )
    return table, acc


def _cles_candidates(
    noms: tuple[str, ...], acc: Mapping[str, _Accumulateur], nb_lignes: int
) -> tuple[tuple[str, ...], ...]:
    """Colonnes puis couples uniques et non nuls (SPEC §6.4)."""
    if nb_lignes < NB_LIGNES_MIN_CLE:  # TODO(AMB-015)
        return ()
    sans_nul = [n for n in noms if acc[n].nb_nuls == 0]
    simples = [n for n in sans_nul if len(acc[n].compteur) == nb_lignes]
    cles: list[tuple[str, ...]] = [(n,) for n in simples]
    restantes = [n for n in sans_nul if n not in simples]
    for a, b in combinations(restantes, 2):
        # Un couple ne peut être unique que si le produit des distincts atteint nb_lignes.
        if len(acc[a].compteur) * len(acc[b].compteur) < nb_lignes:
            continue
        if len(set(zip(acc[a].cles, acc[b].cles))) == nb_lignes:
            cles.append((a, b))
    return tuple(cles)


def _relations(
    tables: list[TableProfil], accs: Mapping[str, Mapping[str, _Accumulateur]]
) -> list[RelationCandidate]:
    """Colonne A incluse à ≥ 99 % dans une colonne clé candidate B, types compatibles."""
    cibles = [
        (t.nom, c[0], accs[t.nom][c[0]])
        for t in tables
        for c in t.cles_candidates
        if len(c) == 1
    ]
    relations: list[RelationCandidate] = []
    for t in tables:
        for colonne in t.colonnes:
            a = accs[t.nom][colonne.nom]
            if a.nb_valeurs == 0 or len(a.familles) != 1:
                continue
            for table_b, colonne_b, b in cibles:
                if (table_b, colonne_b) == (t.nom, colonne.nom) or a.familles != b.familles:
                    continue
                # TODO(AMB-017) : taux calculé sur les lignes non nulles (provisoire).
                incluses = sum(n for cle, n in a.compteur.items() if cle in b.compteur)
                taux = Decimal(incluses) / Decimal(a.nb_valeurs)
                if taux >= SEUIL_INCLUSION:
                    relations.append(
                        RelationCandidate(
                            t.nom,
                            colonne.nom,
                            table_b,
                            colonne_b,
                            taux.quantize(_QUATRE_DECIMALES),
                            a.nb_valeurs,
                            incluses,
                        )
                    )
    return relations


def profiler(
    source: SourceDonnees,
    tables_ignorees: Collection[str] = (),
    version_jet: str | None = None,
    maintenant: Callable[[], datetime] = datetime.now,
    horloge: Callable[[], float] = time.perf_counter,
) -> Profil:
    """Profile toutes les tables non ignorées. `version_jet` est affichée dans le profil."""
    debut = horloge()
    ignorees = {n.lower() for n in tables_ignorees}
    profil = Profil(maintenant(), version_jet)
    accs: dict[str, Mapping[str, _Accumulateur]] = {}
    for nom in source.lister_tables():
        if nom.lower() in ignorees:
            continue
        table, acc = _profiler_table(nom, source)
        profil.tables.append(table)
        accs[nom] = acc
    profil.relations = _relations(profil.tables, accs)
    profil.duree_s = horloge() - debut
    return profil


def cles_candidates_du_profil(profil: Profil) -> dict[str, tuple[str, ...]]:
    """Clé candidate par table sans clé primaire, pour `comparer_instantanes` (SPEC §6.3).

    TODO(AMB-014) : parmi plusieurs candidates, le moins de colonnes puis la première
    dans l'ordre des colonnes (provisoire).
    """
    return {
        t.nom: min(t.cles_candidates, key=len)
        for t in profil.tables
        if not t.cle_primaire and t.cles_candidates
    }
