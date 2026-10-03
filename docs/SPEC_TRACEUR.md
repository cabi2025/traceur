# SPEC — Traceur V1

## 1. Objectif
Pendant qu'un comptable exécute un scénario court (une « fiche ») dans le logiciel legacy, le traceur détecte **tout ce que l'action écrit** dans la base `.mdb` de TEST. Il **interprète** ces changements (lien écran → colonne, champs calculés) et produit des rapports exploitables.

Utilisateurs :
- **le comptable**, qui exécute les fiches dans un autre bureau, a peu de temps et n'est pas technicien ;
- **l'analyste**, qui exploite les rapports.

## 2. Périmètre

### V1 (à coder)
| # | Fonction |
|---|---|
| F1 | Configuration et contrôles de sécurité au démarrage |
| F2 | Profilage initial de la base |
| F3 | Calibration du bruit (tables qui bougent sans action) |
| F4 | Instantané avant / après |
| F5 | Diff : INSERT / UPDATE / DELETE au niveau champ |
| F6 | Lien automatique valeur saisie → colonne |
| F7 | Détection et hypothèses de champs calculés |
| F8 | Fiches intégrées : affichage, cochage, remarques, contrôle des écarts de saisie |
| F9 | Captures d'écran automatiques |
| F10 | Réinitialisation de la base de TEST |
| F11 | Rapports JSON + HTML, dépôt dans le dossier partagé |

### V2 (hors périmètre — prévoir seulement les points d'extension)
- Génération de cas de test exécutables à partir des traces.
- Génération d'un schéma SQL cible et d'un squelette de migration.
- Validation des règles sur l'historique complet.
- Carte de couverture multi-scénarios.

**Points d'extension :** le format JSON des traces (§8) est stable et versionné (`format_version`). Les modules V2 le liront sans modifier le moteur.

## 3. Contraintes et choix techniques
- **Cible d'exécution :** poste Windows du comptable (Windows 10/11), sans installation de Python. Livraison sous forme d'un `.exe` unique (PyInstaller, `--onefile`).
- **Build 32 bits obligatoire.** Windows fournit nativement le pilote ODBC 32 bits « Microsoft Access Driver (*.mdb) » (Jet 4.0). En 32 bits, il n'y a aucun pilote à installer.
  - Au démarrage, il faut détecter les pilotes disponibles (`pyodbc.drivers()`). On préfère `Microsoft Access Driver (*.mdb)` ou `Microsoft Access Driver (*.mdb, *.accdb)`. Si aucun n'est trouvé, on affiche un message clair.
- **Version Jet :** Jet 3 (Access 97) et Jet 4 (Access 2000) sont tous deux supportés. La version est détectée par l'octet 0x14 de l'en-tête (0 = Jet 3, 1 = Jet 4, voir `outils/version_jet.py`) et affichée dans le profil.
- **Connexion en lecture seule et en accès partagé** pendant que le logiciel legacy tourne : `ReadOnly=1`, mot de passe `PWD` si fourni, fichier de groupe de travail `SystemDB` si `.mdw` fourni. Le fichier ne doit jamais être verrouillé en exclusif.
- **Volumétrie :** jusqu'à environ 25 ans d'écritures, donc des tables de plusieurs centaines de milliers de lignes. Une photo complète doit rester **en dessous de 60 s** sur un poste ordinaire. Si ce n'est pas tenable, c'est une ambiguïté à remonter. Le temps de photo est **mesuré et affiché** (par table et au total) dès le moteur ; aucune optimisation n'est faite avant une mesure sur la vraie base (AMB-002).
- **Encodage :** textes Jet décodés selon `encodage_texte` (défaut `cp1252`).
- **Interface :** Tkinter, en français, gros boutons, lisible par un non-technicien.

## 4. Entrées — `config.json`
Voir l'exemple dans `docs/formats/config.example.json`.

