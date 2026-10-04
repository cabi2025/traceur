# SUIVI DES AMBIGUÏTÉS

> Règle : aucune ambiguïté n'est résolue sans **décision explicite de l'utilisateur**, recopiée ici.
> Statuts : `OUVERTE` · `BLOQUANTE` · `CLOSE`

## Modèle

### AMB-000 — Titre court
- **Statut :** OUVERTE
- **Jalon / SPEC :** J1 / §6.3
- **Contexte :** ce qui est muet, contradictoire ou irréalisable.
- **Options :**
  1. …
  2. …
- **Recommandation :** option + raison.
- **Code concerné :** `TODO(AMB-000)` dans `…`
- **Décision utilisateur :** _(vide tant que non tranché)_
- **Date de clôture :**

---

## Ambiguïtés connues dès la rédaction

### AMB-001 — Format exact du `.mdb` (Jet 3 ou Jet 4)
- **Statut :** CLOSE
- **Jalon / SPEC :** J4 / §3
- **Contexte :** le logiciel date de 2000 ; la base peut être en Jet 3 (Access 97) ou Jet 4 (Access 2000). Le pilote ODBC 32 bits de Windows lit les deux, mais le comportement des types (Currency, dates) est à vérifier sur la vraie base.
- **Options :** 1. Supporter les deux et le détecter. 2. Attendre l'identification sur la vraie base.
- **Recommandation :** 1, avec détection affichée dans le profil.
- **Décision utilisateur :** Option 1 — supporter Jet 3 et Jet 4, détection affichée dans le profil. `outils/version_jet.py` lit l'octet 0x14 de l'en-tête (0 = Jet 3, 1 = Jet 4).
- **Date de clôture :** 2026-10-03

