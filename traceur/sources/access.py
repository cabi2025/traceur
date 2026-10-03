"""SourceDonnees pour une base Access `.mdb` via pyodbc et le pilote Jet (F1, SPEC §3).

Lecture seule et accès partagé : `ReadOnly=1` dans la chaîne de connexion, `readonly=True` sur
la connexion, et une seule instruction exécutée par cette classe : `SELECT`. Aucune méthode
d'écriture n'existe. Le moteur Jet gère lui-même le fichier de verrou `.ldb` à côté de la base :
c'est le seul fichier qu'il crée ou modifie.

Les mots de passe ne sont jamais écrits dans un journal ni dans un message d'erreur.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, Iterator, Sequence

from traceur.config import Configuration
from traceur.moteur.source import Colonne, SchemaTable

journal = logging.getLogger("traceur.access")

PILOTES_PREFERES = ("Microsoft Access Driver (*.mdb)", "Microsoft Access Driver (*.mdb, *.accdb)")
TAILLE_LOT = 10_000
NOM_INDEX_CLE_PRIMAIRE = "PrimaryKey"  # nom Access de l'index de clé primaire (AMB-028)


class ErreurAccess(Exception):
    """Erreur d'accès à la base Access (message en français, sans mot de passe)."""


class ErreurPilote(ErreurAccess):
    """pyodbc ou le pilote ODBC Access est absent."""


class ErreurConnexion(ErreurAccess):
    """Connexion à la base impossible."""


@dataclass(frozen=True)
class ParametresAccess:
    chemin: str
    mot_de_passe: str | None = field(default=None, repr=False)
    fichier_mdw: str | None = None
    utilisateur: str | None = None
    mot_de_passe_mdw: str | None = field(default=None, repr=False)
    encodage_texte: str = "cp1252"

    @classmethod
    def depuis_configuration(cls, config: Configuration) -> ParametresAccess:
        return cls(config.base_test, config.mot_de_passe, config.fichier_mdw, config.utilisateur,
                   config.mot_de_passe_mdw, config.encodage_texte)

    def secrets(self) -> list[str]:
        return [s for s in (self.mot_de_passe, self.mot_de_passe_mdw) if s]


def importer_pyodbc() -> ModuleType:
    try:
        import pyodbc
    except ImportError:
        raise ErreurPilote(
            "Le module Python « pyodbc » n'est pas installé.\nInstallez-le avec : pip install pyodbc"
        ) from None
    return pyodbc


def choisir_pilote(pilotes: Sequence[str]) -> str:
    """Pilote Access à utiliser parmi ceux que pyodbc voit, ou message clair s'il n'y en a pas."""
    for prefere in PILOTES_PREFERES:
        if prefere in pilotes:
            return prefere
    bits = struct.calcsize("P") * 8
    visibles = ", ".join(pilotes) if pilotes else "aucun"
    raise ErreurPilote(
        "Aucun pilote ODBC Access n'a été trouvé.\n"
        f"Ce Python fonctionne en {bits} bits : il ne voit que les pilotes {bits} bits.\n"
        "Le pilote « Microsoft Access Driver (*.mdb) » de Windows est un pilote 32 bits : "
        "utilisez Python 32 bits (ou installez le moteur de base de données Access Microsoft "
        f"correspondant à {bits} bits).\nPilotes ODBC visibles : {visibles}."
    )


def version_jet_de(chemin: str) -> str | None:
    """« Jet 3 » / « Jet 4 » d'après l'en-tête du fichier (AMB-001), ou None si illisible."""
    from outils.version_jet import FormatInconnu, version_jet

    try:
        return version_jet(chemin).libelle
    except (OSError, FormatInconnu):
        return None


def _valeur_odbc(valeur: str) -> str:
    """Protège une valeur de chaîne de connexion ODBC (accolades si nécessaire)."""
    if any(c in valeur for c in ";{}=") or valeur != valeur.strip():
        return "{" + valeur.replace("}", "}}") + "}"
    return valeur


