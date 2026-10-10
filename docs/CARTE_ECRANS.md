# Carte des écrans — Compta PLus (GENIE LOG)

> Référentiel unique des écrans du logiciel legacy. Captures, fiches, traces et futurs écrans du nouveau logiciel utilisent ces codes.
> Version 6 — 2026-10-05 — + réponses du comptable (§9) et priorisation v2 (§10).

## 1. Identification du logiciel (capture E-8)

| Élément | Valeur |
|---|---|
| Produit | **Compta PLus** Ver. 2019.01 |
| Éditeur | GENIE LOG SARL, Meknès (coordonnées sur la capture E-8) |
| Licence | N° 1 |
| Dernier contrat de maintenance | 10/06/2020 |
| Origine | Noyau 2000, retouches mineures jusqu'en 2019 ; menu « Reprise d'un dossier dos » ⇒ ascendance DOS |
| Barre de titre | `*** <SOCIÉTÉ> Exercice <AAAA> Utilisateur <PROFIL> ***` ⇒ repère TEST visible ici |

## 2. Règles de nomenclature

- `E-<menu>.<entrée>` : entrée de menu, numérotée dans l'ordre d'affichage (ex. `E-2.01`).
- `E-<menu>.<entrée>.<sous-entrée>` : entrée d'un sous-menu ▸ (ex. `E-2.01.02`).
- Suffixe `-a`, `-b`… : onglet ou fenêtre secondaire d'un écran (ex. `E-7.04-a`).
- Fichier de capture : `E-2.01.02_saisie-avec-tva_vide.png`. États : `_menu`, `_vide`, `_rempli`, `_message`, `_apercu`.
- Les boutons de la barre d'outils n'ont pas de code propre : ils renvoient à une entrée de menu (§4).
- Un code n'est jamais réattribué. Une entrée découverte plus tard reçoit le numéro suivant libre.

## 3. Arborescence

Légende risque : 🟢 consultation, capture sans risque · 🟠 écran de saisie ou paramétrage, ouvrir puis **Annuler**, uniquement sur le dossier TEST · 🔴 traitement lourd ou global, **ne pas ouvrir** avant l'environnement TEST isolé (AMB-038) · ▸ sous-menu à capturer.

### E-0 — Écran principal 🟢

### E-1 — Dossier
| Code | Entrée | Risque | Remarque |
|---|---|---|---|
| E-1.01 | Création dossier | 🔴 | Écrit dans le catalogue. Lot 1b |
| E-1.02 | Création exercice | 🔴 | Lot 1b |
| E-1.03 | Ouverture exercice | 🟢 | Choix société/exercice (liste du catalogue) |
| E-1.04 | Fermer un dossier | 🟢 | |
| E-1.05 | Sauvegarde d'un exercice sur disque | 🔴 | Format de sauvegarde à étudier plus tard |
| E-1.06 | Installation de la liasse fiscale | 🔴 | Modèle de liasse installé à part ? |
| E-1.07 | Réparation de la base de donnée | 🔴 | Grisé pour le profil SAISIE (droits) |
| E-1.08 | Quitter le programme | 🟢 | |

### E-2 — Ecriture
| Code | Entrée | Risque | Remarque |
|---|---|---|---|
| E-2.01 | Saisie des écritures ▸ | 🟠 | Cœur du lot 2 |
| E-2.01.01 | ↳ Avec TVA | 🟠 | = bouton « Avec TVA » |
| E-2.01.02 | ↳ Sans TVA | 🟠 | = bouton « Sans TVA » |
| E-2.01.03 | ↳ Ancienne version | 🟠 | = bouton « Anc. Version ». **Jamais utilisé — hors périmètre** |
| E-2.02 | Transfert ▸ | 🔴 | Déplacement d'écritures. **Utilisé chaque jour** (comptable) : à tracer sur TEST |
| E-2.02.01 | ↳ De compte à compte | 🔴 | |
| E-2.02.02 | ↳ De journal à journal | 🔴 | |
| E-2.03 | Pointage des écritures | 🟠 | Distinct du lettrage (voir E-2.04). Lot 3 |
| E-2.04 | Analyse des tiers ▸ | 🟠 | **C'est le lettrage** (et non une consultation) |
| E-2.04.01 | ↳ Pré-lettrage des tiers | 🟠 | Lot 3 |
| E-2.04.02 | ↳ Lettrage des tiers | 🟠 | Lot 3 |
| E-2.04.03 | ↳ Lettrage automatique | 🔴 | Traitement de masse |
| E-2.05 | Rapprochement bancaire | 🟠 | Lot 3 |
| E-2.06 | Contrôle de la comptabilité | 🔴 | **Utilisé chaque jour** (comptable). Corrige-t-il des données ? À tracer sur TEST |
| E-2.07 | Pont avec la gestion comm. ▸ | 🔴 | **Génération automatique d'écritures** depuis la gestion commerciale |
| E-2.07.01 | ↳ Comptabilité des achats | 🔴 | |
| E-2.07.02 | ↳ Comptabilité des ventes | 🔴 | |
| E-2.07.03 | ↳ Comptabilité des règlements fournisseur | 🔴 | |
| E-2.07.04 | ↳ Comptabilité des règlements client | 🔴 | |
| E-2.07.05 | ↳ Comptabilité des retours emballages | 🔴 | **Jamais utilisé — hors périmètre** |
| E-2.07.06 | ↳ Comptabilité des dossiers imports | 🔴 | **Jamais utilisé — hors périmètre** |
| E-2.07.07 | ↳ Comptabilité des achats de MP et Emballage | 🔴 | **Jamais utilisé — hors périmètre** |
| E-2.07.08 | ↳ Suppression des transferts fournisseurs | 🔴 | |
| E-2.07.09 | ↳ Suppression des transferts clients | 🔴 | |
| E-2.07.10 | ↳ Suppression des transferts dossiers imports | 🔴 | **Hors périmètre** (dossiers imports jamais utilisés) |
| E-2.07.11 | ↳ Contrôle des transferts clients | 🟢 ? | Probablement lecture seule, à confirmer |
| E-2.07.12 | ↳ Contrôle des transferts fournisseurs | 🟢 ? | idem |

### E-3 — Consultation
| Code | Entrée | Risque |
|---|---|---|
| E-3.01 | Consultation des journaux ▸ | 🟢 |
| E-3.01.01 | ↳ Ecritures par journal | 🟢 |
| E-3.01.02 | ↳ Centralisation par journal | 🟢 |
| E-3.01.03 | ↳ Journal général | 🟢 |
| E-3.01.04 | ↳ Ecritures par journal avec solde | 🟢 |
| E-3.01.05 | ↳ Totaux des journaux | 🟢 |
| E-3.02 | Consultation extrait de compte ▸ | 🟢 |
| E-3.02.01 | ↳ Sans solde | 🟢 |
| E-3.02.02 | ↳ Avec solde | 🟢 |
| E-3.03 | Consultation des balances ▸ | 🟢 |
| E-3.03.01 | ↳ Balance exercice en cours | 🟢 |
| E-3.03.02 | ↳ Balance ouverture | 🟢 |
| E-3.03.03 | ↳ Balance exercice précédent | 🟢 |
| E-3.03.04 | ↳ Balance Agée | 🟢 |
| E-3.04 | Autres consultations ▸ | 🟢 |
| E-3.04.01 | ↳ Consultation des rapprochements | 🟢 |
| E-3.04.02 | ↳ Consultation échéancier | 🟢 |
| E-3.04.03 | ↳ Consultation des chèques | 🟢 |
| E-3.04.04 | ↳ Consultation des pièces | 🟢 |
| E-3.04.05 | ↳ Consultation de la Tva à déclarer | 🟢 |
| E-3.04.06 | ↳ Consultation de la declaration de la TVA | 🟢 |
| E-3.04.07 | ↳ Cons. Etat des ventes | 🟢 |
| E-3.05 | Recherche multi-critères | 🟢 |
| E-3.06 | Consultation de la liasse fiscale ▸ | 🟢 |
| E-3.06.01 | ↳ **Calcul** — calcule la liasse, écrit probablement des tables de résultats ; trace à très forte valeur, **sur TEST uniquement** | 🔴 |
| E-3.06.02 | ↳ Bilan | 🟢 |
| E-3.06.03 | ↳ CPC | 🟢 |
| E-3.06.04 | ↳ Détail CPC | 🟢 |
| E-3.06.05 | ↳ TFR et CAF | 🟢 |
| E-3.06.06 | ↳ Etat des immobilisations | 🟢 |
| E-3.06.07 | ↳ Etat des amortissements | 🟢 |
| E-3.06.08 | ↳ Etat des provisions | 🟢 |
| E-3.06.09 | ↳ Etat de la TVA | 🟢 |
| E-3.06.10 | ↳ Etat des cessions | 🟢 |
| E-3.06.11 | ↳ Contrôle des immobilisations | 🟢 |

