"""Contrôles de sécurité au démarrage (F1) et réinitialisation de la base de TEST (F10).

Règles non négociables (CLAUDE.md) :
- le traceur n'écrit jamais dans la base tracée ;
- la seule écriture dans un `.mdb` est la copie de `instantane_reference` vers `base_test`,
  et uniquement vers ce chemin (`reinitialiser_base_test`, seule fonction qui écrit) ;
- refus de démarrer si `base_test` est une base interdite, ou la même que l'instantané ;
- aucun mot de passe dans les journaux (`FormateurMasque`) ni dans les rapports.
"""

from __future__ import annotations

import hashlib
import logging
import ntpath
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .config import Configuration

journal = logging.getLogger("traceur.securite")

ResolveurLecteur = Callable[[str], "str | None"]
TAILLE_BLOC = 1024 * 1024
VERROUS = {".mdb": ".ldb", ".accdb": ".laccdb"}  # AMB-008


class ErreurSecurite(Exception):
    """Contrôle de sécurité refusé. Le message est destiné à l'utilisateur (français)."""


class ReinitialisationAnnulee(ErreurSecurite):
    """L'utilisateur n'a pas confirmé la réinitialisation."""


# --- chemins ---------------------------------------------------------------------------------

def lecteur_vers_unc(lecteur: str) -> str | None:
    """« Z: » → « \\\\SERVEUR\\Partage » si c'est un lecteur réseau (Windows seulement)."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    mpr = ctypes.WinDLL("mpr")  # type: ignore[attr-defined]
    taille = wintypes.DWORD(1024)
    tampon = ctypes.create_unicode_buffer(1024)
    code = mpr.WNetGetConnectionW(lecteur, tampon, ctypes.byref(taille))
    return str(tampon.value) if code == 0 and tampon.value else None


def normaliser_chemin(chemin: str, resoudre_lecteur: ResolveurLecteur | None = lecteur_vers_unc) -> str:
    """Forme canonique pour comparer deux chemins Windows : casse, séparateurs, `.`/`..`, UNC.

    Limites (AMB-024) : un nom de serveur et son adresse IP, ou deux alias DNS, ne sont pas
    reconnus comme identiques.
    """
    texte = chemin.strip().strip('"').replace("/", "\\")
    if texte.upper().startswith("\\\\?\\UNC\\"):
        texte = "\\\\" + texte[8:]
    elif texte.startswith(("\\\\?\\", "\\\\.\\")):
        texte = texte[4:]
    debut = "\\\\" if texte.startswith("\\\\") else ""  # préfixe UNC conservé
    texte = debut + re.sub(r"\\{2,}", r"\\", texte[len(debut):])  # séparateurs répétés
    if len(texte) >= 2 and texte[1] == ":" and resoudre_lecteur is not None:
        unc = resoudre_lecteur(texte[:2].upper())
        if unc:
            texte = unc.rstrip("\\") + texte[2:]
    if sys.platform == "win32" and len(texte) >= 2 and texte[1] == ":" and os.path.exists(texte):
        texte = os.path.realpath(texte)  # lecteurs locaux substitués, liens, noms courts 8.3
        if texte.upper().startswith("\\\\?\\UNC\\"):
            texte = "\\\\" + texte[8:]
        elif texte.startswith("\\\\?\\"):
            texte = texte[4:]
    return ntpath.normpath(texte).casefold().rstrip("\\")


def _est_ou_contient(parent: str, enfant: str) -> bool:
    return enfant == parent or enfant.startswith(parent + "\\")


def chemin_verrou(base: str) -> str:
    """Fichier de verrou Jet à côté de la base : `.ldb` (.mdb) ou `.laccdb` (.accdb)."""
    racine, extension = ntpath.splitext(base)
    verrou = VERROUS.get(extension.lower())
    if verrou is None:
        raise ErreurSecurite(
            f"Extension de base non reconnue : « {extension} » (attendu : .mdb ou .accdb)."
        )
    return racine + verrou


def empreinte_sha256(chemin: str | Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        while bloc := f.read(TAILLE_BLOC):
            h.update(bloc)
    return "sha256:" + h.hexdigest()


# --- F1 : contrôles de démarrage ---------------------------------------------------------------

def verifier_demarrage(
    config: Configuration, resoudre_lecteur: ResolveurLecteur | None = lecteur_vers_unc
) -> None:
    """Refuse de démarrer si la base de TEST est une base interdite ou l'instantané de référence.

    AMB-024 (provisoire) : « interdit » = égal à un chemin interdit ou situé dedans.
    """
    test = normaliser_chemin(config.base_test, resoudre_lecteur)
    for interdit in config.chemins_interdits:
        if _est_ou_contient(normaliser_chemin(interdit, resoudre_lecteur), test):
            journal.error("Démarrage refusé : base de TEST interdite (%s).", config.base_test)
            raise ErreurSecurite(
                "DÉMARRAGE REFUSÉ : la base de TEST indiquée est une base de PRODUCTION.\n"
                f"  base_test       : {config.base_test}\n"
                f"  chemin interdit : {interdit}\n"
                "Corrigez « base_test » dans config.json pour viser la copie de TEST."
            )
    if test == normaliser_chemin(config.instantane_reference, resoudre_lecteur):
        journal.error("Démarrage refusé : base de TEST identique à l'instantané de référence.")
        raise ErreurSecurite(
            "DÉMARRAGE REFUSÉ : la base de TEST est le même fichier que l'instantané de référence.\n"
            f"  {config.base_test}\n"
            "La réinitialisation écraserait la copie fraîche. Utilisez deux fichiers distincts."
        )


# --- F10 : réinitialisation --------------------------------------------------------------------

@dataclass(frozen=True)
class ResultatReinitialisation:
    cible: str
    reference: str
    empreinte: str
    octets: int
    duree_s: float


def texte_confirmation(config: Configuration) -> str:
    """Texte à présenter à l'utilisateur : rappelle la base visée."""
    return (
        "Vous allez ÉCRASER la base de TEST :\n"
        f"    {config.base_test}\n"
        "avec la copie de référence :\n"
        f"    {config.instantane_reference}\n"
        "Toutes les modifications faites dans la base de TEST seront perdues.\n"
        "Le logiciel de comptabilité doit être fermé. Confirmer ?"
    )