def construire_chaine_connexion(parametres: ParametresAccess, pilote: str, masquer: bool = False) -> str:
    """Chaîne ODBC en lecture seule et accès partagé. `masquer=True` pour l'afficher ou la journaliser."""
    secret = "***" if masquer else None
    morceaux = [f"DRIVER={{{pilote}}}", f"DBQ={_valeur_odbc(parametres.chemin)}", "ReadOnly=1", "Exclusive=0"]
    if parametres.fichier_mdw:
        morceaux.append(f"SystemDB={_valeur_odbc(parametres.fichier_mdw)}")
        morceaux.append(f"UID={_valeur_odbc(parametres.utilisateur or '')}")
        if parametres.mot_de_passe_mdw:
            morceaux.append("PWD=" + (secret or _valeur_odbc(parametres.mot_de_passe_mdw)))
    elif parametres.mot_de_passe:
        morceaux.append("PWD=" + (secret or _valeur_odbc(parametres.mot_de_passe)))
    return ";".join(morceaux) + ";"


def expliquer_erreur_odbc(texte: str) -> str:
    """Traduit les erreurs courantes du pilote en conseil pour l'utilisateur."""
    t = texte.lower()
    if "not a valid password" in t or "mot de passe" in t:
        return "Mot de passe incorrect pour la base."
    if "could not find file" in t or "introuvable" in t or "cannot find" in t:
        return "Fichier de base introuvable : vérifiez le chemin « base_test » et l'accès au partage réseau."
    if "already in use" in t or "exclusively" in t or "exclusif" in t:
        return "La base est ouverte en mode exclusif par un autre programme : fermez-la ou attendez."
    if "data source name not found" in t or "no default driver" in t:
        return "Pilote ODBC introuvable : Python et le pilote doivent avoir la même taille (32 ou 64 bits)."
    if "unrecognized database format" in t or "format de base de données non reconnu" in t:
        return "Format de base non reconnu : le fichier n'est pas un .mdb lisible par ce pilote."
    if "workgroup" in t or "groupe de travail" in t or "not have the necessary permissions" in t:
        return "Droits insuffisants : vérifiez le fichier de groupe de travail, l'utilisateur et son mot de passe."
    return "Erreur du pilote ODBC (détail dans journal.log)."


def _citer(table: str) -> str:
    return "[" + table.replace("]", "]]") + "]"


