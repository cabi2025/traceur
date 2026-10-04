# J4 — Quoi installer et quoi lancer sur Windows

> **Terminal :** ces guides fonctionnent dans PowerShell (invite `PS C:\...>`) comme dans l'invite de commandes classique. Seule différence connue : pour afficher le code de sortie d'une commande, PowerShell utilise `$LASTEXITCODE` et cmd utilise `%ERRORLEVEL%`.

Ce guide vous fait valider le jalon J4 (accès Access en lecture seule, sécurité, réinitialisation) **sur un poste Windows**.
Le code a été écrit et testé sous Linux avec un faux pilote : **rien de ce qui suit n'a encore tourné sur un vrai Access**.
Chaque étape dit quoi taper et **quel résultat attendre**. Si un résultat diffère, arrêtez-vous et envoyez-moi
l'étape et le texte affiché.

> **Règle d'or :** ne mettez jamais le chemin de la base de production dans `base_test`.
> Tout ce guide commence par une **base synthétique** que le script crée lui-même.
> Seules les étapes 11 et 12 touchent votre copie de TEST, et uniquement en lecture (sauf la réinitialisation, étape 10, faite sur la base synthétique).

---

## 1. Installer Python 32 bits

Le pilote Access de Windows est un pilote **32 bits** : il faut Python **32 bits**.

1. Aller sur <https://www.python.org/downloads/windows/> et télécharger **« Windows installer (32-bit) »** de Python 3.11 ou 3.12.
2. Dans l'installateur, cocher **« Add python.exe to PATH »**, puis *Install Now*.
3. Ouvrir une nouvelle invite de commandes (`cmd`) et taper :

```bat
python -c "import struct,sys; print(sys.version); print(struct.calcsize('P')*8)"
```

**Résultat attendu :** une ligne `3.11.x ... [MSC v.... 32 bit (Intel)]` puis `32`.
Si vous lisez `64`, ce n'est pas le bon Python (désinstallez-le ou appelez le 32 bits par son chemin complet).

## 2. Récupérer le projet

```bat
mkdir C:\Traceur
cd C:\Traceur
git clone -b claude/charming-franklin-92qwrm https://github.com/cabi2025/traceur.git
cd traceur
```

(Sans `git` : sur GitHub, branche `claude/charming-franklin-92qwrm` → *Code* → *Download ZIP*, puis dézipper dans `C:\Traceur\traceur`.)

