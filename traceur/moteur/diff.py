"""Comparaison de deux instantanés (F5, SPEC §6.3). Format de sortie : `trace.example.json`."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .instantane import Instantane, Ligne, TableInstantane
from .normalisation import normaliser_valeur, valeur_json

# Nombre maximal de paires ajoutée/supprimée comparées pour `update_probable`.
LIMITE_APPARIEMENT = 1_000_000  # TODO(AMB-013)
ECART_MAX_UPDATE_PROBABLE = 2


@dataclass(frozen=True)
class ChampModifie:
    colonne: str
    avant: Any
    apres: Any


@dataclass(frozen=True)
class LigneCle:
    cle: dict[str, Any]
    valeurs: dict[str, Any]


@dataclass(frozen=True)
class UpdateCle:
    cle: dict[str, Any]
    champs: list[ChampModifie]


@dataclass(frozen=True)
class UpdateProbable:
    avant: dict[str, Any]
    apres: dict[str, Any]
    champs: list[ChampModifie]


@dataclass
class DiffTable:
    table: str
    type_cle: str  # "primaire" | "candidate" | "aucune"
    colonnes_cle: tuple[str, ...]
    inserts: list[LigneCle] = field(default_factory=list)
    updates: list[UpdateCle] = field(default_factory=list)
    deletes: list[LigneCle] = field(default_factory=list)
    lignes_ajoutees: list[dict[str, Any]] = field(default_factory=list)
    lignes_supprimees: list[dict[str, Any]] = field(default_factory=list)
    updates_probables: list[UpdateProbable] = field(default_factory=list)

    @property
    def nb_changements(self) -> int:
        return (
            len(self.inserts) + len(self.updates) + len(self.deletes)
            + len(self.lignes_ajoutees) + len(self.lignes_supprimees)
            + len(self.updates_probables)
        )

    def vers_dict(self) -> dict[str, Any]:
        resultat: dict[str, Any] = {
            "table": self.table,
            "cle_utilisee": {"type": self.type_cle, "colonnes": list(self.colonnes_cle)},
        }
        if self.type_cle == "aucune":
            resultat["lignes_ajoutees"] = [{"valeurs": _json(v)} for v in self.lignes_ajoutees]
            resultat["lignes_supprimees"] = [
                {"valeurs": _json(v)} for v in self.lignes_supprimees
            ]
        else:
            resultat["inserts"] = [
                {"cle": _json(i.cle), "valeurs": _json(i.valeurs)} for i in self.inserts
            ]
            resultat["updates"] = [
                {"cle": _json(u.cle), "champs": [_champ_json(c) for c in u.champs]}
                for u in self.updates
            ]
            resultat["deletes"] = [
                {"cle": _json(d.cle), "valeurs": _json(d.valeurs)} for d in self.deletes
            ]
        resultat["updates_probables"] = [
            {
                "avant": _json(u.avant),
                "apres": _json(u.apres),
                "champs": [_champ_json(c) for c in u.champs],
            }
            for u in self.updates_probables
        ]
        return resultat


@dataclass(frozen=True)
class SchemaModifie:
    table: str
    nature: str  # "colonnes_modifiees" | "table_ajoutee" | "table_supprimee"
    avant: list[dict[str, str]] | None
    apres: list[dict[str, str]] | None

    def vers_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "nature": self.nature,
            "avant": self.avant,
            "apres": self.apres,
        }


@dataclass
class ResultatDiff:
    changements: list[DiffTable] = field(default_factory=list)
    schema_modifie: list[SchemaModifie] = field(default_factory=list)

    def vers_dict(self) -> dict[str, Any]:
        return {
            "changements": [c.vers_dict() for c in self.changements],
            "schema_modifie": [s.vers_dict() for s in self.schema_modifie],
        }


def _json(valeurs: Mapping[str, Any]) -> dict[str, Any]:
    return {k: valeur_json(v) for k, v in valeurs.items()}


def _champ_json(champ: ChampModifie) -> dict[str, Any]:
    return {
        "colonne": champ.colonne,
        "avant": valeur_json(champ.avant),
        "apres": valeur_json(champ.apres),
    }


def _description_schema(table: TableInstantane) -> list[dict[str, str]]:
    return [{"nom": c.nom, "type": c.type_declare} for c in table.schema.colonnes]


def _signature_schema(table: TableInstantane) -> tuple[Any, ...]:
    return (table.schema.colonnes, table.schema.cle_primaire)


def _en_dict(noms: Sequence[str], ligne: Ligne) -> dict[str, Any]:
    return dict(zip(noms, ligne.valeurs))


def _champs_differents(
    noms: Sequence[str], avant: Ligne, apres: Ligne
) -> list[ChampModifie]:
    return [
        ChampModifie(nom, a, b)
        for nom, a, b in zip(noms, avant.valeurs, apres.valeurs)
        if normaliser_valeur(a) != normaliser_valeur(b)
    ]


def _indexer(
    table: TableInstantane, indices: Sequence[int]
) -> dict[tuple[str, ...], Ligne] | None:
    """Index par clé ; None si la clé n'est pas unique (repli sur les multiensembles)."""
    index: dict[tuple[str, ...], Ligne] = {}
    for ligne in table.lignes:
        cle = tuple(normaliser_valeur(ligne.valeurs[i]) for i in indices)
        if cle in index:
            return None
        index[cle] = ligne
    return index