| Clé | Oblig. | Description |
|---|---|---|
| `base_test` | oui | Chemin du `.mdb` de TEST tracé |
| `mot_de_passe` | non | Mot de passe base (si non retiré) |
| `fichier_mdw` | non | Fichier groupe de travail + `utilisateur` / `mot_de_passe_mdw` |
| `instantane_reference` | oui (F10) | Copie fraîche servant à la réinitialisation |
| `chemins_interdits` | oui | Chemins de production. Le démarrage est refusé si `base_test` y figure (comparaison sur chemins normalisés, sans tenir compte de la casse, UNC inclus) |
| `fichier_fiches` | oui (F8) | Fichier JSON des fiches de scénarios |
| `dossier_sorties` | oui | Dossier de dépôt (local ou partage réseau) |
| `tables_ignorees` | non | Liste manuelle, ajoutée à la calibration (F3) |
| `encodage_texte` | non | Défaut `cp1252` |
| `delai_stabilisation_s` | non | Défaut 3. Attente après « Fin » avant la photo, pour laisser le legacy terminer ses écritures |

## 5. Interface — écrans

### 5.1 Écran principal
- Bandeau : base de TEST active, état de la connexion, date du dernier profilage. Si aucun profil n'existe : « Profil absent — lancer le profilage ».
- Liste des fiches avec leur statut (`à faire` / `faite` / `écart` / `annulée`), dérivé de la dernière trace de la fiche (voir §8.2).
- Boutons : **Choisir une fiche**, **Réinitialiser la base**, **Profiler la base**, **Calibrer le bruit**.

### 5.2 Exécution d'une fiche
- La fiche est affichée : titre, durée, prérequis, étapes numérotées avec case à cocher, référence de capture.
- **Début** prend la photo avant et une capture d'écran, puis active les cases.
- **Fin** attend le délai de stabilisation, prend la photo après et une capture, calcule le diff et génère le rapport.
- Champ libre **« Remarques / messages affichés »**, obligatoirement proposé avant de clôturer.
- **Annuler** (entre Début et Fin) : la trace est marquée `annulée` et conservée.
- Pendant le calcul, une barre de progression s'affiche et l'interface ne doit jamais sembler figée.

### 5.3 Fin de fiche
- Résumé lisible : « 3 tables modifiées, 4 lignes ajoutées, 1 modifiée ».
- **Alerte d'écart de saisie** si F8 détecte une valeur attendue introuvable (voir §7.4) : message simple, et proposition de réinitialiser puis rejouer.

## 6. Moteur

### 6.1 Architecture
```
traceur/
  moteur/        # pur Python, sans dépendance Windows — testable partout
    source.py      # interface SourceDonnees (lister_tables, schema, lire_lignes)
    normalisation.py  # normalisation des valeurs, empreintes (§6.2)
    instantane.py  # photo d'une base via une SourceDonnees
    diff.py        # comparaison de deux instantanés
    liens.py       # F6
    calcules.py    # F7
    profilage.py   # F2
  sources/
    access.py      # SourceDonnees via pyodbc/Jet
    sqlite.py      # SourceDonnees pour les tests
  ui/              # Tkinter
  rapports/        # JSON + HTML
  securite.py      # F1, F10
outils/
  version_jet.py   # version Jet d'un .mdb (octet 0x14)
  generer_mdb_test.py
```
Le moteur ne connaît que `SourceDonnees`. Les tests unitaires utilisent la source SQLite.

### 6.2 Instantané (F4)
Pour chaque table non ignorée :
- schéma : colonnes, types, clé primaire si déclarée ;
- `nb_lignes` et **empreinte de table** (hash stable de l'ensemble des empreintes de lignes, indépendant de l'ordre) ;
- empreintes de lignes, et contenu complet des lignes.

**Normalisation avant hash :** `None` devient un marqueur nul ; les dates sont écrites en ISO ; les montants (`Decimal`/`Currency`) en chaîne exacte ; les flottants en `repr` ; les binaires en hash du contenu ; les textes sont normalisés en NFC, **sans** trim (un espace final est une donnée).

Optimisation autorisée : si deux tables ont la même empreinte et le même nombre de lignes, on ne compare pas leur contenu.

