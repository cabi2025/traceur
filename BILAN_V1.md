# Bilan de la V1 du Traceur

Date : 2026-10-04. Périmètre : jalons J0 à J7 (SPEC `docs/SPEC_TRACEUR.md`, fonctions F1 à F11). Rien de V2 n'a été codé.

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
- À valider avec `outils\LISEZMOI_J7.md` : construction de l'exe, lancement de l'exe, poste sans Python.

## 3. Ambiguïtés
**Closes** : AMB-001 et AMB-003 à AMB-036 (décisions recopiées dans `SUIVI_AMBIGUITES.md`).
**Ouvertes, en attente de la vraie base :**
- **AMB-002 — durée de photo réelle.** Mesuré : 23,9 s pour 1,2 million de lignes en mémoire (SQLite, moteur seul, sur ce poste de développement). La lecture ODBC d'Access sera plus lente : à mesurer (`diagnostic.py --photo`, `LISEZMOI_J7.md` étapes 7 et 8). Aucune optimisation avant cette mesure.
- **AMB-028 — noms des clés primaires** de la vraie base avec le pilote Jet (`sonder_pilote.py` sur une copie).
- **AMB-001 — version Jet** de la vraie base : décision prise, `version_jet.py` à lancer sur une copie pour le constater.

## 4. Limites connues
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

## 5. Prochaines étapes
1. Dérouler `outils\LISEZMOI_J7.md` (exe, poste propre, photo sur grosse base).
2. Mesures sur une **copie** de la vraie base : AMB-001, 002, 028.
3. Fiche S-000 sur le poste du comptable, puis premières fiches réelles.
4. V2 (hors périmètre ici) : génération de tests, schéma SQL cible, validation sur l'historique, carte de couverture. Le format `trace.json` (version 1.0) est stable et prêt à être lu.
