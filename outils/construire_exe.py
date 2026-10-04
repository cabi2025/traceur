"""Construit `dist\\traceur.exe` (PyInstaller, un seul fichier, sans console).

    python outils\\construire_exe.py            # construit
    python outils\\construire_exe.py --verifier # contrôle seulement l'environnement de construction

À lancer depuis la racine du dépôt, dans le `.venv` du **Python 32 bits** (SPEC §3) où sont installés
pyodbc, Pillow et pyinstaller (`pip install -e .[access,ui,build]`). Un `.exe` construit avec un Python
64 bits ne trouverait pas le pilote ODBC Access 32 bits : le script refuse de construire.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import struct
import subprocess
import sys
from pathlib import Path
from typing import Sequence

RACINE = Path(__file__).resolve().parent.parent
NOM = "traceur"
# Importés tardivement (pyodbc dans importer_pyodbc, Pillow dans captures) : PyInstaller ne les voit pas seul.
IMPORTS_CACHES = ("pyodbc", "PIL.Image", "PIL.ImageGrab", "tkinter", "tkinter.ttk", "tkinter.messagebox")
MODULES_REQUIS = ("pyodbc", "PIL", "tkinter", "PyInstaller")


def problemes_environnement(
    taille_pointeur: int | None = None,
    plateforme: str | None = None,
    modules_absents: Sequence[str] | None = None,
) -> list[str]:
    """Liste ce qui empêche de construire un `.exe` utilisable (vide = tout est bon)."""
    taille = struct.calcsize("P") if taille_pointeur is None else taille_pointeur
    plateforme = sys.platform if plateforme is None else plateforme
    if modules_absents is None:
        modules_absents = [m for m in MODULES_REQUIS if importlib.util.find_spec(m) is None]
    problemes: list[str] = []
    if plateforme != "win32":
        problemes.append("La construction doit se faire sous Windows (l'exécutable cible est un .exe Windows).")
    if taille != 4:
        problemes.append("Python 32 bits requis : ce Python est en %d bits. Le pilote ODBC Access "
                         "« Microsoft Access Driver (*.mdb) » n'existe qu'en 32 bits." % (taille * 8))
    for module in modules_absents:
        problemes.append(f"Module « {module} » introuvable : installez-le (pip install -e .[access,ui,build]).")
    return problemes


def commande_pyinstaller(racine: Path = RACINE, python: str | None = None) -> list[str]:
    """Ligne de commande PyInstaller (sans fichier .spec : tout est visible ici)."""
    commande = [python or sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
                "--windowed", "--name", NOM,
                "--distpath", str(racine / "dist"), "--workpath", str(racine / "build"),
                "--specpath", str(racine / "build")]
    for module in IMPORTS_CACHES:
        commande += ["--hidden-import", module]
    commande.append(str(racine / "traceur" / "__main__.py"))
    return commande


def empreinte(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def architecture_exe(chemin: Path) -> str:
    """Lit l'en-tête PE : « 32 bits » (x86), « 64 bits » (x64) ou « inconnue »."""
    with chemin.open("rb") as f:
        entete = f.read(4096)
    if entete[:2] != b"MZ" or len(entete) < 0x40:
        return "inconnue"
    decalage = int.from_bytes(entete[0x3C:0x40], "little")
    if entete[decalage:decalage + 4] != b"PE\0\0":
        return "inconnue"
    machine = int.from_bytes(entete[decalage + 4:decalage + 6], "little")
    return {0x14C: "32 bits", 0x8664: "64 bits"}.get(machine, "inconnue")


def construire() -> int:
    exe = RACINE / "dist" / f"{NOM}.exe"
    code = subprocess.call(commande_pyinstaller(), cwd=RACINE)
    if code != 0 or not exe.is_file():
        print("ÉCHEC de la construction (voir le détail ci-dessus).", file=sys.stderr)
        return code or 1
    print(f"\nConstruit : {exe} ({exe.stat().st_size // 1024} Ko)")
    architecture = architecture_exe(exe)
    print(f"SHA-256   : {empreinte(exe)}")
    print(f"Architecture de l'exécutable : {architecture}")
    if architecture != "32 bits":
        print("PROBLÈME : l'exécutable n'est pas 32 bits : il ne verra pas le pilote ODBC Access.", file=sys.stderr)
        return 3
    print("Étape suivante : copiez traceur.exe et config.example.json (docs\\formats) dans un dossier de travail,")
    print("renommez la config en config.json, puis suivez GUIDE_INSTALLATION.md.")
    return 0


def principal(argv: Sequence[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description="Construit traceur.exe (PyInstaller, 32 bits).")
    parseur.add_argument("--verifier", action="store_true", help="contrôle l'environnement sans construire")
    args = parseur.parse_args(argv)
    problemes = problemes_environnement()
    for p in problemes:
        print("PROBLÈME :", p, file=sys.stderr)
    if problemes:
        return 2
    print("Environnement de construction : OK (Windows, Python 32 bits, modules présents).")
    return 0 if args.verifier else construire()


if __name__ == "__main__":
    raise SystemExit(principal())
