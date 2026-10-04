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
- **Statut :** OUVERTE
- **Jalon / SPEC :** J6 / §8.1 (`base.empreinte_fichier_avant`)
- **Contexte :** la trace porte l'empreinte du fichier avant l'action. La calculer lit tout le `.mdb` (gros fichier, partage réseau) à chaque « Début ».
- **Options :** 1. La calculer à chaque « Début » (non bloquant : si elle échoue, `null` + avertissement). 2. La calculer seulement à la demande. 3. L'abandonner.
- **Recommandation :** 1 tant que la durée reste raisonnable ; à mesurer sur la vraie base (étape 13 de `LISEZMOI_J4.md`).
- **Code concerné :** `traceur/controleur.py` (`debut`, provisoirement option 1).
- **Décision utilisateur :**

### AMB-033 — Persistance locale du profil et de la calibration
- **Statut :** OUVERTE
- **Jalon / SPEC :** J6 / §5.1, §6.4, §6.5, §8
- **Contexte :** le bandeau affiche « la date du dernier profilage » et la calibration doit survivre au redémarrage. La SPEC place `profil/` et `calibration/` dans `dossier_sorties` (partage, parfois indisponible). Rien n'est dit d'un profil devenu périmé (réinitialisation, base modifiée).
- **Options :** 1. Écrire dans `donnees_locales/` (à côté du programme) puis copier sur le partage ; recharger le profil local au démarrage ; ne pas détecter la péremption (l'utilisateur reprofile quand il le juge utile). 2. Détecter un profil plus ancien que le fichier de la base.
- **Recommandation :** 1.
- **Code concerné :** `traceur/controleur.py` (`_publier`, `_charger_etat_local`, provisoirement option 1).
- **Décision utilisateur :**

### AMB-034 — Cases à cocher des étapes
- **Statut :** OUVERTE
- **Jalon / SPEC :** J6 / §5.2, §8.1
- **Contexte :** l'écran propose une case par étape, mais le format de `trace.json` n'a aucun champ pour les étapes cochées.
- **Options :** 1. Aide visuelle pour le comptable, état non enregistré. 2. Ajouter `execution.etapes_cochees` au format (version de format à incrémenter).
- **Recommandation :** 1 en V1.
- **Code concerné :** `traceur/controleur.py` (`SessionFiche.cochees`, provisoirement option 1).
- **Décision utilisateur :**

### AMB-035 — Comportements de l'écran de fiche non précisés
- **Statut :** OUVERTE
- **Jalon / SPEC :** J6 / §5.2, §9
- **Contexte :** (a) `reinitialiser_avant: true` : imposé ou proposé ? (b) « Remarques obligatoirement proposées » : un champ vide est-il accepté ? (c) « Annuler » pendant la photo de « Début » : trace ou rien ? (d) heures `debut` et `fin` de la trace (elles bornent `horodatage_systeme`).
- **Options / recommandation :** (a) l'interface propose la réinitialisation, l'utilisateur peut refuser ; (b) champ vide accepté après une confirmation explicite (« Terminer sans remarque ? ») ; (c) annulation sans trace (la fiche n'a pas commencé) ; (d) `debut` = fin de la photo avant, `fin` = clic sur « Fin » (avant le délai de stabilisation).
- **Code concerné :** `traceur/ui/application.py`, `traceur/controleur.py` (provisoirement comme recommandé).
- **Décision utilisateur :**

### AMB-036 — Message de reprise des dépôts en attente
- **Statut :** CLOSE (2026-10-04)
- **Jalon / SPEC :** J6 / §5.2, §8
- **Contexte :** au démarrage, « Vérification des traces en attente de dépôt… » n'apparaît que dans la ligne d'état, quelques centièmes de seconde : l'utilisateur ne le voit pas. Constaté sous Windows ; le dépôt lui-même a fonctionné (journal, dossier `sorties\traces`, `index.html`).
- **Options :** 1. Laisser tel quel (le journal et l'index font foi). 2. Afficher un message persistant (« n trace(s) en attente déposée(s) »).
- **Décision utilisateur :** option 1, « laisse tel quel » (2026-10-04).
- **Code concerné :** `traceur/controleur.py` (`reprendre_depots`), inchangé.
