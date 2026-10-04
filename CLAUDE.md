# CLAUDE.md — Projet Traceur

## Contexte
Ce dépôt contient le **traceur**, premier outil d'un projet de rétro-ingénierie d'un logiciel de comptabilité marocaine :
- un exécutable autonome de 2000, dont le code source est inaccessible ;
- une base Access `.mdb` partagée en réseau.

Le traceur observe ce que le logiciel écrit dans la base quand un comptable exécute des scénarios courts. Il produit des rapports exploitables pour reconstruire le logiciel.

La vue d'ensemble du projet est dans `docs/architectures.md`. La spécification de l'outil est dans `docs/SPEC_TRACEUR.md`. **La SPEC fait foi.**

## Documents de pilotage — à lire avant toute action
| Fichier | Rôle |
|---|---|
| `docs/SPEC_TRACEUR.md` | Spécification fonctionnelle et technique |
| `JALONS.md` | Jalons à franchir dans l'ordre, avec critères d'acceptation |
| `SUIVI_AMBIGUITES.md` | Registre des ambiguïtés |
| `docs/formats/` | Formats d'entrée et de sortie (exemples de référence) |
| `docs/CARTE_ECRANS.md` | Carte des écrans du logiciel « Compta PLus » (codes E-x.yy.zz, risques, priorisation des fiches, pont gestion commerciale). Référence pour `capture_ref` et tout libellé d'écran |

## Protocole de travail (strict)
1. **Les jalons se font dans l'ordre.** Un jalon est terminé quand **tous** ses critères d'acceptation passent. Arrête-toi alors, fais un compte rendu et attends **GO** avant le jalon suivant.
2. **Aucune ambiguïté n'est résolue seul.** Si la SPEC est muette, contradictoire ou irréalisable :
   - inscris l'ambiguïté dans `SUIVI_AMBIGUITES.md` (contexte, options, recommandation) ;
   - si elle bloque, arrête-toi et demande ;
   - sinon, continue sur le reste et marque le point concerné `TODO(AMB-xxx)` dans le code.
   - Une ambiguïté n'est close qu'avec une **décision explicite de l'utilisateur**, recopiée dans le registre.
3. **Pas de fonctionnalité hors périmètre.** Les fonctions marquées « V2 » dans la SPEC ne doivent pas être codées en V1. Prévois seulement les points d'extension décrits.
4. Mets `JALONS.md` à jour (cases cochées, date, remarques) à la fin de chaque jalon.
5. Tout compte rendu de jalon commence par : nombre de tests pytest verts / échoués, résultat de mypy --strict.

## Règles de sécurité (non négociables)
- Le traceur **n'écrit jamais** dans la base tracée. Il l'ouvre **en lecture seule**.
- La seule opération qui modifie un fichier `.mdb` est la **réinitialisation**. C'est une copie de fichier depuis l'instantané de référence vers le chemin de la base de TEST, et uniquement vers ce chemin.
- Le traceur **refuse de démarrer** si le chemin de la base de TEST figure dans `chemins_interdits` (base de production) ou s'il est identique au chemin de l'instantané de référence.
- Aucune donnée réelle n'est versionnée dans le dépôt. `.gitignore` exclut `*.mdb`, `*.ldb`, `*.mdw`, `sorties/` et `config.json`.
- Les mots de passe ne sont **jamais** journalisés ni écrits dans les rapports.

### Pont gestion commerciale (GC, SQL Server) — règles posées le 2026-10-04 (rien n'est codé)
- Le paramétrage du pont (écran **E-7.08**) ne se modifie **jamais** dans la comptabilité de production.
- Préparation TEST, **dans cet ordre** : (1) copier la base GC 2026 en `GC_TEST` ; (2) copier le dossier compta ; (3) **dans le dossier TEST uniquement**, régler E-7.08 sur `GC_TEST` / 2026, en **vérifiant la barre de titre avant de valider** ; (4) prendre les instantanés de référence (dossier TEST et sauvegarde de `GC_TEST`).
- Les fiches **E-2.07.x** sont **interdites** tant que `GC_TEST` n'existe pas et que le traçage multi-bases (AMB-038) n'est pas livré.
- Serveur SQL `192.168.16.99` : **jamais de redémarrage**. L'accès du traceur est limité à `GC_TEST`, en **lecture seule** (`db_datareader`, authentification Windows). Les bases GC de production sont **interdites** (équivalent SQL Server de `chemins_interdits`).
- Les **captures de E-7.08 masquent le champ mot de passe**.

## Stack (décidée — voir SPEC §3)
- Python 3.11+ **32 bits**, `pyodbc`, Tkinter, Pillow, PyInstaller (un seul `.exe`).
- Tests : `pytest`. Le moteur de diff est testé **sans** Access, via une source de données abstraite (voir SPEC §6.1).

## Conventions
- Code, noms de variables et commentaires en **français** pour le domaine (`fiche`, `instantane`, `ecart`). Les termes techniques standard restent en anglais.
- Typage (`mypy --strict` sur `traceur/moteur/`).
- Les codes d'écran (`E-x.yy.zz`) de `docs/CARTE_ECRANS.md` servent de `capture_ref` et de libellés d'écran dans les fiches, traces et rapports.
- Tous les fichiers produits sont en **UTF-8**. Les textes lus depuis le `.mdb` sont décodés selon la page de code configurée (défaut `cp1252`).
- Les dates sont écrites en ISO 8601 et les montants comme des chaînes décimales exactes, jamais comme des flottants.