Constats E-3 :
- **Balance exercice précédent** et **Balance ouverture** : le logiciel lit un autre dossier (exercice N-1) ou des à-nouveaux. Lecture inter-dossiers à prévoir dans la migration.
- **Échéancier, chèques, balance âgée** : les écritures portent des échéances et des références de chèques.
- **TVA à déclarer / déclaration de la TVA** : la logique TVA existe dans le logiciel (règles de 2019 au plus tard).
- **Liasse fiscale** : Bilan, CPC, TFR/CAF et états annexes. Si « Calcul » stocke ses résultats en base, une seule trace donne le mapping comptes → lignes des états de synthèse, avec les chiffres de référence pour le comparateur d'états.

### E-4 — Edition
| Code | Entrée | Risque | Remarque |
|---|---|---|---|
| E-4.01 | Edition du grand livre ▸ | 🟢 | État de référence (lot 4) |
| E-4.01.01 | ↳ Grand livre détaillé | 🟢 | |
| E-4.01.02 | ↳ Grand livre centralisé | 🟢 | |
| E-4.02 | Edition des soldes par mois des comptes | 🟢 | État de référence |
| E-4.03 | Edition du plan comptable | 🟢 | Source du plan comptable des fiches |

### E-5 — Immobilisation (nouveau domaine)
| Code | Entrée | Risque |
|---|---|---|
| E-5.01 | Codification des immobilisations | 🟠 |
| E-5.02 | Calcul des amortissements | 🔴 |
| E-5.03 | Gestion des cessions/retraits/virements | 🟠 |
| E-5.04 | Recherche des immobilisations | 🟢 |

### E-6 — Clôt./Réouv.
| Code | Entrée | Risque | Remarque |
|---|---|---|---|
| E-6.01 | Clôture périodique | 🔴 | Lot 3, sur TEST uniquement, après instantané |
| E-6.02 | Clôture de l'exercice | 🔴 | Lot 5 |
| E-6.03 | Report à nouveau | 🔴 | Lot 5 |

