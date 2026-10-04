# Bilan de la V1 du Traceur

Date : 2026-10-04. **J7 clos avec réserves** (voir §5). Périmètre : jalons J0 à J7 (SPEC `docs/SPEC_TRACEUR.md`, fonctions F1 à F11). Rien de V2 n'a été codé.

## 1. Ce qui est livré
| Livrable | Où |
|---|---|
| Moteur de diff, liens, hypothèses, profilage, calibration (testés sans Access) | `traceur/moteur/` |
| Source Access (lecture seule), sécurité de démarrage, réinitialisation | `traceur/sources/access.py`, `traceur/securite.py` |
| Rapports JSON/HTML, index, captures, dépôt atomique avec reprise | `traceur/rapports/`, `traceur/captures.py` |
| Interface Tkinter | `traceur/ui/` |
| Construction de `traceur.exe` (PyInstaller 32 bits) | `outils/construire_exe.py` |
| Guides | `GUIDE_COMPTABLE.md`, `GUIDE_INSTALLATION.md` (dont la fiche S-000), `outils/LISEZMOI_J4…J7.md` |
| Outils de diagnostic | `outils/` : `diagnostic.py`, `version_jet.py`, `sonder_pilote.py`, `generer_mdb_test.py`, `simuler_logiciel.py` |

## 2. Validé sous Windows (Python 3.14.8 32 bits, pilote ODBC Access de Windows)
- Tests d'intégration Access (12) et suite complète.
- Lecture seule vérifiée (journal sans `ReadOnly=0`), cache du pilote Jet mesuré (AMB-027), clés primaires lues via les index (AMB-028 pour la vraie base).
- Parcours J6 complet sur la base synthétique : profilage, calibration, deux fiches, annulation, réinitialisation avec contrôle SHA-256, refus si `.ldb`, partage indisponible puis reprise, refus de démarrer.
- `traceur.exe` 32 bits (16 733 Ko) construit sous Windows : lancement sans console, `journal.log` à côté de l'exe, profilage, S-SYN-01, refus de démarrer. **Test « sans Python » partiel seulement** (PATH réduit sur le poste de développement : pas de poste propre ni de Bac à sable Windows disponibles).
- Photo ODBC Access sur base synthétique locale : 152 506 lignes en 2,93 s.

## 3. Ambiguïtés
**Closes** : AMB-001 et AMB-003 à AMB-037 (décisions recopiées dans `SUIVI_AMBIGUITES.md`).
**Ouvertes, en attente de la vraie base :**
- **AMB-002 — durée de photo réelle.** Mesuré sous Windows par ODBC Access (Python 32 bits, disque local, base synthétique Jet 4 de 7,8 Mo, lignes de 6 colonnes) : **152 506 lignes en 2,93 s** (LIGNES 100 000 en 1,92 s, FACTURES 50 000 en 0,93 s), soit environ 52 000 lignes/s ; profilage complet 3,9 s. Ce n'est qu'un ordre de grandeur : la vraie base sera sur un partage, avec des tables plus larges. Mesuré aussi, moteur seul : 23,9 s pour 1,2 million de lignes en mémoire (SQLite, moteur seul, sur ce poste de développement). La lecture ODBC d'Access sera plus lente : à mesurer (`diagnostic.py --photo`, `LISEZMOI_J7.md` étapes 7 et 8) ; la mesure finale se fait depuis le poste du comptable, base sur le partage réseau. Aucune optimisation avant cette mesure.
- **AMB-028 — noms des clés primaires** de la vraie base avec le pilote Jet (`sonder_pilote.py` sur une copie).
- **AMB-001 — version Jet** de la vraie base : décision prise, `version_jet.py` à lancer sur une copie pour le constater.

## 4. Limites connues
- **Clés candidates sur petites tables (AMB-037, close).** Sur une table de moins de 50 lignes, une clé candidate du profil peut être unique par hasard. Le profil (`profil.html`) et la trace (`avertissements`, `rapport.html`) le signalent ; profiler juste après une réinitialisation.
- **Hypothèses, pas règles.** Les « valeurs calculées » (compteur, horodatage, somme de lignes, copie, constante, cumul) et les relations candidates sont des hypothèses. Sur des petites tables d'entiers, des relations fortuites apparaissent (ex. `LIGNES.QTE → CLIENTS.ID` sur la base synthétique) ; le rapport les présente comme candidates à trier.
- **Détection de ce qui est écrit, pas de ce qui est lu** : le Traceur ne voit que les écritures dans la base. Il ne voit pas les calculs faits à l'écran, ni les fichiers écrits ailleurs.
- **Une fiche = une saisie courte.** Si le logiciel écrit après le délai de stabilisation, l'écriture manque ; la fiche S-000 sert à régler ce délai sur chaque poste.
- **Captures de tous les écrans** : elles peuvent montrer des informations confidentielles (le guide demande de fermer les fenêtres sensibles). La capture « début » est prise pendant la photo « avant ».
- **Cases à cocher des étapes** : aide visuelle, non enregistrées dans la trace (AMB-034).
- **Profil et calibration** gardés localement et copiés sur le partage ; pas de détection de péremption (AMB-033).
- **Mot de passe + groupe de travail** : incompatibles avec le pilote ; la configuration est refusée avec conseil.
- **Exécutable non signé** : Windows SmartScreen peut afficher un avertissement au premier lancement.
- **Message de reprise des dépôts** au démarrage : très bref, laissé tel quel (AMB-036). Le journal et `index.html` font foi.
- **L'exe doit être construit sous Windows avec un Python 32 bits** ; il n'a pas pu l'être dans l'environnement de développement Linux. Un essai de construction Linux (64 bits) a seulement confirmé le point d'entrée, l'inclusion de Tkinter/Pillow et l'écriture du journal à côté de l'exécutable.

## 5. Réserves de clôture de J7 et prochaines étapes
**Réserves (décision de l'utilisateur) :**
1. Premier lancement sur un poste réellement propre = poste du comptable, **antivirus actif** (repli : `--onedir`, exclusion de dossier).
2. **Mesures sur copie réelle (AMB-001, 002, 028) avant la première session**, depuis le poste du comptable, base sur le partage.
3. **Fiche S-000** à exécuter avec le comptable (délai de stabilisation).
4. **Levée.** `GUIDE_COMPTABLE.md` (texte de l'utilisateur) intégré ; `GUIDE_INSTALLATION.md` relu et validé, avec la nouvelle section 2 bis (raccourci « Compta TEST », repère visible). **À compléter avant livraison** (les `[…]` du guide) : repère TEST affiché par le logiciel, nom et téléphone du contact, et la manière dont le logiciel choisit sa base.

**Ensuite :**
1. Premières fiches réelles.
2. V2 (hors périmètre ici) : génération de tests, schéma SQL cible, validation sur l'historique, carte de couverture. Le format `trace.json` (version 1.0) est stable et prêt à être lu.
