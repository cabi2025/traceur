# MISSION — prompt de lancement pour Claude Code

À coller tel quel comme premier message dans Claude Code, ouvert à la racine du dossier `kit-traceur`.

---

Tu vas développer le **traceur**, un outil Windows qui observe ce qu'un vieux logiciel de comptabilité écrit dans sa base Access `.mdb`.

Avant toute chose, lis dans cet ordre : `CLAUDE.md`, `docs/SPEC_TRACEUR.md`, `JALONS.md`, `SUIVI_AMBIGUITES.md`, `docs/formats/*`, puis `docs/architectures.md` pour le contexte global.

Règles :
- Tu appliques strictement le protocole de `CLAUDE.md` : jalons dans l'ordre, arrêt et compte rendu à la fin de chaque jalon, **attente de GO** avant de continuer.
- Aucune ambiguïté n'est tranchée seul : registre `SUIVI_AMBIGUITES.md` + `TODO(AMB-xxx)`.
- Les fonctions V2 ne sont pas codées.
- Le traceur n'écrit jamais dans la base tracée.

Commence par le **jalon J0** uniquement. À la fin, donne-moi :
1. l'état du dépôt ;
2. les ambiguïtés relevées à la lecture de la SPEC ;
3. ton plan pour J1 à J7 ;
4. ce dont tu as besoin de ma part (environnement Windows, Python 32 bits, etc.).

Puis attends mon GO.
