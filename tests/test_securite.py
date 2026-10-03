import json
import logging
from pathlib import Path

import pytest

from traceur.config import (
    Configuration,
    ErreurConfiguration,
    charger_configuration,
    configuration_depuis_dict,
)
from traceur.securite import (
    ErreurSecurite,
    FormateurMasque,
    ReinitialisationAnnulee,
    chemin_verrou,
    configurer_journal,
    empreinte_sha256,
    masquer,
    normaliser_chemin,
    reinitialiser_base_test,
    texte_confirmation,
    verifier_demarrage,
)

EXEMPLE = Path(__file__).parent.parent / "docs" / "formats" / "config.example.json"
BASE = {
    "base_test": r"\\SERVEUR\Compta_TEST\compta_test.mdb",
    "instantane_reference": r"D:\Traceur\reference\compta_reference.mdb",
    "chemins_interdits": [r"\\SERVEUR\Compta\compta.mdb"],
    "fichier_fiches": r"D:\Traceur\fiches\lot1.json",
    "dossier_sorties": r"\\SERVEUR\Partage\Traceur\sorties",
}


def _config(**changements: object) -> Configuration:
    return configuration_depuis_dict({**BASE, **changements})


# --- configuration ---------------------------------------------------------------------------

def test_exemple_de_config_valide() -> None:
    c = charger_configuration(EXEMPLE)
    assert c.base_test.endswith("compta_test.mdb") and c.encodage_texte == "cp1252"
    assert c.delai_stabilisation_s == 3 and c.mot_de_passe is None and c.fichier_mdw is None


def test_bom_utf8_tolere(tmp_path: Path) -> None:
    f = tmp_path / "config.json"
    f.write_bytes(b"\xef\xbb\xbf" + json.dumps(BASE).encode("utf-8"))
    assert charger_configuration(f).base_test == BASE["base_test"]


@pytest.mark.parametrize("cle", ["base_test", "instantane_reference", "chemins_interdits",
                                 "fichier_fiches", "dossier_sorties"])
def test_cles_obligatoires(cle: str) -> None:
    donnees = dict(BASE)
    del donnees[cle]
    with pytest.raises(ErreurConfiguration, match=cle):
        configuration_depuis_dict(donnees)


def test_chemins_interdits_ne_peut_pas_etre_vide() -> None:
    with pytest.raises(ErreurConfiguration, match="ne doit pas être vide"):
        _config(chemins_interdits=[])
    with pytest.raises(ErreurConfiguration):
        _config(chemins_interdits=["  "])


def test_types_et_valeurs_invalides() -> None:
    for changement in ({"encodage_texte": "nimporte"}, {"delai_stabilisation_s": -1},
                       {"delai_stabilisation_s": "3"}, {"base_test": 12}, {"tables_ignorees": "A"}):
        with pytest.raises(ErreurConfiguration):
            _config(**changement)


def test_mot_de_passe_et_mdw_refuses_ensemble() -> None:
    with pytest.raises(ErreurConfiguration, match="ne peuvent pas être utilisés ensemble") as e:
        _config(mot_de_passe="S3cr3t!", fichier_mdw=r"C:\s.mdw", utilisateur="u")
    assert "S3cr3t!" not in str(e.value)
    with pytest.raises(ErreurConfiguration, match="utilisateur"):
        _config(fichier_mdw=r"C:\s.mdw")


def test_json_invalide_et_fichier_absent(tmp_path: Path) -> None:
    f = tmp_path / "c.json"
    f.write_text('{"base_test": "C:\\x.mdb"}', encoding="utf-8")  # antislash non doublé
    with pytest.raises(ErreurConfiguration, match="doublez|Pensez à doubler"):
        charger_configuration(f)
    with pytest.raises(ErreurConfiguration, match="introuvable"):
        charger_configuration(tmp_path / "absent.json")


def test_mots_de_passe_absents_de_repr() -> None:
    c = _config(mot_de_passe="S3cr3t!")
    assert "S3cr3t!" not in repr(c) and "S3cr3t!" not in str(c)
    c2 = _config(fichier_mdw=r"C:\s.mdw", utilisateur="u", mot_de_passe_mdw="Autre#1")
    assert "Autre#1" not in repr(c2) and c2.secrets() == ["Autre#1"]


# --- normalisation des chemins ---------------------------------------------------------------