### E-7 — Initialisation
| Code | Entrée | Risque | Remarque |
|---|---|---|---|
| E-7.01 | Codification des comptes | 🟠 | Lot 1a (plan comptable : dossier ou catalogue ?) |
| E-7.02 | Codification des journaux | 🟠 | Lot 1a |
| E-7.03 | Codification des TVA | 🟠 | Clé pour la saisie « Avec TVA » |
| E-7.04 | Codification des tiers | 🟠 | Lot 1a (S-000) |
| E-7.05 | Codification des modes de paiement | 🟠 | |
| E-7.06 | Paramétrage du type de compte par journal | 🟠 | Règles de contrôle de saisie |
| E-7.07 | Paramétrage de l'exercice | 🟠 | Dates, périodes, verrouillages |
| E-7.08 | Paramétrage du transfert de la gestion commerciale | 🟠 | |
| E-7.09 | Reprise d'un dossier dos | 🔴 | Héritage DOS |
| E-7.10 | Ajout d'écritures d'un autre dossier | 🔴 | |
| E-7.11 | Correction de la version | 🔴 | Modifie probablement la structure de la base : **jamais** |
| E-7.12 | Ajout d'écriture d'un fichier excel | 🔴 | **Jamais utilisé — hors périmètre** (outil de migration de l'éditeur) |
| E-7.13 | Ajout d'immobilisations d'un fichier excel | 🔴 | **Jamais utilisé — hors périmètre** |
| E-7.14 | Ajout des écritures de vente par excel | 🔴 | **Jamais utilisé — hors périmètre** |
| E-7.15 | Paramétrage Ecriture d'abonnement | 🟠 | Écritures récurrentes |
| E-7.16 | Interface GC compta par excel | 🔴 | **Jamais utilisé — hors périmètre** |

### E-8 — ©GENIE LOG (fenêtre « Copyright ») 🟢

## 4. Barre d'outils → menus

Correspondances **supposées**, à confirmer par l'infobulle (bandeau rose) de chaque bouton.

| Bouton | Renvoie à | Statut |
|---|---|---|
| Ouvre | E-1.03 | supposé |
| Ferme | E-1.04 | confirmé (infobulle « fermer un dossier ») |
| Avec TVA | E-2.01.01 | confirmé (libellé identique) |
| Sans TVA | E-2.01.02 | confirmé |
| Anc. Version | E-2.01.03 | confirmé |
| Analyse | ? (pas E-2.04, qui est le lettrage) | à confirmer |
| Compte | E-3.02.x | supposé |
| Journal | E-3.01.x | confirmé (infobulle « consulter le journal ») |
| Balance | E-3.03.x | supposé |
| Calcul | E-3.06.01 (calcul de la liasse) ? | **probable, ne pas cliquer** — vérifier l'infobulle |
| Liasse | E-3.06.x | supposé |
| ? Ecriture | E-3.05 ? | à confirmer |
| ? Compte | ? | à confirmer |
| ? Immob. | E-5.04 | supposé |
| Arrêt du programme | E-1.08 | confirmé |

## 5. Questions ouvertes

1. Quels menus le comptable utilise-t-il réellement, et lesquels jamais ? Cela réduit le périmètre à reconstruire.
2. ~~Gestion commerciale~~ → même éditeur, SQL Server `192.168.16.99` ; mécanisme décrit au §8. La part des écritures venant du pont se **mesure** par comptage de `Externe`.
3. ~~Imports Excel~~ → **jamais utilisés** (pas de modèle fourni par le logiciel ; probablement des outils de migration de l'éditeur). Hors périmètre.
4. Le plan comptable est-il propre au dossier ou partagé dans le catalogue ? (Test de la date de `catalogue.mdb` pendant une fiche E-7.01.)
5. Le profil SAISIE a-t-il des droits restreints (E-1.07 grisé) ? Les fiches doivent utiliser le profil réel du comptable.
6. L'éditeur GENIE LOG est-il joignable (dictionnaire de données, formats) ?

## 6. Vague 1 de captures

**A. Sous-menus ▸** (menu ouvert, sans cliquer, la base de production convient) :
- ✅ terminée : tous les sous-menus sont capturés.

**B. Écrans 🟢** (production possible, lecture seule) :
E-1.03, E-3.01.x, E-3.02.x, E-3.03.x, E-4.03 (aperçu), et les infobulles des boutons « à confirmer » du §4.

**C. Écrans 🟠, uniquement sur le dossier TEST** (ouvrir, capturer `_vide`, **Annuler**) :
E-2.01.x (Avec TVA, Sans TVA), E-7.01, E-7.02, E-7.03, E-7.04, E-7.06, E-7.07.

> Pourquoi pas en production : un écran de saisie peut réserver un numéro de pièce ou poser un verrou dès son ouverture, ce qui est une écriture dans la vraie base.

## 7. Priorisation des premières fiches (proposition v1 — **remplacée par la v2 au §10**)

**Critère :** le maximum de règles apprises pour le minimum de temps du comptable, du plus simple au plus complexe, chaque fiche s'appuyant sur la précédente.
**Numérotation :** `S-<lot><nn>`, par exemple S-101 pour la première fiche du lot 1, S-201 pour la première du lot 2.
**Statut :** provisoire. L'ordre peut changer selon les réponses du comptable aux questions 1 à 3 du §5.

### Étape 0 — sans le comptable (vous seul, sur le dossier TEST)
| Action | But |
|---|---|
| Profilage du dossier TEST | Dictionnaire des tables, clés, relations |
| Calibration du bruit (logiciel ouvert, sans action) | Isoler les tables techniques |
| S-000 (validation du délai + date de `catalogue.mdb`) | Valider l'outil et la réserve du catalogue |

### Séance 1 — Référentiels (lot 1a) · ~15 min
| Fiche | Écran | Ce qu'on apprend |
|---|---|---|
| S-101 Création d'un compte | E-7.01 | Table du plan comptable ; le plan est-il dans le dossier ou dans le catalogue ? |
| S-102 Création d'un journal | E-7.02 | Table des journaux, paramètres, compteur de pièces |
| S-103 Création d'un tiers | E-7.04 | Table des tiers, lien avec le compte collectif (S-000 la couvre déjà en partie) |

### Séance 2 — Saisie de base (lot 2) · ~15 min
| Fiche | Écran | Ce qu'on apprend |
|---|---|---|
| S-201 Écriture simple sans TVA (2 lignes) | E-2.01.02 | Tables en-tête/lignes, numérotation des pièces, cumuls éventuels |
| S-202 Facture d'achat avec TVA | E-2.01.01 | **Génération automatique de la ligne TVA**, codes TVA, arrondis |
| S-203 Facture de vente avec TVA | E-2.01.01 | TVA collectée vs déductible, sens des montants |

### Séance 3 — Cycle de vie d'une écriture (lot 2) · ~15 min
| Fiche | Écran | Ce qu'on apprend |
|---|---|---|
| S-204 Modification d'une écriture (S-201) | E-2.01.02 | UPDATE ou supprimer/recréer ? historique ? |
| S-205 Suppression d'une écriture | E-2.01.02 | Suppression physique ou logique ? trou de numérotation ? |
| S-206 Écriture avec échéance et chèque | E-2.01.x | Champs utilisés par l'échéancier et la consultation des chèques |

### Séance 4 — Traitements (lot 3) · ~15 min
| Fiche | Écran | Ce qu'on apprend |
|---|---|---|
| S-301 Lettrage manuel d'un tiers (S-202 + règlement) | E-2.04.02 | Code de lettrage, où il est stocké |
| S-302 Pointage d'écritures | E-2.03 | Différence pointage / lettrage |
| S-303 Rapprochement bancaire | E-2.05 | Tables de rapprochement |

### Séance 5 — États et liasse (lot 4) · ~15 min
| Fiche | Écran | Ce qu'on apprend |
|---|---|---|
| S-401 Balance + grand livre exportés | E-3.03.01, E-4.01.01 | États de référence pour le comparateur (aucune écriture attendue) |
| S-402 TVA à déclarer | E-3.04.05 | Règles de la déclaration TVA |
| S-403 **Calcul de la liasse** (réinitialiser avant) | E-3.06.01 | Correspondance comptes → Bilan/CPC si les résultats sont stockés. **Trace à plus forte valeur** |

### Reportés, à décider selon les réponses du comptable
| Domaine | Écrans | Condition |
|---|---|---|
| Pont gestion commerciale | E-2.07.x | **Devient prioritaire** si la majorité des écritures en vient. Prérequis : copie TEST de la base GC + E-7.08 repointé + traçage multi-bases (voir §8) |
| Immobilisations | E-5.x | Si utilisé (question 1) |
| Écritures d'abonnement | E-7.15 | Si utilisé (question 1 au comptable). Imports Excel E-7.12 à E-7.14, E-7.16 : **hors périmètre** |
| Clôture périodique | E-6.01 | Après la séance 4, sur TEST réinitialisé |
| Lots 1b et 5 | E-1.01, E-1.02, E-6.02, E-6.03 | Après AMB-038 (catalogue) |

## 8. Pont gestion commerciale (GC) — constats du 2026-10-04

**Source :** captures E-7.08 et E-2.07.02, et explications de l'utilisateur. La GC est du **même éditeur** (GENIE LOG).

### E-7.08 — Paramétrage du transfert de la gestion commerciale
| Bloc | Champs |
|---|---|
| GC principale | Dossier GC ou nom de base, Exercice, Programme GC ; case **Base donnée SQL SERVER** + Serveur, Utilisateur, Mot de passe, Serveur local |
| Gestion minoterie | idem + case « Gestion des Blés » |
| GC (briq), GC (Gaz) | Dossier, Exercice, Programme GC |
| Hôtel | Nom base, Nom serveur, case « Factures traitées » |
| Clinique | Base clinique |
| Options | **Création des tiers automatique**, **Utiliser les comptes de l'indexe** |

Constats :
- Le logiciel est un **produit générique multi-métiers** (minoterie, briqueterie, gaz, hôtel, clinique). **Confirmé par l'utilisateur : seul le bloc « GC principale » est utilisé.** Tous les autres blocs sont **hors périmètre**.
- **Capture du 2026-10-04 :** SQL Server coché, Serveur = `192.168.16.99`, Utilisateur et mot de passe vides (probablement une authentification Windows). Les valeurs `GC_TEST` / 2024 visibles ont été **saisies pour la démonstration et non validées** : la configuration de production n'a pas été modifiée.
- **Cible TEST décidée :** base SQL Server `GC_TEST` = copie de la GC 2026 ; E-7.08 du **dossier TEST** réglé sur `GC_TEST` / 2026.
- ⇒ **La GC est une base SQL Server.** Pour tracer le pont, le traceur devra lire une base SQL Server en plus du `.mdb`. L'interface `SourceDonnees` le permet sans toucher au moteur.
- Le transfert peut **créer des tiers** dans la comptabilité et imputer via des **comptes d'index**, qui sont des règles d'imputation à documenter.
- ⚠️ Cet écran contient un **mot de passe**. Toute capture doit masquer ce champ.

### E-2.07.02 — Comptabilité des factures de vente (même logique pour les achats, E-2.07.01)
| Élément | Détail |
|---|---|
| Sélection | Période du/au, Journal, Représentant, Dossier/Exercice GC |
| Options | Même libellé pour les écritures ; **Passer avoir en contre-passation** ; **Passer ICE de la Gestion à la Compta** ; **Passer ICE de la Compta à la Gestion** |
| Boutons | Valider, **Transférer ICE**, STOP |
| Résultat | **Liste des anomalies** (contrôles avant ou pendant le transfert) |

Constats :
- **Le transfert écrit dans les deux bases.** « Passer ICE de la Compta à la Gestion » modifie la base GC, et le marquage « déjà transférée » se trouve probablement aussi côté GC. Le traceur V1, qui ne voit que le dossier comptable, **ne suffit pas pour ces fiches**. Il faut aussi tracer une **copie de la base GC**, à rattacher à AMB-038 (traçage multi-bases).
- **ICE** : identifiant fiscal des tiers, synchronisé dans les deux sens. C'est un champ clé pour la TVA et la facturation électronique.
- **Liste des anomalies** : les messages d'anomalie sont des règles de contrôle. Il faut les capturer systématiquement (`_message`).

### Mécanisme du transfert (déclaré par l'utilisateur le 2026-10-04, à confirmer par trace)
| Côté | Effet d'un transfert |
|---|---|
| **GC (SQL Server)** | Les champs **Journal** et **Pièce** de l'en-tête de facture sont renseignés dans la table **`Ecrit`**. Ils servent de **verrou** : toute modification ou suppression de la facture est refusée avec le message « modification/suppression impossible : transférée dans la comptabilité ». |
| **Comptabilité (.mdb)** | Les écritures créées portent **`Externe = 1`**, ce qui distingue une écriture transférée d'une écriture saisie à la main (`Externe = 0` présumé). |

Structure des factures GC (déclarée) :
| Table | Contenu | Rôle dans le transfert |
|---|---|---|
| **`Ecrit`** | En-tête : date, tiers, mode de règlement, journal, pièce… | **Seule table concernée** par le transfert et le verrou (Journal + Pièce) |
| **`EcritL`** | Lignes : code article, désignation, prix unitaire… | Lue pour calculer les montants et imputations ; non modifiée par le transfert |

Règles d'imputation (déclarées) :
| Source GC | Champ | Utilisé pour |
|---|---|---|
| **Article** (code unique) | **Compte comptable achat** (obligatoire) | Ligne de charge HT d'une facture d'achat |
| **Article** | **Compte comptable vente** (obligatoire) | Ligne de produit HT d'une facture de vente |
| **Tiers** (client/fournisseur) | **Compte comptable** | Ligne TTC du tiers |

Écriture type supposée, à confirmer par trace :
- Vente : Débit compte tiers (TTC) / Crédit compte vente de l'article (HT) / Crédit TVA collectée.
- Achat : Débit compte achat de l'article (HT) / Débit TVA déductible / Crédit compte tiers (TTC).

Inconnues :
- ~~TVA : taux porté par l'article ou par la ligne ?~~ → **par la ligne** : chaque ligne de `EcritL` porte un champ **`CodeTVA`** (déclaré). En saisie manuelle, la TVA est saisie dans l'écran « Avec TVA ».
- **Correspondance des codes TVA :** le `CodeTVA` de la GC renvoie-t-il aux mêmes codes que la codification TVA de la compta (E-7.03), qui donne le taux et le compte de TVA ? Ou existe-t-il une table de TVA propre à la GC ?
- **Regroupement :** une ligne d'écriture par ligne de facture, ou regroupement par compte / par taux ?
- **Option « Utiliser les comptes de l'indexe »** (E-7.08) : imputation alternative ?
- **Option « Création des tiers automatique »** : crée le compte du tiers dans la compta s'il n'existe pas ?
- **Liste des anomalies** : probablement article sans compte, tiers sans compte, compte absent du plan comptable.

Codification TVA de la GC (capture du 2026-10-04) :
| Code | Désignation | Taux | Compte achat | Compte vente | Constat |
|---|---|---|---|---|---|
| 00 | EXONERER | 0,00 | 34551 | 4455 | Exonéré imputé sur 34551 (TVA récupérable sur **immobilisations** en CGNC) : à vérifier |
| 01 | TVA 20% | 20,00 | 34552 | 4455 | OK |
| 02 | TVA 14% | 14,00 | 34552 | *(vide)* | ⚠️ pas de compte vente : une vente à 14 % échoue ou est mal imputée |
| 03 | TVA 7% | 7,00 | *(vide)* | *(vide)* | ⚠️ aucun compte |
| 04 | TVA 10% | 10,00 | 34552 | 4455 | OK |
| 05 | TVA 10% | **0,00** | 34552 | 4455 | ⚠️ **libellé 10 % mais taux 0** : une ligne codée 05 ne génère aucune TVA |

Constats :
- Un **seul compte de TVA collectée (4455)** et un seul compte déductible sur charges (34552), quel que soit le taux. La ventilation par taux exigée par la déclaration de TVA doit donc venir d'ailleurs : code TVA conservé sur la ligne d'écriture ? À vérifier par trace.
- **Ventes : 20 % uniquement** (déclaré). Les incohérences des codes 02, 03 et 05 sont donc sans effet côté ventes. **Côté achats**, des fournisseurs peuvent facturer à 7, 10 ou 14 % ou en exonéré : il faut vérifier les codes utilisés sur les factures d'achat.
- Les codes 02, 03 et 05 sont **incohérents ou incomplets**. Il faut vérifier s'ils sont utilisés dans `EcritL` (requête de comptage par `CodeTVA`). À traiter comme règle de qualité de données dans la migration.
- Les taux de TVA marocains ont évolué récemment : le référentiel du nouveau logiciel sera établi à partir de la réglementation en vigueur, pas recopié tel quel.
- À comparer avec la codification TVA de la **compta** (E-7.03) : mêmes codes ?

Conséquences :
- **Lien facture ↔ écriture** = (Journal, Pièce), stocké côté GC. C'est la clé de rapprochement entre les deux bases.
- **Hypothèse à vérifier** par trace (E-2.07.08 à .10) : la « suppression des transferts » vide Journal/Pièce côté GC (déverrouillage) et supprime les écritures `Externe = 1` correspondantes.
- **Nouveau logiciel :** reproduire le verrou de la facture transférée et la traçabilité de l'origine des écritures.
- **La part des écritures venant du pont se mesure directement** : `SELECT Externe, COUNT(*) FROM <table des écritures> GROUP BY Externe` sur la copie du dossier. Il n'est plus besoin de la demander.

### ⚠️ Règle de sécurité pour les fiches du pont
Dans le dossier TEST, le paramétrage E-7.08 pointe encore vers la **base GC de production**. Un transfert lancé depuis le dossier TEST **lirait la vraie GC et pourrait y écrire** (ICE, marques de transfert).
**Avant toute fiche E-2.07.x :** créer une copie TEST de la base GC, modifier E-7.08 **dans le dossier TEST** pour la faire pointer vers cette copie, et seulement ensuite prendre l'instantané de référence. Tant que ce n'est pas fait, **les fiches E-2.07.x sont interdites**.

### Questions restantes (utilisateur)
1. ~~Base GC : Access ou SQL Server ?~~ → **SQL Server, 192.168.16.99**. Base de test à créer : `GC_TEST` (copie de la GC 2026).
2. ~~Marque « déjà transférée »~~ → Journal + Pièce dans `Ecrit` (GC), `Externe = 1` côté compta.
3. Une écriture par facture, ou une centralisation ? Dans quel journal ?
4. Part des écritures venant du pont → **à mesurer** par comptage de `Externe` sur la copie.

## 9. Réponses du comptable (2026-10-05)

### 9.1 Fréquence d'utilisation déclarée
| Fréquence | Fonctions |
|---|---|
| **Chaque jour** | Saisie Avec TVA (E-2.01.01), Saisie Sans TVA (E-2.01.02), Transfert compte à compte / journal à journal (E-2.02), Pointage (E-2.03), Rapprochement bancaire (E-2.05), **Contrôle de la comptabilité (E-2.06)**, Balances (E-3.03), Échéancier / chèques (E-3.04.02-03), Recherche multi-critères (E-3.05), Création comptes / tiers / journaux (E-7.01, 7.02, 7.04) |
| **Chaque semaine** | Lettrage des tiers (E-2.04), Journaux (E-3.01), Extrait de compte (E-3.02) |
| **Chaque mois** | Pont GC : achats, ventes, règlements (E-2.07.01 à .04), Écritures d'abonnement (E-7.15), TVA à déclarer / déclaration (E-3.04.05-06), Éditions (E-4), Clôture périodique (E-6.01) |
| **Chaque année** | Liasse fiscale (E-3.06), Immobilisations (E-5), Clôture d'exercice / report à nouveau (E-6.02, E-6.03) |
| **Jamais → hors périmètre** | Saisie « Ancienne version » (E-2.01.03), Transferts dossiers imports / MP / emballages (E-2.07.05 à .07, E-2.07.10) |

Constats :
- **Le cœur quotidien est la saisie manuelle**, pas le pont. Le pont est **mensuel** (sa volumétrie réelle reste à mesurer par `Externe`).
- **Contrôle de la comptabilité** et **Transfert compte à compte** sont quotidiens alors qu'ils sont classés 🔴 : il faut savoir ce qu'ils écrivent. Ils passent en priorité, sur TEST uniquement.
- Les **5 écrans « les plus ouverts »** cités incluent des écrans annuels (immobilisations, liasse, clôture). Le comptable a sans doute compris « les plus importants ». Ils sont traités comme **critiques**, pas comme fréquents.
- **Questions 3 et 4 non renseignées** (applis externes, irritants). À redemander.

### 9.2 Écrans détaillés fournis (5 captures)

**E-2.01.01 — Saisie des écritures comptables avec TVA** (écran n° 1)
- En-tête : **Siècle / An / Mois** (ex. 20 / 25 / 01), **Code et nom du journal** (ex. 611 JOURNAL ACHAT), **Contre partie** (« Contre partie auto. avec ou sans TVA »), Liste des libellés ; totaux **Débit journal / Crédit journal / Solde journal** ⇒ saisie par **journal + mois**.
- Ligne : Document, **Pièce**, **Ord.**, Jour, Compte, Libellé, Débit, Crédit, **Mois TVA**, **Échéance** ; « Période de déclaration de la TVA », « Mois TVA contre-partie ».
- Détail : Compte, **Code TVA**, **Compte TVA**, Libellé, **Débit ou HT**, **Mont. TVA débit**, **Crédit ou HT**, **Mont. TVA crédit**, Compteur, Libellé TVA ; boutons Valider ligne / Supprimer ligne / Supprimer toutes les lignes.
- Onglets : **Écriture**, **Photo** (pièce justificative jointe ?), **Écriture d'abonnement**.
- Commandes : Ajouter, Modifier (F1), Supprimer (F2), Nouv. écrit., Imprimer pièce, Supp. + écrit., Commentaire.
- Données visibles :
  - comptes de tiers **auxiliarisés dans le plan** (ex. `44110024` = 4411 + n° fournisseur) ;
  - **code TVA compta = `A20`**, porté sur la ligne HT **et** sur la ligne de TVA (34552) ;
  - n° de document de la GC repris (ex. `FC26B000057`, `FAC26010140`).
- ⇒ **Les codes TVA diffèrent entre GC (`01`) et compta (`A20`)** : le pont applique une **correspondance** à identifier (E-7.03 + E-7.08 ?).
- ⇒ Le **mois de déclaration TVA est porté par ligne** : c'est ce qui ventile la déclaration (régime des encaissements ou décalage possible).

**E-5.01 — Codification des immobilisations** (écran n° 2)
- Champs : Code, Désignation, Date achat, Montant d'achat, **Mode** (Linéaire…), Durée, Taux %, Amortis. antérieur, Cpt Immob, Cpt Amortis, **Cpt Dotation**, **Plafond**, **Type immob** (Acquisition…), **Coeff.** (dégressif), Amortis. de l'exercice, Code de regroupement, Mois/An début de calcul, Réf. inventaire, Date et montant de **réévaluation**, cases Immob. cédée / ratée, Observation.
- Onglets Exercice en cours / **Exercices précédents** ; boutons **Excel**, Imprimer, Correction erreurs.
- Données : ~30 immobilisations, comptes 23xx / 283xx / 619xx. Le **plafond** fait référence à la limite fiscale d'amortissement des véhicules de tourisme.

**E-3.03.01 — Consultation de la balance exercice en cours** (écran n° 3)
- Filtres : Type de balance (Générale…), Du / Au (Mois/An), Compte de début / fin, **Collectif**, Type balance (Simplifiée…), **Mouvementée**, Type compte, Imprimer la date d'édition, Référence.
- Colonnes : Compte, Désignation, **Début période**, Débit, Crédit, Solde, avec des sous-totaux par classe et rubrique.
- **Bouton Excel** ⇒ export possible : c'est l'état de référence idéal pour le comparateur (S-401).

**E-3.06.02 — Bilan actif / passif** (écran n° 4)
- Actif : Brut, Amort./Provis., **Net EXE**, **Net EXE-1** ; Passif : Exercice, Exercice-1. Boutons CPC, DCPC, TFR/CAF, Immob., Amort., TVA, Cession, Cont. Immob, Imprimer.
- ⇒ Lit l'exercice N-1 (autre dossier). Le mapping comptes → postes est à établir par le comparateur.

**E-6.02 — Clôture de l'exercice** (écran n° 5)
- Comptes de résultats paramétrés : Exploitation **8100**, Financier **8300**, Courant **8400**, Non courant **8500**, Avant impôt **8600**, Après impôt **8800**, Résultat net (vide) ; Code journal, Date, Libellé ; Valider.
- ⇒ La clôture **génère des écritures** de détermination du résultat via la classe 8 du CGNC. Lot 5, après AMB-038.

## 10. Priorisation des fiches v2 (après réponses du comptable)

**Principe :** le **quotidien d'abord** (c'est ce que le comptable fera dans le nouveau logiciel tous les jours), puis l'hebdomadaire, puis le mensuel, puis l'annuel.

| Séance | Fiches | Écrans | Fréquence | But |
|---|---|---|---|---|
| 0 | Profilage, calibration, S-000, **comptage `Externe`** | — | — | Préparer et mesurer le poids du pont |
| 1 | S-101 compte · S-102 journal · S-103 tiers (compte auxiliaire 4411xxxx) | E-7.01, 7.02, 7.04 | jour | Référentiels, auxiliarisation, catalogue ? |
| 2 | S-201 écriture sans TVA · S-202 facture d'achat avec TVA (A20, mois TVA, échéance) · S-203 facture de vente avec TVA | E-2.01.02, E-2.01.01 | jour | Modèle journal/mois, ligne TVA, mois TVA |
| 3 | S-204 modification · S-205 suppression · S-206 « Contre partie auto » | E-2.01.x | jour | Cycle de vie, contrepartie automatique |
| 4 | S-301 pointage · S-302 rapprochement bancaire · S-303 chèque + échéancier | E-2.03, E-2.05, E-3.04.02-03 | jour | Champs de pointage et de rapprochement |
| 5 | S-304 **contrôle de la comptabilité** · S-305 **transfert compte à compte** | E-2.06, E-2.02.01 | jour | 🔴 quotidiens : savoir ce qu'ils écrivent (réinitialiser avant) |
| 6 | S-401 balance + export Excel · S-402 lettrage manuel | E-3.03.01, E-2.04.02 | jour / semaine | État de référence pour le comparateur, code de lettrage |
| 7 | S-501 TVA à déclarer · S-502 écriture d'abonnement · S-503 clôture périodique | E-3.04.05, E-7.15, E-6.01 | mois | Règles TVA, récurrence, verrouillage mensuel |
| 8 | Pont GC : S-601 achats · S-602 ventes · S-603 règlements | E-2.07.01 à .04 | mois | **Prérequis AMB-038** (`GC_TEST` + traçage multi-bases) |
| 9 | S-701 immobilisation · S-702 calcul liasse · (clôture d'exercice en dernier) | E-5.01, E-3.06.01, E-6.02 | an | Immobilisations, liasse, clôture (lot 5 après AMB-038) |

Questions à poser (utilisateur ou comptable) :
1. ~~Contrôle de la comptabilité~~ → **vérification des soldes de comptes et de balances** (cohérence). La trace S-304 dira s'il **recalcule et réécrit** des soldes ou cumuls stockés. Un usage quotidien laisse penser que ces cumuls se désynchronisent.
2. ~~Transfert compte à compte~~ → **reprise des imputations erronées** (reclassement). La trace S-305 dira s'il **modifie les lignes existantes** (non conforme au principe d'intangibilité des écritures) ou s'il **génère des écritures de reclassement**.
3. Où est la **correspondance des codes TVA** GC (`01`) → compta (`A20`) ?
4. Onglet **Photo** : la pièce scannée est-elle stockée dans la base ou comme fichier ?
5. ~~Applis externes~~ → voir §11. Irritants (question 4) : toujours sans réponse.

## 11. Outils externes utilisés (déclaré le 2026-10-05) → cible du nouveau logiciel

| Outil externe | Usage actuel | Cible dans le nouveau logiciel |
|---|---|---|
| **Site des impôts (DGI)** | Dépôt **manuel** des déclarations | Produire des fichiers prêts à déposer ; le dépôt reste manuel sauf canal officiel automatisable (à vérifier au moment du développement) |
| **Application locale de préparation des EDI TVA** | Fichier EDI de la déclaration de TVA (relevé des déductions…) | **Générer directement le fichier EDI** à partir des écritures (code TVA + mois TVA par ligne), au format DGI en vigueur |
| **Excel** (usage principal) | Inconnu à ce stade | **À identifier** : récupérer les classeurs utilisés. Chaque tableau Excel récurrent est un besoin non couvert par le logiciel actuel (états, contrôles, analyses) |

Constats :
- Le besoin fiscal central est la **TVA**. Le mois TVA et le code TVA portés par chaque ligne de saisie (§9.2) sont exactement les données qu'exige l'EDI. La reprise de ces champs est critique.
- **Excel est le plus gros gisement de besoins cachés.** Demander 3 à 5 classeurs représentatifs, même anonymisés, avec une phrase sur l'usage de chacun.
- Nom et version de l'**application EDI locale** à relever : son format de sortie servira de référence de test.

## 12. Tables d'un dossier `.mdb` (société + exercice) — inventaire du 2026-10-05

> Source : captures de la liste complète des tables d'un dossier réel. Les rôles sont des **hypothèses**, à confirmer par le profilage puis les traces.
> La « Date Modified » (03/11/2025 13:09:54, identique partout) vient d'un compactage ou d'une copie globale : **elle n'est pas exploitable**.

### 12.1 Noyau comptable (1995-1999)
| Table | Col. | Index | Rôle supposé | Lien écran |
|---|---|---|---|---|
| **`ecrit`** | 45 | XClef6 | **Lignes d'écritures**, table unique (pas d'en-tête séparé) : journal, mois, pièce, ord., jour, compte, libellé, débit, crédit, code TVA, mois TVA, échéance, document, `Externe`, lettrage, pointage… | E-2.01.x |
| **`compte`** | 21 | XCompte | Plan comptable (tiers auxiliarisés compris : `4411xxxx`). 21 colonnes : peut-être des **cumuls** | E-7.01 |
| **`scompte`** | 6 | XClef1 | **Soldes stockés par compte** (et par mois ?) | Mis à jour par la saisie ; vérifié par E-2.06 |
| **`sjournal`** | 8 | XClef1 | **Totaux stockés par journal** (et par mois ?) | Débit/Crédit/Solde journal de E-2.01 |
| **`journal`** | 14 | XCode | Journaux (110, 111, 510-515, 611…) | E-7.02 |
| `piece` | 10 | XClef1 | Compteur ou en-tête de pièces ? | Numérotation |
| `collectif` | 2 | XCompte | Comptes collectifs (4411, 3421…) | Balance « Collectif » |
| `tiers` | 12 | PrimaryKey | Fiches tiers (ICE ?) | E-7.04 |
| `tva` | 4 | XCode | Codification TVA **compta** (`A20`…) | E-7.03 |
| `libelle` | 2 | XCodej | Libellés types par journal | « Liste des libellés » |
| `autorise` | 2 | XCodej | Droits utilisateur par journal ? | Profil SAISIE |
| `coment` | 5 | — | Commentaires | Bouton « Commentaire » |
| `mouva` | 10 | XClef1 | Mouvements… d'à-nouveaux ? | **À identifier** |
| `ecritkm` | 32 | XClef6 | Variante de `ecrit` (brouillard ? archive ?) | **À identifier** |
| `immob` | 31 | XCode | Immobilisations | E-5.01 |
| `parametre` | 11 | — | Paramètres du dossier | E-7.07 |
| `paratrans` | 12 | — | Paramétrage du transfert GC (⚠️ peut contenir un **mot de passe**) | E-7.08 |
| `tailleimp` | 2 | XNom | Formats d'impression | — |

