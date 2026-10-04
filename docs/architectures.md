# Architecture — Migration du logiciel de comptabilité

> Document de cadrage. Rien n'est codé tant que cette logique n'est pas validée.

---

## 0. Contexte

| Élément | État actuel |
|---|---|
| Logiciel | **Compta PLus** Ver. 2019.01 (GENIE LOG SARL, Meknès) : exécutable autonome, noyau de 2000, retouches mineures jusqu'en 2019, code source inaccessible. Carte des écrans : `docs/CARTE_ECRANS.md` |
| Base de données | Fichiers Access `.mdb`, partagés sur le réseau, mots de passe connus. **Structure : un catalogue `.mdb` + des dossiers `.mdb`** (voir ci-dessous) |
| Domaine | Comptabilité marocaine (CGNC / PCGE) |
| Problème | Migration repoussée depuis des années ; évolutions fiscales compensées par des applis externes |

**Structure des données (confirmée le 2026-10-04).** Le logiciel ouvre un **catalogue** `.mdb`, situé dans le même dossier que les dossiers, qu'il trouve automatiquement ; le catalogue liste les **sociétés et exercices**. Chaque **dossier** `.mdb` = une société + un exercice. Conséquence pour le traçage : le traceur observe un dossier (`base_test`) ; les écritures éventuelles dans le catalogue ne sont pas tracées (AMB-038, ouverte, reportée). **Périmètre de la phase 1 des sessions :** une seule société et un seul exercice, dans un dossier TEST copié d'un exercice réel récent et encore ouvert (non clôturé), déclaré dans le catalogue sous le nom « ZZ-TEST TRACEUR ».

**Gestion commerciale (GC).** La GC est du **même éditeur** et tourne sur **SQL Server** (`192.168.16.99` ; le logiciel legacy s'y connecte avec le compte Windows du comptable ; le Traceur utilisera un login SQL dédié en lecture seule, AMB-038). Elle alimente la comptabilité par un **pont** (menu E-2.07.x, paramétré par l'écran E-7.08) : le transfert écrit dans les deux bases (Journal + Pièce dans la table `Ecrit` de la GC ; écritures `Externe = 1` dans la comptabilité). Faits déclarés, à confirmer par trace : `docs/CARTE_ECRANS.md` §8. Le traçage de la GC relève de AMB-038 (traçage multi-bases).

**Objectif :** reconstruire un logiciel équivalent et **fiable**, puis y intégrer les fonctionnalités des applis externes.

**Idée centrale :** on ne peut pas lire le code, donc on **observe le logiciel comme une boîte noire**. On regarde ce qu'il écrit en base et ce qu'il produit en sortie, puis on en déduit ses règles.

---

## 1. Principes directeurs

1. **Rien n'est deviné sans preuve.** Chaque règle reconstruite est rattachée à une trace, à un écart d'état ou à une capture.
2. **Travail exclusivement sur une copie de la base.** La comptabilité réelle n'est jamais touchée.
3. **Une action = une trace.** Le comptable fait une seule manipulation par scénario.
4. **Le comptable est sollicité en sessions courtes**, avec des fiches précises et autonomes.
5. **La fiabilité est prouvée, pas supposée.** Avec les mêmes données en entrée, le nouveau logiciel doit sortir les mêmes états que l'ancien.

---

## 2. Vue d'ensemble — les phases

```
 A. COLLECTE            B. RÉTRO-INGÉNIERIE           C. SPÉCIFICATION
 ─────────────          ───────────────────           ─────────────────
 .mdb (copie)    ──►    Traceur avant/après    ──►    Base de connaissance
 Captures écrans ──►    (écritures)                   - dictionnaire tables
 États de réf.   ──►    Comparateur d'états    ──►    - fiches écrans
                        (lectures)                    - règles prouvées
                                                       - journal des ambiguïtés
                                                              │
                                                              ▼
 E. EXTENSIONS          D. RECONSTRUCTION + VALIDATION
 ─────────────          ───────────────────────────────
 Fonctions des   ◄──    Nouveau logiciel ──► Tests de non-régression
 applis externes        Migration données     (mêmes entrées = mêmes états)
                                              Double run → bascule
```

---

## 3. Sources de connaissance