### 6.3 Diff (F5)
Pour chaque table dont l'empreinte a changé (une table à empreinte, nombre de lignes et schéma identiques est ignorée) :
- **avec clé primaire déclarée :** appariement par clé. On obtient `insert`, `delete`, et `update` avec, pour chaque champ, `avant` → `apres`.
- **sans clé primaire :** on cherche une **clé candidate** issue du profilage (colonne ou couple de colonnes uniques et non nulles) et on l'utilise.
  - À défaut, on compare des **multiensembles d'empreintes de lignes**. On obtient `lignes_ajoutees` et `lignes_supprimees`.
  - Une paire ajoutée/supprimée qui diffère d'au plus 2 champs est proposée comme **`update_probable`**.
- Le changement de schéma entre deux photos est signalé à part (`schema_modifie`).

### 6.4 Profilage (F2)
Pour chaque table : nombre de lignes, colonnes, types déclarés et types observés, % de nuls, nombre de valeurs distinctes, min/max.

Le profilage détecte :
- les **clés candidates** : colonnes ou couples uniques et non nuls ;
- les **relations candidates** : colonne A dont les valeurs non nulles sont incluses à au moins 99 % dans une colonne clé candidate B, avec des types compatibles ; chaque relation reçoit un taux d'inclusion.

Sortie : `profil.json` et `profil.html` (dictionnaire des tables + graphe des relations rendu en SVG ou en Mermaid embarqué, **sans dépendance réseau**).

### 6.5 Calibration du bruit (F3)
Le traceur prend 2 photos espacées de N secondes (défaut 30) **sans aucune action**, avec le logiciel ouvert. Les tables qui changent sont proposées comme `tables_bruit` et l'utilisateur valide.

Pendant un diff, les tables de bruit sont rapportées à part (`bruit`), pas mêlées aux changements.

## 7. Interprétation

### 7.1 Lien saisie → colonne (F6)
Chaque fiche déclare des **valeurs saisies** typées (§9). Pour chacune, le traceur cherche les correspondances dans les lignes insérées ou modifiées.
- Correspondance exacte après normalisation de type : montant décimal, date (plusieurs formats), texte.
- Correspondances tolérées, chacune signalée avec son type : signe inversé, montant × 100 ou ÷ 100, date stockée en date-heure, texte tronqué ou en majuscules.

Le lien se fait **par valeur** : chaque lien porte la valeur saisie concernée (deux saisies d'un même champ d'écran donnent deux liens distincts). **Aucun lien automatique** n'est fait en V1 entre le texte libre des remarques (messages affichés) et les valeurs en base.

Résultat : `liens = [{champ_ecran, ecran, valeur, table, colonne, type_correspondance, confiance}]`.

Une valeur attendue mais introuvable produit l'**écart de saisie** (§5.3).

### 7.2 Champs calculés (F7)
Tout champ d'une ligne insérée ou modifiée **non expliqué par F6** est un champ calculé. Le traceur teste ces hypothèses, dans l'ordre, et retient toutes celles qui tiennent :

| Hypothèse | Test |
|---|---|
| `compteur` | Vaut max(colonne avant) + 1, ou + pas constant. Pour un texte : préfixe éventuel + suffixe numérique incrémenté, largeur conservée (ex. `0041` → `0042`, `ACH-0041` → `ACH-0042`) ; un texte entièrement numérique est le cas sans préfixe |
| `horodatage_systeme` | Date ou heure comprise dans l'intervalle [Début, Fin] |
| `somme_lignes` | Égale à la somme d'une colonne numérique des lignes liées insérées dans le même diff |
| `copie` | Égale à une valeur d'une autre table, lue dans la photo avant via une relation candidate |
| `constante` | Toujours la même valeur sur toute la table (voir profil) |
| `cumul_mis_a_jour` | Delta du champ égal à un montant saisi ou à son opposé |
| `inconnu` | Aucune hypothèse ne tient |

**Profil absent :** si aucun profil n'est disponible, les hypothèses qui en dépendent (`constante`, `copie`) sont désactivées et un avertissement est inscrit dans le rapport (`avertissements[]`).

Chaque hypothèse est **marquée comme hypothèse**, pas comme règle. La confirmation se fait plus tard, côté analyse.

### 7.3 Pas d'inférence inventée
Aucune autre heuristique ne doit être ajoutée sans passer par `SUIVI_AMBIGUITES.md`.

