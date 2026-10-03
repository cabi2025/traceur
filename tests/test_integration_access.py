"""Intégration J4 sur une vraie base Access (.mdb) : Windows, Python 32 bits, pyodbc, pywin32.

Chaque test est SAUTÉ (et le motif affiché avec `pytest -rs`) si l'environnement ne convient pas.
Résultat attendu sur le poste Windows : tous passés, aucun sauté. Voir outils/LISEZMOI_J4.md.
"""

from __future__ import annotations

import json
import logging
import os
import struct
import subprocess
import sys
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

from conftest import DEBUT, FIN, saisie
from outils import generer_mdb_test as gen
from traceur.config import Configuration
from traceur.moteur.diff import comparer_instantanes
from traceur.moteur.instantane import prendre_instantane
from traceur.moteur.interpretation import interpreter
from traceur.moteur.profilage import cles_candidates_du_profil, profiler
from traceur.securite import (
    ErreurSecurite,
    configurer_journal,
    empreinte_sha256,
    reinitialiser_base_test,
    verifier_demarrage,
)
from traceur.sources.access import (
    ErreurConnexion,
    ParametresAccess,
    SourceAccess,
    choisir_pilote,
    version_jet_de,
)

pytestmark = pytest.mark.windows
OUTILS = Path(__file__).parent.parent / "outils"
MOT_DE_PASSE = "S3cr3t!Test"
NB_FACTURES = 200


def _raison_de_saut() -> str | None:
    if sys.platform != "win32":
        return "Windows requis"
    try:
        import pyodbc
        import win32com.client  # noqa: F401
    except ImportError as erreur:
        return f"module absent : {erreur.name} (pip install pyodbc pywin32)"
    if not any(p.startswith("Microsoft Access Driver (*.mdb") for p in pyodbc.drivers()):
        return "aucun pilote ODBC Access visible : Python 32 bits requis (voir LISEZMOI_J4)"
    return None


RAISON = _raison_de_saut()
if RAISON is not None:
    pytestmark = [pytest.mark.windows, pytest.mark.skip(reason=RAISON)]


@pytest.fixture(scope="module")
def pyodbc_reel() -> Any:
    import pyodbc

    return pyodbc


@pytest.fixture
def base_synthetique(tmp_path: Path) -> str:
    chemin = tmp_path / "synthetique.mdb"
    gen.creer_base(chemin, NB_FACTURES, progression=lambda _: None)
    return str(chemin)


def _source(chemin: str, mot_de_passe: str | None = None) -> SourceAccess:
    return SourceAccess(ParametresAccess(chemin, mot_de_passe=mot_de_passe))


def _simuler(chemin: str, mot_de_passe: str | None = None) -> dict[str, Any]:
    commande = [sys.executable, str(OUTILS / "simuler_logiciel.py"), chemin]
    if mot_de_passe:
        commande += ["--mot-de-passe", mot_de_passe]
    resultat = subprocess.run(commande, capture_output=True, text=True, timeout=120)
    assert resultat.returncode == 0, resultat.stderr
    return json.loads(resultat.stdout)  # type: ignore[no-any-return]


def _attendre_disparition(chemin: str, delai_s: float = 10.0) -> bool:
    fin = time.monotonic() + delai_s
    while os.path.exists(chemin) and time.monotonic() < fin:
        time.sleep(0.2)
    return not os.path.exists(chemin)


# --- environnement ---------------------------------------------------------------------------

def test_python_32_bits() -> None:
    assert struct.calcsize("P") * 8 == 32, "Ce test d'intégration doit tourner avec Python 32 bits"


def test_pilote_et_version_jet(base_synthetique: str, pyodbc_reel: Any) -> None:
    assert choisir_pilote(list(pyodbc_reel.drivers())).startswith("Microsoft Access Driver")
    assert version_jet_de(base_synthetique) == "Jet 4"


def test_version_jet3_detectee(tmp_path: Path) -> None:
    chemin = tmp_path / "jet3.mdb"
    gen.creer_base(chemin, 20, jet3=True, progression=lambda _: None)
    assert version_jet_de(str(chemin)) == "Jet 3"


# --- lecture ---------------------------------------------------------------------------------

def test_lecture_du_schema_et_des_valeurs(base_synthetique: str) -> None:
    with _source(base_synthetique) as source:
        assert source.lister_tables() == ["CLIENTS", "COMPTEURS", "FACTURES", "LIGNES", "SESSIONS"]
        factures = source.schema("FACTURES")
        assert factures.cle_primaire == ("NUM",) and source.schema("LIGNES").cle_primaire == ()
        types = {c.nom: c.type_declare.upper() for c in factures.colonnes}
        assert types["MONTANT"] == "CURRENCY" and types["DATE_F"] in ("DATETIME", "DATE")
        lignes = list(source.lire_lignes("FACTURES"))
        assert len(lignes) == NB_FACTURES
        premiere = next(ligne for ligne in lignes if ligne[0] == gen.PREMIERE_FACTURE)
        assert isinstance(premiere[2], Decimal) and premiere[2] == Decimal("100.00")
        assert isinstance(premiere[3], datetime)
        assert [c[1] for c in source.lire_lignes("CLIENTS") if c[0] == 1] == [gen.NOM_AVEC_ACCENTS]
        assert len(list(source.lire_lignes("LIGNES"))) == 2 * NB_FACTURES


