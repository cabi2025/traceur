# Carte des écrans — Compta PLus (GENIE LOG)

> Référentiel unique des écrans du logiciel legacy. Captures, fiches, traces et futurs écrans du nouveau logiciel utilisent ces codes.
> Version 5 — 2026-10-04 — arborescence complète (E-0 à E-8 et tous les sous-menus) + pont GC et TVA (§8).

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
| E-2.01.03 | ↳ Ancienne version | 🟠 | = bouton « Anc. Version ». Encore utilisé ? |
| E-2.02 | Transfert ▸ | 🔴 | Déplacement en masse d'écritures |
| E-2.02.01 | ↳ De compte à compte | 🔴 | |
| E-2.02.02 | ↳ De journal à journal | 🔴 | |
| E-2.03 | Pointage des écritures | 🟠 | Distinct du lettrage (voir E-2.04). Lot 3 |
| E-2.04 | Analyse des tiers ▸ | 🟠 | **C'est le lettrage** (et non une consultation) |
| E-2.04.01 | ↳ Pré-lettrage des tiers | 🟠 | Lot 3 |
| E-2.04.02 | ↳ Lettrage des tiers | 🟠 | Lot 3 |
| E-2.04.03 | ↳ Lettrage automatique | 🔴 | Traitement de masse |
| E-2.05 | Rapprochement bancaire | 🟠 | Lot 3 |
| E-2.06 | Contrôle de la comptabilité | 🔴 | Peut corriger des données : à confirmer |
| E-2.07 | Pont avec la gestion comm. ▸ | 🔴 | **Génération automatique d'écritures** depuis la gestion commerciale |
| E-2.07.01 | ↳ Comptabilité des achats | 🔴 | |
| E-2.07.02 | ↳ Comptabilité des ventes | 🔴 | |
| E-2.07.03 | ↳ Comptabilité des règlements fournisseur | 🔴 | |
| E-2.07.04 | ↳ Comptabilité des règlements client | 🔴 | |
| E-2.07.05 | ↳ Comptabilité des retours emballages | 🔴 | Spécifique métier |
| E-2.07.06 | ↳ Comptabilité des dossiers imports | 🔴 | Spécifique métier |
| E-2.07.07 | ↳ Comptabilité des achats de MP et Emballage | 🔴 | Spécifique métier |
| E-2.07.08 | ↳ Suppression des transferts fournisseurs | 🔴 | |
| E-2.07.09 | ↳ Suppression des transferts clients | 🔴 | |
| E-2.07.10 | ↳ Suppression des transferts dossiers imports | 🔴 | |
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

## 7. Priorisation des premières fiches (proposition v1)

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