def _verifier_logiciel_ferme(base: str) -> None:
    verrou = chemin_verrou(base)
    if os.path.exists(verrou):
        raise ErreurSecurite(
            "RÉINITIALISATION REFUSÉE : la base de TEST semble utilisée "
            f"(fichier de verrou présent : {verrou}).\n"
            "Fermez le logiciel de comptabilité sur tous les postes, fermez aussi la connexion du "
            "traceur à la base, puis recommencez. Si personne ne l'utilise, un arrêt brutal a pu "
            "laisser ce fichier : vérifiez avant de le supprimer à la main."
        )


def reinitialiser_base_test(
    config: Configuration,
    confirmer: Callable[[str], bool],
    resoudre_lecteur: ResolveurLecteur | None = lecteur_vers_unc,
    copier: Callable[[str, str], object] = shutil.copyfile,
    horloge: Callable[[], float] = time.perf_counter,
) -> ResultatReinitialisation:
    """Copie `instantane_reference` vers `base_test` (et nulle part ailleurs), puis vérifie le hash.

    Ordre : contrôles F1, instantané présent, logiciel fermé (pas de `.ldb`), confirmation de
    l'utilisateur, nouvelle vérification du verrou, copie, comparaison SHA-256, journal.
    AMB-025 (provisoire) : copie directe, sans fichier temporaire.
    """
    verifier_demarrage(config, resoudre_lecteur)
    reference, cible = config.instantane_reference, config.base_test
    if not os.path.isfile(reference):
        raise ErreurSecurite(f"RÉINITIALISATION IMPOSSIBLE : instantané de référence introuvable : {reference}")
    if not os.path.isdir(os.path.dirname(os.path.abspath(cible))):
        raise ErreurSecurite(f"RÉINITIALISATION IMPOSSIBLE : le dossier de la base de TEST n'existe pas : {cible}")
    _verifier_logiciel_ferme(cible)
    if not confirmer(texte_confirmation(config)):
        journal.info("Réinitialisation annulée par l'utilisateur (%s).", cible)
        raise ReinitialisationAnnulee("Réinitialisation annulée : rien n'a été modifié.")
    _verifier_logiciel_ferme(cible)  # le logiciel a pu être rouvert pendant la confirmation
    debut = horloge()
    attendu = empreinte_sha256(reference)
    try:
        copier(reference, cible)
        obtenu = empreinte_sha256(cible)
    except OSError as erreur:
        journal.error("Réinitialisation échouée (%s) : %s", cible, erreur)
        raise ErreurSecurite(
            f"RÉINITIALISATION ÉCHOUÉE : {erreur}\n"
            "La base de TEST peut être incomplète : ne l'utilisez pas avant une réinitialisation réussie."
        ) from erreur
    if obtenu != attendu:
        journal.error("Réinitialisation : empreintes différentes (%s).", cible)
        raise ErreurSecurite(
            "RÉINITIALISATION ÉCHOUÉE : la copie ne correspond pas à l'instantané de référence "
            "(empreintes différentes).\nLa base de TEST est à considérer comme invalide : "
            "recommencez la réinitialisation."
        )
    resultat = ResultatReinitialisation(
        cible, reference, attendu, os.path.getsize(cible), horloge() - debut
    )
    journal.info("Réinitialisation réussie : %s <- %s (%d octets, %s, %.1f s).", cible, reference,
                 resultat.octets, attendu, resultat.duree_s)
    return resultat


# --- journal sans mot de passe -----------------------------------------------------------------

class FormateurMasque(logging.Formatter):
    """Remplace chaque secret par `***` dans le texte final (message, arguments, exceptions)."""

    def __init__(self, secrets: Iterable[str], fmt: str | None = None) -> None:
        super().__init__(fmt or "%(asctime)s %(levelname)s %(name)s : %(message)s")
        # Les plus longs d'abord : un secret contenu dans un autre ne doit pas le casser.
        self._secrets = sorted({s for s in secrets if s}, key=len, reverse=True)

    def format(self, record: logging.LogRecord) -> str:
        return masquer(super().format(record), self._secrets)


def masquer(texte: str, secrets: Iterable[str]) -> str:
    for secret in sorted({s for s in secrets if s}, key=len, reverse=True):
        texte = texte.replace(secret, "***")
    return texte


def dossier_application() -> Path:
    """Dossier de l'exécutable (PyInstaller) ou du dépôt en développement."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path.cwd()


def configurer_journal(
    secrets: Iterable[str], dossier: Path | None = None, niveau: int = logging.INFO
) -> logging.Handler:
    """Journal `journal.log` local à côté de l'exécutable (AMB-007), UTF-8, secrets masqués."""
    dossier = dossier or dossier_application()
    dossier.mkdir(parents=True, exist_ok=True)
    gestionnaire = logging.FileHandler(dossier / "journal.log", encoding="utf-8")
    gestionnaire.setFormatter(FormateurMasque(secrets))
    racine = logging.getLogger("traceur")
    racine.setLevel(niveau)
    racine.addHandler(gestionnaire)
    return gestionnaire
