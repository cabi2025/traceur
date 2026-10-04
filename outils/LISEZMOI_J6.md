# J6 — Parcours complet sous Windows : profiler → calibrer → fiche → rapport → réinitialiser

Ce guide vous fait dérouler **toute l'application** sur la **base synthétique**, sans le vrai logiciel de comptabilité : un petit script (`outils\simuler_logiciel.py`) joue le rôle du logiciel entre « Début » et « Fin ».
L'interface a été testée sous Linux avec un écran virtuel (27 tests de fenêtre) ; **son rendu sous Windows est ce que vous allez vérifier**. À chaque étape : quoi faire, quel résultat attendre. En cas de différence, notez l'étape et envoyez-moi une capture d'écran.

> Aucune étape ne touche une base réelle. Ne mettez jamais le chemin de la production dans `base_test`.

---

## 0. Prérequis

- Les étapes 1 à 8 de `outils\LISEZMOI_J4.md` sont faites : Python 32 bits, `.venv`, base synthétique `C:\Traceur\test\synthetique.mdb`, copie de référence `C:\Traceur\reference\synthetique_reference.mdb`.
- Tkinter est fourni avec Python (installateur python.org, option « tcl/tk and IDLE » cochée par défaut). Vérification : `python -m tkinter` ouvre une petite fenêtre de test (la fermer).
- Pillow pour les captures d'écran : `pip install Pillow`.
- Mettre le projet à jour : `git pull`, puis dans le terminal du projet (avec `.venv` activé) :

```bat
python -m pytest -q -rs
```

**Résultat attendu :** `405 passed`, **aucune ligne `SKIPPED`**. Pendant ces tests, des fenêtres apparaissent et disparaissent très vite : c'est normal (tests de l'interface). Si des tests de l'interface échouent, envoyez-moi le premier message d'erreur de chacun.

## 1. Préparer `config.json` et les fiches

Dans `C:\Traceur\traceur`, `config.json` :

```json
{
  "base_test": "C:\\Traceur\\test\\synthetique.mdb",
  "mot_de_passe": "",
  "fichier_mdw": "",
  "utilisateur": "",
  "mot_de_passe_mdw": "",
  "instantane_reference": "C:\\Traceur\\reference\\synthetique_reference.mdb",
  "chemins_interdits": ["C:\\Traceur\\production\\compta.mdb"],
  "fichier_fiches": "C:\\Traceur\\traceur\\docs\\formats\\fiches_synthetique.json",
  "dossier_sorties": "C:\\Traceur\\sorties",
  "tables_ignorees": [],
  "encodage_texte": "cp1252",
  "delai_stabilisation_s": 3
}
```

Ouvrez **deux** invites de commandes dans `C:\Traceur\traceur`, `.venv` activé dans chacune : le **terminal A** pour l'application, le **terminal B** pour jouer le rôle du logiciel.

## 2. Lancer l'application

Dans le terminal A :

```bat
python -m traceur
```

**Résultat attendu :** une fenêtre « Traceur — observation des écritures » avec :
- en haut : `Base de TEST active : C:\Traceur\test\synthetique.mdb`, `Connexion : Connectée en lecture seule (5 tables)` en vert, et **`Profil absent — lancer le profilage` en orange et en gras** ;
- la liste des fiches : `S-SYN-01` et `S-SYN-02`, durée, statut **à faire** ;
- quatre gros boutons : **Choisir une fiche**, **Réinitialiser la base**, **Profiler la base**, **Calibrer le bruit** ;
- en bas : « Prêt. » et une barre de progression.

Un fichier `journal.log` apparaît dans `C:\Traceur\traceur`.

## 3. Profiler la base

Cliquez sur **Profiler la base**.

**Résultat attendu :**
- pendant le calcul, tous les boutons sont grisés, la barre avance (« Profilage de la table … ») et le bouton **Annuler l'opération** est actif ; la fenêtre reste réactive (vous pouvez la déplacer) ;
- une boîte « Profilage terminé : 5 tables, 3056 lignes, N relations candidates. Ouvrir le profil dans le navigateur ? » (N autour de 7) : répondez **Oui** → `profil.html` s'ouvre (tables, clés, graphe des relations) ;
- le bandeau passe à `Dernier profilage : JJ/MM/AAAA HH:MM`, en gris (plus en orange) ;
- fichiers : `C:\Traceur\traceur\donnees_locales\profil\profil.html` et `C:\Traceur\sorties\profil\profil.html`.

*Essai d'annulation (facultatif) :* relancez **Profiler la base** et cliquez aussitôt sur **Annuler l'opération** → « Opération annulée : rien n'a été enregistré. » Si l'opération est trop rapide pour être annulée, c'est normal sur 3 056 lignes.

## 4. Calibrer le bruit

Cliquez sur **Calibrer le bruit** et **ne touchez à rien pendant 30 secondes**.

