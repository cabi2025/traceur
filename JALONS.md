# JALONS — Traceur V1

> Règle : un jalon à la fois. À la fin de chaque jalon, compte rendu puis **attendre GO**.
> Légende : [ ] à faire · [x] fait · date + remarques sous chaque jalon.

---

## J0 — Cadrage technique (pas de code métier)
- [x] Lecture complète de `CLAUDE.md`, `docs/SPEC_TRACEUR.md`, `docs/formats/*`
- [x] Squelette du dépôt conforme à SPEC §6.1, `pyproject.toml`, `.gitignore`, `pytest` qui tourne (test vide)
- [x] Liste des ambiguïtés détectées à la lecture, inscrites dans `SUIVI_AMBIGUITES.md`
- [x] Compte rendu : plan d'implémentation des jalons J1 à J7, risques techniques identifiés

> 2026-10-03 — Squelette créé, `pytest` vert (1 test), `mypy --strict` OK, AMB-003 à AMB-010 inscrites. Reste à cocher : compte rendu / plan, en attente du **GO**. Python local 64 bits (le 32 bits sera nécessaire dès J4).

**Acceptation :** dépôt initialisé, `pytest` vert, registre des ambiguïtés à jour, plan validé par GO.

---

## J1 — Moteur : instantané + diff (F4, F5) sur SQLite
- [x] Interface `SourceDonnees` + implémentation SQLite
- [x] Normalisation des valeurs (SPEC §6.2), empreintes de lignes et de tables
- [x] Diff avec clé primaire : insert / update (champ à champ) / delete
- [x] Diff sans clé primaire : multiensembles, `update_probable`
- [x] Détection `schema_modifie`
- [x] Tests : PK / sans PK / doublons / nuls / dates / décimaux / espaces finaux / schéma modifié / table inchangée ignorée

> 2026-10-03 — Fait. 36 tests verts, `mypy --strict traceur/moteur` sans erreur, aucun flottant pour un montant (`Decimal` → chaîne exacte).
> Ajouts demandés : mesure du temps de photo (`Instantane.resume()`, `tests/test_mesure_temps.py`) et `outils/version_jet.py` (AMB-001).
> Mesure indicative sur SQLite en mémoire : 120 000 lignes en ~1,4 s — **ne vaut pas mesure sur la vraie base** (AMB-002 reste ouverte).
> Décisions AMB-001, 003 à 010 recopiées dans le registre ; SPEC mise à jour. Nouvelles ambiguïtés ouvertes : AMB-011 à AMB-013 (`TODO` dans `diff.py`).

**Acceptation :** tous les tests verts ; `mypy --strict traceur/moteur` sans erreur ; aucun flottant pour un montant.

---

## J2 — Profilage + calibration (F2, F3)
- [x] Profil par table (SPEC §6.4) : stats, clés candidates, relations candidates avec taux d'inclusion
- [x] Utilisation des clés candidates par le diff sans PK
- [x] Calibration du bruit : 2 photos sans action → `bruit.json` ; tables de bruit isolées dans le diff
- [x] `profil.html` autonome avec graphe des relations, sans réseau

> 2026-10-03 — Fait. 66 tests `pytest` verts, `mypy --strict traceur/moteur` sans erreur. HTML vérifié hors ligne dans Chromium (aucune requête réseau).
> En tête de J2 : AMB-011/012/013 implémentées et closes (inserts/deletes des tables ajoutées/supprimées, diff sur colonnes communes, avertissements).
> Nouvelles ambiguïtés ouvertes : AMB-014 à AMB-018 (`TODO` dans `profilage.py` et `calibration.py`). AMB-016 : relations sur colonnes à peu de valeurs distinctes acceptées telles que la SPEC les définit.
> Ajout : `docs/formats/bruit.example.json` (format provisoire de `bruit.json`).

**Acceptation :** tests sur une base SQLite à relations connues (FK retrouvées, fausses relations absentes) ; HTML ouvrable hors ligne.

---

## J3 — Interprétation (F6, F7)
- [x] Lien saisie → colonne : exact + correspondances tolérées signalées (SPEC §7.1)
- [x] Écarts de saisie (SPEC §7.4)
- [x] Champs calculés : chaque hypothèse de SPEC §7.2, plusieurs hypothèses possibles par champ
- [x] Tests : un cas par type de correspondance, un cas par hypothèse, un cas `inconnu`, un écart de saisie

> 2026-10-03 — Fait. 131 tests `pytest` verts, `mypy --strict traceur/moteur` sans erreur.
> Avant J3 : décisions AMB-011 et AMB-014 à 018 intégrées (clés candidates filtrées et ordonnées, relations à `confiance` faible, taux sur valeurs distinctes dans le profil).
> Nouvelles ambiguïtés ouvertes : AMB-019 à AMB-022 (`TODO` dans `liens.py` et `calcules.py`). Les règles correspondantes sont provisoires et décrites dans la SPEC.

