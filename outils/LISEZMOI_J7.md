# J7 — Construire et essayer `traceur.exe` (Windows)

Ce guide se déroule sous Windows, **pas à pas**. Après chaque étape, vous avez un **résultat attendu**. Si ce n'est pas ce que vous voyez, arrêtez-vous et envoyez-moi la capture ou le texte.

Les terminaux : **A** = le terminal du `.venv` (Python 32 bits) dans `C:\Traceur\traceur`. Pour l'étape 5, un **poste propre** (sans Python) est idéal : un autre PC, ou *Bac à sable Windows* si votre Windows le propose.

## 0. Mettre à jour et tester
Terminal A :
```
cd C:\Traceur\traceur
.venv\Scripts\activate
git pull
python -m pytest -q -rs
```
**Attendu :** `416 passed`, **aucune ligne `SKIPPED`**.

## 1. Vérifier l'environnement de construction
```
pip install -e .[access,ui,build]
python outils\construire_exe.py --verifier
```
**Attendu :** `Environnement de construction : OK (Windows, Python 32 bits, modules présents).` (Si « Python 32 bits requis » s'affiche : vous n'êtes pas dans le bon `.venv`.)

## 2. Construire
```
python outils\construire_exe.py
```
Cela prend 1 à 3 minutes. **Attendu**, en fin de sortie :
```
Construit : C:\Traceur\traceur\dist\traceur.exe (… Ko)
SHA-256   : …
Architecture de l'exécutable : 32 bits
```
Notez la taille et le SHA-256 (envoyez-les-moi). Si une erreur s'affiche, envoyez-moi les 30 dernières lignes.

*Si l'antivirus bloque ou met en quarantaine `traceur.exe`* (il disparaît, ou une alerte s'affiche) : notez le nom de l'antivirus et le message, ajoutez une exclusion pour le dossier (voir `GUIDE_INSTALLATION.md`, section 7), puis, en repli, construisez en dossier : `python outils\construire_exe.py --onedir` → `dist\traceur\traceur.exe`. Dans ce cas, **copiez tout le dossier `dist\traceur\`** à l'étape 3 au lieu du seul `.exe`.

## 3. Préparer un dossier de travail propre
```
mkdir C:\TraceurExe
copy dist\traceur.exe C:\TraceurExe\
copy docs\formats\fiches_synthetique.json C:\TraceurExe\fiches.json
copy config.json C:\TraceurExe\config.json
```
Ouvrez `C:\TraceurExe\config.json` et changez seulement :
```
"fichier_fiches": "C:\\TraceurExe\\fiches.json",
"dossier_sorties": "C:\\TraceurExe\\sorties"
```
(les chemins `base_test` et `instantane_reference` de la base synthétique restent ceux de vos essais précédents).

## 4. Lancer l'exécutable (sur votre poste de développement)
Double-cliquez `C:\TraceurExe\traceur.exe`.

**Attendu :**
1. Aucune fenêtre noire (console) n'apparaît ; la fenêtre du Traceur s'ouvre.
2. Bandeau : « Base de TEST active : C:\Traceur\test\synthetique.mdb » et « Connectée en lecture seule (5 tables) » en vert.
3. `C:\TraceurExe\journal.log` apparaît **à côté de l'exe** (et non dans un autre dossier).
4. Les deux fiches S-SYN-01 et S-SYN-02 sont listées.