@pytest.mark.parametrize("a", [
    r"\\SERVEUR\Compta\compta.mdb", r"\\serveur\COMPTA\COMPTA.MDB", "//SERVEUR/Compta/compta.mdb",
    r"\\SERVEUR\Compta\.\compta.mdb", r"\\SERVEUR\Compta\Autre\..\compta.mdb",
    r"\\SERVEUR\\Compta\compta.mdb", r'  "\\SERVEUR\Compta\compta.mdb"  ',
    r"\\?\UNC\SERVEUR\Compta\compta.mdb",
])
def test_formes_equivalentes_d_un_chemin_unc(a: str) -> None:
    assert normaliser_chemin(a, None) == normaliser_chemin(r"\\SERVEUR\Compta\compta.mdb", None)


def test_chemins_differents_restent_differents() -> None:
    assert normaliser_chemin(r"\\SERVEUR\Compta\compta.mdb", None) != normaliser_chemin(
        r"\\SERVEUR\Compta_TEST\compta.mdb", None)
    assert normaliser_chemin(r"C:\a\b.mdb", None) == normaliser_chemin("c:/A/./B.MDB", None)
    assert normaliser_chemin(r"\\?\C:\a\b.mdb", None) == normaliser_chemin(r"C:\a\b.mdb", None)


def test_lecteur_reseau_resolu_en_unc() -> None:
    cartes = {"Z:": r"\\SERVEUR\Compta"}
    assert normaliser_chemin(r"z:\compta.mdb", cartes.get) == normaliser_chemin(
        r"\\SERVEUR\Compta\compta.mdb", None)
    assert normaliser_chemin(r"Y:\compta.mdb", cartes.get) == r"y:\compta.mdb"  # pas un lecteur réseau


# --- F1 : contrôles de démarrage -------------------------------------------------------------

@pytest.mark.parametrize("test", [
    r"\\SERVEUR\Compta\compta.mdb", r"\\serveur\compta\COMPTA.MDB", "//SERVEUR/Compta/compta.mdb",
    r"\\?\UNC\SERVEUR\Compta\compta.mdb", r"\\SERVEUR\Compta\x\..\compta.mdb",
])
def test_demarrage_refuse_la_base_de_production(test: str) -> None:
    with pytest.raises(ErreurSecurite, match="(?s)DÉMARRAGE REFUSÉ.*PRODUCTION") as e:
        verifier_demarrage(_config(base_test=test), None)
    assert "compta.mdb" in str(e.value)


def test_demarrage_refuse_un_lecteur_reseau_equivalent() -> None:
    with pytest.raises(ErreurSecurite, match="PRODUCTION"):
        verifier_demarrage(_config(base_test=r"Z:\compta.mdb"), {"Z:": r"\\SERVEUR\Compta"}.get)


def test_demarrage_refuse_un_fichier_dans_un_dossier_interdit() -> None:
    config = _config(base_test=r"\\SERVEUR\Compta\copie\test.mdb", chemins_interdits=[r"\\SERVEUR\Compta"])
    with pytest.raises(ErreurSecurite, match="PRODUCTION"):
        verifier_demarrage(config, None)


def test_demarrage_accepte_un_dossier_au_nom_voisin() -> None:
    verifier_demarrage(_config(chemins_interdits=[r"\\SERVEUR\Compta"]), None)  # Compta_TEST ≠ Compta
    verifier_demarrage(_config(), None)


def test_demarrage_refuse_test_egal_a_la_reference() -> None:
    with pytest.raises(ErreurSecurite, match="même fichier que l'instantané"):
        verifier_demarrage(_config(base_test=r"D:\Traceur\reference\COMPTA_reference.mdb"), None)


def test_demarrage_controle_toutes_les_bases_interdites() -> None:
    config = _config(chemins_interdits=[r"\\A\x.mdb", r"\\B\y.mdb"], base_test=r"\\b\Y.mdb")
    with pytest.raises(ErreurSecurite, match="PRODUCTION"):
        verifier_demarrage(config, None)


# --- verrous ---------------------------------------------------------------------------------

def test_chemin_verrou() -> None:
    assert chemin_verrou(r"\\S\x\base.mdb") == r"\\S\x\base.ldb"
    assert chemin_verrou(r"C:\base.MDB") == r"C:\base.ldb"
    assert chemin_verrou(r"C:\base.accdb") == r"C:\base.laccdb"
    with pytest.raises(ErreurSecurite, match="Extension"):
        chemin_verrou(r"C:\base.xls")