### 12.2 Ajouts 2013-2019
| Table | Rôle supposé |
|---|---|
| `ecrit_abonne` (45 col., même structure que `ecrit`) | Modèles d'écritures d'abonnement (E-7.15) |
| `gc_compta` (2 col.) | **Correspondance GC → compta** : candidate n° 1 pour `01` → `A20` (codes TVA) |
| `imput` (10 col.) | Imputations ; « comptes de l'index » du pont ? |
| `mode` (3 col.) | Modes de paiement (E-7.05) |
| `controle` (12 col.) | Résultats ou paramètres du contrôle de la comptabilité (E-2.06) |
| `affiche` (7 col.) | Paramètres d'affichage |
| `tab_etat_vente` | État des ventes (E-3.04.07) |
| `tableau1_actif` … `tableau26` | **Résultats de la liasse fiscale** (numérotation des tableaux officiels) |
| `tabN_param`, `tableauN_param` | **Correspondance comptes → lignes de la liasse** : à lire directement |
| `…_nouv`, `…_simplifie` (2018-2019) | Nouveau modèle de liasse ; les versions 2013 sont probablement **mortes** |
| `Requête9`, `Requête10` (**vues**) | Requêtes enregistrées : leur **SQL est une règle métier lisible** |

### 12.3 Tables récentes ou parasites — à expliquer
| Table | Créée le | Question |
|---|---|---|
| `DataSteRatios` | 21/07/2025 | Après la fin de maintenance (2020) : créée par qui ? Un outil maison ? |
| `ListingControles` | 26/12/2025 | Créée par le logiciel lors d'un contrôle, ou par un outil externe ? |
| `Erreurs de conversion` 0 à 5 | 2023 → **04/03/2026** | Tables générées par Access lors d'**imports ratés** : qui importe des données dans ce dossier, et quoi ? |
| `Table des erreurs` | 03/02/2020 | Idem (résidu Access) |

