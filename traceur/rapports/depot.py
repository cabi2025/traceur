"""Écriture locale d'une trace puis dépôt atomique dans `dossier_sorties` (F11, SPEC §8, §8.2).

1. La trace est d'abord écrite dans un dossier local (`traces_locales/`, AMB-029) construit sous
   un nom caché puis renommé : jamais de dossier à moitié écrit.
2. Le dépôt copie le dossier vers un nom caché du partage, vérifie le SHA-256 de chaque fichier,
   puis le renomme en une fois vers `traces/NOM`. Le dossier local n'est supprimé qu'après succès.
3. Si le partage est inaccessible, la trace reste en local, son dépôt est `en_attente_depot`
   (`depot.json`, jamais copié) et une nouvelle tentative a lieu au démarrage suivant.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from traceur.securite import masquer

from .index import ecrire_index
from .rapport import generer_rapport_html
from .trace import nom_dossier_trace

journal = logging.getLogger("traceur.depot")

DEPOSEE = "deposee"
EN_ATTENTE = "en_attente_depot"
MARQUEUR = "depot.json"
FICHIERS_CAPTURES = {"debut": "capture_debut.png", "fin": "capture_fin.png"}


@dataclass(frozen=True)
class ResultatDepot:
    nom: str
    statut: str  # DEPOSEE | EN_ATTENTE
    destination: Path | None = None
    erreur: str | None = None
    index_a_jour: bool = True


@dataclass
class _Marqueur:
    depot: str = EN_ATTENTE
    tentatives: int = 0
    derniere_erreur: str | None = None
    cree: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


def _lire_marqueur(dossier: Path) -> _Marqueur:
    try:
        d = json.loads((dossier / MARQUEUR).read_text(encoding="utf-8"))
        return _Marqueur(d.get("depot", EN_ATTENTE), int(d.get("tentatives", 0)), d.get("derniere_erreur"), d.get("cree", ""))
    except (OSError, ValueError):
        return _Marqueur()


def _ecrire_marqueur(dossier: Path, marqueur: _Marqueur) -> None:
    donnees = {"depot": marqueur.depot, "tentatives": marqueur.tentatives,
               "derniere_erreur": marqueur.derniere_erreur, "cree": marqueur.cree}
    (dossier / MARQUEUR).write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        while bloc := f.read(1024 * 1024):
            h.update(bloc)
    return h.hexdigest()


def creer_trace_locale(
    trace: dict[str, Any],
    dossier_local: Path,
    captures: Mapping[str, Path | None] | None = None,
    secrets: tuple[str, ...] = (),
) -> Path:
    """Écrit `trace.json`, `rapport.html`, `remarques.txt` et les captures dans `dossier_local/NOM`.

    `captures` : fichiers PNG déjà pris (début, fin) ; copiés sous leur nom définitif. Tout `secret`
    qui apparaîtrait dans un texte est remplacé par `***` (les mots de passe n'entrent jamais
    dans un rapport).
    """
    nom = nom_dossier_trace(trace["fiche"]["id"], datetime.fromisoformat(trace["execution"]["debut"]))
    final = dossier_local / nom
    if final.exists():  # même fiche relancée dans la même seconde : jamais écraser une trace
        final = _nom_libre(dossier_local, nom)
        nom = final.name
    temporaire = dossier_local / f".{nom}.en_cours"
    shutil.rmtree(temporaire, ignore_errors=True)
    temporaire.mkdir(parents=True)
    noms_captures: dict[str, str | None] = {}
    for cle, nom_fichier in FICHIERS_CAPTURES.items():
        source = (captures or {}).get(cle)
        if source is not None and Path(source).is_file():
            shutil.copyfile(source, temporaire / nom_fichier)
            noms_captures[cle] = nom_fichier
        else:
            noms_captures[cle] = None
    (temporaire / "trace.json").write_text(
        masquer(json.dumps(trace, ensure_ascii=False, indent=2), secrets), encoding="utf-8")
    (temporaire / "rapport.html").write_text(
        masquer(generer_rapport_html(trace, noms_captures), secrets), encoding="utf-8")
    (temporaire / "remarques.txt").write_text(masquer(trace["execution"]["remarques"], secrets), encoding="utf-8")
    _ecrire_marqueur(temporaire, _Marqueur())
    temporaire.rename(final)
    return final


def _copier_fichier(source: Path, destination: Path) -> None:
    shutil.copyfile(source, destination)


def deposer_trace(
    dossier_trace: Path,
    dossier_sorties: Path,
    copier: Callable[[Path, Path], None] = _copier_fichier,
    maintenant: Callable[[], datetime] = datetime.now,
) -> ResultatDepot:
    """Dépose une trace locale. Ne lève jamais d'erreur d'accès au partage : la trace reste en
    attente de dépôt (`en_attente_depot`) et sera reprise par `reprendre_depots_en_attente`."""
    nom = dossier_trace.name
    marqueur = _lire_marqueur(dossier_trace)
    temporaire: Path | None = None
    try:
        dossier_traces = dossier_sorties / "traces"
        dossier_traces.mkdir(parents=True, exist_ok=True)
        final = dossier_traces / nom
        if final.exists():
            if (final / "trace.json").is_file() and _sha256(final / "trace.json") == _sha256(dossier_trace / "trace.json"):
                journal.info("Trace %s déjà présente sur le partage : dépôt considéré comme fait.", nom)
                return _terminer(dossier_trace, dossier_sorties, final, maintenant)
            final = _nom_libre(dossier_traces, nom)
        temporaire = dossier_traces / f".{nom}.depot-tmp"
        shutil.rmtree(temporaire, ignore_errors=True)
        temporaire.mkdir()
        fichiers = [f for f in sorted(dossier_trace.iterdir()) if f.is_file() and f.name != MARQUEUR]
        for fichier in fichiers:
            copier(fichier, temporaire / fichier.name)
        for fichier in fichiers:  # vérification avant le renommage final
            if _sha256(temporaire / fichier.name) != _sha256(fichier):
                raise OSError(f"copie corrompue : {fichier.name}")
        temporaire.rename(final)
        temporaire = None
    except OSError as erreur:
        if temporaire is not None:
            shutil.rmtree(temporaire, ignore_errors=True)
        marqueur.depot, marqueur.tentatives, marqueur.derniere_erreur = EN_ATTENTE, marqueur.tentatives + 1, str(erreur)
        try:
            _ecrire_marqueur(dossier_trace, marqueur)
        except OSError:
            pass
        journal.warning("Dépôt de %s impossible (tentative %d) : %s. La trace reste en local (en_attente_depot).",
                        nom, marqueur.tentatives, erreur)
        return ResultatDepot(nom, EN_ATTENTE, None, str(erreur))
    return _terminer(dossier_trace, dossier_sorties, final, maintenant)


def _nom_libre(dossier_traces: Path, nom: str) -> Path:
    n = 2
    while (dossier_traces / f"{nom}_{n}").exists():
        n += 1
    return dossier_traces / f"{nom}_{n}"


def _terminer(dossier_trace: Path, dossier_sorties: Path, final: Path, maintenant: Callable[[], datetime]) -> ResultatDepot:
    shutil.rmtree(dossier_trace, ignore_errors=True)
    index_a_jour = True
    try:
        ecrire_index(dossier_sorties, maintenant())
    except OSError as erreur:
        index_a_jour = False
        journal.warning("Trace déposée mais index.html non mis à jour : %s", erreur)
    journal.info("Trace déposée : %s", final)
    return ResultatDepot(final.name, DEPOSEE, final, None, index_a_jour)


def lister_en_attente(dossier_local: Path) -> list[Path]:
    """Dossiers locaux de traces dont le dépôt est en attente (les dossiers cachés sont ignorés)."""
    if not dossier_local.is_dir():
        return []
    return [d for d in sorted(dossier_local.iterdir())
            if d.is_dir() and not d.name.startswith(".") and (d / MARQUEUR).is_file()
            and _lire_marqueur(d).depot == EN_ATTENTE]


def reprendre_depots_en_attente(
    dossier_local: Path, dossier_sorties: Path, **options: Any
) -> list[ResultatDepot]:
    """À appeler au démarrage : nouvelle tentative pour chaque trace en attente de dépôt."""
    return [deposer_trace(d, dossier_sorties, **options) for d in lister_en_attente(dossier_local)]


def enregistrer_trace(
    trace: dict[str, Any],
    dossier_local: Path,
    dossier_sorties: Path,
    captures: Mapping[str, Path | None] | None = None,
    secrets: tuple[str, ...] = (),
) -> ResultatDepot:
    """Écriture locale puis dépôt. Point d'entrée de « Fin » (SPEC §5.2)."""
    return deposer_trace(creer_trace_locale(trace, dossier_local, captures, secrets), dossier_sorties)