### AMB-002 — Temps de photo sur la vraie volumétrie
- **Statut :** OUVERTE
- **Jalon / SPEC :** J1, J7 / §3
- **Contexte :** l'objectif de 60 s n'est vérifiable que sur la vraie base. Si dépassé : photo partielle (seulement les tables qui ont changé d'empreinte) ou empreinte par tranche.
- **Recommandation :** mesurer d'abord ; n'optimiser qu'avec une mesure en main.
- **Décision utilisateur (2026-10-03) :** mesurer d'abord. Temps de photo mesuré et affiché dès J1, aucune optimisation avant mesure sur la vraie base. Reste OUVERTE jusqu'à cette mesure.

---

## Ambiguïtés détectées à la lecture (J0, 2026-10-03)

### AMB-003 — Noms des clés de `changements[]` (SPEC §8.1 vs exemple)
- **Statut :** CLOSE
- **Jalon / SPEC :** J1, J5 / §8.1, `trace.example.json`
- **Contexte :** le §8.1 cite `insert/update/delete/update_probable` ; l'exemple utilise `inserts`, `updates`, `deletes`, `updates_probables`, `lignes_ajoutees`, `lignes_supprimees`.
- **Options :** 1. L'exemple fait foi (pluriels). 2. Aligner l'exemple sur le §8.1.
- **Recommandation :** 1, et corriger la formulation du §8.1.
- **Décision utilisateur :** Option 1 — `trace.example.json` fait foi ; formulation du §8.1 corrigée.
- **Date de clôture :** 2026-10-03

### AMB-004 — Hypothèse `compteur` sur un champ texte
- **Statut :** CLOSE
- **Jalon / SPEC :** J3 / §7.2
- **Contexte :** `PIECE` vaut `"0042"` (texte, zéros de tête, « max avant = 0041 »). « max + 1 » n'est défini que pour un numérique.
- **Options :** 1. Accepter un texte entièrement numérique, en conservant la largeur. 2. Numérique uniquement. 3. Gérer préfixe + suffixe numérique.
- **Recommandation :** 1.
- **Décision utilisateur :** Option 3 — préfixe éventuel + suffixe numérique incrémenté, largeur conservée (couvre aussi le texte entièrement numérique).
- **Date de clôture :** 2026-10-03

### AMB-005 — Lien entre message affiché et valeurs en base
- **Statut :** CLOSE
- **Jalon / SPEC :** J3 / §7.1, §5.2
- **Contexte :** message `2025-ACH-0042`, colonne `PIECE` = `0042`. La saisie « Remarques » est du texte libre ; aucun lien n'est prévu.
- **Options :** 1. Aucun lien automatique (analyste). 2. Recherche de sous-chaînes numériques des remarques dans les lignes insérées (hors SPEC).
- **Recommandation :** 1 en V1.
- **Décision utilisateur :** Option 1 — aucun lien automatique en V1.
- **Date de clôture :** 2026-10-03

### AMB-006 — Statuts non énumérés
- **Statut :** CLOSE
- **Jalon / SPEC :** J5, J6 / §5.1, §8
- **Contexte :** statuts de fiche (`à faire`/`faite`/`écart`) et de trace (`terminee`, `annulee`, `ecart_saisie`, `en_attente_depot`) incohérents ; pas de statut de fiche pour « annulée ».
- **Options :** 1. Statut de fiche dérivé de la dernière trace, ajout de `annulée`. 2. Garder tel quel.
- **Recommandation :** 1, enum unique documentée.
- **Décision utilisateur :** Option 1 — énumération unique documentée (SPEC §8.2), statut de fiche dérivé de la dernière trace, ajout de `annulée`.
- **Date de clôture :** 2026-10-03

### AMB-007 — Emplacement de `journal.log`
- **Statut :** CLOSE
- **Jalon / SPEC :** J4, J6 / §10, §11
- **Contexte :** §10 : `sorties/journal.log` (peut être un partage réseau indisponible) ; §11 : `journal.log` sans chemin. Un mot de passe ne doit jamais y figurer.
- **Options :** 1. Dossier local à côté de l'exe. 2. Dans `dossier_sorties`. 3. Local, copie dans `dossier_sorties` au dépôt.
- **Recommandation :** 1.
- **Décision utilisateur :** Option 3 — journal local à côté de l'exe, copié dans `dossier_sorties` à chaque dépôt. Jamais de mot de passe dedans.
- **Date de clôture :** 2026-10-03

### AMB-008 — Fichier de verrou `.ldb` / `.laccdb`
- **Statut :** CLOSE
- **Jalon / SPEC :** J4 / §10
- **Contexte :** seul `.ldb` est vérifié ; `.gitignore` prévoit aussi `.accdb`/`.laccdb`.
- **Options :** 1. `.ldb` et `.laccdb` selon l'extension de la base. 2. `.ldb` uniquement.
- **Recommandation :** 1.
- **Décision utilisateur :** Option 1 — `.ldb` ou `.laccdb` selon l'extension de la base.
- **Date de clôture :** 2026-10-03

### AMB-009 — Valeurs saisies répétées pour un même champ d'écran
- **Statut :** CLOSE
- **Jalon / SPEC :** J3 / §7.1, §9
- **Contexte :** « Débit » apparaît 2 fois (1234.56 et 246.91) avec les mêmes `champ_ecran`/`ecran`. Le lien est cherché valeur par valeur, mais le rapport ne distingue pas les occurrences.
- **Options :** 1. Lier par valeur, rapporter la valeur dans chaque lien. 2. Ajouter un index d'occurrence au format des fiches.
- **Recommandation :** 1 (aucun changement de format).
- **Décision utilisateur :** Option 1 — lien par valeur, la valeur figure dans chaque lien.
- **Date de clôture :** 2026-10-03

### AMB-010 — F7 sans profil disponible
- **Statut :** CLOSE
- **Jalon / SPEC :** J2, J3 / §7.2, §6.4
- **Contexte :** `constante` et l'usage des relations candidates (`copie`) dépendent du profil ; comportement si absent ou périmé non défini.
- **Options :** 1. Hypothèses dépendantes du profil désactivées, avertissement dans le rapport. 2. Profilage obligatoire avant toute fiche.
- **Recommandation :** 1.
- **Décision utilisateur :** Option 1 — hypothèses dépendant du profil désactivées si profil absent, avertissement dans le rapport, bandeau « Profil absent — lancer le profilage » sur l'écran principal.
- **Date de clôture :** 2026-10-03

---

## Ambiguïtés détectées en J1 (2026-10-03)

### AMB-011 — Table ajoutée ou supprimée entre deux photos
- **Statut :** CLOSE
- **Jalon / SPEC :** J1 / §6.3
- **Contexte :** la SPEC ne traite que le changement de schéma d'une table existante.
- **Options :** 1. Signaler dans `schema_modifie` (nature `table_ajoutee` / `table_supprimee`), sans diff de lignes. 2. Traiter comme insert/delete de toutes les lignes.
- **Recommandation :** 1.
- **Décision utilisateur :** Lecture validée : une table ajoutée → `inserts` (clé) ou `lignes_ajoutees` (sans clé) ; une table supprimée → `deletes` ou `lignes_supprimees`.
- **Date de clôture :** 2026-10-03

### AMB-012 — Diff de lignes d'une table dont le schéma a changé
- **Statut :** CLOSE
- **Jalon / SPEC :** J1 / §6.3
- **Contexte :** `schema_modifie` est « signalé à part », mais la SPEC ne dit pas si les lignes sont comparées.
- **Options :** 1. Pas de diff de lignes pour cette table (signalement seul). 2. Diff sur les colonnes communes.
- **Recommandation :** 1 (rien d'inventé ; l'analyste voit le changement de schéma).
- **Décision utilisateur :** Diff des lignes sur les colonnes communes aux deux photos, avertissement listant les colonnes ajoutées/supprimées, signalement conservé dans `schema_modifie`.
- **Date de clôture :** 2026-10-03

### AMB-013 — Appariement des `update_probable`
- **Statut :** CLOSE
- **Jalon / SPEC :** J1 / §6.3
- **Contexte :** « une paire ajoutée/supprimée qui diffère d'au plus 2 champs » ne dit pas : (a) l'algorithme quand plusieurs paires sont possibles ; (b) si les lignes appariées sortent de `lignes_ajoutees` / `lignes_supprimees` ; (c) le coût O(n×m) sur de gros volumes.
- **Options :** (a) appariement glouton déterministe, plus petit nombre de champs différents, puis premier dans l'ordre ; (b) retirer les lignes appariées des deux listes ; (c) plafond de 1 000 000 de comparaisons, au-delà pas d'appariement.
- **Recommandation :** a + b + c tels quels.
- **Décision utilisateur :** Option provisoire acceptée (glouton déterministe, lignes appariées retirées des listes, plafond 1 000 000), à condition que l'atteinte du plafond produise un avertissement explicite dans `avertissements` (table concernée, nombre de lignes non appariées).
- **Date de clôture :** 2026-10-03

---

## Ambiguïtés détectées en J2 (2026-10-03)

### AMB-014 — Choix de la clé candidate utilisée par le diff quand il y en a plusieurs
- **Statut :** CLOSE
- **Jalon / SPEC :** J2 / §6.3
- **Contexte :** une table sans clé primaire peut avoir plusieurs colonnes ou couples uniques et non nuls ; la SPEC dit « on utilise une clé candidate » sans critère.
- **Options :** 1. Le moins de colonnes, puis premier dans l'ordre des colonnes. 2. Validation par l'utilisateur (hors périmètre V1).
- **Recommandation :** 1.
- **Décision utilisateur :** Sont exclues des clés candidates les colonnes montant/décimal, flottant, date/date-heure et mémo/binaire. Ordre de préférence : entier, puis texte court ; puis le moins de colonnes ; puis l'ordre des colonnes. La clé retenue reste visible dans `cle_utilisee`. (Interprétations de l'implémentation : « texte court » = au plus 255 caractères observés, au-delà traité comme mémo ; booléen non exclu, classé après le texte ; le type d'un couple est celui de sa colonne la moins préférée.)
- **Date de clôture :** 2026-10-03

### AMB-015 — Clés candidates sur les tables très petites
- **Statut :** CLOSE
- **Jalon / SPEC :** J2 / §6.4
- **Contexte :** une table de 0 ou 1 ligne rend toutes ses colonnes « uniques et non nulles » : les clés (et relations) déduites n'ont aucun sens.
- **Options :** 1. Aucune clé candidate sous 2 lignes. 2. Seuil plus élevé (à fixer). 3. Appliquer la règle telle quelle.
- **Recommandation :** 1 (seuil minimal ; à relever si les profils réels montrent du bruit).
- **Décision utilisateur :** Comportement provisoire validé (aucune clé candidate sous 2 lignes).
- **Date de clôture :** 2026-10-03

### AMB-016 — Fausses relations sur colonnes à peu de valeurs distinctes
- **Statut :** CLOSE
- **Jalon / SPEC :** J2 / §6.4
- **Contexte :** la règle (≥ 99 % d'inclusion, types compatibles) accepte une colonne `0/1` ou un code à 3 valeurs incluse dans une clé numérique 1..N. Ces relations sont fausses mais conformes à la SPEC.
- **Options :** 1. Appliquer la règle telle quelle (l'analyste filtre). 2. Seuil minimal de valeurs distinctes pour la colonne source. 3. Exiger un nom de colonne proche.
- **Recommandation :** 1 en V1 (« aucune heuristique hors SPEC »), à réévaluer sur la vraie base.
- **Décision utilisateur :** Relations dont la colonne source est booléenne ou a moins de 3 valeurs distinctes non nulles : conservées avec `confiance: faible`, listées dans le dictionnaire, non dessinées dans le graphe.
- **Date de clôture :** 2026-10-03

### AMB-017 — Taux d'inclusion : par lignes ou par valeurs distinctes
- **Statut :** CLOSE
- **Jalon / SPEC :** J2 / §6.4
- **Contexte :** « valeurs non nulles incluses à au moins 99 % » : sur les lignes (une valeur fréquente pèse plus) ou sur les valeurs distinctes ?
- **Options :** 1. Sur les lignes non nulles. 2. Sur les valeurs distinctes.
- **Recommandation :** 1 (une clé étrangère orpheline fréquente est un vrai défaut d'intégrité).
- **Décision utilisateur :** Critère de rétention maintenu sur les lignes non nulles ; le taux sur valeurs distinctes est ajouté au profil à titre informatif.
- **Date de clôture :** 2026-10-03

### AMB-018 — Format de `bruit.json` et rôle de `tables_ignorees`
- **Statut :** CLOSE
- **Jalon / SPEC :** J2 / §4, §6.5, §8
- **Contexte :** `bruit.json` n'a pas d'exemple dans `docs/formats/`. Par ailleurs `tables_ignorees` est « ajoutée à la calibration » (§4) alors que §6.2 ne photographie que les tables « non ignorées » : ignorées de la photo, ou rapportées comme bruit ?
- **Options :** 1. `tables_ignorees` exclues des photos (jamais rapportées) ; `bruit.json` les liste séparément ; les tables de bruit validées restent photographiées et sont rapportées dans `bruit`. 2. `tables_ignorees` fusionnées dans `tables_bruit` (photographiées, rapportées dans `bruit`).
- **Recommandation :** 1. Format proposé : `docs/formats/bruit.example.json`.
- **Décision utilisateur :** Comportement et `docs/formats/bruit.example.json` validés.
- **Date de clôture :** 2026-10-03

---

## Ambiguïtés détectées en J3 (2026-10-03)

### AMB-019 — Échelle de `confiance` des liens
- **Statut :** CLOSE
- **Jalon / SPEC :** J3 / §7.1
- **Contexte :** `confiance` est dans le format (`"haute"` dans l'exemple) mais l'échelle n'est pas définie.
- **Options :** 1. `haute` (exacte, date stockée en date-heure) · `moyenne` (signe inversé, majuscules, texte tronqué) · `faible` (× 100, ÷ 100). 2. Tout `haute` pour l'exacte, `faible` pour toute tolérance.
- **Recommandation :** 1.
- **Décision utilisateur :** Échelle validée : `haute` (exacte, date_heure), `moyenne` (signe_inverse, majuscules, tronque), `faible` (x100, div100).
- **Date de clôture :** 2026-10-03

### AMB-020 — Règles précises des correspondances tolérées
- **Statut :** CLOSE
- **Jalon / SPEC :** J3 / §7.1
- **Contexte :** la SPEC liste les tolérances sans règles de détail :
  (a) une correspondance tolérée est-elle cherchée même si une exacte existe ? (b) longueur minimale d'un texte tronqué ; (c) une date-heure à minuit est-elle « exacte » ou « date stockée en date-heure » ? (d) tolérances applicables au type `code` ; (e) un montant stocké en texte ; (f) saisie à 0 (signe inversé, × 100 identiques).
- **Options / recommandation :** (a) tolérées seulement s'il n'existe aucune exacte pour cette saisie (sinon bruit : 12,34 × 100 = 1234) ; (b) 3 caractères ; (c) lecture littérale : toute date-heure est `date_heure` (à reconsidérer, Jet renvoie toujours des date-heure) ; (d) aucune tolérance pour `code` ; un entier égal au code (sans zéro de tête) est exact ; (e) refusé, les montants sont comparés aux colonnes numériques ; (f) aucune tolérance pour 0.
- **Décision utilisateur :** Règles validées, sauf les dates : une date-heure à minuit pile = correspondance `exacte` ; `date_heure` uniquement si une heure non nulle est présente.
- **Date de clôture :** 2026-10-03

### AMB-021 — Écart de saisie : « diffère manifestement » et « colonne attendue »
- **Statut :** CLOSE
- **Jalon / SPEC :** J3 / §7.4
- **Contexte :** la SPEC donne un exemple (1 243,56 au lieu de 1 234,56, même colonne) mais ni la définition de « manifestement », ni l'origine de la « colonne attendue » (la fiche ne la porte pas).
- **Options :** 1. Colonne attendue = colonne où d'autres saisies du même champ d'écran ont été liées dans la même trace ; « manifestement » = une insertion, suppression, substitution ou transposition de deux caractères voisins (distance ≤ 1) sur la forme normalisée (montant, date ISO, texte/code d'au moins 4 caractères) ; cellules déjà expliquées exclues. 2. Utiliser l'historique de traces (hors V1). 3. Colonne attendue déclarée dans la fiche (changement de format).
- **Recommandation :** 1.
- **Décision utilisateur :** Colonne sœur validée ; distance = Damerau-Levenshtein ≤ 1 (une transposition compte 1), calculée sur la valeur normalisée. Test : 1234.56 → 1243.56 est reconnu grâce à la transposition (distance 1, contre 2 en Levenshtein simple) ; contre-épreuve avec la distance simple : l'écart n'est plus reconnu.
- **Date de clôture :** 2026-10-03

### AMB-022 — Détails des hypothèses de champs calculés (F7)
- **Statut :** CLOSE
- **Jalon / SPEC :** J3 / §7.2
- **Contexte :** points non définis : (a) `compteur` « + pas constant » : pas déduit des valeurs d'avant (écarts constants) ou, pour une ligne modifiée, delta constant entre lignes ; plusieurs lignes insérées d'un coup (max + 1, + 2…) ; (b) `horodatage_systeme` : horloge du poste vs serveur, aucune marge ; date-heure à minuit = date seule ; (c) `somme_lignes` : « lignes liées » via relations candidates `normale` du profil, valeur nulle exclue ; (d) `copie` : relation candidate `normale`, table différente, hors colonne clé ; (e) `constante` : colonne à une seule valeur, sans nul, table d'au moins 2 lignes dans le profil ; (f) `cumul_mis_a_jour` : lignes modifiées uniquement, delta non nul ; (g) `somme_lignes` dépend du profil (relations), comme `copie` et `constante` (AMB-010) ; (h) cellules NULL ignorées ; (i) pour une ligne modifiée, seuls les champs modifiés sont des cellules.
- **Recommandation :** comportement ci-dessus.
- **Décision utilisateur :** Validé, avec deux changements : marge de ±2 minutes sur `horodatage_systeme` ; relations `faible` exclues de `somme_lignes` et `copie`.
- **Date de clôture :** 2026-10-03

---

## Ambiguïtés détectées en J4 (2026-10-03)

### AMB-023 — Clés de configuration « oui (F10) » / « oui (F8) »
- **Statut :** CLOSE
- **Jalon / SPEC :** J4 / §4
- **Contexte :** `instantane_reference` est « oui (F10) » et `fichier_fiches` « oui (F8) » : obligatoires toujours, ou seulement quand la fonction est utilisée ?
- **Options :** 1. Toujours exigées au démarrage (l'outil offre toutes les fonctions). 2. Exigées à l'usage seulement.
- **Recommandation :** 1 (le contrôle `base_test ≠ instantane_reference` n'a de sens que si les deux sont connues).
- **Décision utilisateur :** `fichier_fiches` optionnel ; absent → seuls profilage et calibration sont disponibles, boutons de fiche désactivés avec un message. `instantane_reference` reste obligatoire.
- **Date de clôture :** 2026-10-03

### AMB-024 — « Le chemin de TEST figure dans `chemins_interdits` » : égalité ou inclusion ; limites de la normalisation
- **Statut :** CLOSE
- **Jalon / SPEC :** J4 / §4, CLAUDE.md (sécurité)
- **Contexte :** (a) « figure » = égal, ou aussi situé dans un dossier interdit ? (b) la normalisation (casse, `/` ou `\`, `..`, préfixe `\\?\`, UNC, lecteur réseau résolu en UNC par Windows) ne peut pas reconnaître qu'un nom de serveur et son adresse IP, ou deux alias DNS, désignent le même fichier.
- **Options :** (a) 1. Égal ou contenu dans un chemin interdit (composantes entières) ; 2. égal seulement. (b) 1. Limite documentée dans le guide ; 2. résolution DNS/IP (hors périmètre).
- **Recommandation :** (a) 1, par prudence ; (b) 1.
- **Décision utilisateur :** Dossiers contenus validés. Résolution DNS des noms de serveur (des deux côtés) avant comparaison ; si elle échoue, comparaison textuelle + avertissement au journal. Conseil dans `LISEZMOI_J4.md` : lister nom ET IP dans `chemins_interdits`.
- **Date de clôture :** 2026-10-03

### AMB-025 — Réinitialisation : copie directe ou via un fichier temporaire
- **Statut :** CLOSE
- **Jalon / SPEC :** J4 / §10
- **Contexte :** la règle de sécurité n'autorise la copie que « vers le chemin de la base de TEST, et uniquement vers ce chemin ». Un fichier temporaire suivi d'un remplacement atomique protégerait d'une copie interrompue, mais écrirait un autre fichier dans le dossier de TEST.
- **Options :** 1. Copie directe vers `base_test`, puis vérification du hash SHA-256 ; en cas d'écart, erreur claire et base à considérer comme invalide jusqu'à une nouvelle réinitialisation réussie. 2. Fichier temporaire + remplacement atomique.
- **Recommandation :** 1 (respecte la lettre de la règle ; la base de TEST est jetable).
- **Décision utilisateur :** Copie directe validée ; en cas d'écart de hash : message clair, journal, pas de nouvelle tentative automatique.
- **Date de clôture :** 2026-10-03

### AMB-026 — Mot de passe de base et groupe de travail (.mdw) simultanés
- **Statut :** CLOSE
- **Jalon / SPEC :** J4 / §3, §4
- **Contexte :** la SPEC prévoit `PWD` (mot de passe de base) et `SystemDB` + utilisateur + mot de passe du groupe de travail. Le pilote ODBC Access n'a qu'un paramètre `PWD` : avec `SystemDB`, c'est le mot de passe de l'utilisateur. Les deux protections sont en principe alternatives dans Jet.
- **Options :** 1. Refuser la combinaison au démarrage avec un message clair. 2. Priorité au groupe de travail et ignorer `mot_de_passe`.
- **Recommandation :** 1 (rien n'est ignoré en silence ; à lever si la vraie base combine les deux).
- **Décision utilisateur :** Validé ; le message de refus conseille de retirer le mot de passe de la copie de TEST.
- **Date de clôture :** 2026-10-03

### AMB-027 — Cache du pilote Jet sur une connexion longue
- **Statut :** CLOSE
- **Jalon / SPEC :** J4 / §3, §4 (`delai_stabilisation_s`), §5.2
- **Contexte :** le moteur Jet met en cache les pages lues et ne les rafraîchit qu'après un délai (`PageTimeout`, 5 s par défaut). Une connexion ouverte avant l'action du comptable peut donc renvoyer, à la photo « après », des données périmées, même après `delai_stabilisation_s`. Non vérifiable ici (Linux) : à mesurer sur Windows (`tests/test_integration_access.py::test_cache_jet_connexion_longue`).
- **Options :** 1. Rouvrir la connexion avant chaque photo (`SourceAccess.rafraichir()`), sans toucher au délai. 2. Garder une connexion unique et exiger un délai ≥ `PageTimeout`.
- **Mesure (Windows 32 bits, 2026-10-03) :** `connexion longue : avant=200, immédiat=200, après 6 s=201 ; connexion rouverte=201`. Une connexion ouverte **ne voit pas** une écriture tierce juste après (immédiat=200) et ne la voit qu'après le délai de cache (≈ 5 s). Une connexion rouverte voit l'écriture immédiatement : le test de diff, qui rouvre la connexion juste après le script tiers, passe.
- **Recommandation :** 1 (coût négligeable, indépendant du réglage du poste). La mesure confirme le risque et l'efficacité de la réouverture ; `delai_stabilisation_s` (3 s par défaut) seul ne suffirait pas sur une connexion longue.
- **Décision utilisateur :** Option 1 — `rafraichir()` avant chaque photo, mesure consignée dans la SPEC. `delai_stabilisation_s` conservé à 3 s pour couvrir le délai d'écriture du logiciel legacy lui-même. Ajouter au futur guide (J7) une fiche de validation « S-000 » : une saisie simple, photo après 3 s puis après 10 s ; si les deux diffs diffèrent, augmenter le délai.
- **Date de clôture :** 2026-10-03

### AMB-028 — Clé primaire déclarée avec le pilote Jet
- **Statut :** OUVERTE
- **Jalon / SPEC :** J4 / §6.2, §6.3
- **Contexte :** constaté sur Windows (2026-10-03) : le pilote ODBC Jet ne prend pas en charge `SQLPrimaryKeys` (erreur `IM001`). Aucune clé primaire n'était lue.
- **Options :** 1. Lire les index uniques (`SQLStatistics`) et retenir l'index nommé « PrimaryKey » (nom donné par Access). 2. Passer par ADO/ADOX (`pywin32`) : fiable mais ajoute une dépendance COM à l'exécutable. 3. Ne pas lire de clé primaire et laisser le profilage fournir des clés candidates (le diff reste correct, seul `cle_utilisee.type` vaut `candidate` au lieu de `primaire`).
- **Constat (2e essai Windows) :** `SQLStatistics` répond, mais une clé déclarée en SQL (`... LONG PRIMARY KEY`) n'a pas reçu l'index « PrimaryKey » attendu : le nom donné par Jet à une clé SQL sans nom est inconnu. Le générateur de test nomme donc la contrainte explicitement. Reste à savoir ce qu'il en est de la **vraie** base (`outils/sonder_pilote.py`).
- **Vérification (Windows, 2026-10-04) :** sur la base synthétique, `diagnostic.py` affiche `clé primaire : NUM` (FACTURES) et `ID` (CLIENTS, SESSIONS) : la lecture par l'index « PrimaryKey » fonctionne quand la clé est nommée ainsi. Reste la vraie base.
- **Recommandation :** 1, avec repli sur 3 si aucun index « PrimaryKey » n'existe (ex. clé primaire renommée dans une base ancienne). À valider sur la vraie base avec `outils/sonder_pilote.py`.
- **Code concerné :** `traceur/sources/access.py` (`_cle_primaire`, provisoirement option 1 + repli 3).
- **Décision utilisateur :**

---

## Ambiguïtés détectées en J5 (2026-10-03)

### AMB-029 — Dossier local de travail, marqueur de dépôt, mécanique du « déplacement atomique »
- **Statut :** CLOSE
- **Jalon / SPEC :** J5 / §8, §8.2
- **Contexte :** la SPEC dit « écriture dans un dossier temporaire local, puis déplacé en une fois » et « `en_attente_depot` avec nouvelle tentative au démarrage » sans préciser : (a) l'emplacement du dossier local ; (b) où est mémorisé l'état de dépôt ; (c) comment déplacer de façon atomique d'un disque local vers un partage réseau (un `rename` ne passe pas d'un volume à l'autre).
- **Options :** (a) 1. `traces_locales/` à côté de l'exécutable (comme `journal.log`). (b) 1. Fichier `depot.json` dans le dossier local de la trace, jamais copié vers le partage. (c) 1. Copie vers un dossier caché `.NOM.depot-tmp` du partage, vérification SHA-256 de chaque fichier, puis renommage atomique vers `traces/NOM`, puis suppression de la copie locale. En cas de collision de nom : même `trace.json` → déjà déposée ; sinon suffixe `_2`, `_3`…
- **Recommandation :** (a)(b)(c) ci-dessus.
- **Décision utilisateur :** Validé ; dossier local à côté de l'exécutable (cohérent avec AMB-007) ; mécanique du dépôt et format de `depot.json` décrits dans la SPEC.
- **Date de clôture :** 2026-10-03

### AMB-030 — Captures d'écran : quel écran
- **Statut :** CLOSE
- **Jalon / SPEC :** J5 / §5.2, §8 (F9)
- **Contexte :** `ImageGrab.grab()` capture l'écran principal ; le logiciel legacy peut être sur un autre écran. La capture est une aide, jamais bloquante.
- **Options :** 1. Écran principal ; en cas d'échec, trace sans capture et avertissement. 2. Tous les écrans (`all_screens=True`, image plus grande).
- **Recommandation :** 1 en V1.
- **Décision utilisateur :** Capturer tous les écrans (`ImageGrab.grab(all_screens=True)` sous Windows), repli sur l'écran principal en cas d'échec.
- **Date de clôture :** 2026-10-03

### AMB-031 — Présentation des valeurs dans `rapport.html`
- **Statut :** CLOSE
- **Jalon / SPEC :** J5 / §8
- **Contexte :** « lisible par un non-technicien » : montants affichés comme stockés (`1234.56`, point décimal) et dates ISO, ou reformatés à la française (`1 234,56`, `15/01/2025`) ? Un reformatage facilite la lecture mais éloigne le rapport de `trace.json`.
- **Options :** 1. Valeurs telles que dans `trace.json` ; seuls les en-têtes (début, fin) sont en format français. 2. Tout en format français.
- **Recommandation :** 1 (le rapport sert aussi à retrouver une valeur saisie telle qu'elle a été fournie).
- **Décision utilisateur :** Valeurs brutes (comme dans `trace.json`) validées dans le rapport.
- **Date de clôture :** 2026-10-03

---

## Ambiguïtés détectées en J6 (2026-10-03)

### AMB-032 — Empreinte SHA-256 du fichier `.mdb` à chaque « Début »
- **Statut :** CLOSE (2026-10-04)
- **Jalon / SPEC :** J6 / §8.1 (`base.empreinte_fichier_avant`)
- **Contexte :** la trace porte l'empreinte du fichier avant l'action. La calculer lit tout le `.mdb` (gros fichier, partage réseau) à chaque « Début ».
- **Options :** 1. La calculer à chaque « Début » (non bloquant : si elle échoue, `null` + avertissement). 2. La calculer seulement à la demande. 3. L'abandonner.
- **Recommandation :** 1 tant que la durée reste raisonnable ; à mesurer sur la vraie base (étape 13 de `LISEZMOI_J4.md`).
- **Code concerné :** `traceur/controleur.py` (`debut`, provisoirement option 1).
- **Décision utilisateur :** Option 1 (recommandation) : empreinte calculée à chaque « Début », non bloquante ; durée à mesurer sur la vraie base. (« ok recommandations », 2026-10-04).

### AMB-033 — Persistance locale du profil et de la calibration
- **Statut :** CLOSE (2026-10-04)
- **Jalon / SPEC :** J6 / §5.1, §6.4, §6.5, §8
- **Contexte :** le bandeau affiche « la date du dernier profilage » et la calibration doit survivre au redémarrage. La SPEC place `profil/` et `calibration/` dans `dossier_sorties` (partage, parfois indisponible). Rien n'est dit d'un profil devenu périmé (réinitialisation, base modifiée).
- **Options :** 1. Écrire dans `donnees_locales/` (à côté du programme) puis copier sur le partage ; recharger le profil local au démarrage ; ne pas détecter la péremption (l'utilisateur reprofile quand il le juge utile). 2. Détecter un profil plus ancien que le fichier de la base.
- **Recommandation :** 1.
- **Code concerné :** `traceur/controleur.py` (`_publier`, `_charger_etat_local`, provisoirement option 1).
- **Décision utilisateur :** Option 1 (recommandation) : `donnees_locales/` puis copie sur le partage ; pas de détection de péremption. (« ok recommandations », 2026-10-04).

### AMB-034 — Cases à cocher des étapes
- **Statut :** CLOSE (2026-10-04)
- **Jalon / SPEC :** J6 / §5.2, §8.1
- **Contexte :** l'écran propose une case par étape, mais le format de `trace.json` n'a aucun champ pour les étapes cochées.
- **Options :** 1. Aide visuelle pour le comptable, état non enregistré. 2. Ajouter `execution.etapes_cochees` au format (version de format à incrémenter).
- **Recommandation :** 1 en V1.
- **Code concerné :** `traceur/controleur.py` (`SessionFiche.cochees`, provisoirement option 1).
- **Décision utilisateur :** Option 1 (recommandation) : cases à cocher = aide visuelle, état non enregistré en V1. (« ok recommandations », 2026-10-04).

### AMB-035 — Comportements de l'écran de fiche non précisés
- **Statut :** CLOSE (2026-10-04)
- **Jalon / SPEC :** J6 / §5.2, §9
- **Contexte :** (a) `reinitialiser_avant: true` : imposé ou proposé ? (b) « Remarques obligatoirement proposées » : un champ vide est-il accepté ? (c) « Annuler » pendant la photo de « Début » : trace ou rien ? (d) heures `debut` et `fin` de la trace (elles bornent `horodatage_systeme`).
- **Options / recommandation :** (a) l'interface propose la réinitialisation, l'utilisateur peut refuser ; (b) champ vide accepté après une confirmation explicite (« Terminer sans remarque ? ») ; (c) annulation sans trace (la fiche n'a pas commencé) ; (d) `debut` = fin de la photo avant, `fin` = clic sur « Fin » (avant le délai de stabilisation).
- **Code concerné :** `traceur/ui/application.py`, `traceur/controleur.py` (provisoirement comme recommandé).
- **Décision utilisateur :** Recommandations (a) à (d) validées : réinitialisation proposée, remarques vides après confirmation, annulation pendant la photo de Début sans trace, `debut` = fin de la photo avant / `fin` = clic sur « Fin ». (« ok recommandations », 2026-10-04).

### AMB-036 — Message de reprise des dépôts en attente
- **Statut :** CLOSE (2026-10-04)
- **Jalon / SPEC :** J6 / §5.2, §8
- **Contexte :** au démarrage, « Vérification des traces en attente de dépôt… » n'apparaît que dans la ligne d'état, quelques centièmes de seconde : l'utilisateur ne le voit pas. Constaté sous Windows ; le dépôt lui-même a fonctionné (journal, dossier `sorties\traces`, `index.html`).
- **Options :** 1. Laisser tel quel (le journal et l'index font foi). 2. Afficher un message persistant (« n trace(s) en attente déposée(s) »).
- **Décision utilisateur :** option 1, « laisse tel quel » (2026-10-04).
- **Code concerné :** `traceur/controleur.py` (`reprendre_depots`), inchangé.

### AMB-037 — Clé candidate fortuite sur une petite table (profil)
- **Statut :** CLOSE (2026-10-04)
- **Jalon / SPEC :** J7 (constaté avec `traceur.exe`) / §6.3, §6.4 ; AMB-014 (préférence), AMB-015 (minimum de lignes)
- **Contexte :** sur la base synthétique, `COMPTEURS` (3 lignes) a été profilée à un moment où `DERNIER_NUM` valait trois valeurs différentes (3, …, 42). Colonne entière et unique, elle devient clé candidate et passe **avant** `CODE_JOURNAL` (entier préféré au texte, AMB-014). Or c'est le compteur qui change : le diff y voit une ligne supprimée et une ajoutée, et le rapport affiche « Modification probable… à confirmer » au lieu de « Ligne modifiée (CODE_JOURNAL = ACH) ». Même base, même scénario : le profil de 13:34 (2 valeurs distinctes) donnait la bonne clé. Le résultat reste correct mais moins net ; aucune donnée n'est perdue.
- **Options :** 1. Ne rien changer au moteur ; profiler toujours la base **juste après réinitialisation** (état de référence, reproductible) — consigné dans les guides ; le repli « modification probable » couvre le reste. 2. Relever `NB_LIGNES_MIN_CLE` (par exemple 10) : une table de moins de 10 lignes n'a plus de clé candidate fortuite, donc comparaison par multi-ensemble avec « modification probable » (moins précise, plus prudente). 3. Signaler dans `profil.html`, pour les tables de moins de N lignes, que la clé candidate est peu fiable. 4. Préférer un texte court à un entier pour les petites tables (change AMB-014).
- **Recommandation :** 1 + 3. 1 est déjà appliqué dans les guides ; 3 rend le risque visible sans changer le comportement du diff.
- **Code concerné :** `traceur/moteur/profilage.py` (`_cles_candidates`, `NB_LIGNES_MIN_CLE`), `traceur/rapports/profil.py`. `traceur/moteur/diff.py` (`SEUIL_PETITE_TABLE`, `_avertir_petite_table`).
- **Décision utilisateur :** « OK reco » (options 1 + 3) étendue : avertissement dans `profil.html` pour les tables sans clé primaire de moins de 50 lignes ayant une clé candidate, **et** avertissement dans `trace.json` (`avertissements[]`, code `cle_candidate_petite_table`) et dans `rapport.html` quand un diff utilise une clé candidate issue d'une table de moins de 50 lignes. Tests associés. Le moteur de choix des clés (AMB-014/015) est inchangé (2026-10-04).

### AMB-038 — Traçage multi-bases : catalogue `.mdb` et base GC SQL Server
- **Statut :** OUVERTE — **reportée** (décision de cadrage du 2026-10-04). Rien n'est codé.
- **Jalon / SPEC :** après J7 / §2, §3, §4, §6.2 (réinitialisation), §8.1 (format de trace) ; `docs/architectures.md` §0, §4, §6, §9, §12
- **Contexte confirmé :** le logiciel ouvre un **catalogue** `.mdb`, situé dans le même dossier que les dossiers (`.mdb`), que le logiciel trouve tout seul ; il liste les sociétés et exercices. Chaque **dossier** `.mdb` = une société + un exercice. Tant que le catalogue de production est accessible au logiciel, celui-ci peut y écrire même en travaillant sur le dossier TEST, et le Traceur (qui ne regarde que `base_test`) ne le voit pas.
- **Périmètre de la phase 1 (décidé) :** une seule société, un seul exercice, dans un dossier TEST. « Figé » = choisi et fixe, **pas clôturé** : l'exercice reste ouvert à la saisie. Le dossier TEST est une copie d'un exercice réel récent et encore ouvert (vrais comptes, tiers, journaux). `base_test` = chemin fixe de ce dossier, renseigné en dur dans `config.json` ; le Traceur n'a besoin d'aucun autre chemin. Il est déclaré dans le catalogue sous le nom **ZZ-TEST TRACEUR**, via la fonction du logiciel. **Lots couverts : 1a, 2, 3 et 4** (1a : création de compte, tiers, journal ; saisies, traitements, états). **Lots reportés : 1b et 5** (1b : création de société ou d'exercice ; 5 : clôture annuelle, ouverture du nouvel exercice) : ils nécessitent le catalogue. **Réserve :** si la date de `catalogue.mdb` change pendant S-000 ou une fiche du lot 1a (plan comptable éventuellement partagé), le lot 1a passe aussi en reporté.
- **Mesure de substitution (phase 1, documents seulement) :** noter la date de modification de `catalogue.mdb` avant et après la fiche S-000 (`GUIDE_INSTALLATION.md` §2 bis). Si elle change : arrêter et prévenir.
- **Quand le rouvrir :** avant les lots 1b et 5 ; **plus tôt** si la date de modification du catalogue de production change pendant S-000.
- **Cible à étudier (non décidée) :** environnement TEST isolé = un dossier `Compta_TEST` contenant une **copie du catalogue** + le dossier TEST ; le logiciel est lancé de façon à n'utiliser que ce dossier (mécanisme à confirmer, recherche en cours avec Process Monitor). Configuration envisagée : `base_catalogue_test` dans `Compta_TEST` ; dossier de production entier dans `chemins_interdits` ; instantané de référence et réinitialisation portant sur les deux fichiers, avec retrait des `.mdb` créés pendant une fiche (par exemple un nouvel exercice) ; détection des `.mdb` apparus ou disparus dans `Compta_TEST`.
- **Options :**
  1. **Statu quo (retenu pour la phase 1).** Une seule base tracée ; surveillance manuelle de la date du catalogue.
  2. **Détection seule.** Le Traceur liste les `.mdb` de `Compta_TEST` au Début et à la Fin et signale ceux qui sont apparus ou ont disparu (avertissement dans la trace). Aucun diff du catalogue, aucune suppression.
  3. **Deux bases tracées.** Le catalogue de TEST est lu en lecture seule, photographié et comparé comme le dossier ; réinitialisation multi-fichiers.
  4. **Option 3 + nettoyage.** La réinitialisation retire aussi les `.mdb` créés pendant une fiche. Recommandation sur ce point : les déplacer vers une corbeille dans `Compta_TEST` plutôt que les supprimer.
- **Impact sur le format de trace (options 2 à 4) :** additif, `format_version` 1.0 → 1.1. `base` (une base) devient `bases[]` (rôle `catalogue` ou `dossier`, chemin, empreinte avant) ; chaque élément de `changements[]` et de `bruit[]` porte sa `base` (deux bases peuvent avoir une table de même nom) ; nouvelle section `fichiers_apparus` / `fichiers_disparus`. Les lecteurs V2 de 1.0 resteraient valides.
- **Impact sur le code :** option 2 : `traceur/controleur.py`, `traceur/rapports/` (petit). Options 3 et 4 : photo et diff par base (`traceur/moteur/instantane.py`, `diff.py`, `calibration.py`, `profilage.py`), configuration (`base_catalogue_test`, `dossier_test`), sécurité de démarrage et réinitialisation multi-fichiers (`traceur/securite.py`), rapports, index, tests Windows.
- **Impact sur les règles de sécurité de `CLAUDE.md` :** l'option 4 modifie la règle « la seule opération qui modifie un fichier `.mdb` est la réinitialisation, par copie vers le chemin de la base de TEST, uniquement » (copie de deux fichiers, retrait de fichiers créés). Elle exige une décision explicite et des garde-fous : dossier jamais dans `chemins_interdits`, confirmation listant les fichiers touchés, déplacement et non suppression.
- **Estimation (grossière, pour décider) :** option 2 : un quart de jalon. Options 3 et 4 : environ un jalon complet (moteur à plusieurs bases, sécurité, rapports, tests Windows), plus une phase de mesure avec Process Monitor.
- **Recommandation :** option 1 pour la phase 1 ; envisager 2 en premier (la moins coûteuse, sans risque pour les fichiers) puis 3 avant les lots 1b et 5, quand le mécanisme de lancement isolé du logiciel sera confirmé.
- **Questions tranchées le 2026-10-04 (2e décision) :** (a) **emplacement du dossier TEST** : préféré = sous-dossier séparé (`…\Compta\TEST\`) si le logiciel accepte de déclarer un dossier situé ailleurs, `chemins_interdits` gardant le dossier de production entier ; sinon même dossier que la production, `chemins_interdits` listant le catalogue et chaque dossier réel un par un (rappel : ajouter tout nouveau dossier de production) ; le guide décrit les deux cas, choix à l'étape 2. (b) **lot 1** découpé : 1a (création compte, tiers, journal) actif, S-000 inchangée ; 1b (création société/exercice) reporté, sous AMB-038. (c) **repère** : ce que le logiciel affiche réellement à l'étape 3 ; si le nom de la société réelle apparaît, le renommer dans le dossier TEST (paramètres société) avant l'instantané de référence ; sinon le repère est le nom choisi dans la liste.
- **Élargissement du 2026-10-04 : la base GC (SQL Server).** AMB-038 couvre désormais **deux sources supplémentaires** à tracer : (1) le **catalogue `.mdb`** (lots 1b et 5) ; (2) la **base GC SQL Server** (`192.168.16.99`, authentification Windows), pour les fiches du pont **E-2.07.x** : le transfert écrit dans la GC (Journal + Pièce de `Ecrit`) et dans la comptabilité (`Externe = 1`). Faits déclarés (à confirmer par trace) : `docs/CARTE_ECRANS.md` §8.
  - **Cible :** une nouvelle `SourceDonnees` **SQL Server** (pyodbc, **lecture seule**, connexion Windows, rôle `db_datareader`), sur la base **`GC_TEST` uniquement**, avec une **liste blanche de tables** : `Ecrit`, `EcritL`, la table des tiers de la GC (**nom à identifier**, `TODO(AMB-038)`), pour ne jamais photographier toute la base.
  - **Sécurité (équivalent de F1, à décider dans le détail) :** refus de démarrer si la base SQL demandée n'est pas `GC_TEST` ou figure dans une liste de bases GC interdites (production) ; contrôle à la connexion que la base courante (`SELECT DB_NAME()`) est bien celle attendue ; aucune instruction autre que `SELECT` ; aucune table hors liste blanche ; mot de passe jamais journalisé (l'authentification Windows n'en utilise pas). Le serveur `192.168.16.99` héberge aussi la production : jamais de redémarrage, jamais d'accès hors `GC_TEST`.
  - **Prérequis techniques à vérifier :** un pilote ODBC SQL Server **32 bits** (le pilote historique « SQL Server » est fourni avec Windows ; les pilotes « ODBC Driver 17/18 » sont à installer et leur disponibilité en 32 bits est à vérifier) ; le compte Windows qui lance le Traceur doit être membre de `db_datareader` sur `GC_TEST` et **sur rien d'autre** (à demander à l'administrateur de la base).
  - **Réinitialisation de `GC_TEST` :** elle demande une **restauration** de base (`RESTORE`), donc des droits que le Traceur en lecture seule n'a pas, et que la règle « le traceur n'écrit jamais dans la base tracée » lui interdit. Options : (a) restauration manuelle par l'administrateur, procédure écrite, avant chaque fiche du pont ; (b) script séparé, hors Traceur, lancé par l'administrateur ; (c) le Traceur avec un compte d'écriture limité à `GC_TEST` : **modifierait la règle de sécurité** de `CLAUDE.md`, non recommandé. Recommandation : (a), puis (b).
- **Options pour le traçage multi-bases (catalogue + GC) :**
  1. **Statu quo.** Dossier comptable seul ; fiches du pont interdites ; catalogue surveillé par sa date (phase 1).
  2. **Détection seule** (catalogue : `.mdb` apparus ou disparus ; GC : comptage de lignes de la liste blanche avant/après, sans détail). Peu coûteuse, mais ne dit pas ce qui a changé dans la GC.
  3. **Diff complet de la GC** : `SourceDonnees` SQL Server, liste blanche, diff par table comme pour le `.mdb`, rapports « changements par base ». Nécessaire pour les fiches E-2.07.x.
  4. **Option 3 + catalogue** (deuxième `SourceDonnees` Access) et environnement TEST isolé (copie du catalogue dans `Compta_TEST`, réinitialisation multi-fichiers). Nécessaire pour les lots 1b et 5.
- **Impact sur le format de trace (options 3 et 4) :** additif, `format_version` 1.0 → 1.1. `base` (un chemin, une empreinte) devient `bases[]` : `role` (`dossier`, `catalogue`, `gc`), `moteur` (`access`, `sqlserver`), identifiant (chemin ou `serveur/base`), empreinte avant pour un `.mdb` (aucune pour SQL Server, ou la sauvegarde de référence). Chaque élément de `changements[]`, `bruit[]`, `schema_modifie[]` et `avertissements[]` porte sa **base** (deux bases peuvent avoir une table de même nom : `Ecrit` côté GC, les écritures côté `.mdb`). Les liens F6 et les hypothèses F7 pourraient lier des valeurs **entre bases** (ex. (Journal, Pièce) de la GC retrouvé dans les écritures `Externe = 1`) : à décider. Les lecteurs V2 de 1.0 restent valides.
- **Impact sur le code (options 3 et 4) :** source SQL Server (`traceur/sources/`), moteur à plusieurs sources (`traceur/moteur/instantane.py`, `diff.py`, `liens.py`, `calcules.py`, `calibration.py`, `profilage.py`), configuration (sources SQL, liste blanche, bases interdites), sécurité de démarrage (`traceur/securite.py`), rapports et index, interface (état des connexions), tests avec une base SQL Server de test.
- **Estimation (grossière, pour décider) :** source SQL Server en lecture seule avec liste blanche et sécurité : environ un demi-jalon. Moteur et format multi-bases, rapports, interface : environ un jalon. Source du catalogue et réinitialisation multi-fichiers (option 4) : environ un demi-jalon de plus. Tests sous Windows avec `GC_TEST` : à prévoir en fin de jalon, avec l'administrateur de la base. **Total des options 3 + 4 : environ deux jalons.**
- **Recommandation (mise à jour) :** phase 1 en option 1. Pour le pont : option 3 (GC seule, `GC_TEST`, liste blanche) en premier, car elle porte la valeur (règles d'imputation, verrou, `Externe`), puis ajout du catalogue (option 4) avant les lots 1b et 5. Le comptage de `Externe` sur la copie du dossier (`docs/CARTE_ECRANS.md` §8) donne tout de suite la part des écritures venant du pont, et dira si le pont est prioritaire.
- **Code concerné :** aucun pour l'instant (`TODO(AMB-038)` : nom de la table des tiers de la GC).
- **Décision utilisateur :** 2026-10-04 — périmètre de la phase 1 figé (une société, un exercice ouvert, dossier TEST copié d'un exercice réel, déclaré sous « ZZ-TEST TRACEUR ») ; lots 2, 3 et 4 couverts ; lots 1 et 5 reportés ; AMB-038 ouverte et reportée ; à rouvrir avant les lots 1b et 5, ou plus tôt si la date de modification du catalogue de production change pendant S-000 ; rien n'est codé. *Précisé le même jour (2e décision) : lots couverts 1a, 2, 3, 4 ; lot 1 découpé (1b reporté) ; voir « Questions tranchées » ci-dessus.*
- **Décision utilisateur (suite, 2026-10-04) :** AMB-038 **élargie** en « traçage multi-bases » (catalogue `.mdb` + base GC SQL Server `GC_TEST`, liste blanche `Ecrit`, `EcritL`, tiers GC, lecture seule) ; **rien n'est codé** ; fiches E-2.07.x interdites tant que `GC_TEST` n'existe pas et que le traçage multi-bases n'est pas livré.

### AMB-039 — Captures automatiques et champ mot de passe de l'écran E-7.08
- **Statut :** OUVERTE
- **Jalon / SPEC :** après J7 / F9 (captures d'écran), `CLAUDE.md` (mots de passe jamais dans les rapports) ; `docs/CARTE_ECRANS.md` §8
- **Contexte :** l'écran E-7.08 (paramétrage du pont GC) contient un champ **mot de passe** (vide sur la capture du 2026-10-04 : authentification Windows probable). La règle du 2026-10-04 impose que les captures de E-7.08 le masquent. Le Traceur, lui, prend des captures de **tous les écrans** à Début et à Fin (AMB-029/030) et ne sait pas masquer une zone : si E-7.08 est ouvert à ces moments, le champ serait visible dans `capture_debut.png` / `capture_fin.png`, et donc dans le rapport et le dépôt.
- **Options :** 1. **Procédure** (aucun code) : les captures manuelles de E-7.08 masquent le champ ; pendant une fiche, E-7.08 n'est jamais ouvert à Début ni à Fin (guide d'installation, §2 ter). 2. Un champ de fiche indiquant qu'une capture contient une zone sensible, et le Traceur ne prend alors pas de capture automatique (changement de format et de code). 3. Masquage automatique par zone d'écran configurée (complexe, fragile). 4. Si le champ est toujours vide (authentification Windows), accepter le risque et le vérifier à chaque fiche du pont.
- **Recommandation :** 1 maintenant (déjà écrite dans le guide d'installation) ; 2 si une fiche doit réellement manipuler E-7.08 pendant une trace.
- **Code concerné :** aucun.
- **Décision utilisateur :**