**Résultat attendu :**
- la barre avance avec « Attente avant la 2e photo : encore N s — ne touchez pas au logiciel » ;
- puis la boîte « Aucune table ne change toute seule : rien à ignorer. » (la base synthétique est immobile) ;
- fichier : `C:\Traceur\sorties\calibration\bruit.json` avec `"tables_bruit": []`.

*Variante (facultative) pour voir la boîte de choix :* relancez la calibration et, **pendant les 30 secondes**, lancez dans le terminal B :

```bat
python outils\simuler_logiciel.py C:\Traceur\test\synthetique.mdb
```

Une boîte « Calibration du bruit » liste les tables qui ont bougé (CLIENTS, COMPTEURS, FACTURES, LIGNES, SESSIONS) avec une case chacune. **Laissez seulement `SESSIONS` cochée** (décochez les autres), **Valider** → « 1 table(s) de bruit enregistrée(s). ». Pour la suite, la table SESSIONS sera donc rapportée à part. (Cette variante ajoute une facture de test à la base : elle disparaîtra à la première réinitialisation, étape 6 ou 8.)

## 5. Une fiche, avec rapport : S-SYN-01

1. Sélectionnez `S-SYN-01` et cliquez **Choisir une fiche** : l'écran de la fiche s'affiche (titre, durée, prérequis, trois étapes, « À noter », champ « Remarques / messages affichés »). Les cases et le champ de remarques sont **grisés** ; seuls **Début** et « ← Retour à la liste » sont actifs.
2. Cliquez **Début**. Barre de progression (« Lecture de la table … », « Capture d'écran… », « Empreinte du fichier de la base… »). **Attendu :** les cases et le champ de remarques deviennent actifs, **Fin** et **Annuler la fiche** sont actifs, **Début** est grisé.
3. Dans le **terminal B** (le « logiciel ») :

```bat
python outils\simuler_logiciel.py C:\Traceur\test\synthetique.mdb
```

   **Attendu :** une ligne JSON, par exemple `{"facture": 2001, "montant": "1234.56", ...}`. Revenez à l'application, cochez les trois étapes, tapez dans « Remarques » : `Facture 2001 créée`.
4. Cliquez **Fin**. **Attendu :** « Attente de 3 s pour laisser le logiciel finir ses écritures… », puis « Lecture de la table … », « Calcul des différences… », « Écriture du rapport et dépôt… ». Tous les boutons sont grisés pendant ce temps : on ne peut plus annuler une fois « Fin » cliqué.
5. Une boîte **Fiche terminée** apparaît :
   - sans l'étape 4 « variante » : **« 5 tables modifiées, 3 lignes ajoutées, 2 modifiées, 1 supprimée »** (FACTURES +1, LIGNES +2, COMPTEURS ~1, SESSIONS ~1, CLIENTS −1) ;
   - avec SESSIONS en bruit : **« 4 tables modifiées, 3 lignes ajoutées, 1 modifiée, 1 supprimée »**.
6. Cliquez **Ouvrir le rapport** : `rapport.html` s'ouvre. **Vérifiez** : statut « Terminée » en vert ; vos remarques ; une section par table (avant → après) ; « Valeurs saisies retrouvées » (Montant → `FACTURES.MONTANT`, `LIGNES.DEBIT`… ; Commentaire → `FACTURES.COMMENTAIRE`) ; « Valeurs calculées par le logiciel (hypothèses) » (numéro de facture : compteur, date : horodatage) ; les **deux captures d'écran** en bas (tous vos écrans). Fermez la boîte.
7. Retour à l'écran principal : `S-SYN-01` est maintenant **faite** (en vert). Dossier `C:\Traceur\sorties\traces\S-SYN-01_AAAAMMJJ-HHMMSS\` : `trace.json`, `rapport.html`, `remarques.txt`, `capture_debut.png`, `capture_fin.png` ; `C:\Traceur\sorties\index.html` liste la trace.

**Question pour vous :** le rapport est-il compréhensible par quelqu'un qui n'est pas technicien ? Dites-moi ce qui ne l'est pas.

## 6. Écart de saisie, réinitialiser et rejouer : S-SYN-02

1. Choisissez `S-SYN-02`, **Début**, puis dans le terminal B relancez `python outils\simuler_logiciel.py C:\Traceur\test\synthetique.mdb`.
2. Cliquez **Fin**. Un message demande si vous voulez terminer **sans remarque** : c'est la confirmation explicite exigée. Répondez **Non**, tapez `essai d'écart`, cliquez **Fin** de nouveau.
3. **Attendu :** la boîte **Écart de saisie** avec un cadre orange : « ATTENTION : une valeur saisie semble différer de la fiche. • Montant : valeur attendue 9999.99 — introuvable … Proposition : réinitialiser la base de TEST puis rejouer la fiche. » et trois boutons : **Réinitialiser puis rejouer**, **Ouvrir le rapport**, **Fermer**.
4. Cliquez **Réinitialiser puis rejouer**. **Attendu :** une confirmation « Vous allez ÉCRASER la base de TEST : C:\Traceur\test\synthetique.mdb avec la copie de référence : … » → **Oui** → « Base réinitialisée » → l'écran de la fiche `S-SYN-02` revient, prêt pour un nouveau **Début**.
5. Vérification dans un terminal :

```bat
certutil -hashfile C:\Traceur\test\synthetique.mdb SHA256
certutil -hashfile C:\Traceur\reference\synthetique_reference.mdb SHA256
```

   **Attendu :** deux hash **identiques**.
6. Cliquez « ← Retour à la liste » : `S-SYN-02` est en statut **écart** (orange). Son rapport (bandeau orange « Écart de saisie ») est dans `C:\Traceur\sorties\traces\`.

## 7. Annuler une fiche

Choisissez `S-SYN-01`, **Début**, tapez une remarque (`Logiciel planté`), cliquez **Annuler la fiche** :
- **Non** à la confirmation → la fiche continue ;
- **Oui** → retour à la liste, `S-SYN-01` est **annulée** (rouge). Son rapport indique « Annulée » et conserve la remarque ; aucune comparaison n'est faite.

*Fermeture pendant une fiche :* choisissez une fiche, **Début**, puis fermez la fenêtre avec la croix → confirmation « Une fiche est en cours : quitter l'abandonnera… » → **Oui** : la fenêtre se ferme et la fiche est enregistrée comme annulée.

## 8. Réinitialiser la base (bouton direct)

Cliquez **Réinitialiser la base** → le texte de confirmation rappelle la base visée → **Non** : rien ne change ; **Oui** : « Base réinitialisée ». Même vérification de hash qu'à l'étape 6.

*Refus si le logiciel est ouvert :* ouvrez la base synthétique dans Microsoft Access (ou gardez-la ouverte dans un autre programme), puis cliquez **Réinitialiser la base** → message « RÉINITIALISATION REFUSÉE : la base de TEST semble utilisée (fichier de verrou présent : …\synthetique.ldb) ». Fermez Access et recommencez.

## 9. Partage indisponible, puis rétabli

1. Fermez l'application. Dans `config.json`, remplacez `dossier_sorties` par `"Z:\\indisponible"` (un lecteur qui n'existe pas). Relancez `python -m traceur`.
2. Faites la fiche `S-SYN-01` en entier (étape 5). **Attendu :** la boîte de fin ajoute une ligne orange : « Le partage est indisponible : la trace est gardée sur ce poste et sera déposée automatiquement au prochain démarrage. » La trace est dans `C:\Traceur\traceur\traces_locales\…` avec un fichier `depot.json` (`"depot": "en_attente_depot"`).
3. Fermez l'application, remettez `"dossier_sorties": "C:\\Traceur\\sorties"`, relancez. **Attendu :** au démarrage, « Vérification des traces en attente de dépôt… » ; ensuite `traces_locales` est **vide**, la trace est dans `C:\Traceur\sorties\traces\` et `index.html` la liste.

## 10. Refus de démarrer

Dans une copie de `config.json`, mettez `base_test` = `C:\\Traceur\\production\\compta.mdb` (la valeur de `chemins_interdits`) et lancez `python -m traceur --config <cette copie>` : une boîte **« DÉMARRAGE REFUSÉ : la base de TEST indiquée est une base de PRODUCTION »** s'affiche et l'application ne s'ouvre pas.

## 11. Journal

Ouvrez `C:\Traceur\traceur\journal.log` : on y lit la connexion en lecture seule (`ReadOnly=1`), les photos avec leurs durées, les dépôts. **Aucun mot de passe** n'y figure.

---

## À m'envoyer

1. Le résultat de l'étape 0 (`pytest`) : `405 passed` ou le détail des échecs.
2. Des **captures d'écran** : l'écran principal (étape 2), l'écran de fiche en cours (étape 5.2), la boîte d'écart (étape 6.3).
3. Ce qui n'est pas clair ou pas lisible pour le comptable (écrans, rapport).
4. Le temps que prend **Début** et **Fin** sur la base synthétique, puis sur une copie de votre vraie base si vous la testez (AMB-002, AMB-032).
5. `journal.log` si une étape a échoué.

## Dépannage

| Symptôme | Cause probable | Que faire |
|---|---|---|
| La fenêtre ne s'ouvre pas, aucun message | Tkinter absent | `python -m tkinter` ; réinstaller Python avec « tcl/tk » |
| « Connexion impossible » en rouge | base introuvable, mot de passe, pilote | message détaillé dans la boîte ; `outils\diagnostic.py` |
| Le texte est flou ou trop petit | échelle d'affichage Windows | dites-moi le pourcentage d'échelle de votre écran |
| « Capture d'écran impossible » dans le journal | Pillow absent, session verrouillée | `pip install Pillow` ; la fiche continue sans capture |
| `Une opération est déjà en cours` | vous avez cliqué pendant un calcul | attendre la fin, ou **Annuler l'opération** |
