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

## Ambiguïtés détectées à la lecture (J0, 2026-10-03)

### AMB-003 — Noms des clés de `changements[]` (SPEC §8.1 vs exemple)
- **Statut :** OUVERTE
- **Jalon / SPEC :** J1, J5 / §8.1, `trace.example.json`
- **Contexte :** le §8.1 cite `insert/update/delete/update_probable` ; l'exemple utilise `inserts`, `updates`, `deletes`, `updates_probables`, `lignes_ajoutees`, `lignes_supprimees`.
- **Options :** 1. L'exemple fait foi (pluriels). 2. Aligner l'exemple sur le §8.1.
- **Recommandation :** 1, et corriger la formulation du §8.1.
- **Décision utilisateur :**

### AMB-004 — Hypothèse `compteur` sur un champ texte
- **Statut :** OUVERTE
- **Jalon / SPEC :** J3 / §7.2
- **Contexte :** `PIECE` vaut `"0042"` (texte, zéros de tête, « max avant = 0041 »). « max + 1 » n'est défini que pour un numérique.
- **Options :** 1. Accepter un texte entièrement numérique, en conservant la largeur. 2. Numérique uniquement. 3. Gérer préfixe + suffixe numérique.
- **Recommandation :** 1.
- **Décision utilisateur :**

### AMB-005 — Lien entre message affiché et valeurs en base
- **Statut :** OUVERTE
- **Jalon / SPEC :** J3 / §7.1, §5.2
- **Contexte :** message `2025-ACH-0042`, colonne `PIECE` = `0042`. La saisie « Remarques » est du texte libre ; aucun lien n'est prévu.
- **Options :** 1. Aucun lien automatique (analyste). 2. Recherche de sous-chaînes numériques des remarques dans les lignes insérées (hors SPEC).
- **Recommandation :** 1 en V1.
- **Décision utilisateur :**

### AMB-006 — Statuts non énumérés
- **Statut :** OUVERTE
- **Jalon / SPEC :** J5, J6 / §5.1, §8
- **Contexte :** statuts de fiche (`à faire`/`faite`/`écart`) et de trace (`terminee`, `annulee`, `ecart_saisie`, `en_attente_depot`) incohérents ; pas de statut de fiche pour « annulée ».
- **Options :** 1. Statut de fiche dérivé de la dernière trace, ajout de `annulée`. 2. Garder tel quel.
- **Recommandation :** 1, enum unique documentée.
- **Décision utilisateur :**

### AMB-007 — Emplacement de `journal.log`
- **Statut :** OUVERTE
- **Jalon / SPEC :** J4, J6 / §10, §11
- **Contexte :** §10 : `sorties/journal.log` (peut être un partage réseau indisponible) ; §11 : `journal.log` sans chemin. Un mot de passe ne doit jamais y figurer.
- **Options :** 1. Dossier local à côté de l'exe. 2. Dans `dossier_sorties`. 3. Local, copie dans `dossier_sorties` au dépôt.
- **Recommandation :** 1.
- **Décision utilisateur :**

### AMB-008 — Fichier de verrou `.ldb` / `.laccdb`
- **Statut :** OUVERTE
- **Jalon / SPEC :** J4 / §10
- **Contexte :** seul `.ldb` est vérifié ; `.gitignore` prévoit aussi `.accdb`/`.laccdb`.
- **Options :** 1. `.ldb` et `.laccdb` selon l'extension de la base. 2. `.ldb` uniquement.
- **Recommandation :** 1.
- **Décision utilisateur :**

### AMB-009 — Valeurs saisies répétées pour un même champ d'écran
- **Statut :** OUVERTE
- **Jalon / SPEC :** J3 / §7.1, §9
- **Contexte :** « Débit » apparaît 2 fois (1234.56 et 246.91) avec les mêmes `champ_ecran`/`ecran`. Le lien est cherché valeur par valeur, mais le rapport ne distingue pas les occurrences.
- **Options :** 1. Lier par valeur, rapporter la valeur dans chaque lien. 2. Ajouter un index d'occurrence au format des fiches.
- **Recommandation :** 1 (aucun changement de format).
- **Décision utilisateur :**

### AMB-010 — F7 sans profil disponible
- **Statut :** OUVERTE
- **Jalon / SPEC :** J2, J3 / §7.2, §6.4
- **Contexte :** `constante` et l'usage des relations candidates (`copie`) dépendent du profil ; comportement si absent ou périmé non défini.
- **Options :** 1. Hypothèses dépendantes du profil désactivées, avertissement dans le rapport. 2. Profilage obligatoire avant toute fiche.
- **Recommandation :** 1.
- **Décision utilisateur :**
