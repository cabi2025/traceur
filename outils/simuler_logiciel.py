"""Simule le logiciel de comptabilité : un script TIERS qui modifie la base pendant que le traceur
la lit (test d'intégration J4, et essai manuel). Écrit dans la base : à n'utiliser que sur une
base de TEST ou synthétique.

    python outils\\simuler_logiciel.py C:\\Traceur\\test\\synthetique.mdb [--mot-de-passe XXX]

Actions (une transaction) : nouvelle facture + 2 lignes, compteur ACH +1, session 1 horodatée,
suppression du dernier client. Affiche un JSON de ce qui a été fait.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Sequence

PILOTES = ("Microsoft Access Driver (*.mdb)", "Microsoft Access Driver (*.mdb, *.accdb)")
MONTANT = 1234.56


def simuler(chemin: str, mot_de_passe: str | None = None, pyodbc_module: Any | None = None) -> dict[str, Any]:
    if pyodbc_module is None:
        import pyodbc as pyodbc_module
    pilote = next((p for p in PILOTES if p in pyodbc_module.drivers()), None)
    if pilote is None:
        raise RuntimeError("Aucun pilote ODBC Access trouvé (Python 32 bits requis).")
    chaine = f"DRIVER={{{pilote}}};DBQ={chemin};ReadOnly=0;Exclusive=0;"
    if mot_de_passe:
        chaine += "PWD={" + mot_de_passe.replace("}", "}}") + "};"
    connexion = pyodbc_module.connect(chaine, autocommit=False)
    maintenant = datetime.now().replace(microsecond=0)
    try:
        c = connexion.cursor()
        c.execute("SELECT MAX(NUM) FROM FACTURES")
        numero = int(c.fetchone()[0]) + 1
        c.execute("SELECT MAX(ID) FROM CLIENTS")
        client_supprime = int(c.fetchone()[0])
        c.execute("INSERT INTO FACTURES (NUM, CLIENT_ID, MONTANT, DATE_F, STATUT, NOTE) VALUES (?,?,?,?,?,?)",
                  numero, 5, MONTANT, maintenant, "P", "TEST-SIM")
        for rang, debit, credit in ((1, MONTANT, 0.0), (2, 0.0, MONTANT)):
            c.execute("INSERT INTO LIGNES (NUM_FACT, RANG, REF, QTE, DEBIT, CREDIT) VALUES (?,?,?,?,?,?)",
                      numero, rang, "TEST-SIM", 1, debit, credit)
        c.execute("UPDATE COMPTEURS SET DERNIER_NUM = DERNIER_NUM + 1 WHERE CODE_JOURNAL = 'ACH'")
        c.execute("UPDATE SESSIONS SET DERNIER_ACCES = ? WHERE ID = 1", maintenant)
        c.execute("DELETE FROM CLIENTS WHERE ID = ?", client_supprime)
        connexion.commit()
    except Exception:
        connexion.rollback()
        raise
    finally:
        connexion.close()
    return {"facture": numero, "montant": f"{MONTANT:.2f}", "client_supprime": client_supprime,
            "horodatage": maintenant.isoformat()}


def main(argv: Sequence[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description="Simule le logiciel : modifie la base de TEST.")
    parseur.add_argument("chemin")
    parseur.add_argument("--mot-de-passe")
    args = parseur.parse_args(argv)
    try:
        resultat = simuler(args.chemin, args.mot_de_passe)
    except Exception as erreur:
        print(f"Erreur : {str(erreur).replace(args.mot_de_passe or chr(0), '***')}", file=sys.stderr)
        return 1
    print(json.dumps(resultat))
    return 0


if __name__ == "__main__":
    sys.exit(main())
