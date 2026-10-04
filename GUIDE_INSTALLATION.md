# Guide d'installation du Traceur (responsable technique)

Public : la personne qui prépare le poste du comptable. Le comptable, lui, lit `GUIDE_COMPTABLE.md`.

## 1. Ce qu'il faut
- Un poste **Windows 10 ou 11**. **Aucune installation de Python** n'est nécessaire pour utiliser `traceur.exe`.
- Le pilote ODBC 32 bits « Microsoft Access Driver (*.mdb) » : il est **fourni avec Windows**, rien à installer. (`traceur.exe` est un programme 32 bits pour cette raison.)
- Un **dossier de TEST** contenant une copie de la base : c'est la base que le logiciel de comptabilité utilise pendant les fiches (`base_test`).
- Un **instantané de référence** : une copie *fraîche* de cette base, à un autre endroit (`instantane_reference`). La « réinitialisation » copie ce fichier sur la base de TEST. Ne l'ouvrez jamais avec le logiciel.
- Un **dossier de sorties** (local ou partage réseau) où les rapports sont déposés (`dossier_sorties`).
- Les fiches de scénarios (`fichier_fiches`, JSON), facultatif au premier essai : sans fiches, seuls « Profiler » et « Calibrer » fonctionnent.

> Aucune donnée réelle n'est versionnée dans le dépôt. Les copies de bases, `config.json` et les sorties restent sur les postes.