class SourceAccess:
    """Source de données Access en lecture seule. À fermer avec `fermer()` ou `with`."""

    def __init__(
        self,
        parametres: ParametresAccess,
        pyodbc_module: Any | None = None,
        pilote: str | None = None,
    ) -> None:
        self._pyodbc = pyodbc_module if pyodbc_module is not None else importer_pyodbc()
        self._parametres = parametres
        self.pilote = pilote or choisir_pilote(list(self._pyodbc.drivers()))
        self._secrets = parametres.secrets()
        self._pk_par_statistiques = False
        self._pk_illisible_signalee = False
        self._cles_lues: dict[str, tuple[str, ...]] = {}
        self._connexion = self._connecter()

    def _connecter(self) -> Any:
        chaine = construire_chaine_connexion(self._parametres, self.pilote)
        journal.info("Connexion en lecture seule : %s",
                     construire_chaine_connexion(self._parametres, self.pilote, masquer=True))
        try:
            connexion = self._pyodbc.connect(chaine, readonly=True, autocommit=True)
        except self._pyodbc.Error as erreur:
            journal.error("Connexion refusée : %s", erreur)
            raise ErreurConnexion(
                f"Connexion à la base impossible. {expliquer_erreur_odbc(str(erreur))}"
            ) from None
        self._regler_encodage(connexion)
        return connexion

    def _regler_encodage(self, connexion: Any) -> None:
        pyodbc = self._pyodbc
        encodage = self._parametres.encodage_texte
        connexion.setdecoding(pyodbc.SQL_CHAR, encoding=encodage)
        connexion.setdecoding(pyodbc.SQL_WCHAR, encoding="utf-16le")
        connexion.setencoding(encoding="utf-16le")

    # -- SourceDonnees -----------------------------------------------------------------------

    def lister_tables(self) -> list[str]:
        """Tables locales (ni tables système `MSys*`/`USys*`, ni temporaires `~*`, ni requêtes)."""
        curseur = self._connexion.cursor()
        try:
            noms = [ligne.table_name for ligne in curseur.tables(tableType="TABLE")]
        finally:
            curseur.close()
        return sorted(n for n in noms if not n.startswith(("MSys", "USys", "~")))

    def schema(self, table: str) -> SchemaTable:
        curseur = self._connexion.cursor()
        try:
            colonnes = sorted(curseur.columns(table=table), key=lambda c: c.ordinal_position)
            cle = self._cle_primaire(curseur, table)
        finally:
            curseur.close()
        return SchemaTable(tuple(Colonne(c.column_name, str(c.type_name)) for c in colonnes), cle)

    def _cle_primaire(self, curseur: Any, table: str) -> tuple[str, ...]:
        """Clé primaire déclarée. Le pilote Jet n'implémente pas SQLPrimaryKeys (erreur IM001) :
        on lit alors les index uniques (SQLStatistics) et on retient l'index « PrimaryKey », nom que
        donne Access à la clé primaire (AMB-028). Sans clé lisible, le profilage fournit des clés
        candidates (SPEC §6.3)."""
        if table in self._cles_lues:
            return self._cles_lues[table]
        self._cles_lues[table] = cle_lue = self._lire_cle_primaire(curseur, table)
        return cle_lue

    def _lire_cle_primaire(self, curseur: Any, table: str) -> tuple[str, ...]:
        if not self._pk_par_statistiques:
            try:
                cles = sorted(curseur.primaryKeys(table=table), key=lambda k: k.key_seq)
                return tuple(k.column_name for k in cles)
            except self._pyodbc.Error as erreur:
                if "IM001" not in str(erreur):
                    journal.warning("Clé primaire illisible pour %s : %s", table, erreur)
                    return ()
                self._pk_par_statistiques = True
                journal.info("Le pilote ne gère pas SQLPrimaryKeys : clé primaire lue via les index "
                             "uniques (index « %s »).", NOM_INDEX_CLE_PRIMAIRE)
        try:
            index = [
                (ligne.index_name, ligne.ordinal_position, ligne.column_name, ligne.non_unique)
                for ligne in curseur.statistics(table=table, unique=False)
                if ligne.index_name and ligne.column_name
            ]
        except self._pyodbc.Error as erreur:
            if not self._pk_illisible_signalee:
                self._pk_illisible_signalee = True
                journal.warning("Clés primaires illisibles (SQLStatistics non pris en charge : %s) : "
                                "les clés candidates du profilage seront utilisées.", erreur)
            return ()
        cle = sorted((o, c) for nom, o, c, _ in index if nom.casefold() == NOM_INDEX_CLE_PRIMAIRE.casefold())
        if not cle:
            vus: dict[str, list[str]] = {}
            for nom, _, colonne, non_unique in sorted(index, key=lambda i: (i[0], i[1])):
                vus.setdefault(f"{nom}{'' if non_unique else ' (unique)'}", []).append(colonne)
            journal.info("Table %s : aucun index « %s » ; index vus : %s.", table, NOM_INDEX_CLE_PRIMAIRE,
                         "; ".join(f"{n} → {', '.join(c)}" for n, c in vus.items()) or "aucun")
        return tuple(c for _, c in cle)

    def lire_lignes(self, table: str) -> Iterator[tuple[Any, ...]]:
        curseur = self._connexion.cursor()
        try:
            self._select(curseur, f"SELECT * FROM {_citer(table)}")
            while lot := curseur.fetchmany(TAILLE_LOT):
                for ligne in lot:
                    yield tuple(ligne)
        finally:
            curseur.close()

    @staticmethod
    def _select(curseur: Any, sql: str) -> None:
        """Seule instruction possible : SELECT (défense en profondeur, en plus de ReadOnly=1)."""
        if not sql.lstrip().upper().startswith("SELECT "):
            raise ErreurAccess("Instruction refusée : le traceur n'exécute que des SELECT.")
        curseur.execute(sql)

    def rafraichir(self) -> None:
        """Rouvre la connexion : à faire avant chaque photo (cache de pages du moteur Jet, AMB-027)."""
        self._connexion.close()
        self._cles_lues.clear()
        self._connexion = self._connecter()

    def fermer(self) -> None:
        self._connexion.close()

    def __enter__(self) -> SourceAccess:
        return self

    def __exit__(self, *_: object) -> None:
        self.fermer()