## 3. Installer les dépendances

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[windows,dev]"
```

Cela installe `pyodbc`, `pywin32`, `pytest`, `mypy` et le traceur lui-même.

**Vérification :**

```bat
python -c "import pyodbc, win32com.client; print('pyodbc', pyodbc.version)"
```

**Résultat attendu :** `pyodbc 5.x.x` (aucune erreur).

## 4. Vérifier le pilote ODBC Access

```bat
python -c "import pyodbc; print(pyodbc.drivers())"
```

**Résultat attendu :** une liste qui contient `'Microsoft Access Driver (*.mdb)'`
(éventuellement aussi `'Microsoft Access Driver (*.mdb, *.accdb)'`).

Si la liste ne contient aucun pilote Access :
- vous êtes en Python 64 bits → reprenez l'étape 1 ;
- ou le pilote manque → installer *Microsoft Access Database Engine 2016 Redistributable* **version 32 bits** (`AccessDatabaseEngine.exe`, site de Microsoft). Si Office 64 bits est installé, l'installateur 32 bits se plaint : lancer `AccessDatabaseEngine.exe /quiet` dans `cmd`. Puis relancer la commande ci-dessus.

## 5. Lancer les tests (rien d'Access à ce stade, sauf les tests d'intégration)

```bat
python -m pytest -q -rs
```

**Résultat attendu :** `245 passed` et **aucune ligne `SKIPPED`**.
(Sous Linux, ces mêmes tests donnent « 233 passed, 12 skipped » : les 12 sautés sont les tests d'intégration Access, qui ne peuvent tourner que chez vous.)
Si des tests sont sautés, la raison s'affiche (`pyodbc`/`pywin32` absent, pilote invisible, Python 64 bits) : corrigez et relancez.

## 6. Créer une base synthétique

```bat
python outils\generer_mdb_test.py C:\Traceur\test\synthetique.mdb --lignes 1000
```

**Résultat attendu :**

```
CLIENTS : 50 lignes
FACTURES : 1000 lignes
LIGNES : 2000 lignes
COMPTEURS : 3 lignes
SESSIONS : 3 lignes
Base créée : C:\Traceur\test\synthetique.mdb (Jet 4)
Lignes : CLIENTS 50, FACTURES 1000, LIGNES 2000, COMPTEURS 3, SESSIONS 3 — total 3056
```

Le fichier n'est jamais écrasé : s'il existe déjà, le script le dit. Option `--jet3` : même base au format Access 97.

## 7. Lire la version Jet (AMB-001)

```bat
python outils\version_jet.py C:\Traceur\test\synthetique.mdb
```

**Résultat attendu :** `Jet 4 (octet 0x14 = 1)`.
(Avec une base créée par `--jet3` : `Jet 3 (octet 0x14 = 0)`.)
Refaites la même commande sur **une copie de votre vraie base** et notez le résultat : c'est ce qui clôt l'AMB-001.

## 8. Préparer `config.json` pour la base synthétique

```bat
mkdir C:\Traceur\reference
copy C:\Traceur\test\synthetique.mdb C:\Traceur\reference\synthetique_reference.mdb
copy docs\formats\config.example.json config.json
notepad config.json
```

Remplacez le contenu par (les antislashs sont **doublés** dans un fichier JSON, et le fichier doit être enregistré en UTF-8) :

```json
{
  "base_test": "C:\\Traceur\\test\\synthetique.mdb",
  "mot_de_passe": "",
  "fichier_mdw": "",
  "utilisateur": "",
  "mot_de_passe_mdw": "",
  "instantane_reference": "C:\\Traceur\\reference\\synthetique_reference.mdb",
  "chemins_interdits": ["C:\\Traceur\\production\\compta.mdb"],
  "fichier_fiches": "C:\\Traceur\\traceur\\docs\\formats\\fiches.example.json",
  "dossier_sorties": "C:\\Traceur\\sorties",
  "tables_ignorees": [],
  "encodage_texte": "cp1252",
  "delai_stabilisation_s": 3
}
```

`config.json` est ignoré par git : il ne sera jamais versionné.

## 9. Diagnostic complet (lecture seule)

```bat
python outils\diagnostic.py --config config.json --photo --profil
```

**Résultat attendu** (les durées varient, les nombres de lignes non) :

```
[1/6] Python
      OK      Python 3.11.x, 32 bits
[2/6] pyodbc et pilote ODBC Access
      OK      pyodbc 5.x.x — pilote retenu : Microsoft Access Driver (*.mdb)
[3/6] Configuration (config.json)
      OK      base_test            : C:\Traceur\test\synthetique.mdb
      ...
      OK      mot de passe         : aucun
[4/6] Contrôles de sécurité au démarrage (F1)
      OK      la base de TEST n'est ni une base interdite, ni l'instantané de référence
[5/6] Fichier de la base de TEST
      OK      0.x Mo — format : Jet 4
      info    fichier de verrou absent : C:\Traceur\test\synthetique.ldb
[6/6] Connexion en lecture seule et lecture des tables
      OK      5 tables lisibles (connexion ReadOnly=1)
              LIGNES                            2000 lignes   clé primaire : aucune
              FACTURES                          1000 lignes   clé primaire : NUM
              CLIENTS                             50 lignes   clé primaire : ID
              COMPTEURS                            3 lignes   clé primaire : aucune
              SESSIONS                             3 lignes   clé primaire : ID
      OK      3056 lignes au total ; 7 relations candidates ; profilage en 0.x s
      OK      profil écrit : diagnostic_sorties\profil\profil.html
      Photo : 5 tables, 3056 lignes en 0.xx s
      ...
      OK      temps de photo : 0.x s (objectif < 60 s) — OK
      OK      connexion fermée