def _diff_avec_cle(
    avant: TableInstantane,
    apres: TableInstantane,
    type_cle: str,
    colonnes_cle: tuple[str, ...],
) -> DiffTable | None:
    noms = apres.schema.noms()
    indices = [noms.index(c) for c in colonnes_cle]
    index_avant = _indexer(avant, indices)
    index_apres = _indexer(apres, indices)
    if index_avant is None or index_apres is None:
        return None
    diff = DiffTable(apres.nom, type_cle, colonnes_cle)
    for cle, ligne in index_apres.items():
        ancienne = index_avant.get(cle)
        cle_dict = {c: ligne.valeurs[i] for c, i in zip(colonnes_cle, indices)}
        if ancienne is None:
            diff.inserts.append(LigneCle(cle_dict, _en_dict(noms, ligne)))
        elif ancienne.empreinte != ligne.empreinte:
            diff.updates.append(UpdateCle(cle_dict, _champs_differents(noms, ancienne, ligne)))
    for cle, ligne in index_avant.items():
        if cle not in index_apres:
            cle_dict = {c: ligne.valeurs[i] for c, i in zip(colonnes_cle, indices)}
            diff.deletes.append(LigneCle(cle_dict, _en_dict(noms, ligne)))
    return diff


def _diff_multiensembles(avant: TableInstantane, apres: TableInstantane) -> DiffTable:
    noms = apres.schema.noms()
    diff = DiffTable(apres.nom, "aucune", ())
    restant_avant = Counter(ligne.empreinte for ligne in avant.lignes)
    ajoutees: list[Ligne] = []
    for ligne in apres.lignes:
        if restant_avant[ligne.empreinte] > 0:
            restant_avant[ligne.empreinte] -= 1
        else:
            ajoutees.append(ligne)
    restant_apres = Counter(ligne.empreinte for ligne in apres.lignes)
    supprimees: list[Ligne] = []
    for ligne in avant.lignes:
        if restant_apres[ligne.empreinte] > 0:
            restant_apres[ligne.empreinte] -= 1
        else:
            supprimees.append(ligne)
    ajoutees, supprimees = _apparier(noms, ajoutees, supprimees, diff)
    diff.lignes_ajoutees = [_en_dict(noms, ligne) for ligne in ajoutees]
    diff.lignes_supprimees = [_en_dict(noms, ligne) for ligne in supprimees]
    return diff


