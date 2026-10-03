# JALONS — Traceur V1

> Règle : un jalon à la fois. À la fin de chaque jalon, compte rendu puis **attendre GO**.
> Légende : [ ] à faire · [x] fait · date + remarques sous chaque jalon.

---

## J0 — Cadrage technique (pas de code métier)
- [x] Lecture complète de `CLAUDE.md`, `docs/SPEC_TRACEUR.md`, `docs/formats/*`
- [x] Squelette du dépôt conforme à SPEC §6.1, `pyproject.toml`, `.gitignore`, `pytest` qui tourne (test vide)
- [x] Liste des ambiguïtés détectées à la lecture, inscrites dans `SUIVI_AMBIGUITES.md`
- [ ] Compte rendu : plan d'implémentation des jalons J1 à J7, risques techniques identifiés

> 2026-10-03 — Squelette créé, `pytest` vert (1 test), `mypy --strict` OK, AMB-003 à AMB-010 inscrites. Reste à cocher : compte rendu / plan, en attente du **GO**. Python local 64 bits (le 32 bits sera nécessaire dès J4).

**Acceptation :** dépôt initialisé, `pytest` vert, registre des ambiguïtés à jour, plan validé par GO.

---

## J1 — Moteur : instantané + diff (F4, F5) sur SQLite
- [ ] Interface `SourceDonnees` + implémentation SQLite
- [ ] Normalisation des valeurs (SPEC §6.2), empreintes de lignes et de tables
- [ ] Diff avec clé primaire : insert / update (champ à champ) / delete
- [ ] Diff sans clé primaire : multiensembles, `update_probable`
- [ ] Détection `schema_modifie`
- [ ] Tests : PK / sans PK / doublons / nuls / dates / décimaux / espaces finaux / schéma modifié / table inchangée ignorée

**Acceptation :** tous les tests verts ; `mypy --strict traceur/moteur` sans erreur ; aucun flottant pour un montant.

---

## J2 — Profilage + calibration (F2, F3)
- [ ] Profil par table (SPEC §6.4) : stats, clés candidates, relations candidates avec taux d'inclusion
- [ ] Utilisation des clés candidates par le diff sans PK
- [ ] Calibration du bruit : 2 photos sans action → `bruit.json` ; tables de bruit isolées dans le diff
- [ ] `profil.html` autonome avec graphe des relations, sans réseau

**Acceptation :** tests sur une base SQLite à relations connues (FK retrouvées, fausses relations absentes) ; HTML ouvrable hors ligne.

---

## J3 — Interprétation (F6, F7)
- [ ] Lien saisie → colonne : exact + correspondances tolérées signalées (SPEC §7.1)
- [ ] Écarts de saisie (SPEC §7.4)
- [ ] Champs calculés : chaque hypothèse de SPEC §7.2, plusieurs hypothèses possibles par champ
- [ ] Tests : un cas par type de correspondance, un cas par hypothèse, un cas `inconnu`, un écart de saisie

**Acceptation :** tests verts ; aucune heuristique hors SPEC.

---

## J4 — Source Access + sécurité (F1, F10)
- [ ] `SourceDonnees` Access via pyodbc : lecture seule, partagé, mot de passe, `.mdw`
- [ ] Détection des pilotes ODBC disponibles, message clair si absent
- [ ] Contrôles de démarrage : `chemins_interdits`, `base_test ≠ instantane_reference`, chemins normalisés (casse, UNC)
- [ ] Réinitialisation : confirmation, refus si `.ldb` présent, copie, vérification du hash, journal
- [ ] `outils/generer_mdb_test.py` (ADOX/pywin32) : base synthétique avec tables avec et sans PK, montants, dates
- [ ] Test d'intégration sous Windows : diff sur une modification faite par un script tiers pendant que la base est ouverte

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