## 2. Dossier de travail
Créez par exemple `C:\Traceur\` (ou un dossier propre à l'utilisateur) et copiez-y :

```
traceur.exe
config.json          ← à partir de docs\formats\config.example.json
fiches\lot1.json     ← vos fiches (voir docs\formats\fiches.example.json)
```

À côté de `traceur.exe`, le programme crée lui-même : `journal.log`, `traces_locales\`, `donnees_locales\` (profil et calibration mémorisés). Lancer `traceur.exe --config autre.json` permet d'utiliser une autre configuration.

## 2 bis. Préparer le dossier de TEST (phase 1 des sessions)
**Contexte.** Le logiciel de comptabilité ouvre un **catalogue** (`catalogue.mdb`), situé dans le même dossier que les dossiers `.mdb` et trouvé automatiquement par le logiciel. Le catalogue liste les sociétés et les exercices ; chaque **dossier** `.mdb` est une société + un exercice.

**Périmètre figé de la phase 1** (décisions du 2026-10-04) : **une seule société, un seul exercice**, dans un dossier TEST. « Figé » veut dire choisi et fixe, **pas clôturé** : l'exercice doit rester **ouvert à la saisie**. Le dossier TEST est une **copie d'un exercice réel récent et encore ouvert** (vrais comptes, tiers, journaux). `base_test` est le chemin fixe de ce dossier, écrit en dur dans `config.json` : le Traceur n'a besoin d'aucun autre chemin.
- **Lots de fiches couverts : 1a, 2, 3 et 4.** Le lot 1a est la création d'un compte, d'un tiers, d'un journal ; le lot 2 les saisies ; le lot 3 les traitements ; le lot 4 les états.
- **Lots reportés : 1b et 5.** Le lot 1b est la création d'une société ou d'un exercice ; le lot 5 la clôture annuelle et l'ouverture du nouvel exercice. Ils nécessitent de tracer le catalogue (AMB-038, ouverte).

**Limite à connaître.** Le Traceur ne regarde que `base_test`. Il ne voit **pas** les écritures que le logiciel ferait dans le catalogue. C'est pourquoi l'étape 5 ci-dessous contrôle la date de modification du catalogue.

**Réserve pour le lot 1a.** Un plan comptable peut être **partagé** entre les sociétés, donc stocké dans le catalogue. Si la date de modification de `catalogue.mdb` change pendant S-000 **ou pendant une fiche du lot 1a**, le lot 1a passe en **reporté** (comme 1b) : arrêtez et prévenez le responsable du projet.

**Préparation, dans cet ordre :**
1. **Copier un exercice réel ouvert** vers le dossier TEST. Le fichier obtenu est celui que désigne `base_test`. *(Fermez le logiciel sur tous les postes avant de copier.)*
2. **Le déclarer dans le catalogue** sous le nom **ZZ-TEST TRACEUR**, avec la fonction du logiciel prévue pour cela. **[À compléter : menu ou fonction exacte du logiciel pour ajouter une société/un exercice existant.]** Cette étape modifie le catalogue : c'est voulu et ponctuel, et elle précède la mesure de l'étape 5. **C'est ici que vous choisissez où se trouve le dossier TEST** (deux cas) :
   - **Cas A (préféré) : sous-dossier séparé** (par exemple `…\Compta\TEST\`), si le logiciel accepte de déclarer un dossier situé ailleurs que dans le dossier de production. Dans `config.json`, `chemins_interdits` garde alors le **dossier de production entier** (par exemple `\\SERVEUR\Compta\`) : tout ce qu'il contient est interdit, et le dossier TEST, situé à part, ne l'est pas. Ajoutez aussi l'adresse IP du serveur (voir section 3).
   - **Cas B : même dossier que la production**, si le logiciel ne sait pas déclarer un dossier situé ailleurs. Le dossier TEST est alors dans un dossier de production : `chemins_interdits` ne peut plus contenir ce dossier (le Traceur refuserait de démarrer), il doit lister **un par un** le **catalogue** et **chaque dossier réel** (exercice de production). **Rappel : ajouter tout nouveau dossier de production à `chemins_interdits`** (nouvelle société, nouvel exercice, copie, restauration), sans quoi il ne serait pas protégé. Le fichier TEST (`base_test`) ne doit **jamais** figurer dans la liste.
   - Notez le cas retenu (A ou B) et la liste de `chemins_interdits` correspondante.
3. **Vérifier que l'exercice accepte une saisie** : ouvrez ZZ-TEST TRACEUR et faites une saisie d'essai ; puis **supprimez cette saisie d'essai, avant l'étape 4**. **Notez ce que le logiciel affiche à l'ouverture, en particulier dans la barre de titre** (`*** <SOCIÉTÉ> Exercice <AAAA> Utilisateur <PROFIL> ***`, voir `docs/CARTE_ECRANS.md` §1) : c'est le repère que verra le comptable (`GUIDE_COMPTABLE.md`, « Avant de commencer »).
   - Si le logiciel affiche **« ZZ-TEST TRACEUR »** : le repère est ce nom.
   - Si le logiciel affiche le **nom de la société réelle** (contenu dans le dossier copié) : **renommez la société dans le dossier TEST**, avec les paramètres société du logiciel, par exemple en « ZZ-TEST TRACEUR ». Faites-le **avant l'instantané de référence** (étape 4), sinon la réinitialisation recopie l'instantané et efface le nouveau nom. Rouvrez et vérifiez que le nouveau nom s'affiche.
   - Si ce renommage est **impossible** : le repère est le nom choisi dans la liste des sociétés à l'ouverture (**ZZ-TEST TRACEUR**) ; dites-le au comptable (étape 1 de son guide).
4. **Prendre l'instantané de référence** : fermez le logiciel, puis copiez le fichier TEST vers `instantane_reference` (un autre fichier, ailleurs). La réinitialisation recopie ce fichier sur `base_test` : l'état de référence est donc celui d'après les étapes 1 à 3 (saisie d'essai supprimée, société renommée si possible).
5. **Surveiller le catalogue.** Notez la **date de modification de `catalogue.mdb`** (clic droit → Propriétés, ou `dir catalogue.mdb`) **avant** la fiche S-000 (section 5) et **après**. **Si elle change : arrêtez et prévenez le responsable du projet** (le logiciel écrit dans le catalogue de production : AMB-038 est à rouvrir immédiatement). Faites le même contrôle avant et après **chaque fiche du lot 1a** (voir la réserve ci-dessus).
   - *Conseil (témoin) :* notez aussi la date après avoir simplement ouvert et fermé le logiciel sur ZZ-TEST TRACEUR **sans rien saisir**, pour savoir si l'ouverture seule modifie le catalogue.

**Aussi :**
- **Données réelles.** Le dossier TEST est une copie de données réelles : les rapports, les captures d'écran et `profil.html` contiennent de vrais montants, comptes et noms de tiers. Traitez le dossier de sorties comme confidentiel.
- **`chemins_interdits`** doit contenir le chemin de l'exercice de **production** et celui du catalogue de production (cas A : le dossier de production entier ; cas B : les fichiers un par un).
- Le comptable choisit **ZZ-TEST TRACEUR** dans la liste des sociétés du logiciel, jamais sa société habituelle.

## 2 ter. Pont avec la gestion commerciale (GC) : fiches E-2.07.x **interdites** pour l'instant
La gestion commerciale (GC), du même éditeur, est une base **SQL Server** (`192.168.16.99`). Le pont (menu E-2.07.x) **écrit dans les deux bases** : dans la GC (Journal et Pièce de la facture) et dans la comptabilité. Le Traceur V1 ne voit que le dossier comptable. **Les fiches E-2.07.x sont donc interdites** tant que (1) la base `GC_TEST` n'existe pas et que (2) le traçage multi-bases n'est pas livré (AMB-038, ouverte, non codée).

**Règles de sécurité :**
- **Le paramétrage du pont (écran E-7.08) ne se modifie jamais dans la comptabilité de production.** Dans le dossier TEST, E-7.08 pointe au départ vers la GC de **production** : un transfert lancé depuis le dossier TEST lirait la vraie GC et pourrait y écrire.
- **Le serveur SQL `192.168.16.99` n'est jamais redémarré.** Le Traceur n'y accédera qu'à `GC_TEST`, en **lecture seule** (rôle `db_datareader`, authentification Windows). Les bases GC de production sont **interdites**, comme `chemins_interdits` l'est pour les `.mdb`.
- **Les captures de E-7.08 masquent le champ mot de passe.** Attention : le Traceur prend des captures de tous les écrans à Début et à Fin ; **ne laissez pas E-7.08 ouvert** à ces moments (AMB-039).

**Préparation TEST du pont, dans cet ordre :**
1. **Copier la base GC 2026 en `GC_TEST`** (sauvegarde/restauration SQL Server, faite par l'administrateur de la base ; jamais d'action sur la base de production autre qu'une sauvegarde).
2. **Copier le dossier compta** : c'est le dossier TEST préparé à la section 2 bis.
3. **Dans le dossier TEST uniquement**, régler E-7.08 (bloc « GC principale ») sur **`GC_TEST`** / **2026**. **Vérifiez la barre de titre avant de valider** : elle doit afficher le dossier TEST (`*** ZZ-TEST TRACEUR Exercice AAAA Utilisateur … ***`), pas la société de production.
4. **Prendre les instantanés de référence** : le **dossier TEST** (à **reprendre après l'étape 3**, car le réglage de E-7.08 fait désormais partie de l'état de référence) **et une sauvegarde de `GC_TEST`**.

*Hors périmètre* (inutilisés, décisions du 2026-10-04) : les autres blocs de E-7.08 (minoterie, briqueterie, gaz, hôtel, clinique) et les imports Excel E-7.12, E-7.13, E-7.14, E-7.16.

## 3. `config.json`
| Clé | Obligatoire | Rôle |
|---|---|---|
| `base_test` | oui | Chemin du `.mdb` de **TEST** |
| `instantane_reference` | oui | Copie fraîche, source de la réinitialisation |
| `chemins_interdits` | oui | Chemins de la **production**. Mettez le nom du serveur **et** son adresse IP (`\\SERVEUR\Compta\compta.mdb`, `\\10.0.0.5\Compta\compta.mdb`) |
| `dossier_sorties` | oui | Dépôt des rapports |
| `fichier_fiches` | non | Fichier JSON des fiches |
| `mot_de_passe` | non | Mot de passe de la base (déconseillé : retirez-le de la copie de TEST) |
| `fichier_mdw`, `utilisateur`, `mot_de_passe_mdw` | non | Groupe de travail Access (incompatible avec `mot_de_passe`) |
| `tables_ignorees` | non | Tables à ignorer en plus de la calibration |
| `encodage_texte` | non | Défaut `cp1252` |
| `delai_stabilisation_s` | non | Défaut 3 : attente après « Fin » avant la photo |

Dans le JSON, chaque `\` s'écrit `\\` (exemple : `"C:\\Traceur\\test\\compta_test.mdb"`).

**Règles de sécurité appliquées au démarrage (non contournables) :** refus si `base_test` figure dans `chemins_interdits` ou dans un dossier interdit ; refus si `base_test` et `instantane_reference` désignent le même fichier. Le Traceur ouvre la base **en lecture seule** ; la seule écriture sur un `.mdb` est la réinitialisation (copie vers `base_test` uniquement). Les mots de passe ne sont jamais écrits dans le journal ni dans les rapports.

## 4. Premier démarrage
1. Double-cliquez `traceur.exe`. Si Windows SmartScreen affiche un avertissement (programme non signé), cliquez « Informations complémentaires » puis « Exécuter quand même ».
2. Le bandeau doit afficher **« Connectée en lecture seule (N tables) »** en vert.
3. **Réinitialisez la base** (bouton « Réinitialiser la base »), *puis* cliquez **Profiler la base** : le profil doit être pris sur l'état de référence, reproductible (sur une petite table, des valeurs qui changent d'une saisie à l'autre peuvent rendre fortuitement unique une colonne qui ne l'est pas d'habitude, et fausser la clé retenue : AMB-037). Un `profil.html` est produit dans le dossier de sorties (dictionnaire des tables, clés, relations candidates).
4. Cliquez **Calibrer le bruit** : attendez le décompte **sans toucher à la base ni au logiciel**. Le Traceur propose les tables qui changent toutes seules (journaux, verrous…).

## 5. Fiche de validation du poste « S-000 » (à faire une fois par poste)
But : vérifier que le délai de stabilisation (`delai_stabilisation_s`, 3 s par défaut) suffit pour que le logiciel de comptabilité ait fini d'écrire quand le Traceur prend la photo « après ».

**Avant et après S-000, notez la date de modification de `catalogue.mdb`** (section 2 bis, étape 5).

La fiche est dans `docs\formats\fiche_S000.json` (une saisie simple : créer un tiers de nom `TEST-S000`). Pour l'utiliser, mettez-la dans `fichier_fiches`, ou copiez son contenu dans votre fichier de fiches.

1. Mettez `"delai_stabilisation_s": 3`. Lancez `traceur.exe`, **Réinitialiser la base**, faites S-000 (Début → saisie → Fin). Ouvrez le rapport et notez, pour chaque table, le nombre de lignes ajoutées/modifiées/supprimées.
2. Fermez le Traceur. Mettez `"delai_stabilisation_s": 10`. Relancez, **réinitialisez la base**, refaites **exactement** la même saisie.
3. Comparez les deux rapports (section « Ce que la fiche a écrit dans la base »).
   - **Identiques** : le délai de 3 s suffit. Remettez 3.
   - **Différents** (le rapport à 10 s contient des écritures de plus) : le logiciel écrit lentement. Augmentez `delai_stabilisation_s` (essayez 10), et refaites S-000 pour confirmer.
4. Notez la valeur retenue et la durée de photo affichée dans le journal (`Photo : N tables, M lignes en X s`). La photo d'une base de plusieurs centaines de milliers de lignes doit rester sous une minute ; si ce n'est pas le cas, signalez-le : c'est un point ouvert (AMB-002).

## 6. Dépannage
| Message | Cause probable |
|---|---|
| « pyodbc n'est pas installé » / « Aucun pilote ODBC Access » | Ne devrait pas arriver avec `traceur.exe`. Vérifiez que c'est bien la version **32 bits** (`python outils\construire_exe.py` l'indique) et que le pilote existe : `odbcad32` 32 bits (`C:\Windows\SysWOW64\odbcad32.exe`) → onglet *Pilotes*. |
| « Connexion impossible » | Chemin `base_test` faux, droits insuffisants, mot de passe ou groupe de travail manquant. Détail dans `journal.log`. |
| « DÉMARRAGE REFUSÉ » | Règle de sécurité : corrigez `config.json`, ne cherchez pas à la contourner. |
| « RÉINITIALISATION REFUSÉE : la base semble utilisée » | Fichier `.ldb` présent : fermez le logiciel sur tous les postes. Si personne ne l'utilise, un arrêt brutal a pu laisser le fichier : vérifiez avant de le supprimer à la main. |
| « Le partage est indisponible » | La trace est gardée dans `traces_locales\` et déposée au prochain démarrage. |
| Texte accentué faux dans les rapports | Changez `encodage_texte`. |

Le journal `journal.log` (à côté de `traceur.exe`) contient le détail de chaque opération et les erreurs ; envoyez-le avec toute demande d'aide (il ne contient aucun mot de passe).

## 7. Antivirus : exécutable bloqué ou mis en quarantaine
Un programme PyInstaller en fichier unique, non signé, est parfois pris pour un logiciel malveillant (« faux positif ») : l'antivirus le bloque au lancement, le supprime, ou le met en quarantaine. Signes : `traceur.exe` disparaît du dossier, une alerte de l'antivirus s'affiche, ou rien ne se passe au double-clic.

1. **Ne désactivez pas l'antivirus.** Demandez au responsable informatique d'ajouter une **exclusion pour le dossier du Traceur** (par exemple `C:\Traceur\`, celui qui contient `traceur.exe`, `config.json`, `journal.log`, `traces_locales\`), et, si l'antivirus le permet, d'**exclure le fichier** `traceur.exe`.
2. Si `traceur.exe` est en quarantaine : **restaurez-le** depuis l'interface de l'antivirus *après* avoir ajouté l'exclusion. Vérifiez qu'il s'agit bien du fichier fourni : comparez son **SHA-256** (`certutil -hashfile traceur.exe SHA256`) avec celui affiché par `construire_exe.py` à la construction.
3. Vous pouvez signaler le fichier comme faux positif à l'éditeur de l'antivirus (en lui envoyant le SHA-256).
4. **Solution de repli : `--onedir`.** Construisez le programme sous forme de dossier plutôt que de fichier unique : `python outils\construire_exe.py --onedir`. Le résultat est le dossier `dist\traceur\` : `traceur.exe` et ses bibliothèques. **Copiez le dossier en entier** (pas le seul `.exe`) sur le poste, et lancez `traceur.exe` à l'intérieur. Cette forme ne se décompresse pas à chaque lancement et est généralement moins suspecte pour les antivirus. `config.json`, le journal et les dossiers `traces_locales\` et `donnees_locales\` se placent à côté de `traceur.exe`, dans ce dossier.

Le Traceur n'a besoin d'aucun accès réseau sortant, n'installe rien et n'écrit que dans son dossier, dans `dossier_sorties` et — pour la réinitialisation seulement — sur la base de TEST.

## 8. Construire `traceur.exe` (développeur)
Sur un poste Windows avec **Python 32 bits** :
```
python -m venv .venv
.venv\Scripts\activate
pip install -e .[access,ui,build]
python outils\construire_exe.py --verifier
python outils\construire_exe.py
```
Le script refuse de construire avec un Python 64 bits, produit `dist\traceur.exe` (un seul fichier, sans console), affiche son SHA-256 et contrôle que l'exécutable est bien 32 bits. Si un antivirus bloque le fichier unique, voir la section 7 (`--onedir`). Pour mettre à jour un poste : remplacez `traceur.exe` (ou le dossier en mode `--onedir`) ; `config.json`, le journal, `donnees_locales\` et `traces_locales\` ne bougent pas.