**Acceptation :** tests verts ; aucune heuristique hors SPEC.

---

## J4 — Source Access + sécurité (F1, F10)
- [x] `SourceDonnees` Access via pyodbc : lecture seule, partagé, mot de passe, `.mdw`
- [x] Détection des pilotes ODBC disponibles, message clair si absent
- [x] Contrôles de démarrage : `chemins_interdits`, `base_test ≠ instantane_reference`, chemins normalisés (casse, UNC)
- [x] Réinitialisation : confirmation, refus si `.ldb` présent, copie, vérification du hash, journal
- [x] `outils/generer_mdb_test.py` (ADOX/pywin32) : base synthétique avec tables avec et sans PK, montants, dates
- [x] Test d'intégration sous Windows : diff sur une modification faite par un script tiers pendant que la base est ouverte

> 2026-10-03 — **J4 TERMINÉ.** Quatrième essai Windows (Python 32 bits) : **245 passed** (233 tests unitaires + 12 tests d'intégration Access), 0 échoué, 0 sauté. Critères d'acceptation : intégration verte sous Windows 32 bits ✔ ; INSERT et DELETE refusés via la connexion du traceur, `.mdb` inchangé (SHA-256) ✔ ; mot de passe absent des logs (base protégée, bon et mauvais mot de passe) ✔.
> Validation manuelle sous Windows (2026-10-04, Python 3.14.8 32 bits) : diagnostic complet (étape 9) ; refus de démarrer sur base de production, sous deux écritures du chemin, et sur TEST = instantané, code de sortie 1 (étape 11) ; script tiers puis réinitialisation réelle : refus sur `non`, copie vérifiée sur `OUI`, SHA-256 de la base de TEST identique à celui de la référence (`19f0287a…c14f45`), effectifs revenus à 2000 / 1000 / 50 lignes (étape 12). Clés primaires lues sur Jet (NUM, ID) : AMB-028 vérifié sur la base synthétique.
> Historique : voir les essais 1 à 3 ci-dessous. Restent ouverts, sans bloquer J5 : AMB-001 (version Jet de la vraie base), AMB-002 (temps de photo réel), AMB-027 (mesurée : voir le registre ; décision à prendre), AMB-028 (clés primaires de la vraie base : `outils/sonder_pilote.py`).
> Texte initial : Tout ce qui est testable sous Linux est vert (233 passés, 12 sautés = tests d'intégration Access, `mypy --strict traceur/moteur` sans erreur). La case « Test d'intégration sous Windows » reste à cocher après exécution de `outils/LISEZMOI_J4.md` (étapes 5, 9, 10).
> Livrés : `traceur/config.py`, `traceur/securite.py`, `traceur/sources/access.py`, `outils/{generer_mdb_test,version_jet,simuler_logiciel,diagnostic}.py`, `tests/test_integration_access.py`.
> Ambiguïtés ouvertes : AMB-023 à AMB-027 (dont AMB-027, cache Jet, à mesurer sur Windows).
> Premier essai Windows (2026-10-03) : 224 tests unitaires + `test_python_32_bits` verts (225 passés) ; 11 tests d'intégration en échec à cause d'un seul défaut du générateur : la colonne `NOTE` (mot réservé Jet, synonyme de MEMO) → corrigé (colonne `COMMENTAIRE`, identifiants entre crochets). Nouvel essai demandé.
> Deuxième essai Windows : 235 passés, 3 échoués. Cause principale : le pilote Jet ne gère pas `SQLPrimaryKeys` (IM001) → clé primaire lue via `SQLStatistics`, index « PrimaryKey » (AMB-028) ; un test d'intégration attendait à tort `lignes_ajoutees` pour `LIGNES` alors que sa clé candidate donne des `inserts` → corrigé. `outils/sonder_pilote.py` ajouté pour diagnostiquer.
> Troisième essai Windows : 239 passés, 3 échoués (tous liés à la clé primaire : le repli était actif mais aucun index « PrimaryKey » trouvé pour les clés déclarées en SQL). Réponse : le générateur nomme désormais explicitement `CONSTRAINT [PrimaryKey]` ; le traceur journalise les index vus quand aucun n'est nommé « PrimaryKey » (une fois par table) ; cache des clés par connexion.

**Acceptation :** intégration verte sous Windows 32 bits ; preuve qu'aucune écriture n'est possible via la connexion du traceur (tentative d'INSERT refusée) ; mot de passe absent des logs.

> ⚠️ Si l'environnement de Claude Code n'est pas Windows, ce jalon s'arrête à la livraison du code et des scripts de test, et l'exécution est faite par l'utilisateur. Le signaler dans le compte rendu.

---

## J5 — Rapports + dépôt (F9, F11)
- [x] `trace.json` conforme à `docs/formats/trace.example.json` (+ `format_version`)
- [x] `rapport.html` autonome et lisible par un non-technicien, en français
- [x] `index.html` des traces
- [x] Captures d'écran début/fin (Pillow `ImageGrab`)
- [x] Écriture en local puis déplacement atomique ; `en_attente_depot` + nouvelle tentative au démarrage

> 2026-10-04 — **J5 validé sous Windows** (Python 3.14.8 32 bits) : trace d'exemple déposée avec **vraies captures d'écran** (`capture_debut.png`, `capture_fin.png`, sans `depot.json`) ; rapport affiché correctement (en-tête, statut, tableaux avant/après, valeurs retrouvées, hypothèses, captures) ; écart de saisie ; **partage indisponible** (`Z:\` inexistant : « Le chemin d'accès spécifié est introuvable », trace conservée en local, `en_attente_depot`) puis **rétabli** (« Reprise d'un dépôt en attente … → deposee »). Lisibilité du rapport pour un comptable : **confirmée par l'utilisateur** (2026-10-04) ; index vérifié (4 traces, plus récentes d'abord, statut « Écart de saisie » en orange).
> 2026-10-03 — Fait sous Linux : 293 tests `pytest` verts (12 sautés = intégration Access), `mypy --strict traceur/moteur` sans erreur. Rapport et index vérifiés dans Chromium. Simulation « partage indisponible puis rétabli » : `tests/test_depot.py` et `tests/test_demo_j5.py`. Reste à vérifier sous Windows : la vraie capture d'écran (`outils/LISEZMOI_J5.md`).
> En tête de J5 : AMB-023 à 027 intégrées (`fichier_fiches` optionnel, résolution DNS des serveurs interdits, copie sans nouvelle tentative, `rafraichir()` avant chaque photo). Ouvertes : AMB-028, AMB-029 à AMB-031.

**Acceptation :** rapport généré depuis une trace de test ; simulation d'un partage indisponible puis rétabli.

---

## J6 — Interface Tkinter (F8)
- [x] Écran principal, exécution de fiche, fin de fiche (SPEC §5)
- [x] Chargement de `fiches.example.json`, statuts des fiches
- [x] Barre de progression, interface jamais figée (calculs hors thread UI)
- [x] Annuler, remarques, alerte d'écart de saisie
- [x] Messages d'erreur en français, détail dans `journal.log`

> 2026-10-03 — **Livré, parcours Windows en attente.** Sous Linux : Python 3.11 → 363 passés, 14 sautés (12 Access + 2 Tkinter) ; Python 3.12 avec écran virtuel (`xvfb-run`) → 392 passés, 12 sautés (Access seulement), dont 27 tests de la vraie fenêtre Tkinter et 7 du point d'entrée. `mypy --strict traceur/moteur` sans erreur.
> Validé sous Windows (2026-10-04, Python 3.14.8 32 bits) : 403 tests passés (dont les 27 de la fenêtre Tkinter) ; l'application se lance et affiche « Connectée en lecture seule (5 tables) » (à lancer dans l'environnement `.venv`). Constat : curseur vert figé sur la barre au repos → corrigé (404 attendus après `git pull`).
> Attendu sous Windows : 404 passés, 0 sauté (`outils/LISEZMOI_J6.md`, étape 0). Reste à vérifier chez vous le rendu réel et le parcours complet (étapes 2 à 11).
> En tête de J6 : AMB-029, 030, 031 closes (captures de tous les écrans). Nouvelles ambiguïtés ouvertes : AMB-032 à AMB-035.
> Correction de sécurité trouvée par les tests : au lancement, le journal était configuré deux fois (sans puis avec secret) et le premier gestionnaire n'avait pas le masquage → un seul journal désormais.

**Acceptation :** parcours complet sur la base synthétique : profiler → calibrer → fiche → rapport → réinitialiser.

---

## J7 — Livraison
- [ ] Build PyInstaller `--onefile` **32 bits** : `traceur.exe`
- [ ] `GUIDE_COMPTABLE.md` (1 page, langage simple) + `GUIDE_INSTALLATION.md` (config, chemins, partage)
- [ ] Fiche de validation « S-000 » dans le guide (AMB-027) : une saisie simple ; photo après 3 s puis après 10 s ; si les deux diffs diffèrent, augmenter `delai_stabilisation_s`
- [ ] Test de l'`.exe` sur un poste Windows sans Python
- [ ] Bilan : ambiguïtés ouvertes, limites connues, temps de photo mesuré sur la base synthétique volumineuse

**Acceptation :** `.exe` lancé sur un poste propre, parcours complet OK, guides relus.