def test_profil_de_la_base_synthetique(base_synthetique: str) -> None:
    with _source(base_synthetique) as source:
        profil = profiler(source, version_jet=version_jet_de(base_synthetique))
    assert profil.version_jet == "Jet 4"
    assert cles_candidates_du_profil(profil) == {"LIGNES": ("NUM_FACT", "RANG"), "COMPTEURS": ("CODE_JOURNAL",)}
    assert ("FACTURES", "CLIENT_ID", "CLIENTS", "ID") in {
        (r.table_source, r.colonne_source, r.table_cible, r.colonne_cible) for r in profil.relations}


# --- sécurité : aucune écriture --------------------------------------------------------------

def test_aucune_ecriture_possible_via_la_connexion_du_traceur(base_synthetique: str, pyodbc_reel: Any) -> None:
    empreinte_avant = empreinte_sha256(base_synthetique)
    with _source(base_synthetique) as source:
        source.lister_tables()
        for table in source.lister_tables():
            list(source.lire_lignes(table))
        curseur = source._connexion.cursor()
        with pytest.raises(pyodbc_reel.Error):  # contourne la garde de la classe : le pilote refuse
            curseur.execute("INSERT INTO FACTURES (NUM, CLIENT_ID) VALUES (999999, 1)")
        with pytest.raises(pyodbc_reel.Error):
            curseur.execute("DELETE FROM FACTURES")
        curseur.execute("SELECT COUNT(*) FROM FACTURES")
        assert curseur.fetchone()[0] == NB_FACTURES
    assert _attendre_disparition(base_synthetique.replace(".mdb", ".ldb"))
    assert empreinte_sha256(base_synthetique) == empreinte_avant  # le .mdb n'a pas bougé d'un octet


# --- diff pendant que la base est ouverte ----------------------------------------------------

def test_diff_d_une_modification_faite_par_un_script_tiers(base_synthetique: str) -> None:
    with _source(base_synthetique) as source:
        profil = profiler(source)
        cles = cles_candidates_du_profil(profil)
        avant = prendre_instantane(source)
        # le script tiers écrit pendant que la connexion du traceur est ouverte (accès partagé)
        fait = _simuler(base_synthetique)
        source.rafraichir()  # AMB-027 : connexion fraîche avant la photo « après »
        apres = prendre_instantane(source)
    diff = comparer_instantanes(avant, apres, cles, tables_bruit=["SESSIONS"])
    changements = {c.table: c for c in diff.changements}
    assert set(changements) == {"CLIENTS", "COMPTEURS", "FACTURES", "LIGNES"}
    assert not diff.schema_modifie
    factures = changements["FACTURES"]
    assert [i.cle for i in factures.inserts] == [{"NUM": fait["facture"]}]
    assert factures.inserts[0].valeurs["MONTANT"] == Decimal("1234.56")
    assert factures.inserts[0].valeurs["COMMENTAIRE"] == "TEST-SIM"
    assert len(changements["LIGNES"].lignes_ajoutees) == 2
    compteurs = changements["COMPTEURS"]
    assert compteurs.type_cle == "candidate" and compteurs.colonnes_cle == ("CODE_JOURNAL",)
    assert [(u.cle, [(c.colonne, c.avant, c.apres) for c in u.champs]) for u in compteurs.updates] == [
        ({"CODE_JOURNAL": "ACH"}, [("DERNIER_NUM", 40, 41)])]
    assert [d.cle for d in changements["CLIENTS"].deletes] == [{"ID": fait["client_supprime"]}]
    assert [b["table"] for b in diff.bruit] == ["SESSIONS"]
    resultat = interpreter(diff, avant, apres, [saisie("Montant", "1234.56"), saisie("Commentaire", "TEST-SIM", "texte")],
                           DEBUT, FIN, profil)
    liens = {(x.table, x.colonne, x.type_correspondance) for x in resultat.liens}
    assert ("FACTURES", "MONTANT", "exacte") in liens and ("FACTURES", "COMMENTAIRE", "exacte") in liens
    assert not resultat.a_un_ecart_de_saisie


