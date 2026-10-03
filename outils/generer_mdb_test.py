"""Génère une base Access synthétique (.mdb) pour tester le traceur. Windows + pywin32 (ADOX/ADO).

    python outils\\generer_mdb_test.py C:\\Traceur\\test\\synthetique.mdb --lignes 1000

Tables : CLIENTS, FACTURES (clé primaire, montants CURRENCY, dates, mémo), LIGNES (sans clé
primaire ; couple unique NUM_FACT + RANG), COMPTEURS (sans clé primaire ; CODE_JOURNAL unique,
DERNIER_NUM volontairement non unique), SESSIONS (table qui « bouge » : bruit).
Les données sont déterministes. Les montants sont écrits via des flottants à 2 décimales :
c'est un outil de test, pas le traceur (qui ne lit que des Decimal exacts).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

MOTEUR_JET4 = 5  # « Jet OLEDB:Engine Type » : 5 = Jet 4.0 (Access 2000), 4 = Jet 3.x (Access 97)
MOTEUR_JET3 = 4
FOURNISSEUR = "Microsoft.Jet.OLEDB.4.0"
AD_OPEN_KEYSET, AD_LOCK_OPTIMISTIC, AD_CMD_TABLE = 1, 3, 2

# La clé primaire est nommée « PrimaryKey » explicitement (nom que donne l'interface d'Access) : le
# traceur lit la clé primaire via l'index de ce nom (le pilote ODBC Jet n'a pas SQLPrimaryKeys).
# Tous les identifiants sont entre crochets : Jet a beaucoup de mots réservés (NOTE, par exemple,
# est un synonyme du type MEMO) et refuse « NOTE MEMO » avec « Erreur de syntaxe dans la
# définition de champ ».
TABLES: dict[str, str] = {
    "CLIENTS": "CREATE TABLE [CLIENTS] ([ID] LONG, [NOM] TEXT(50), [CODE] TEXT(10), "
               "[SOLDE] CURRENCY, [CREE] DATETIME, CONSTRAINT [PrimaryKey] PRIMARY KEY ([ID]))",
    "FACTURES": "CREATE TABLE [FACTURES] ([NUM] LONG, [CLIENT_ID] LONG, [MONTANT] CURRENCY, "
                "[DATE_F] DATETIME, [STATUT] TEXT(1), [COMMENTAIRE] MEMO, "
                "CONSTRAINT [PrimaryKey] PRIMARY KEY ([NUM]))",
    "LIGNES": "CREATE TABLE [LIGNES] ([NUM_FACT] LONG, [RANG] INTEGER, [REF] TEXT(10), [QTE] LONG, "
              "[DEBIT] CURRENCY, [CREDIT] CURRENCY)",
    "COMPTEURS": "CREATE TABLE [COMPTEURS] ([CODE_JOURNAL] TEXT(3), [DERNIER_NUM] LONG)",
    "SESSIONS": "CREATE TABLE [SESSIONS] ([ID] LONG, [DERNIER_ACCES] DATETIME, CONSTRAINT [PrimaryKey] PRIMARY KEY ([ID]))",
}
COLONNES: dict[str, tuple[str, ...]] = {
    "CLIENTS": ("ID", "NOM", "CODE", "SOLDE", "CREE"),
    "FACTURES": ("NUM", "CLIENT_ID", "MONTANT", "DATE_F", "STATUT", "COMMENTAIRE"),
    "LIGNES": ("NUM_FACT", "RANG", "REF", "QTE", "DEBIT", "CREDIT"),
    "COMPTEURS": ("CODE_JOURNAL", "DERNIER_NUM"),
    "SESSIONS": ("ID", "DERNIER_ACCES"),
}
PREMIERE_FACTURE = 1001
NOM_AVEC_ACCENTS = "Société Générale"  # vérifie le décodage cp1252


def generer_donnees(nb_factures: int) -> dict[str, list[tuple[Any, ...]]]:
    """Lignes de chaque table (fonction pure, déterministe)."""
    nb_clients = max(20, nb_factures // 20)
    base = datetime(2024, 1, 1)
    clients = [
        (i, NOM_AVEC_ACCENTS if i == 1 else f"Client {i:05d}", f"C{i:05d}",
         Decimal(i) * Decimal("10.25"), base + timedelta(days=i % 300))
        for i in range(1, nb_clients + 1)
    ]
    factures: list[tuple[Any, ...]] = []
    lignes: list[tuple[Any, ...]] = []
    for i in range(nb_factures):
        num = PREMIERE_FACTURE + i
        montant = Decimal(100 + i) + Decimal(i % 100) / 100
        factures.append((num, 1 + i % nb_clients, montant, base + timedelta(days=i % 365),
                         "P" if i % 2 else "V", None if i % 4 == 0 else f"note {i}"))
        ref, qte = f"R{i % 10:02d}", 1 + i % 5
        lignes.append((num, 1, ref, qte, montant, Decimal("0.00")))
        lignes.append((num, 2, ref, qte, Decimal("0.00"), montant))
    return {
        "CLIENTS": clients,
        "FACTURES": factures,
        "LIGNES": lignes,
        # DERNIER_NUM non unique exprès : la clé candidate est CODE_JOURNAL (texte), sans ambiguïté
        "COMPTEURS": [("ACH", 40), ("VTE", 40), ("OD", 3)],
        "SESSIONS": [(1, base), (2, base), (3, base)],
    }


def _valeur_com(valeur: Any) -> Any:
    if isinstance(valeur, Decimal):
        return float(valeur)
    if isinstance(valeur, date) and not isinstance(valeur, datetime):
        return datetime(valeur.year, valeur.month, valeur.day)
    return valeur


def _echapper_crochets(texte: str) -> str:
    return texte.replace("]", "]]")


def chaine_oledb(chemin: str, mot_de_passe: str | None = None, exclusif: bool = False) -> str:
    morceaux = [f"Provider={FOURNISSEUR}", f"Data Source={chemin}"]
    if exclusif:
        morceaux.append("Mode=Share Exclusive")
    if mot_de_passe:
        morceaux.append(f"Jet OLEDB:Database Password={mot_de_passe}")
    return ";".join(morceaux) + ";"


def creer_base(
    chemin: str | Path,
    nb_factures: int = 1000,
    jet3: bool = False,
    mot_de_passe: str | None = None,
    dispatch: Callable[[str], Any] | None = None,
    progression: Callable[[str], None] = print,
) -> dict[str, int]:
    """Crée le fichier (ADOX), les tables (DDL) et les lignes (ADO). Retourne les effectifs."""
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    chemin = str(Path(chemin).resolve())
    if Path(chemin).exists():
        raise FileExistsError(f"Le fichier existe déjà : {chemin} (supprimez-le ou choisissez un autre nom)")
    if dispatch is None:
        import win32com.client  # type: ignore[import-not-found,unused-ignore]

        dispatch = win32com.client.Dispatch
    moteur = MOTEUR_JET3 if jet3 else MOTEUR_JET4
    catalogue = dispatch("ADOX.Catalog")
    catalogue.Create(f"{chaine_oledb(chemin)}Jet OLEDB:Engine Type={moteur};")
    catalogue.ActiveConnection.Close()
    connexion = dispatch("ADODB.Connection")
    connexion.Open(chaine_oledb(chemin))
    effectifs: dict[str, int] = {}
    try:
        for nom, ddl in TABLES.items():
            try:
                connexion.Execute(ddl)
            except Exception as erreur:
                raise RuntimeError(f"Échec de la création de la table {nom} : {erreur}\nInstruction : {ddl}") from erreur
        donnees = generer_donnees(nb_factures)
        for nom, lignes in donnees.items():
            _remplir(dispatch, connexion, nom, lignes, progression)
            effectifs[nom] = len(lignes)
    finally:
        connexion.Close()
    if mot_de_passe:
        _proteger(dispatch, chemin, mot_de_passe)
    return effectifs


def _remplir(dispatch: Callable[[str], Any], connexion: Any, table: str,
             lignes: Sequence[tuple[Any, ...]], progression: Callable[[str], None]) -> None:
    jeu = dispatch("ADODB.Recordset")
    jeu.Open(table, connexion, AD_OPEN_KEYSET, AD_LOCK_OPTIMISTIC, AD_CMD_TABLE)
    connexion.BeginTrans()
    try:
        for n, ligne in enumerate(lignes, 1):
            jeu.AddNew()
            for position, valeur in enumerate(ligne):
                if valeur is not None:
                    jeu.Fields.Item(position).Value = _valeur_com(valeur)
            jeu.Update()
            if n % 5000 == 0:
                connexion.CommitTrans()
                connexion.BeginTrans()
                progression(f"  {table} : {n} / {len(lignes)}")
        connexion.CommitTrans()
    finally:
        jeu.Close()
    progression(f"{table} : {len(lignes)} lignes")


def _proteger(dispatch: Callable[[str], Any], chemin: str, mot_de_passe: str) -> None:
    """Pose un mot de passe de base (ouverture exclusive requise)."""
    connexion = dispatch("ADODB.Connection")
    connexion.Open(chaine_oledb(chemin, exclusif=True))
    try:
        connexion.Execute(f"ALTER DATABASE PASSWORD [{_echapper_crochets(mot_de_passe)}] Null")
    finally:
        connexion.Close()


def main(argv: Sequence[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description="Génère une base Access synthétique (.mdb).")
    parseur.add_argument("chemin", help="fichier .mdb à créer (ne doit pas exister)")
    parseur.add_argument("--lignes", type=int, default=1000, help="nombre de factures (défaut 1000)")
    parseur.add_argument("--jet3", action="store_true", help="format Jet 3 (Access 97) au lieu de Jet 4")
    parseur.add_argument("--mot-de-passe", help="protège la base par ce mot de passe")
    args = parseur.parse_args(argv)
    if sys.platform != "win32":
        print("Erreur : ce script demande Windows (ADOX/ADO via pywin32).")
        return 2
    try:
        effectifs = creer_base(args.chemin, args.lignes, args.jet3, args.mot_de_passe)
    except ImportError:
        print("Erreur : le module pywin32 est absent. Installez-le avec : pip install pywin32")
        return 2
    except (FileExistsError, OSError) as erreur:
        print(f"Erreur : {erreur}")
        return 1
    except Exception as erreur:  # erreurs COM/ADO : message du pilote, jamais le mot de passe
        message = str(erreur).replace(args.mot_de_passe or "\0", "***")
        print(f"Erreur COM/ADO : {message}")
        return 1
    print(f"Base créée : {args.chemin} ({'Jet 3' if args.jet3 else 'Jet 4'})")
    print("Lignes : " + ", ".join(f"{t} {n}" for t, n in effectifs.items()) + f" — total {sum(effectifs.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