def _apparier(
    noms: Sequence[str],
    ajoutees: list[Ligne],
    supprimees: list[Ligne],
    diff: DiffTable,
) -> tuple[list[Ligne], list[Ligne]]:
    """Apparie ajoutée/supprimée différant d'au plus 2 champs (glouton, déterministe).

    TODO(AMB-013) : algorithme, retrait des lignes appariées et plafond à confirmer.
    """
    if len(ajoutees) * len(supprimees) > LIMITE_APPARIEMENT:
        return ajoutees, supprimees
    normalisees = {
        id(ligne): tuple(normaliser_valeur(v) for v in ligne.valeurs)
        for ligne in (*ajoutees, *supprimees)
    }
    libres = list(supprimees)
    ajoutees_restantes: list[Ligne] = []
    for ajoutee in ajoutees:
        meilleure: int | None = None
        meilleur_ecart = ECART_MAX_UPDATE_PROBABLE + 1
        na = normalisees[id(ajoutee)]
        for position, candidate in enumerate(libres):
            nc = normalisees[id(candidate)]
            ecart = sum(1 for x, y in zip(na, nc) if x != y)
            if ecart < meilleur_ecart:
                meilleure, meilleur_ecart = position, ecart
                if ecart == 1:
                    break
        if meilleure is None:
            ajoutees_restantes.append(ajoutee)
            continue
        ancienne = libres.pop(meilleure)
        diff.updates_probables.append(
            UpdateProbable(
                _en_dict(noms, ancienne),
                _en_dict(noms, ajoutee),
                _champs_differents(noms, ancienne, ajoutee),
            )
        )
    return ajoutees_restantes, libres


def _diff_table(
    avant: TableInstantane,
    apres: TableInstantane,
    cle_candidate: Sequence[str] | None,
) -> DiffTable:
    noms = set(apres.schema.noms())
    if apres.schema.cle_primaire:
        resultat = _diff_avec_cle(avant, apres, "primaire", apres.schema.cle_primaire)
        if resultat is not None:
            return resultat
    elif cle_candidate and set(cle_candidate) <= noms:
        resultat = _diff_avec_cle(avant, apres, "candidate", tuple(cle_candidate))
        if resultat is not None:
            return resultat
    return _diff_multiensembles(avant, apres)


def comparer_instantanes(
    avant: Instantane,
    apres: Instantane,
    cles_candidates: Mapping[str, Sequence[str]] | None = None,
) -> ResultatDiff:
    """Compare deux photos. `cles_candidates` (table -> colonnes) viendra du profilage (J2)."""
    cles_candidates = cles_candidates or {}
    resultat = ResultatDiff()
    for nom, table_apres in apres.tables.items():
        table_avant = avant.tables.get(nom)
        if table_avant is None:
            # TODO(AMB-011) : table ajoutée, signalée sans diff de lignes.
            resultat.schema_modifie.append(
                SchemaModifie(nom, "table_ajoutee", None, _description_schema(table_apres))
            )
            continue
        if _signature_schema(table_avant) != _signature_schema(table_apres):
            # TODO(AMB-012) : pas de diff de lignes quand le schéma a changé.
            resultat.schema_modifie.append(
                SchemaModifie(
                    nom,
                    "colonnes_modifiees",
                    _description_schema(table_avant),
                    _description_schema(table_apres),
                )
            )
            continue
        if (
            table_avant.empreinte == table_apres.empreinte
            and table_avant.nb_lignes == table_apres.nb_lignes
        ):
            continue
        diff = _diff_table(table_avant, table_apres, cles_candidates.get(nom))
        if diff.nb_changements:
            resultat.changements.append(diff)
    for nom, table_avant in avant.tables.items():
        if nom not in apres.tables:
            # TODO(AMB-011) : table supprimée, signalée sans diff de lignes.
            resultat.schema_modifie.append(
                SchemaModifie(nom, "table_supprimee", _description_schema(table_avant), None)
            )
    return resultat
