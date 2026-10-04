import copy
import re
import sqlite3
from html.parser import HTMLParser
from typing import Any, Callable

from conftest import DEBUT, FIN, Scenario
from traceur.rapports.rapport import SEUIL_REPLIAGE, generer_rapport_html
from traceur.rapports.trace import Execution, FicheTrace, construire_trace


class _Balises(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ouvertes: list[str] = []
        self.vues: list[str] = []
        self.erreurs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.vues.append(tag)
        if tag not in ("meta", "img", "br"):
            self.ouvertes.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.ouvertes or self.ouvertes[-1] != tag:
            self.erreurs.append(tag)
        else:
            self.ouvertes.pop()


CAPTURES = {"debut": "capture_debut.png", "fin": "capture_fin.png"}


def test_rapport_autonome_et_bien_forme(trace_facture: dict[str, Any]) -> None:
    html = generer_rapport_html(trace_facture, CAPTURES)
    for interdit in ("http:", "https:", "//", "<script", "<link", "@import", "href=", "onclick", "javascript:"):
        assert interdit not in html, interdit
    assert not re.search(r"url\(", html)
    assert re.findall(r'src="([^"]+)"', html) == ["capture_debut.png", "capture_fin.png"]  # fichiers voisins
    p = _Balises()
    p.feed(html)
    assert not p.erreurs and not p.ouvertes
    assert html.startswith("<!doctype html>") and 'lang="fr"' in html and "<style>" in html


def test_rapport_lisible_en_francais(trace_facture: dict[str, Any]) -> None:
    html = generer_rapport_html(trace_facture, CAPTURES)
    for attendu in ("S-003 — Saisie facture achat avec TVA", "Du <b>05/10/2026 10:15:22</b> au <b>05/10/2026 10:18:04</b>",
                    "durée 2 min 42 s", "PC-COMPTA", "comptable", "<b>Terminée.</b>",
                    "3 tables modifiées, 2 lignes ajoutées, 1 modifiée",
                    "Remarques et messages affichés", "2025-ACH-0042",
                    "Ce que la fiche a écrit dans la base", "Table ECRITURES", "Table LIGNES", "Table COMPTEURS",
                    "1 ligne(s) ajoutée(s)", "Ligne modifiée (CODE_JOURNAL = ACH)",
                    "<th>Avant</th><th>Après</th>", "Valeurs saisies retrouvées", "valeur identique",
                    "Valeurs calculées par le logiciel (hypothèses)", "compteur (numéro qui augmente)",
                    "<b>hypothèses</b> à confirmer, pas des règles", "Tables qui bougent toutes seules",
                    "SESSIONS : 1 ligne modifiée (ignorée : table de bruit)", "Captures d'écran"):
        assert attendu in html, attendu
    assert "Écarts de saisie" not in html
    assert "Profil absent" in html  # la trace d'exemple a été produite sans profil (AMB-010)


def _table(trace: dict[str, Any], nom: str) -> dict[str, Any]:
    return next(c for c in trace["changements"] if c["table"] == nom)


def test_avant_apres_et_valeurs_vides_affiches(trace_facture: dict[str, Any]) -> None:
    html = generer_rapport_html(trace_facture)
    assert re.search(r'<td>DERNIER_NUM</td><td class="avant">41</td><td class="apres">42</td>', html)
    assert '<td class="nul">(vide)</td>' not in html  # aucune valeur nulle dans ce scénario
    t = copy.deepcopy(trace_facture)
    _table(t, "ECRITURES")["inserts"][0]["valeurs"]["PIECE"] = None
    assert '<td class="nul">(vide)</td>' in generer_rapport_html(t)


def test_ecart_de_saisie_mis_en_evidence(trace_avec_ecart: dict[str, Any]) -> None:
    html = generer_rapport_html(trace_avec_ecart)
    assert "<b>Écart de saisie.</b>" in html and "bandeau alerte" in html
    assert "<h2>Écarts de saisie</h2>" in html and "Réinitialisez la base de TEST puis rejouez la fiche." in html
    assert "Valeur attendue <b>1234.56</b> : introuvable dans la base." in html


def test_ecart_valeur_differente_affiche_les_deux_valeurs(trace_facture: dict[str, Any]) -> None:
    t = copy.deepcopy(trace_facture)
    t["execution"]["statut"] = "ecart_saisie"
    t["ecarts_saisie"] = [{"champ_ecran": "Débit", "ecran": "001", "valeur_attendue": "1234.56",
                           "type_ecart": "valeur_differente", "table": "LIGNES", "colonne": "DEBIT", "valeur_trouvee": "1243.56"}]
    html = generer_rapport_html(t)
    assert "Valeur attendue <b>1234.56</b>, valeur trouvée <b>1243.56</b> dans LIGNES.DEBIT." in html


def test_fiche_annulee(trace_facture: dict[str, Any]) -> None:
    t = copy.deepcopy(trace_facture)
    t.update(changements=[], liens=[], champs_calcules=[], bruit=[])
    t["execution"]["statut"] = "annulee"
    html = generer_rapport_html(t)
    assert "<b>Annulée.</b>" in html and "Fiche annulée : rien à comparer." in html
    assert "Valeurs saisies retrouvées" not in html and "Aucune valeur saisie n'a été retrouvée" not in html


def test_aucune_modification_et_sections_vides(trace_facture: dict[str, Any]) -> None:
    t = copy.deepcopy(trace_facture)
    t.update(changements=[], liens=[], champs_calcules=[], bruit=[])
    html = generer_rapport_html(t)
    assert "Aucune modification détectée." in html and "Aucune valeur saisie n'a été retrouvée dans la base." in html
    assert "Valeurs calculées" not in html and "Tables qui bougent" not in html
    t["fiche"]["valeurs_saisies"] = []
    assert "ne déclare aucune valeur saisie" in generer_rapport_html(t)


def test_avertissements_schema_et_remarques_vides(trace_facture: dict[str, Any]) -> None:
    t = copy.deepcopy(trace_facture)
    t["avertissements"] = [{"table": None, "code": "profil_absent", "message": "Profil absent : lancer le profilage."}]
    t["schema_modifie"] = [{"table": "N", "nature": "table_ajoutee", "avant": None, "apres": []}]
    t["execution"]["remarques"] = "   "
    html = generer_rapport_html(t)
    assert "<h2>Avertissements</h2>" in html and "Profil absent : lancer le profilage." in html
    assert "Structure de la base modifiée" in html and "N : table ajoutée" in html
    assert "Remarques et messages affichés" not in html


def test_aucune_injection_html(trace_facture: dict[str, Any]) -> None:
    t = copy.deepcopy(trace_facture)
    t["fiche"]["titre"] = "<script>alert(1)</script>"
    t["execution"]["remarques"] = '"><img src=x onerror=alert(1)>'
    _table(t, "ECRITURES")["inserts"][0]["valeurs"]["PIECE"] = "<i>x</i>"
    _table(t, "ECRITURES")["table"] = "T<b>"
    html = generer_rapport_html(t, {"debut": 'a".png'})
    assert "<script>" not in html and "<img src=x" not in html and "<i>x</i>" not in html and "T<b>" not in html
    assert "&lt;script&gt;" in html and "T&lt;b&gt;" in html and 'src="a&quot;.png"' in html


def test_grosse_table_repliee(trace_facture: dict[str, Any]) -> None:
    t = copy.deepcopy(trace_facture)
    ecritures = _table(t, "ECRITURES")
    ecritures["inserts"] = [copy.deepcopy(ecritures["inserts"][0]) for _ in range(SEUIL_REPLIAGE + 1)]
    html = generer_rapport_html(t)
    assert f"Table ECRITURES — {SEUIL_REPLIAGE + 1} changement(s)" in html
    assert re.search(r"<details><summary>Table ECRITURES", html)  # repliée
    assert re.search(r"<details open><summary>Table LIGNES", html)  # petite table : dépliée


def test_captures_absentes(trace_facture: dict[str, Any]) -> None:
    assert "Aucune capture disponible." in generer_rapport_html(trace_facture)
    html = generer_rapport_html(trace_facture, {"debut": "capture_debut.png", "fin": None})
    assert 'src="capture_debut.png"' in html and "capture_fin.png" not in html


def test_modification_probable_et_cle_deduite() -> None:
    trace = {
        "format_version": "1.0", "fiche": {"id": "S-1", "titre": "t", "valeurs_saisies": []},
        "execution": {"debut": "2026-10-05T10:00:00", "fin": "2026-10-05T10:01:00", "poste": "p",
                      "utilisateur_windows": "u", "statut": "terminee", "remarques": ""},
        "base": {"chemin": "b.mdb", "empreinte_fichier_avant": None},
        "changements": [{"table": "L", "cle_utilisee": {"type": "aucune", "colonnes": []}, "lignes_ajoutees": [],
                         "lignes_supprimees": [], "updates_probables": [
                             {"avant": {"M": "1"}, "apres": {"M": "7"}, "champs": [{"colonne": "M", "avant": "1", "apres": "7"}]}]},
                        {"table": "C", "cle_utilisee": {"type": "candidate", "colonnes": ["CODE"]}, "inserts": [],
                         "updates": [], "deletes": [], "updates_probables": []}],
        "bruit": [], "liens": [], "champs_calcules": [], "ecarts_saisie": [], "schema_modifie": [], "avertissements": [],
    }
    html = generer_rapport_html(trace)
    assert "Modification probable" in html and "à confirmer" in html
    assert "aucune clé" in html and "clé déduite du profil : CODE" in html


def test_avertissement_petite_table_dans_trace_et_rapport(base: sqlite3.Connection, jouer: Callable[..., Scenario]) -> None:
    """AMB-037 : de bout en bout, la clé candidate d'une petite table est signalée (trace.json et rapport.html)."""
    base.execute("CREATE TABLE COMPTEURS (CODE_JOURNAL TEXT, DERNIER_NUM INTEGER)")
    base.executemany("INSERT INTO COMPTEURS VALUES (?,?)", [("ACH", 40), ("VTE", 3), ("OD", 42)])
    s = jouer(["UPDATE COMPTEURS SET DERNIER_NUM=41 WHERE CODE_JOURNAL='ACH'"], avec_profil=True)
    trace = construire_trace(FicheTrace("S-X", "t", ()), Execution(DEBUT, FIN), "base.mdb", s.diff, s.interpretation, None)
    (a,) = [a for a in trace["avertissements"] if a["code"] == "cle_candidate_petite_table"]
    assert (a["table"], a["nb_lignes"], a["cle_candidate"]) == ("COMPTEURS", 3, ["DERNIER_NUM"])
    html = generer_rapport_html(trace)
    assert "<h2>Avertissements</h2>" in html and "Table COMPTEURS (3 lignes)" in html and "À confirmer" in html