| Source | Ce qu'elle apporte | Limite |
|---|---|---|
| **Base `.mdb`** | Structure des tables, toutes les données depuis 2000, éventuelles requêtes enregistrées | Ne dit pas *comment* les données sont produites |
| **Captures d'écran** | Écrans, champs, boutons, navigation | Ne montrent pas les règles cachées |
| **Traceur avant/après** | Ce que chaque action **écrit** : tables, lignes, champs calculés | Ne voit pas les **lectures** |
| **Comparateur d'états** | Ce que le logiciel **lit et calcule** : filtres, regroupements, arrondis | Demande des états de référence exportables |
| **Connaissance comptable** (CGNC, fiscalité marocaine) | Cadre théorique pour interpréter les traces | Le logiciel peut s'en écarter, et c'est la trace qui fait foi |

---

## 4. Environnement de test

1. Copier le `.mdb` en `.mdb` de TEST, sans mot de passe.
2. Faire pointer l'exe sur la base de TEST, sur le poste du comptable.
   - *Identifié (2026-10-04) :* le logiciel passe par le **catalogue** (voir §0). Le dossier TEST y est déclaré sous « ZZ-TEST TRACEUR » ; le comptable le choisit dans la liste des sociétés. Procédure : `GUIDE_INSTALLATION.md` §2 bis. Isoler complètement le catalogue : AMB-038.
3. Garder une **copie fraîche** de référence pour pouvoir réinitialiser avant les scénarios destructifs (clôtures).

---

## 5. Composant 1 — Le traceur (écritures)

### Rôle
Détecter tout ce qu'une action du logiciel modifie dans la base.

### Fonctionnement
1. Le comptable clique **« Début S-xxx »** : le traceur prend une **photo** de toutes les tables.
2. Le comptable exécute l'action décrite dans la fiche.
3. Le comptable clique **« Fin »** : nouvelle photo, puis **comparaison**.
4. Une **capture d'écran automatique** est prise au début et à la fin.

### Algorithme de comparaison
- **Étape 1, tri rapide :** nombre de lignes et empreinte globale par table, pour ignorer les tables inchangées.
- **Étape 2, détail sur les tables modifiées :**
  - avec clé primaire, on compare ligne à ligne pour classer en **INSERT / UPDATE / DELETE**, avec les champs avant → après ;
  - sans clé primaire, on compare les empreintes de lignes (en comptant les doublons) pour isoler les lignes ajoutées ou supprimées.

### Sortie
- **Un fichier JSON par scénario**, exploitable par l'analyse.
- **Un rapport HTML lisible** qui présente le scénario, les tables touchées, les lignes et les champs.
- Le tout est rangé par code de scénario (`S-001/`, `S-002/`…).

### Contraintes techniques
- Le traceur tourne sous **Windows**, sur le poste où l'exe est installé.
- Il faut le pilote **Jet/ACE**. Attention à la correspondance 32/64 bits entre le pilote et le traceur.
- La base est lue en **accès partagé** pendant que l'exe tourne.
- Il doit rester rapide sur de gros volumes, d'où le tri par empreinte.

---

## 6. Composant 2 — Le protocole comptable

### Règles (données une fois au comptable)
- Il travaille uniquement sur la base de TEST.
- Une fiche correspond à une action, encadrée par Début et Fin dans le traceur.
- Il saisit exactement les valeurs de la fiche.
- Erreur ou message inattendu : il ne corrige pas, il note et passe à la suite.
- Les sessions durent environ 15 minutes, pour 3 à 4 fiches.

### Format d'une fiche
Code, titre, durée, prérequis, étapes numérotées avec référence de capture, valeurs exactes, et ce qu'il faut noter. **`docs/CARTE_ECRANS.md` est la référence** pour le champ `capture_ref` (codes `E-x.yy.zz`) et pour tout libellé d'écran ; les fiches sont numérotées `S-<lot><nn>` (par exemple S-201). Les priorités des premières fiches sont au §7 de ce document.

### Conventions de traçabilité
- **Montants uniques** (ex. 1 234,56) pour retrouver chaque ligne instantanément.
- **Libellé `TEST-Sxxx`** sur chaque saisie.