# --- F10 : réinitialisation ------------------------------------------------------------------

@pytest.fixture
def dossier(tmp_path: Path) -> Path:
    (tmp_path / "ref").mkdir()
    (tmp_path / "test").mkdir()
    (tmp_path / "ref" / "reference.mdb").write_bytes(b"REFERENCE" * 1000)
    (tmp_path / "test" / "test.mdb").write_bytes(b"MODIFIEE")
    return tmp_path


def _cfg(dossier: Path, **changements: object) -> Configuration:
    donnees: dict[str, object] = {
        "base_test": str(dossier / "test" / "test.mdb"),
        "instantane_reference": str(dossier / "ref" / "reference.mdb"),
        "chemins_interdits": [r"\\SERVEUR\Compta\compta.mdb"],
    }
    return _config(**{**donnees, **changements})


def _contenu(dossier: Path) -> bytes:
    return (dossier / "test" / "test.mdb").read_bytes()


def test_reinitialisation_copie_verifie_et_journalise(dossier: Path, caplog: pytest.LogCaptureFixture) -> None:
    textes: list[str] = []
    caplog.set_level(logging.INFO, "traceur")
    resultat = reinitialiser_base_test(_cfg(dossier), lambda t: textes.append(t) or True, None)
    assert _contenu(dossier) == b"REFERENCE" * 1000
    assert resultat.empreinte == empreinte_sha256(dossier / "ref" / "reference.mdb")
    assert resultat.octets == 9000 and resultat.empreinte.startswith("sha256:")
    assert str(dossier / "test" / "test.mdb") in textes[0] and "ÉCRASER" in textes[0]
    assert "Réinitialisation réussie" in caplog.text and resultat.empreinte in caplog.text


def test_reinitialisation_n_ecrit_que_dans_la_base_de_test(dossier: Path) -> None:
    avant = {p: p.read_bytes() for p in dossier.rglob("*") if p.is_file()}
    destinations: list[str] = []

    def copier(source: str, destination: str) -> None:
        destinations.append(destination)
        Path(destination).write_bytes(Path(source).read_bytes())

    config = _cfg(dossier)
    reinitialiser_base_test(config, lambda t: True, None, copier)
    assert destinations == [config.base_test]
    apres = {p: p.read_bytes() for p in dossier.rglob("*") if p.is_file()}  # aucun fichier créé
    assert set(apres) == set(avant)
    assert [p for p in apres if apres[p] != avant[p]] == [dossier / "test" / "test.mdb"]


def test_refus_si_verrou_ldb_present(dossier: Path) -> None:
    (dossier / "test" / "test.ldb").write_bytes(b"")
    appels: list[str] = []
    with pytest.raises(ErreurSecurite, match="(?s)RÉINITIALISATION REFUSÉE.*test.ldb"):
        reinitialiser_base_test(_cfg(dossier), lambda t: appels.append(t) or True, None)
    assert _contenu(dossier) == b"MODIFIEE" and not appels  # rien modifié, confirmation non demandée


def test_refus_si_verrou_laccdb_pour_une_base_accdb(dossier: Path) -> None:
    (dossier / "test" / "test.accdb").write_bytes(b"MODIFIEE")
    (dossier / "ref" / "reference.accdb").write_bytes(b"R")
    (dossier / "test" / "test.laccdb").write_bytes(b"")
    config = _config(base_test=str(dossier / "test" / "test.accdb"),
                     instantane_reference=str(dossier / "ref" / "reference.accdb"))
    with pytest.raises(ErreurSecurite, match="(?s)REFUSÉE.*laccdb"):
        reinitialiser_base_test(config, lambda t: True, None)
    assert (dossier / "test" / "test.accdb").read_bytes() == b"MODIFIEE"


def test_refus_si_l_utilisateur_ne_confirme_pas(dossier: Path) -> None:
    with pytest.raises(ReinitialisationAnnulee):
        reinitialiser_base_test(_cfg(dossier), lambda t: False, None)
    assert _contenu(dossier) == b"MODIFIEE"


