"""Cellules écrites par une action : valeurs des lignes insérées et champs modifiés (SPEC §7.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .diff import ResultatDiff
from .instantane import Instantane
from .normalisation import normaliser_valeur


@dataclass(frozen=True)
class Cellule:
    table: str
    colonne: str
    valeur: Any
    origine: str  # "insert" | "ligne_ajoutee" | "update" | "update_probable"
    avant: Any
    ligne: Mapping[str, Any]  # ligne complète après l'action
    ref: tuple[str, int, str]  # (table, numéro de ligne, colonne), identifie la cellule

    @property
    def est_insertion(self) -> bool:
        return self.origine in ("insert", "ligne_ajoutee")


def extraire_cellules(diff: ResultatDiff, apres: Instantane) -> list[Cellule]:
    """Cellules des lignes insérées (toutes les colonnes) et champs modifiés (champs changés).

    Les tables de bruit ne sont pas dans `diff.changements` et n'apparaissent donc pas ici.
    """
    cellules: list[Cellule] = []
    numero = 0
    for t in diff.changements:
        for ligne in (*(i.valeurs for i in t.inserts), *t.lignes_ajoutees):
            origine = "insert" if t.type_cle != "aucune" else "ligne_ajoutee"
            for colonne, valeur in ligne.items():
                cellules.append(
                    Cellule(t.table, colonne, valeur, origine, None, ligne, (t.table, numero, colonne))
                )
            numero += 1
        index = _index_apres(apres, t.table, t.colonnes_cle) if t.updates else {}
        for u in t.updates:
            cle = tuple(normaliser_valeur(u.cle[c]) for c in t.colonnes_cle)
            complete = index.get(cle) or {**u.cle, **{c.colonne: c.apres for c in u.champs}}
            for champ in u.champs:
                cellules.append(
                    Cellule(t.table, champ.colonne, champ.apres, "update", champ.avant, complete,
                            (t.table, numero, champ.colonne))
                )
            numero += 1
        for p in t.updates_probables:
            for champ in p.champs:
                cellules.append(
                    Cellule(t.table, champ.colonne, champ.apres, "update_probable", champ.avant,
                            p.apres, (t.table, numero, champ.colonne))
                )
            numero += 1
    return cellules


def lignes_inserees(diff: ResultatDiff) -> dict[str, list[Mapping[str, Any]]]:
    """Lignes insérées par table (avec ou sans clé)."""
    resultat: dict[str, list[Mapping[str, Any]]] = {}
    for t in diff.changements:
        lignes: list[Mapping[str, Any]] = [*(i.valeurs for i in t.inserts), *t.lignes_ajoutees]
        if lignes:
            resultat[t.table] = lignes
    return resultat


def _index_apres(
    apres: Instantane, table: str, colonnes_cle: tuple[str, ...]
) -> dict[tuple[str, ...], Mapping[str, Any]]:
    photo = apres.tables[table]
    noms = photo.schema.noms()
    indices = [noms.index(c) for c in colonnes_cle]
    return {
        tuple(normaliser_valeur(ligne.valeurs[i]) for i in indices): dict(zip(noms, ligne.valeurs))
        for ligne in photo.lignes
    }