Faites alors le parcours court :
- **Réinitialiser la base** → Oui → « Base réinitialisée ».
- **Profiler la base** (toujours *après* une réinitialisation : voir AMB-037) → `profil.html` (dans `C:\TraceurExe\sorties\profil\`).
- **S-SYN-01** : Choisir → Début → attendre que **Fin** soit actif → dans le terminal A `python outils\simuler_logiciel.py C:\Traceur\test\synthetique.mdb` (une fois) → Fin → remarque libre → **Ouvrir le rapport**.

**Attendu :** « 5 tables modifiées, 3 lignes ajoutées, 2 modifiées, 1 supprimée » ; rapport complet avec les deux captures ; dossier `C:\TraceurExe\sorties\traces\S-SYN-01_…` et `index.html`.

Fermez la fenêtre (croix).

## 5. Poste sans Python (le test d'acceptation)
Copiez **seulement** `traceur.exe` et un `config.json` adapté (chemins valides **sur ce poste** : une base de test, une copie de référence, un dossier de sorties) sur un poste où Python n'est **pas** installé, puis double-cliquez l'exe.

**Attendu :** la même ouverture qu'à l'étape 4 (connexion en lecture seule). Si la fenêtre affiche « Aucun pilote ODBC Access trouvé », envoyez-moi la capture : cela veut dire que ce poste n'a pas le pilote 32 bits (`C:\Windows\SysWOW64\odbcad32.exe` → onglet *Pilotes*).

Si vous n'avez pas de poste propre sous la main, faites au moins ce test partiel sur votre poste : ouvrez un **nouveau** terminal (hors `.venv`), tapez `where python` (notez s'il est trouvé), puis lancez `C:\TraceurExe\traceur.exe` depuis l'explorateur : l'exe doit fonctionner sans l'environnement `.venv`.

## 6. Refus de démarrer avec l'exe
Copiez `C:\TraceurExe\config.json` en `C:\TraceurExe\config_prod.json`, mettez `base_test` = une valeur de `chemins_interdits`, et lancez dans un terminal :
```
C:\TraceurExe\traceur.exe --config C:\TraceurExe\config_prod.json
```
**Attendu :** boîte « DÉMARRAGE REFUSÉ : la base de TEST indiquée est une base de PRODUCTION ». Aucune fenêtre ne s'ouvre.

## 7. Mesurer le temps d'une photo sur une grosse base synthétique
Terminal A :
```
python outils\generer_mdb_test.py C:\Traceur\test\gros.mdb --lignes 50000
copy config.json config_gros.json
```
Dans `config_gros.json`, mettez `"base_test": "C:\\Traceur\\test\\gros.mdb"` (le reste ne change pas) puis :
```
python outils\diagnostic.py --config config_gros.json --photo
```
**Attendu :** la génération prend quelques minutes (150 000 lignes environ) ; le diagnostic affiche le temps de la photo par table et au total (objectif : moins de 60 s). **Envoyez-moi cette sortie.** Supprimez `gros.mdb` ensuite (c'est une base synthétique, `.gitignore` l'exclut du dépôt).

**Important : la mesure qui compte est celle de la vraie copie, faite depuis le poste du comptable, avec la base sur le partage réseau** (étape 8). La grosse base synthétique locale ci-dessus ne donne qu'un ordre de grandeur : un disque local est bien plus rapide qu'un partage. Pour la mesure finale, mettez `base_test` sur le **chemin réseau réel** (par exemple `\\SERVEUR\Compta_TEST\copie.mdb`, qui s'écrit `"\\\\SERVEUR\\Compta_TEST\\copie.mdb"` dans `config.json`).

## 8. Sur la vraie base (quand vous pouvez, avec une **copie**)
Ces trois mesures règlent des points encore ouverts ; elles ne modifient jamais la base :
```
python outils\version_jet.py <copie.mdb>                 (AMB-001 : version Jet)
python outils\sonder_pilote.py <copie.mdb>               (AMB-028 : noms des clés primaires)
python outils\diagnostic.py --config config.json --photo (AMB-002 : durée de photo réelle)
```
**Faites ces mesures depuis le poste du comptable, avec la copie de la base placée sur le partage réseau** (le chemin que le comptable utilisera), pas depuis votre poste de développement ni avec un fichier local : la durée de photo dépend du réseau et du poste. Si le comptable n'a pas Python, lancez-les depuis votre poste *connecté au même partage*, en le notant dans votre retour.
Pour valider le poste du comptable, faites ensuite la fiche **S-000** (`GUIDE_INSTALLATION.md`, section 5).

## 9. Ce que je vous demande en retour
1. Le résultat de l'étape 0 (`416 passed`).
2. Étape 2 : taille, SHA-256, « 32 bits ».
3. Étape 4 : capture de la fenêtre ouverte et du rapport.
4. Étape 5 : le résultat sur un poste propre (ou le test partiel).
5. Étape 7 : la sortie de `diagnostic.py --photo`.
6. Une relecture de `GUIDE_COMPTABLE.md` (une page) : ce qui est incompréhensible ou faux.
