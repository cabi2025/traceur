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
- **Statut :** OUVERTE
- **Jalon / SPEC :** J4 / §3
- **Contexte :** le logiciel date de 2000 ; la base peut être en Jet 3 (Access 97) ou Jet 4 (Access 2000). Le pilote ODBC 32 bits de Windows lit les deux, mais le comportement des types (Currency, dates) est à vérifier sur la vraie base.
- **Options :** 1. Supporter les deux et le détecter. 2. Attendre l'identification sur la vraie base.
- **Recommandation :** 1, avec détection affichée dans le profil.
- **Décision utilisateur :**

### AMB-002 — Temps de photo sur la vraie volumétrie
- **Statut :** OUVERTE
- **Jalon / SPEC :** J1, J7 / §3
- **Contexte :** l'objectif de 60 s n'est vérifiable que sur la vraie base. Si dépassé : photo partielle (seulement les tables qui ont changé d'empreinte) ou empreinte par tranche.
- **Recommandation :** mesurer d'abord ; n'optimiser qu'avec une mesure en main.
- **Décision utilisateur :**

---

## Ambiguïtés issues de la première trace réelle (S-201)

### AMB-041 — Interprétation de la trace réelle S-201 : 3 corrections de F6/F7 + 1 hypothèse facultative
- **Statut :** OUVERTE (non bloquante : rien n'est codé tant que l'utilisateur n'a pas tranché)
- **Jalon / SPEC :** J3 / §7.1 (F6), §7.2 (F7), §7.3, §7.4
- **Source :** `donnees_reelles/S-201/trace.json` (fiche S-201, facture d'achat avec TVA, 5 tables modifiées, 14 liens, 79 champs calculés, 2 écarts de saisie).
- **Contexte général :** la SPEC est muette sur ces cas. Le §7.3 interdit toute heuristique non passée par ce registre ; les points 1 à 3 modifient des règles de F6/F7, le point 4 en ajoute une.

#### Point 1 — Espaces de fin (F6 et F7/§7.4)
- **Constat :** le logiciel stocke les textes complétés par des espaces (CHAR). Exemples de la trace : `ecrit.Document = 'TEST-S201     '`, `ecrit.Libelle = 'TEST-S201                               '`, `ecrit.Compte = '61263    '`. F6 ne les relie pas à la saisie `TEST-S201` / `61263` (« exacte » exige l'égalité stricte) : d'où deux faux écarts `introuvable` (Document, Libellé) et `Document`/`Libelle`/`Compte` classés `inconnu` dans `champs_calcules`. La même cause fait que le compte `34552    ` et la clé `compte.Compte = '34552    '` apparaissent avec leurs espaces.
- **Options :**
  1. Nouveau `type_correspondance = espaces_fin` : comparaison après `rstrip` des deux côtés (espaces uniquement, pas les autres blancs), confiance **haute**, utilisée par F6 (liens) **et** par la recherche de valeur attendue de §7.4 (un lien `espaces_fin` n'est jamais un écart). Valeurs brutes inchangées dans `trace.json`.
  2. Normaliser (rstrip) dès la photo/le diff (SPEC §6.2). Rejeté par la demande : fausserait les valeurs brutes et masquerait un changement d'espaces seul dans le diff.
  3. Ne rien faire et tolérer les faux écarts. Rejeté : le rapport est inexploitable.
- **Recommandation :** option 1. Pas de `lstrip` ni de casse : ce sont d'autres correspondances (déjà prévues, « majuscules »). Le `rstrip` se limite aux colonnes texte ; il ne s'applique jamais à un montant.
- **Tests (à écrire avec le code, après décision) :**
  - unitaire F6 : `'TEST-S201     '` ↔ `'TEST-S201'` donne un lien `espaces_fin`, confiance haute ; `'61263    '` ↔ `'61263'` idem ;
  - `' TEST-S201'` (espace en tête) ne correspond **pas** ;
  - une valeur exacte reste classée `exacte` (priorité sur `espaces_fin`) ;
  - §7.4 : un écart n'est pas émis quand la valeur est trouvée en `espaces_fin` ; il l'est toujours quand elle est absente ou différente (`1243.56` vs `1234.56`) ;
  - non-régression : valeurs brutes de `trace.json` strictement identiques ;
  - **cas réel :** rejouer l'analyse de `trace.json` S-201 → `ecarts_saisie == []` (plus d'écart sur Document ni Libellé) ; `ecrit.Document`, `ecrit.Libelle` (ligne 3), `ecrit.Compte` (`61263    `) apparaissent dans `liens`, plus dans `champs_calcules`.
- **Sous-question à trancher :** la ligne 2 `Libelle = 'TVA/TEST-S201   …'` contient la saisie sans lui être égale ; elle reste `inconnu` (pas de correspondance « contient » en V1) — OK ?

#### Point 2 — Bruit de l'hypothèse `copie`
- **Constat :** sur 79 champs calculés, la majorité des `copie` sont fortuites : `ecrit.Debit 0.0000 copie de Tableau20.Brut (ligne code = 10)`, `ecrit.Lettrage 0 copie de tab3_param.code_Intitule`, `ecrit.Tva '   ' copie de journal.Tva`, `ecrit.Pointage ' ' copie de Table des erreurs.Compte`. Une valeur triviale (0, vide, blanc) se retrouve dans n'importe quelle table, et `Table des erreurs` / `Erreurs de conversion*` sont des tables techniques d'Access, sources aléatoires.
- **Options :**
  1. (a) Exclure de `copie` les valeurs triviales : nulles, `0` / `0.0000` (tout zéro décimal), chaîne vide ou blanche (après `rstrip`) ; (b) nouveau paramètre de config `tables_ignorees_analyse` (liste, motifs avec `*` acceptés, défaut `["Table des erreurs", "Erreurs de conversion*"]`) retirant ces tables **comme sources** de `copie` uniquement. Elles restent photographiées et diffées (contrairement à `tables_ignorees` existant, qui les exclut de tout).
  2. Idem 1(a) mais sans paramètre : liste codée en dur. Moins flexible, plus simple.
  3. Réutiliser `tables_ignorees`. Rejeté : masquerait aussi leurs changements dans le diff, ce qui est une perte d'information.
- **Recommandation :** option 1. Un champ trivial dont `copie` est écartée reste alors `constante` si elle tient, sinon `inconnu` ; il n'est pas supprimé du rapport. On n'invente pas d'étiquette « valeur_triviale » (§7.3).
- **Tests :**
  - unitaire : `0`, `0.0000`, `''`, `'   '`, `None` ne produisent jamais `copie` ; `'A20'` ou `20.0000` (non triviale) peut encore la produire ;
  - une source nommée `Table des erreurs` ou `Erreurs de conversion (1)` n'est jamais citée dans `details` ; une autre table l'est toujours ;
  - `tables_ignorees_analyse` vide ⇒ ces tables redeviennent sources ; ajouter `config.example.json` + validation de la clé ;
  - **cas réel :** sur S-201, plus aucune ligne « copie de Tableau20.Brut », « copie de tab3_param.code_Intitule » (valeurs 0) ni « copie de Table des erreurs.Compte » ; `ecrit.Debit 0.0000` passe à `constante`/`inconnu`.
- **Question :** noms exacts des tables techniques et motif `Erreurs de conversion*` : à confirmer sur la vraie base (casse, suffixes numériques).

#### Point 3 — Hypothèse `compteur` sur colonnes monétaires
- **Constat :** `compte.Credit 39650045.36 → 39651526.83` est marqué `compteur` (parce que delta constant = 1481.47), alors que c'est un cumul de montants. Même cas `scompte.Credit 732.00 → 2213.47`. Ces lignes portent déjà `cumul_mis_a_jour`, la mention `compteur` est trompeuse.
- **Options :**
  1. `compteur` réservée aux colonnes de type entier (SMALLINT, INTEGER, COUNTER/NuméroAuto) et aux colonnes texte dont **toutes** les valeurs avant sont numériques (codes comme `Piece`) ; jamais aux types CURRENCY/DECIMAL/DOUBLE/SINGLE.
  2. Même restriction, mais le type est déduit des seules valeurs (forme décimale `x.xxxx` ⇒ monnaie), faute de type fiable. Moins sûr avec le pilote ODBC (voir AMB-001).
  3. Ne pas restreindre. Rejeté : bruit et risque de conclusion fausse.
- **Recommandation :** option 1, avec le type issu des métadonnées de colonne (SPEC §6.4). Pour une colonne texte, vérifier sur la photo avant (≥ N lignes, toutes `^\d+$` après `rstrip`) ; N à fixer.
- **Tests :** `ecrit.Compteur` (entier, `max avant = 26601`) reste `compteur` ; `ecrit.Lien` (entier) idem ; `compte.Credit`, `scompte.Credit` (monnaie) n'ont **jamais** `compteur`, mais gardent `cumul_mis_a_jour` ; colonne texte numérique (type `Piece`) éligible, colonne texte mixte non ; `CURRENCY` constant +1 non éligible ; **cas réel :** plus de ligne « compteur : 39650045.3600 → 39651526.8300 ».
- **Question :** `ecrit.Piece = '990201'` est un code texte numérique : faut-il le laisser `inconnu` ou l'autoriser en `compteur` si la photo montre `max avant = 990200` ? Le critère « texte numérique » l'autorise.

#### Point 4 (facultatif) — Hypothèse `cumul_hierarchique`
- **Constat :** 13 comptes de `compte` sont modifiés pour 2 comptes saisis (61263 et 441110024) plus la TVA 34552 générée par le logiciel. Chaque compte et tous ses préfixes reçoivent le même delta : `61263/6126/612/61` +1234.56 (Débit) ; `441110024/44111/4411/441/44` +1481.47 (Crédit) ; `34552/3455/345/34` +246.91 (Débit). Le delta 246.91 (20 % de 1234.56) n'est **pas** un montant saisi : `cumul_mis_a_jour` ne l'explique pas, donc ces 4 lignes restent `inconnu`.
- **Options :**
  1. Ajouter `cumul_hierarchique` : delta identique d'une colonne sur un compte et sur ses préfixes (compte parent = préfixe de longueur inférieure, après `rstrip`) ; détail = « delta d sur N niveaux, rattaché à la ligne `ecrit` x » quand une ligne insérée a ce montant (cas 246.91 = `ecrit.Debit` de la ligne 2). Marquée hypothèse, comme les autres.
  2. Ne pas l'ajouter en V1 ; l'analyse humaine le déduira. Les 4 lignes `34…` resteront `inconnu`.
  3. Étendre `cumul_mis_a_jour` plutôt que créer une hypothèse. Plus économe, mais mélange deux logiques.
- **Recommandation :** option 1 si l'utilisateur veut un rapport lisible dès J3 ; sinon option 2 (aucune dette). Reste hors périmètre V1 si non validée (CLAUDE.md règle 3).
- **Tests :** trace S-201 : trois chaînes (4 + 5 + 4 comptes) toutes reconnues ; delta différent sur un préfixe ⇒ pas d'hypothèse ; deux comptes sans lien de préfixe avec même delta ⇒ pas d'hypothèse ; préfixe sans mise à jour ⇒ hypothèse non retenue ; le préfixe est calculé sur la clé après `rstrip` (point 1).

- **Constats hors périmètre (aucune décision demandée) :** `ecrit.lien_tva = 26603` reste `inconnu` (il vaut le `Compteur` de la ligne 2 — une copie intra-table, pas prévue par F7) ; `ecrit.Contre_partie = 2` et `sjournal.Piece` idem. À reprendre si l'utilisateur le souhaite via un autre AMB.
- **Ordre de mise en œuvre recommandé :** 1 → 3 → 2 → (4). Le point 1 conditionne le point 4 (préfixes sur clés `rstrip`).
- **Code concerné :** `TODO(AMB-041)` dans `traceur/moteur/liens.py` (points 1) et `traceur/moteur/calcules.py` (points 2 à 4) — pas encore créés ; `config.example.json` (clé `tables_ignorees_analyse`).
- **Décision utilisateur :** _(vide : à indiquer par point — 1, 2, 3 : option retenue ; 4 : oui/non)_
- **Date de clôture :**