### Ordre des lots
| Lot | Contenu |
|---|---|
| 1a | Référentiel : création de compte, de tiers, de journal. **Couvert en phase 1** ; passe en reporté si la date de `catalogue.mdb` change pendant S-000 ou une fiche du lot 1a (plan comptable éventuellement partagé) |
| 1b | Création de société, création d'exercice. **Reporté** : conditionné au traçage du catalogue (AMB-038) |
| 2 | Saisie : écriture simple, avec TVA, modification, suppression, validation d'un brouillard. **Couvert en phase 1** |
| 3 | Traitements : lettrage, délettrage, clôture mensuelle. **Couvert en phase 1** |
| 4 | États : balance, grand livre, déclaration TVA, exportés si possible. **Couvert en phase 1** |
| 5 | Clôture annuelle et à-nouveaux, sur copie fraîche, en dernier. **Reporté** : conditionné au traçage du catalogue (AMB-038) |
| Pont GC | Comptabilisation des factures et règlements de la gestion commerciale (E-2.07.x). **Conditionné à AMB-038** (traçage multi-bases : base GC SQL Server `GC_TEST`) ; fiches **interdites** avant (voir `CLAUDE.md`, règles de sécurité) |

**Hors périmètre (décisions du 2026-10-04) :** imports Excel E-7.12, E-7.13, E-7.14 et E-7.16 (jamais utilisés) ; blocs génériques du paramétrage E-7.08 (minoterie, briqueterie, gaz, hôtel, clinique), seul le bloc « GC principale » est utilisé. **Ventes : TVA à 20 % uniquement** ; les achats peuvent porter d'autres taux. **En attente du questionnaire du comptable** (menus utilisés) : abonnements, immobilisations, ancienne saisie, transferts, contrôle de la comptabilité.