Diagnostic terminé : tout est OK.
```

- Les clés primaires attendues sont lues même si le pilote ne gère pas `SQLPrimaryKeys` (le journal contient alors une ligne « clé primaire lue via les index uniques »).
- Le nombre de relations candidates peut différer de 7 : plusieurs sont de fausses relations connues (AMB-016), c'est normal.
- Ouvrez `diagnostic_sorties\profil\profil.html` dans le navigateur : tables, clés candidates et graphe doivent s'afficher, **sans connexion internet**.
- Ouvrez `journal.log` (dossier courant) : vous devez y voir la ligne `Connexion en lecture seule : DRIVER=...;ReadOnly=1;Exclusive=0;`.

## 10. Tests d'intégration Access (le cœur de J4)

```bat
python -m pytest tests\test_integration_access.py -v -rs -s
```

**Résultat attendu : `12 passed`, 0 skipped.** Ce que chaque test prouve :

| Test | Preuve |
|---|---|
| `test_python_32_bits` | Python 32 bits |
| `test_pilote_et_version_jet` / `test_version_jet3_detectee` | pilote vu ; octet 0x14 → « Jet 4 » / « Jet 3 » |
| `test_lecture_du_schema_et_des_valeurs` | tables, clé primaire, `CURRENCY` → `Decimal` exact, dates, accents (« Société Générale ») |
| `test_profil_de_la_base_synthetique` | clés candidates et relations retrouvées |
| `test_aucune_ecriture_possible_via_la_connexion_du_traceur` | **un INSERT et un DELETE sont refusés par le pilote** ; le fichier `.mdb` a le **même SHA-256** avant/après |
| `test_diff_d_une_modification_faite_par_un_script_tiers` | un autre processus écrit pendant que le traceur est connecté ; le diff voit insert, update, delete, lignes sans clé, table de bruit |
| `test_la_connexion_du_traceur_ne_bloque_pas_l_ecriture_tierce` | accès partagé, aucun verrou exclusif |
| `test_cache_jet_connexion_longue` | **mesure** (AMB-027) : voir ci-dessous |
| `test_base_protegee_et_mot_de_passe_absent_du_journal` | base avec mot de passe : accès OK, mauvais mot de passe → message clair, **mot de passe absent de `journal.log`** |
| `test_demarrage_refuse_la_base_de_production` | refus de démarrer, même avec une casse ou une forme de chemin différente |
| `test_reinitialisation_reelle_refusee_tant_que_la_base_est_ouverte` | **refus quand le fichier `.ldb` est présent**, puis copie vérifiée par hash une fois la base fermée |

Le test `test_cache_jet_connexion_longue` affiche une ligne de ce type :

```
connexion longue : avant=200, immédiat=?, après 6 s=?, connexion rouverte=201
```

**Copiez-moi cette ligne telle quelle** : elle dit si une connexion ouverte voit tout de suite les écritures d'un autre programme (AMB-027). Seul « connexion rouverte=201 » est contrôlé par le test.

Si le test sur le `.mdb` inchangé échoue (SHA-256 différent), **ne continuez pas** : envoyez-moi le message, c'est précisément ce que J4 doit exclure.

## 11. Contrôle de sécurité : le refus de démarrer

Ce test ne touche à aucune base. Faites une copie de `config.json` où `base_test` est **identique** à l'entrée de `chemins_interdits` :

```bat
copy config.json config_refus.json
notepad config_refus.json
```

Dans `config_refus.json`, mettez `"base_test": "C:\\Traceur\\production\\compta.mdb"` (la même valeur que dans `chemins_interdits`), puis :

```bat
python outils\diagnostic.py --config config_refus.json
echo $LASTEXITCODE        # PowerShell (l'invite commence par « PS »)
echo %ERRORLEVEL%         # invite de commandes classique (cmd)
```

**Résultat attendu :** l'étape 4 affiche `ÉCHEC   DÉMARRAGE REFUSÉ : la base de TEST indiquée est une base de PRODUCTION`, le diagnostic s'arrête avant l'étape 5, et le code de sortie vaut `1` (`$LASTEXITCODE` sous PowerShell, `%ERRORLEVEL%` sous cmd : sous PowerShell, `%ERRORLEVEL%` s'afficherait tel quel, sans valeur).
Essayez aussi avec la même valeur écrite autrement (`c:/traceur/PRODUCTION/compta.mdb`) : même refus.
**Conseil important :** dans `chemins_interdits`, listez **le nom ET l'adresse IP** du serveur de production (par exemple `\\\\SERVEUR\\Compta\\compta.mdb` **et** `\\\\192.168.1.10\\Compta\\compta.mdb`), et le lecteur réseau s'il y en a un. Le traceur résout les noms de serveur en adresses IP avant de comparer ; si cette résolution échoue (réseau coupé, nom inconnu), il compare seulement les textes et écrit un avertissement dans `journal.log` : seule la liste du nom ET de l'IP protège alors.
Dernier essai : `base_test` = `instantane_reference` → refus « même fichier que l'instantané de référence ».

## 12. Réinitialisation à la main (sur la base synthétique)

```bat
python outils\simuler_logiciel.py C:\Traceur\test\synthetique.mdb
python outils\diagnostic.py --config config.json --reinitialiser
```

**Résultat attendu :**
- la 1re commande affiche un JSON (`{"facture": 2001, "montant": "1234.56", ...}`) : la base de TEST a été modifiée ;
- la 2e fait les 6 étapes, puis affiche le texte « Vous allez ÉCRASER la base de TEST : … » et attend. Tapez `non` : `Réinitialisation annulée : rien n'a été modifié.` ; relancez et tapez `OUI` : `copie vérifiée (… octets, sha256:…)`.