### 12.4 Conséquences
- **Soldes stockés (`scompte`, `sjournal`)** : ils expliquent le contrôle quotidien (E-2.06). Le nouveau logiciel calculera les soldes à partir des écritures, ou garantira la cohérence des cumuls par transaction.
- **Trace attendue pour S-201** (hypothèse à confirmer) : INSERT de 2 ou 3 lignes dans `ecrit`, UPDATE de `scompte` (61263, 34552, 44110024), UPDATE de `sjournal` (journal 611, mois 10), et peut-être `piece` (compteur).
- **Les fichiers `.mdb` ne contiennent pas les tables du catalogue** : celui-ci est bien un fichier séparé.
- **Profilage à lancer sur la copie TEST** pour obtenir les colonnes exactes, et **exporter le SQL de `Requête9` et `Requête10`** (Access → mode SQL → copier).

## 13. Environnement TEST et second fichier par exercice (2026-10-06)

### 13.1 Dossier TEST créé
- Société fictive code **`zz_test`** (longueur du code limitée), désignation affichée **« ZZ-TEST TRACEUR »** dans la barre de titre : **repère TEST confirmé**.
- Contenu : copie des dossiers réels d'une société existante (données réelles, usage interne).
- Arborescence observée : `C:\wcpt\<code société>\<exercice>\` (ex. `C:\wcpt\ZZ_TEST\2026\`).

### 13.2 Deux fichiers `.mdb` par exercice
| Fichier | Taille | Rôle |
|---|---|---|
| `dossier.mdb` | ~7,5 Mo | Base comptable (tables du §12 : `ecrit`, `compte`, `scompte`…) |
| `copie.mdb` | ~2 Mo | **Tables de travail des éditions et de la liasse** : `cpc`, `dcpc`, `declare_tva`, `etat_immob`, `etat_vente`, `etbN` / `etbN_nouv`, `extraitc`, `extraitj`, `general`, `ligne_immob`, `entete_immob`, `imput`… |

### 13.3 Table `cpc` de `copie.mdb` (capture)
| Colonne | Contenu observé | Interprétation |
|---|---|---|
| `Code` | A010, A011… E010 | Ligne du CPC |
| `Designation` | VENTES DE MARCHANDISES… | Libellé officiel |
| `Exe` | `711`, `712`, `TOTAL`, `A-B`, `LIGNE` | **Comptes inclus** (préfixes) ou formule |
| `Exe-` | `7118`, `7128`, `6118`… | **Comptes à déduire** (ex. 7118 : rabais accordés) |
| `Type` | SC / SD | Sens du solde retenu (créditeur / débiteur) |
| `MExe`, `MExeA` | montants | Exercice / exercice précédent |
| `TMexe`, `TMExeA` | montants | Totaux |
| `Adresse` | 104, 114… | Position d'affichage / impression |
| `code_exe`, `code_exeA`, `code_texe` | 11176, 11177, 11178… | **Probablement les identifiants de cellule de l'EDI de la liasse (DGI)** |

⇒ **Le mapping comptes → lignes du CPC est lisible directement**, ainsi que, très probablement, les codes EDI. Le comparateur d'états n'aura qu'à le **vérifier**.

### 13.4 Conséquences
- **Les éditions et la liasse écrivent dans `copie.mdb`.** Les fiches de consultation, d'édition et de liasse (S-401, S-501, S-702) devront tracer `copie.mdb` en plus de `dossier.mdb` (extension multi-bases, AMB-038 ; peut-être plus simple : un second `base_test`).
- Pour les fiches de saisie (lots 1a à 3), tracer `dossier.mdb` seul suffit a priori. Vérification : date de modification de `copie.mdb` avant et après S-000.
- **Ne plus ouvrir les fichiers TEST avec Access après l'instantané** (Access peut modifier le fichier à l'ouverture), ou alors en lecture seule.

## 14. Profil du dossier TEST (2026-10-07) — dictionnaire et prédictions

**Mesures :** 84 tables · format **Jet 3 (Access 97)** → AMB-001 constatée · `ecrit` = 1 475 lignes (janvier à octobre 2026).

### 14.1 `ecrit` — lignes d'écritures (45 colonnes, clé candidate `Compteur`)
| Groupe | Colonnes | Constat |
|---|---|---|
| Période | `Siecle` (20), `An` (26), `Mois` (01-10), `Jour`, **`Date` = `AAMMJJ` texte** (ex. 260101) | Dates stockées en texte, pas en date |
| Pièce | `Codej` (journal), `Piece` (000001…970495), `Document`, `Ordre` (toujours 00) | |
| Imputation | `Compte`, `Libelle`, `Debit`, `Credit` (CURRENCY, **négatifs possibles**) | |
| TVA | `Tva` (code, ex. A20), `Taux_tva`, `mont_HT`, `mont_tva`, **`lien_tva`** (-1 ou n° de ligne), `MoisTva`, `declare_tva`, `periode_declare` | La ligne de TVA est **reliée à sa ligne HT** par `lien_tva` |
| Liens | `Compteur` (auto), **`Lien`** (592 valeurs → regroupe les lignes d'une même écriture ?) | À confirmer par S-201 |
| Contrepartie | `Contre` (compte), `Contre_partie` (0 à 2) | Contrepartie automatique des journaux de banque |
| Pont GC | **`Externe`** ('' ou '1'), `Operation` (ex. FREFOU) | |
| Suivi | `Lettrage`, `AncienLettrage`, `Pointage`, `Releve`, `DateValeur`, `Echeance`, `Cheque`, `Bordereau`, `Dateei`, `Datei` | Peu renseignés sur ce dossier |
| Divers | `Debitanc`, `Creditanc` (montants « anciens » ?), `Devise` (0), `Ref`, `mode`, `Photo`, `Selection`, `ObjetSelection` | `Photo` vide : pièces scannées non stockées ici |

### 14.2 Cumuls stockés : **quatre niveaux**
| Table | Clé | Contenu |
|---|---|---|
| `compte` | Compte | `Debit`, `Credit` (cumuls exercice), `Debitanc`/`Creditanc`, `AnouveauD`/`AnouveauC`, champs de lettrage |
| `scompte` | Compte + Mois | `Debit`, `Credit` par mois |
| `sjournal` | Code + Mois | `Debit`, `Credit`, **`Cloture` (N/O : clôture périodique)**, **`Piece` (dernier n° de pièce → compteur)** |
| `journal` | Code | `Debit`, `Credit` totaux, `Nature` (0-3), `Contre` (compte de contrepartie), `Auto`, `Ordre`, `ControleOrdre`, `ParPiece` |

⇒ Une saisie doit mettre à jour **jusqu'à 4 tables de cumuls**. C'est l'origine probable des écarts que le **contrôle quotidien** (E-2.06) corrige.

### 14.3 Référentiels
- `tva` (11 codes, `A10`…`V20` ; colonnes Code, Nom, **un seul Compte**, Taux) : préfixe A = achat, V = vente, + TVA sur immobilisations (34551).
- `tiers` (365) : Compte, Nom, adresse, **IF**, **ICE**, CompteAvance (IF et ICE presque toujours vides).
- `collectif` (5) : 3421, 4411, … `autorise` : droits **utilisateur × journal** (5 utilisateurs).
- **Vides dans ce dossier** : `piece`, `gc_compta`, `paratrans`, `libelle`, `mode`, `ecritkm`, `controle`, `imput`. ⇒ La numérotation passe par `sjournal.Piece`, pas par `piece`. **La correspondance TVA GC → compta n'est pas dans `gc_compta`** (vide) : à chercher ailleurs.

### 14.4 Prédiction de la trace S-201 (à confirmer)
| Table | Changement attendu |
|---|---|
| `ecrit` | INSERT de **3 lignes** : 61263 (débit 1 234,56, Tva A20, mont_HT, Taux 20), 34552 (débit 246,91, `lien_tva` → ligne 61263), 441110024 (crédit 1 481,47), libellé TVA probablement « TVA/TEST-S201 » ; même `Piece`, `Codej` 611, `Mois` 10, `Date` 261015 |
| `scompte` | UPDATE ou INSERT (61263/10, 34552/10, 441110024/10) |
| `compte` | UPDATE `Debit`/`Credit` des 3 comptes |
| `sjournal` | UPDATE (611, 10) : `Debit`, `Credit` + 1 481,47 ; `Piece` = nouveau dernier numéro |
| `journal` | UPDATE (611) : `Debit`, `Credit` + 1 481,47 |

### 14.5 Écriture d'achat réelle observée (consultation des écritures liées, ZZ-TEST)
Journal 611, 06/01/2026, Document `FCT`, Pièce `656602` :
| Compte | TVA | Libellé | Débit | Crédit |
|---|---|---|---|---|
| 441110024 | | AUTOROUTES/RECHARGE… | | 1 500,00 |
| 34552 | A20 | **TVA/**AUTOROUTES/RECHARGE… | 250,00 | |
| 61263 | A20 | AUTOROUTES/RECHARGE… | 1 250,00 | |
⇒ Confirmé : **3 lignes**, le **code TVA A20 sur la ligne HT et sur la ligne TVA**, le libellé de TVA **préfixé par « TVA/ »**. Les comptes fournisseurs ont **9 chiffres** (`4411` + `10024`). La fenêtre « écritures liées » confirme que `Lien` regroupe les lignes d'une même écriture. `Document` contient un type (`FCT`, `VIRT`…) et `Piece` probablement le n° de facture.

## 15. Première trace S-201 (2026-10-07) — constats écran
- **Ergonomie réelle de E-2.01.01** : la **ligne du haut est la ligne du tiers** (Document, Pièce, Ord, Jour, Compte, Libellé, Débit/Crédit, Mois TVA, Échéance). La **ligne de détail** porte le compte HT, le code TVA et le montant HT. **La ligne TVA est générée automatiquement** (34552, libellé **« TVA/ » + libellé**, 246,91 pour 1 234,56 × 20 % = 246,912 → **arrondi au centime inférieur ou au plus proche**, à confirmer avec un cas en ,xx5).
- Le comptable a utilisé « **Contre partie auto. avec ou sans TVA** » : c'est le mode normal du journal d'achat.
- **Libellé de la ligne tiers proposé automatiquement : « AUTOROUTES DU MAROC »** (nom du tiers, ou libellé de la dernière écriture du tiers ?) : règle à confirmer.
- Pièce `990201` saisie manuellement.
- Résumé du traceur : 5 tables modifiées, 7 lignes ajoutées, 24 modifiées. Écart signalé sur Document et Libellé (`TEST-S201` « introuvable ») **alors que les valeurs sont visibles à l'écran** ⇒ cause probable : **champs texte complétés par des espaces** en base (ex. `'VIRT          '`), comparés sans suppression des espaces finaux. Limite du traceur, pas une erreur de saisie.

## 16. Règles établies par la trace S-201 (2026-10-07) — statut : CONFIRMÉE (preuve : trace S-201)

### R-001 — Une facture d'achat avec TVA = 3 lignes dans `ecrit`, insérées dans cet ordre
| Ordre (`Compteur`) | Ligne | `Compte` | `Debit`/`Credit` | `Tva` | `Lien` | `lien_tva` | `Contre` | `Taux_tva`, `mont_HT`, `mont_tva` |
|---|---|---|---|---|---|---|---|---|
| 1 (26602) | **Tiers (en-tête)** | 441110024 | Crédit TTC 1 481,47 | vide | **0** | 0 | vide | 0 |
| 2 (26603) | **TVA (générée)** | 34552 | Débit 246,91 | A20 | **26602** | 0 | 441110024 | 20 / 1 234,56 / 246,91 |
| 3 (26604) | **Charge HT** | 61263 | Débit 1 234,56 | A20 | **26602** | **26603** | 441110024 | 20 / 1 234,56 / 246,91 |
- `Lien` = `Compteur` de la ligne de tiers (0 sur la ligne de tiers elle-même) ⇒ **regroupe l'écriture**.
- `lien_tva` de la ligne HT = `Compteur` de sa ligne de TVA.
- `Contre` = compte du tiers sur les lignes de détail ; `Contre_partie` = 2 (mode « contre partie auto avec ou sans TVA »).
- La ligne TVA porte aussi HT et taux : `mont_HT`, `mont_tva`, `Taux_tva` sont **dupliqués** sur la ligne TVA et la ligne HT.
- Libellé de la ligne TVA = `"TVA/" + libellé de la ligne HT`. Libellé de la ligne de tiers proposé = **« AUTOROUTES DU MAROC »** (nom du tiers ?).
- Communs aux 3 lignes : `Siecle` 20, `An` 26, `Mois` 10, `Jour` 15, **`Date` = « 261015 » (AAMMJJ)**, `Codej`, `Document`, `Piece`, `Ordre` « 00 ».
- **Non renseignés à la saisie** : `MoisTva` (vide), `declare_tva` 0, `Echeance`, `Lettrage`, `Pointage`, `Externe` (vide = saisie manuelle).
- **Textes complétés par des espaces** : `Document` 14, `Libelle` 40, `Compte` et `Contre` 9 caractères.

### R-002 — Calcul de la TVA
- TVA = HT × 20 % = 246,912 → **246,91**. Arrondi au plus proche **ou** troncature : non tranché. **À tester avec un HT donnant ,xx6** (ex. 1 234,58 → 246,916).

### R-003 — Cumuls hiérarchiques par préfixe de compte
- `compte` (cumul exercice) **et** `scompte` (cumul par mois) sont mis à jour pour **le compte et chacun de ses comptes « parents »** présents dans le plan (préfixes de 2 chiffres et plus) :
  - 61263 → 61, 612, 6126, 61263
  - 34552 → 34, 345, 3455, 34552
  - 441110024 → 44, 441, 4411, 44111, 441110024
- `scompte` : **INSERT** si la ligne (compte, mois) n'existe pas, sinon **UPDATE**.
- Aucun cumul de niveau classe (1 chiffre).
- ⇒ 13 comptes touchés pour une écriture de 3 lignes : c'est la principale source de désynchronisation, vérifiée chaque jour par E-2.06.

### R-004 — Cumuls de journal
- `journal` (611) : `Debit` et `Credit` augmentent **tous deux du total de l'écriture** (1 481,47).
- `sjournal` (611, mois 10) : idem.

### R-005 — Numérotation des pièces
- `sjournal.Piece` (par journal et par mois) passe de `006612` à **`990202` = pièce saisie (990201) + 1** ⇒ c'est le **prochain numéro proposé**. Une pièce saisie à la main **réinitialise le compteur** à partir de sa valeur.

### Questions ouvertes après S-201
1. Arrondi de la TVA (voir R-002).
2. Origine du libellé proposé sur la ligne de tiers (`tiers.Nom` ? dernière écriture ?).
3. `MoisTva` : quand est-il rempli (déclaration de TVA ?).
4. `copie.mdb` et `compta.mdb` (catalogue) touchés ou non : dates avant/après à fournir.