**Phase 1 des sessions :** lots **1a, 2, 3 et 4**, sur un seul exercice ouvert. Les lots **1b et 5** (création de société ou d'exercice, clôture annuelle, ouverture du nouvel exercice) ne sont étudiés qu'une fois le catalogue tracé (AMB-038). Réserve : si la date de modification de `catalogue.mdb` change pendant S-000 ou une fiche du lot 1a, le lot 1a passe lui aussi en reporté.

Les fiches réelles sont rédigées **après** réception des captures, pour reprendre les noms exacts des écrans et des boutons.

---

## 7. Composant 3 — Le comparateur d'états (lectures)

### Principe
On compare l'**état produit par le logiciel** avec l'**état recalculé** depuis la base. Chaque écart révèle une règle.

### Boucle
1. On récupère l'état réel, de préférence en export Excel, CSV ou texte.
2. On calcule l'état attendu à partir des tables, selon une hypothèse.
3. On compare ligne par ligne.
4. S'il y a un écart, on ajuste l'hypothèse (filtre, regroupement, arrondi, source) et on recommence.
5. Quand il n'y a plus d'écart, la règle est **confirmée** et versée dans la base de connaissance.

### Ce que ça révèle
- **Filtres :** brouillards, à-nouveaux, bornes de dates, journaux exclus.
- **Regroupements :** quels comptes alimentent quelle ligne du bilan ou du CPC.
- **Arrondis et signes :** reclassements de soldes, niveau d'arrondi.
- **Sources :** quelle table est réellement lue.

### Valeur durable
Ces comparaisons deviennent la **suite de tests de non-régression** du nouveau logiciel.

---

## 8. Composant 4 — La base de connaissance (spécification)

| Élément | Contenu |
|---|---|
| **Dictionnaire des tables** | Chaque table et chaque champ, avec son type, son rôle supposé puis confirmé et ses liens |
| **Fiches écrans** | Capture, champs, boutons, tables écrites (d'après les traces) |
| **Règles** | Énoncé, **preuve** (trace S-xxx, écart d'état, capture), statut *hypothèse* ou *confirmée* |
| **Journal des ambiguïtés** | Ce qui reste incertain, la question posée et la réponse obtenue |

Une règle sans preuve reste au statut *hypothèse* et n'est pas codée comme définitive.

---

## 9. Composant 5 — Le nouveau logiciel

### Modules, par ordre de construction
1. **Noyau :** plan comptable, journaux, tiers, saisie, lettrage, grand livre, balance.
2. **Clôture et états de synthèse :** Bilan, CPC, ESG, Tableau de financement, ETIC.
3. **Fiscal :** TVA, relevé des déductions, exports SIMPL et EDI. Les formats en vigueur seront vérifiés au moment du développement.
4. **Extensions :** fonctionnalités des applis externes, intégrées une par une (phase E).

### Exigences de conformité
- Écritures validées **inaltérables**, corrigées uniquement par contre-passation.
- **Numérotation chronologique** sans trou.
- **Clôture verrouillée.**
- **Piste d'audit.**
- Sauvegardes et **conservation sur 10 ans**.

### Migration des données
Reprise complète depuis le `.mdb` grâce au dictionnaire des tables, puis contrôle par comparaison des balances avant et après migration.

**Multi-société / multi-exercice :** la migration est **pilotée par le catalogue**. Le catalogue donne la liste des sociétés et exercices, donc des dossiers `.mdb` à reprendre, et leurs liens (un dossier = une société + un exercice). Le dictionnaire des tables du catalogue est à établir avant la migration (dépend de AMB-038 pour les lots 1b et 5 : création de société ou d'exercice, ouverture du nouvel exercice).

**Migration = comptabilité (`.mdb`) + liaison avec la GC.** Au-delà du contenu des dossiers, la migration reprend le lien entre les écritures de la comptabilité et les factures de la GC : le couple **(Journal, Pièce)**, stocké côté GC dans la table `Ecrit`, et l'indicateur **`Externe`** côté comptabilité (`Externe = 1` : écriture créée par transfert ; `Externe = 0` présumé : saisie manuelle). Le nouveau logiciel doit reproduire le **verrou** de la facture transférée (modification et suppression refusées) et la traçabilité de l'origine des écritures. La part des écritures venues du pont se **mesure** par comptage de `Externe` sur la copie du dossier (`docs/CARTE_ECRANS.md` §8). Ces mécanismes sont déclarés, **à confirmer par trace**.

**Référentiel TVA : reconstruit, pas recopié.** Le référentiel de TVA du nouveau logiciel est établi **selon la réglementation en vigueur**. La codification TVA de la GC est **incohérente** (code 05 « TVA 10 % » avec taux 0 ; codes 02 et 03 sans compte de vente, le 03 sans aucun compte ; un seul compte de TVA collectée, 4455, quel que soit le taux) : cela **n'est pas à corriger dans l'existant**, c'est à **signaler et à traiter dans la migration** (règle de qualité de données ; usage réel des codes à compter dans `EcritL` par `CodeTVA`). Détail : `docs/CARTE_ECRANS.md` §8.

---

## 10. Validation et bascule

1. **Non-régression :** même base en entrée, le nouveau logiciel doit produire des états identiques à l'ancien.
2. **Double run :** les deux logiciels tournent en parallèle pendant au moins un trimestre. Tout écart signale un bug.
3. **Bascule en début d'exercice.**

---

## 11. Livrables par phase

| Phase | Livrable |
|---|---|
| A | Base de TEST opérationnelle, captures, états de référence |
| B | Traceur, fiches de scénarios, traces JSON/HTML, comparaisons d'états |
| C | Base de connaissance complète (tables, écrans, règles prouvées, ambiguïtés) |
| D | Nouveau logiciel, migration, rapport de non-régression, double run |
| E | Modules d'extension |

---

## 12. Points ouverts — à décider ou identifier

- [ ] Nom du logiciel et langage de l'exe (à déduire des fichiers du dossier d'installation)
- [x] Méthode de localisation de la base par l'exe : un **catalogue** `.mdb`, situé dans le même dossier que les dossiers `.mdb`, trouvé automatiquement par le logiciel et listant les sociétés et exercices (confirmé le 2026-10-04). Reste à étudier : le mécanisme pour isoler un catalogue de test (AMB-038)
- [ ] Version du format `.mdb` (Jet 3 / Jet 4)
- [ ] Volume d'écritures, nombre de sociétés
- [ ] Export possible des états (Excel, CSV, texte, ou impression seule)
- [ ] Liste des applis externes et de leurs fonctions
- [ ] Forme du traceur : script Python autonome ou module de la toolbox
- [ ] Stack technique du nouveau logiciel

---

## 13. Risques et parades

| Risque | Parade |
|---|---|
| Saisies de test dans la vraie compta | Base de TEST obligatoire, exe repointé |
| Règle mal comprise | Statut hypothèse/confirmée, preuve obligatoire |
| Lectures invisibles au traceur | Comparateur d'états |
| Disponibilité du comptable | Fiches courtes et autonomes, lots planifiés |
| Clôture irréversible sur la base de test | Copie fraîche de référence, lot 5 en dernier |
| Évolutions fiscales futures | Module fiscal isolé, formats vérifiés à chaque évolution |
| Écart non détecté avant bascule | Non-régression puis double run d'un trimestre |
