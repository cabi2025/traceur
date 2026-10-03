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
- [ ] Test d'intégration sous Windows : diff sur une modification faite par un script tiers pendant que la base est ouverte

> 2026-10-03 — **Code livré, exécution Windows en attente.** Tout ce qui est testable sous Linux est vert (226 passés, 12 sautés = tests d'intégration Access, `mypy --strict traceur/moteur` sans erreur). La case « Test d'intégration sous Windows » reste à cocher après exécution de `outils/LISEZMOI_J4.md` (étapes 5, 9, 10).
> Livrés : `traceur/config.py`, `traceur/securite.py`, `traceur/sources/access.py`, `outils/{generer_mdb_test,version_jet,simuler_logiciel,diagnostic}.py`, `tests/test_integration_access.py`.
> Ambiguïtés ouvertes : AMB-023 à AMB-027 (dont AMB-027, cache Jet, à mesurer sur Windows).
> Premier essai Windows (2026-10-03) : 224 tests unitaires + `test_python_32_bits` verts (225 passés) ; 11 tests d'intégration en échec à cause d'un seul défaut du générateur : la colonne `NOTE` (mot réservé Jet, synonyme de MEMO) → corrigé (colonne `COMMENTAIRE`, identifiants entre crochets). Nouvel essai demandé.

**Acceptation :** intégration verte sous Windows 32 bits ; preuve qu'aucune écriture n'est possible via la connexion du traceur (tentative d'INSERT refusée) ; mot de passe absent des logs.

> ⚠️ Si l'environnement de Claude Code n'est pas Windows, ce jalon s'arrête à la livraison du code et des scripts de test, et l'exécution est faite par l'utilisateur. Le signaler dans le compte rendu.

---

## J5 — Rapports + dépôt (F9, F11)
- [ ] `trace.json` conforme à `docs/formats/trace.example.json` (+ `format_version`)
- [ ] `rapport.html` autonome et lisible par un non-technicien, en français
- [ ] `index.html` des traces
- [ ] Captures d'écran début/fin (Pillow `ImageGrab`)
- [ ] Écriture en local puis déplacement atomique ; `en_attente_depot` + nouvelle tentative au démarrage

**Acceptation :** rapport généré depuis une trace de test ; simulation d'un partage indisponible puis rétabli.

---

## J6 — Interface Tkinter (F8)
- [ ] Écran principal, exécution de fiche, fin de fiche (SPEC §5)
- [ ] Chargement de `fiches.example.json`, statuts des fiches
- [ ] Barre de progression, interface jamais figée (calculs hors thread UI)
- [ ] Annuler, remarques, alerte d'écart de saisie
- [ ] Messages d'erreur en français, détail dans `journal.log`

**Acceptation :** parcours complet sur la base synthétique : profiler → calibrer → fiche → rapport → réinitialiser.

---

## J7 — Livraison
- [ ] Build PyInstaller `--onefile` **32 bits** : `traceur.exe`
- [ ] `GUIDE_COMPTABLE.md` (1 page, langage simple) + `GUIDE_INSTALLATION.md` (config, chemins, partage)
- [ ] Test de l'`.exe` sur un poste Windows sans Python
- [ ] Bilan : ambiguïtés ouvertes, limites connues, temps de photo mesuré sur la base synthétique volumineuse

**Acceptation :** `.exe` lancé sur un poste propre, parcours complet OK, guides relus.
