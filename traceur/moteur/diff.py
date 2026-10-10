"""Comparaison de deux instantanés (F5, SPEC §6.3). Format de sortie : `trace.example.json`."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Collection, Mapping, Sequence

from .instantane import Instantane, Ligne, TableInstantane
from .normalisation import empreinte_ligne, empreinte_table, normaliser_valeur, valeur_json
from .source import SchemaTable

SEUIL_PETITE_TABLE = 50  # AMB-037 : sous ce nombre de lignes, une clé candidate du profil est peu fiable

# Nombre maximal de paires ajoutée/supprimée comparées pour `update_probable` (AMB-013).
LIMITE_APPARIEMENT = 1_000_000
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


@dataclass(frozen=True)
class Avertissement:
    table: str | None
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def vers_dict(self) -> dict[str, Any]:
        return {"table": self.table, "code": self.code, "message": self.message, **self.details}


@dataclass
class ResultatDiff:
    changements: list[DiffTable] = field(default_factory=list)
    schema_modifie: list[SchemaModifie] = field(default_factory=list)
    bruit: list[dict[str, str]] = field(default_factory=list)
    avertissements: list[Avertissement] = field(default_factory=list)

    def vers_dict(self) -> dict[str, Any]:
        return {
            "changements": [c.vers_dict() for c in self.changements],
            "schema_modifie": [s.vers_dict() for s in self.schema_modifie],
            "bruit": list(self.bruit),
            "avertissements": [a.vers_dict() for a in self.avertissements],
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


def _diff_multiensembles(
    avant: TableInstantane, apres: TableInstantane, avertissements: list[Avertissement]
) -> DiffTable:
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
    ajoutees, supprimees = _apparier(apres.nom, noms, ajoutees, supprimees, diff, avertissements)
    diff.lignes_ajoutees = [_en_dict(noms, ligne) for ligne in ajoutees]
    diff.lignes_supprimees = [_en_dict(noms, ligne) for ligne in supprimees]
    return diff


def _apparier(
    table: str,
    noms: Sequence[str],
    ajoutees: list[Ligne],
    supprimees: list[Ligne],
    diff: DiffTable,
    avertissements: list[Avertissement],
) -> tuple[list[Ligne], list[Ligne]]:
    """Apparie ajoutée/supprimée différant d'au plus 2 champs (glouton, déterministe, AMB-013).

    Au-delà de `LIMITE_APPARIEMENT` comparaisons, aucun appariement n'est tenté et un
    avertissement explicite est produit.
    """
    if len(ajoutees) * len(supprimees) > LIMITE_APPARIEMENT:
        avertissements.append(
            Avertissement(
                table,
                "appariement_plafond_atteint",
                f"Table {table} : trop de lignes ajoutées et supprimées pour chercher les "
                f"modifications probables (plafond de {LIMITE_APPARIEMENT} comparaisons). "
                f"{len(ajoutees)} lignes ajoutées et {len(supprimees)} lignes supprimées "
                "restent non appariées.",
                {
                    "lignes_ajoutees_non_appariees": len(ajoutees),
                    "lignes_supprimees_non_appariees": len(supprimees),
                },
            )
        )
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


def _avertir_petite_table(
    avant: TableInstantane, apres: TableInstantane, cle: tuple[str, ...], avertissements: list[Avertissement]
) -> None:
    """AMB-037 : une clé candidate issue d'une toute petite table peut n'être unique que par hasard."""
    nb_lignes = max(avant.nb_lignes, apres.nb_lignes)
    if nb_lignes >= SEUIL_PETITE_TABLE:
        return
    colonnes = ", ".join(cle)
    avertissements.append(
        Avertissement(
            apres.nom,
            "cle_candidate_petite_table",
            f"Table {apres.nom} ({nb_lignes} lignes) : la clé ({colonnes}) vient du profil et peut être "
            f"unique par hasard sur une si petite table ; une modification peut apparaître comme une "
            f"suppression et un ajout. À confirmer.",
            {"cle_candidate": list(cle), "nb_lignes": nb_lignes},
        )
    )


def _diff_table(
    avant: TableInstantane,
    apres: TableInstantane,
    cle_candidate: Sequence[str] | None,
    avertissements: list[Avertissement],
) -> DiffTable:
    noms = set(apres.schema.noms())
    if apres.schema.cle_primaire:
        resultat = _diff_avec_cle(avant, apres, "primaire", apres.schema.cle_primaire)
        if resultat is not None:
            return resultat
    elif cle_candidate and set(cle_candidate) <= noms:
        resultat = _diff_avec_cle(avant, apres, "candidate", tuple(cle_candidate))
        if resultat is not None:
            _avertir_petite_table(avant, apres, tuple(cle_candidate), avertissements)
            return resultat
    return _diff_multiensembles(avant, apres, avertissements)


def _table_vide(modele: TableInstantane) -> TableInstantane:
    return TableInstantane(modele.nom, modele.schema, 0, empreinte_table([]), [], 0.0)


def resume_table(diff: DiffTable) -> str:
    """Ex. « 1 ligne modifiée », « 2 lignes ajoutées, 1 ligne supprimée »."""

    def lignes(n: int, adjectif: str) -> str:
        return f"{n} ligne{'s' if n > 1 else ''} {adjectif}{'s' if n > 1 else ''}"

    compte = [
        (len(diff.inserts) + len(diff.lignes_ajoutees), "ajoutée"),
        (len(diff.updates) + len(diff.updates_probables), "modifiée"),
        (len(diff.deletes) + len(diff.lignes_supprimees), "supprimée"),
    ]
    return ", ".join(lignes(n, adj) for n, adj in compte if n)


def _resume_bruit(diff: DiffTable) -> str:
    return resume_table(diff) + " (ignorée : table de bruit)"


def _projeter(
    table: TableInstantane, communes: Sequence[str], cle_primaire: tuple[str, ...]
) -> TableInstantane:
    """Table restreinte aux colonnes communes (empreintes recalculées)."""
    noms = table.schema.noms()
    indices = [noms.index(c) for c in communes]
    lignes = []
    for ligne in table.lignes:
        valeurs = tuple(ligne.valeurs[i] for i in indices)
        lignes.append(Ligne(empreinte_ligne(valeurs), valeurs))
    colonnes = tuple(table.schema.colonnes[i] for i in indices)
    return TableInstantane(
        table.nom,
        SchemaTable(colonnes, cle_primaire),
        len(lignes),
        empreinte_table(ligne.empreinte for ligne in lignes),
        lignes,
        table.duree_s,
    )


def _colonnes_communes(
    avant: TableInstantane, apres: TableInstantane, avertissements: list[Avertissement]
) -> tuple[TableInstantane, TableInstantane]:
    """AMB-012 : diff sur les colonnes communes, avec avertissement."""
    types_avant = {c.nom: c.type_declare for c in avant.schema.colonnes}
    types_apres = {c.nom: c.type_declare for c in apres.schema.colonnes}
    communes = [c for c in apres.schema.noms() if c in types_avant]
    ajoutees = [c for c in apres.schema.noms() if c not in types_avant]
    supprimees = [c for c in avant.schema.noms() if c not in types_apres]
    types_changes = [c for c in communes if types_avant[c] != types_apres[c]]
    morceaux = []
    if ajoutees:
        morceaux.append("colonnes ajoutées : " + ", ".join(ajoutees))
    if supprimees:
        morceaux.append("colonnes supprimées : " + ", ".join(supprimees))
    if types_changes:
        morceaux.append("types modifiés : " + ", ".join(types_changes))
    if not communes:
        morceaux.append("aucune colonne commune, lignes non comparées")
    avertissements.append(
        Avertissement(
            apres.nom,
            "schema_modifie_colonnes_communes",
            f"Table {apres.nom} : schéma modifié ({' ; '.join(morceaux)}). "
            "Les lignes sont comparées sur les colonnes communes uniquement.",
            {
                "colonnes_ajoutees": ajoutees,
                "colonnes_supprimees": supprimees,
                "types_modifies": types_changes,
            },
        )
    )
    cle = apres.schema.cle_primaire
    if not (cle and cle == avant.schema.cle_primaire and set(cle) <= set(communes)):
        cle = ()
    return _projeter(avant, communes, cle), _projeter(apres, communes, cle)


def comparer_instantanes(
    avant: Instantane,
    apres: Instantane,
    cles_candidates: Mapping[str, Sequence[str]] | None = None,
    tables_bruit: Collection[str] = (),
) -> ResultatDiff:
    """Compare deux photos.

    `cles_candidates` (table -> colonnes) vient du profilage. Les `tables_bruit` (calibration)
    sont rapportées à part dans `bruit`, pas dans `changements`.
    """
    cles_candidates = cles_candidates or {}
    bruit = {nom.lower() for nom in tables_bruit}
    resultat = ResultatDiff()

    def traiter(table_avant: TableInstantane, table_apres: TableInstantane) -> None:
        diff = _diff_table(
            table_avant, table_apres, cles_candidates.get(table_apres.nom), resultat.avertissements
        )
        if not diff.nb_changements:
            return
        if table_apres.nom.lower() in bruit:
            resultat.bruit.append({"table": table_apres.nom, "resume": _resume_bruit(diff)})
        else:
            resultat.changements.append(diff)

    for nom, table_apres in apres.tables.items():
        table_avant = avant.tables.get(nom)
        if table_avant is None:
            # AMB-011 : toutes les lignes de la table ajoutée sont des inserts.
            resultat.schema_modifie.append(
                SchemaModifie(nom, "table_ajoutee", None, _description_schema(table_apres))
            )
            traiter(_table_vide(table_apres), table_apres)
            continue
        if _signature_schema(table_avant) != _signature_schema(table_apres):
            resultat.schema_modifie.append(
                SchemaModifie(
                    nom,
                    "colonnes_modifiees",
                    _description_schema(table_avant),
                    _description_schema(table_apres),
                )
            )
            projetee_avant, projetee_apres = _colonnes_communes(
                table_avant, table_apres, resultat.avertissements
            )
            table_avant, table_apres = projetee_avant, projetee_apres
        if (
            table_avant.empreinte == table_apres.empreinte
            and table_avant.nb_lignes == table_apres.nb_lignes
        ):
            continue
        traiter(table_avant, table_apres)
    for nom, table_avant in avant.tables.items():
        if nom not in apres.tables:
            # AMB-011 : toutes les lignes de la table supprimée sont des deletes.
            resultat.schema_modifie.append(
                SchemaModifie(nom, "table_supprimee", _description_schema(table_avant), None)
            )
            traiter(table_avant, _table_vide(table_avant))
    return resultat