def test_la_connexion_du_traceur_ne_bloque_pas_l_ecriture_tierce(base_synthetique: str) -> None:
    with _source(base_synthetique) as source:
        list(source.lire_lignes("FACTURES"))
        _simuler(base_synthetique)  # échoue (code de retour ≠ 0) si la base est verrouillée


def test_cache_jet_connexion_longue(base_synthetique: str, record_property: Callable[[str, object], None]) -> None:
    """Mesure informative (AMB-027) : une connexion ouverte voit-elle tout de suite l'écriture tierce ?"""
    with _source(base_synthetique) as source:
        avant = len(list(source.lire_lignes("FACTURES")))
        _simuler(base_synthetique)
        immediat = len(list(source.lire_lignes("FACTURES")))
        time.sleep(6)  # au-delà du PageTimeout par défaut (5 s)
        apres_delai = len(list(source.lire_lignes("FACTURES")))
        source.rafraichir()
        frais = len(list(source.lire_lignes("FACTURES")))
    bilan = (f"connexion longue : avant={avant}, immédiat={immediat}, après 6 s={apres_delai} ; "
             f"connexion rouverte={frais}")
    print("\n" + bilan)
    record_property("cache_jet", bilan)
    assert frais == avant + 1  # la connexion rouverte voit toujours la modification


# --- mot de passe ----------------------------------------------------------------------------

@pytest.fixture
def base_protegee(tmp_path: Path) -> str:
    chemin = tmp_path / "protegee.mdb"
    gen.creer_base(chemin, 20, mot_de_passe=MOT_DE_PASSE, progression=lambda _: None)
    return str(chemin)


def test_base_protegee_et_mot_de_passe_absent_du_journal(base_protegee: str, tmp_path: Path) -> None:
    gestionnaire = configurer_journal([MOT_DE_PASSE], tmp_path / "logs")
    try:
        with _source(base_protegee, MOT_DE_PASSE) as source:
            assert len(list(source.lire_lignes("FACTURES"))) == 20
        with pytest.raises(ErreurConnexion) as erreur:
            _source(base_protegee, "mauvais-mot-de-passe")
        with pytest.raises(ErreurConnexion) as sans:
            _source(base_protegee)
    finally:
        logging.getLogger("traceur").removeHandler(gestionnaire)
        gestionnaire.close()
    journal = (tmp_path / "logs" / "journal.log").read_text(encoding="utf-8")
    assert MOT_DE_PASSE not in journal and "mauvais-mot-de-passe" not in journal and "PWD=***" in journal
    for e in (erreur.value, sans.value):
        assert MOT_DE_PASSE not in str(e) and "mauvais-mot-de-passe" not in str(e)
        assert "Mot de passe incorrect" in str(e)


# --- sécurité de démarrage et réinitialisation -----------------------------------------------

def _config(base_test: str, reference: str, interdits: list[str]) -> Configuration:
    return Configuration(base_test, reference, tuple(interdits), "fiches.json", "sorties")


def test_demarrage_refuse_la_base_de_production(base_synthetique: str, tmp_path: Path) -> None:
    reference = tmp_path / "reference.mdb"
    reference.write_bytes(Path(base_synthetique).read_bytes())
    # même fichier désigné autrement : casse différente, chemin avec « . »
    alias = base_synthetique.upper().replace("\\", "\\.\\")
    with pytest.raises(ErreurSecurite, match="PRODUCTION"):
        verifier_demarrage(_config(base_synthetique, str(reference), [alias]))
    verifier_demarrage(_config(base_synthetique, str(reference), [str(tmp_path / "autre.mdb")]))


def test_reinitialisation_reelle_refusee_tant_que_la_base_est_ouverte(base_synthetique: str, tmp_path: Path) -> None:
    reference = tmp_path / "reference.mdb"
    reference.write_bytes(Path(base_synthetique).read_bytes())
    config = _config(base_synthetique, str(reference), [str(tmp_path / "production.mdb")])
    _simuler(base_synthetique)  # la base de TEST diffère maintenant de la référence
    assert empreinte_sha256(base_synthetique) != empreinte_sha256(reference)
    source = _source(base_synthetique)
    try:
        list(source.lire_lignes("FACTURES"))
        assert os.path.exists(base_synthetique.replace(".mdb", ".ldb"))  # Jet a posé son verrou
        with pytest.raises(ErreurSecurite, match="(?s)REFUSÉE.*\\.ldb"):
            reinitialiser_base_test(config, lambda _: True)
    finally:
        source.fermer()
    assert _attendre_disparition(base_synthetique.replace(".mdb", ".ldb"))
    resultat = reinitialiser_base_test(config, lambda _: True)
    assert empreinte_sha256(base_synthetique) == empreinte_sha256(reference) == resultat.empreinte
    with _source(base_synthetique) as source:  # la base réinitialisée est lisible et redevenue propre
        assert len(list(source.lire_lignes("FACTURES"))) == NB_FACTURES