### 7.4 Écart de saisie
Une valeur attendue est introuvable, ou une valeur saisie diffère manifestement de la fiche (exemple : 1 243,56 trouvé au lieu de 1 234,56, même table et même colonne attendue). Le rapport porte alors le statut `ecart_saisie`.

## 8. Sorties
Arborescence dans `dossier_sorties` :
```
profil/                       profil.json, profil.html
calibration/                  bruit.json
traces/S-003_20261005-101522/
    trace.json                # format §8.1
    rapport.html              # lisible, autonome (CSS inline, pas de réseau)
    capture_debut.png
    capture_fin.png
    remarques.txt
index.html                    # liste des traces, statut, liens
```
Le journal `journal.log` est écrit **en local à côté de l'exécutable** et copié dans `dossier_sorties` à chaque dépôt. Il ne contient jamais de mot de passe.

L'écriture se fait d'abord dans un dossier temporaire local, puis le dossier est **déplacé en une fois** vers `dossier_sorties`. Si le partage est inaccessible, la trace reste en local et son dépôt est marqué `en_attente_depot` (§8.2), avec une nouvelle tentative au démarrage suivant.

### 8.1 `trace.json`
Voir l'exemple complet dans `docs/formats/trace.example.json`. Clés de premier niveau :
`format_version`, `fiche` (id, titre, valeurs_saisies), `execution` (debut, fin, poste, utilisateur_windows, statut, remarques), `base` (chemin, empreinte_fichier_avant), `changements[]`, `bruit[]`, `liens[]`, `champs_calcules[]`, `ecarts_saisie[]`, `schema_modifie[]`, `avertissements[]`.

Chaque élément de `changements[]` porte `table` et `cle_utilisee` (`type` : `primaire` | `candidate` | `aucune`, et `colonnes`), puis, comme dans l'exemple (qui fait foi) :
- table avec clé (primaire ou candidate) : `inserts[]`, `updates[]` (champ à champ : `colonne`, `avant`, `apres`), `deletes[]` ;
- table sans clé : `lignes_ajoutees[]`, `lignes_supprimees[]` ;
- dans les deux cas : `updates_probables[]`.

Valeurs : montants en chaîne décimale exacte, dates en ISO 8601, aucun flottant JSON.

### 8.2 Statuts
- `execution.statut` : `terminee` | `annulee` | `ecart_saisie`.
- Statut d'une fiche (écran principal), dérivé de sa dernière trace : aucune trace → `à faire` ; `terminee` → `faite` ; `ecart_saisie` → `écart` ; `annulee` → `annulée`.
- Dépôt : `deposee` | `en_attente_depot`, distinct du statut d'exécution (son stockage local est précisé en J5).

## 9. Fiches de scénarios — format d'entrée
Voir `docs/formats/fiches.example.json`. Une fiche contient :
`id`, `titre`, `lot`, `duree_min`, `prerequis[]`, `reinitialiser_avant` (bool), `etapes[]` (texte, `capture_ref` éventuelle), `valeurs_saisies[]` (`champ_ecran`, `ecran`, `valeur`, `type`: `montant|date|texte|code`), `a_noter[]`.

## 10. Réinitialisation (F10)
- Elle exige une confirmation explicite, avec un texte qui rappelle la base visée.
- Elle vérifie qu'aucun fichier de verrou actif n'existe à côté de la base de TEST (`.ldb` pour un `.mdb`, `.laccdb` pour un `.accdb`), c'est-à-dire que le logiciel legacy est fermé. Sinon elle refuse, avec un message.
- Elle copie `instantane_reference` vers `base_test` après les contrôles F1, puis vérifie le hash du résultat.
- Elle journalise l'opération dans `journal.log` (local, voir §8).

## 11. Critères de qualité
- Tests unitaires du moteur sur SQLite : tables avec et sans clé primaire, doublons, nuls, dates, décimaux, modification de schéma, chaque hypothèse de F7.
- Test d'intégration sur un `.mdb` synthétique généré par script sous Windows (ADOX via `pywin32`) : `outils/generer_mdb_test.py`.
- Aucune exception non gérée ne doit atteindre l'utilisateur. Les erreurs s'affichent en français, avec le détail dans `journal.log`.
