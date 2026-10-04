"""Script de construction de traceur.exe : contrôles d'environnement et ligne de commande (sans PyInstaller)."""

from __future__ import annotations

from pathlib import Path

from outils import construire_exe as c


def test_environnement_valide() -> None:
    assert c.problemes_environnement(4, "win32", []) == []


def test_refuse_python_64_bits() -> None:
    p = c.problemes_environnement(8, "win32", [])
    assert len(p) == 1 and "32 bits requis" in p[0] and "64 bits" in p[0]


def test_refuse_hors_windows_et_signale_modules_absents() -> None:
    p = c.problemes_environnement(4, "linux", ["pyodbc", "PIL"])
    assert any("Windows" in x for x in p)
    assert any("« pyodbc »" in x for x in p) and any("« PIL »" in x for x in p)


def test_commande_pyinstaller() -> None:
    racine = Path("/depot")
    cmd = c.commande_pyinstaller(racine, python="py")
    assert cmd[:3] == ["py", "-m", "PyInstaller"]
    for option in ("--onefile", "--windowed"):
        assert option in cmd
    assert cmd[cmd.index("--name") + 1] == "traceur"
    caches = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--hidden-import"]
    assert {"pyodbc", "PIL.ImageGrab", "tkinter"} <= set(caches)
    assert cmd[-1] == str(racine / "traceur" / "__main__.py")


def test_empreinte(tmp_path: Path) -> None:
    f = tmp_path / "x.bin"
    f.write_bytes(b"abc")
    assert c.empreinte(f) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def _pe(tmp_path: Path, machine: int) -> Path:
    entete = bytearray(0x100)
    entete[:2] = b"MZ"
    entete[0x3C:0x40] = (0x80).to_bytes(4, "little")
    entete[0x80:0x84] = b"PE\0\0"
    entete[0x84:0x86] = machine.to_bytes(2, "little")
    f = tmp_path / "x.exe"
    f.write_bytes(bytes(entete))
    return f


def test_architecture_exe(tmp_path: Path) -> None:
    assert c.architecture_exe(_pe(tmp_path, 0x14C)) == "32 bits"
    assert c.architecture_exe(_pe(tmp_path, 0x8664)) == "64 bits"
    texte = tmp_path / "t.txt"
    texte.write_text("pas un exe")
    assert c.architecture_exe(texte) == "inconnue"


def test_option_onedir() -> None:
    racine = Path("/depot")
    cmd = c.commande_pyinstaller(racine, python="py", onedir=True)
    assert "--onedir" in cmd and "--onefile" not in cmd and "--windowed" in cmd
    assert "--onefile" in c.commande_pyinstaller(racine, python="py")
    assert c.chemin_exe(racine, onedir=True) == racine / "dist" / "traceur" / "traceur.exe"
    assert c.chemin_exe(racine) == racine / "dist" / "traceur.exe"