Vérification : `certutil -hashfile C:\Traceur\test\synthetique.mdb SHA256` et la même commande sur `C:\Traceur\reference\synthetique_reference.mdb` donnent **le même hash**.
Si un `.ldb` est présent (logiciel ouvert quelque part), la réinitialisation est refusée avec un message qui nomme le fichier.

## 13. Sur votre vraie base de TEST (copie)

Seulement quand les étapes 5 à 12 sont vertes. Créez un second fichier, `config_reel.json`, avec :
- `base_test` : la copie de TEST ;
- `chemins_interdits` : **tous** les chemins de la base de production (forme UNC si possible) ;
- `instantane_reference` : une copie fraîche de la base de TEST ;
- `mot_de_passe` si la base en a un (pas `fichier_mdw` en même temps : AMB-026).

Puis, **en lecture seule** :

```bat
python outils\version_jet.py "chemin\de\la\copie_de_test.mdb"
python outils\diagnostic.py --config config_reel.json --photo --profil
```

Lancez aussi la sonde des clés primaires (lecture seule) : elle montre ce que le pilote répond pour **chaque table de votre base** et quels index existent. C'est ce qui permet de savoir si les clés primaires de votre base sont reconnues (AMB-028) :

```bat
python outils\sonder_pilote.py "chemin\de\la\copie_de_test.mdb"
```

Pour chaque table, une ligne `statistics : index='PrimaryKey' ...` signifie que sa clé primaire est reconnue ; sinon le traceur utilise les clés candidates du profilage (le diff reste correct) et `journal.log` contient « Table X : aucun index « PrimaryKey » ; index vus : … ».

Notez : la version Jet, le nombre de tables et de lignes, **le temps de photo** (AMB-002, objectif < 60 s) et ouvrez le `profil.html` produit.

## À m'envoyer

1. Le résultat de l'étape 5 (`pytest`) et de l'étape 10 (`12 passed` ou le détail des échecs).
2. La ligne « connexion longue : … » de l'étape 10.
3. Le texte complet de l'étape 9, puis de l'étape 13 (copiez-collez la console).
4. Le fichier `journal.log` (il ne contient aucun mot de passe ; vérifiez-le quand même d'un coup d'œil).
5. La sortie de `version_jet.py` sur la copie réelle.

## Dépannage

| Message | Cause probable | Que faire |
|---|---|---|
| `Aucun pilote ODBC Access n'a été trouvé` | Python 64 bits, ou pilote absent | étapes 1 et 4 |
| `Format de base non reconnu` | fichier non `.mdb`, ou base trop récente pour le pilote | `version_jet.py` sur le fichier |
| `Fichier de base introuvable` | mauvais chemin, partage réseau non connecté | tester le chemin dans l'explorateur |
| `La base est ouverte en mode exclusif` | un programme l'a ouverte en exclusif | le fermer |
| `Mot de passe incorrect` | `mot_de_passe` faux ou absent | corriger `config.json` |
| `Droits insuffisants` | groupe de travail (`.mdw`) ou utilisateur mal renseigné | vérifier `fichier_mdw`, `utilisateur` |
| `RÉINITIALISATION REFUSÉE … .ldb` | la base est utilisée, ou un arrêt brutal a laissé le fichier | fermer le logiciel sur tous les postes ; vérifier avant de supprimer le `.ldb` à la main |
| `clé primaire : aucune` pour une table qui en a une (étape 9), ou test de clé primaire en échec | le pilote Jet ne gère pas `SQLPrimaryKeys` ; le traceur lit alors l'index « PrimaryKey » (AMB-028) | `python outils\sonder_pilote.py <base.mdb>` et m'envoyer la sortie |
| La connexion échoue sans raison claire sur un partage | le moteur Jet doit **créer** le fichier `.ldb` à côté de la base | donner le droit d'écriture sur le **dossier** (ce n'est pas une écriture dans la base) |

À savoir : pendant que le traceur est connecté, Windows/Jet crée et supprime tout seul le petit fichier `.ldb` à côté de la base (verrou partagé). Le fichier `.mdb` lui-même n'est jamais modifié : c'est ce que vérifie le test de l'étape 10.