def test_refus_si_le_logiciel_est_rouvert_pendant_la_confirmation(dossier: Path) -> None:
    def confirmer(_: str) -> bool:
        (dossier / "test" / "test.ldb").write_bytes(b"")
        return True

    with pytest.raises(ErreurSecurite, match="REFUSÉE"):
        reinitialiser_base_test(_cfg(dossier), confirmer, None)
    assert _contenu(dossier) == b"MODIFIEE"


def test_refus_si_base_de_production(dossier: Path) -> None:
    config = _cfg(dossier, chemins_interdits=[str(dossier / "test" / "test.mdb")])
    with pytest.raises(ErreurSecurite, match="PRODUCTION"):
        reinitialiser_base_test(config, lambda t: True, None)
    assert _contenu(dossier) == b"MODIFIEE"


def test_refus_si_reference_identique_a_la_base_de_test(dossier: Path) -> None:
    config = _config(base_test=str(dossier / "ref" / "reference.mdb"),
                     instantane_reference=str(dossier / "ref" / "reference.mdb"))
    with pytest.raises(ErreurSecurite, match="même fichier"):
        reinitialiser_base_test(config, lambda t: True, None)
    assert (dossier / "ref" / "reference.mdb").read_bytes() == b"REFERENCE" * 1000


def test_refus_si_reference_ou_dossier_absents(dossier: Path) -> None:
    (dossier / "ref" / "reference.mdb").unlink()
    with pytest.raises(ErreurSecurite, match="introuvable"):
        reinitialiser_base_test(_cfg(dossier), lambda t: True, None)
    (dossier / "ref" / "reference.mdb").write_bytes(b"R")
    config = _config(base_test=str(dossier / "absent" / "t.mdb"),
                     instantane_reference=str(dossier / "ref" / "reference.mdb"))
    with pytest.raises(ErreurSecurite, match="dossier de la base"):
        reinitialiser_base_test(config, lambda t: True, None)


def test_hash_different_apres_copie_est_une_erreur(dossier: Path, caplog: pytest.LogCaptureFixture) -> None:
    def copie_corrompue(source: str, destination: str) -> None:
        Path(destination).write_bytes(Path(source).read_bytes()[:-1] + b"X")

    caplog.set_level(logging.ERROR, "traceur")
    with pytest.raises(ErreurSecurite, match="(?s)empreintes différentes.*invalide"):
        reinitialiser_base_test(_cfg(dossier), lambda t: True, None, copie_corrompue)
    assert "empreintes différentes" in caplog.text


def test_erreur_d_ecriture_signalee(dossier: Path) -> None:
    def echec(source: str, destination: str) -> None:
        raise PermissionError("accès refusé")

    with pytest.raises(ErreurSecurite, match="(?s)ÉCHOUÉE.*accès refusé.*incomplète"):
        reinitialiser_base_test(_cfg(dossier), lambda t: True, None, echec)


def test_texte_de_confirmation_rappelle_la_base_visee(dossier: Path) -> None:
    config = _cfg(dossier)
    texte = texte_confirmation(config)
    assert config.base_test in texte and config.instantane_reference in texte


# --- journal sans mot de passe ---------------------------------------------------------------

def test_masquage() -> None:
    assert masquer("pwd=abc123 et abc", ["abc123", "abc"]) == "pwd=*** et ***"
    assert masquer("rien", []) == "rien" and masquer("x", [""]) == "x"


def test_formateur_masque_message_arguments_et_exception() -> None:
    f = FormateurMasque(["S3cr3t!"])
    try:
        raise ValueError("échec avec S3cr3t!")
    except ValueError:
        import sys

        enreg = logging.LogRecord("traceur.x", logging.ERROR, __file__, 1, "mdp=%s", ("S3cr3t!",), sys.exc_info())
    sortie = f.format(enreg)
    assert "S3cr3t!" not in sortie and "mdp=***" in sortie and "ValueError" in sortie


def test_journal_local_utf8_sans_mot_de_passe(tmp_path: Path) -> None:
    c = _config(mot_de_passe="S3cr3t!")
    gestionnaire = configurer_journal(c.secrets(), tmp_path)
    try:
        log = logging.getLogger("traceur.test")
        log.info("Configuration : %r — connexion avec S3cr3t! à « base_test »", c)
    finally:
        logging.getLogger("traceur").removeHandler(gestionnaire)
        gestionnaire.close()
    contenu = (tmp_path / "journal.log").read_text(encoding="utf-8")
    assert "S3cr3t!" not in contenu and "« base_test »" in contenu and "***" in contenu
