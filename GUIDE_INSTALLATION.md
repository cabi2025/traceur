# GUIDE D'INSTALLATION — Traceur

> Ce guide sera complété au jalon J7. Seule la section « Architecture réelle » est consignée à ce stade.

## Architecture réelle

| Machine | Rôle | Ce qui s'y trouve |
|---|---|---|
| **PC de développement** | Code, tests, build | Dépôt Git, `pytest`, `mypy`. **N'a accès ni au serveur ni au poste du comptable.** |
| **Serveur compta** `\\192.168.16.91` | Logiciel legacy et bases | Windows XP / Server 2003, partage `wcpt`. **Le traceur ne peut pas y tourner** (Python 3.11 non supporté). |
| **Poste du comptable : PC03** | Exécution du traceur | Windows 10 LTSC 1809 |

### Sur PC03
- `C:\traceur\traceur.exe`, `C:\traceur\config.json`, `C:\traceur\fiches_lot2.json`
- Base de TEST lue (lecture seule, via SMB1) : `\\192.168.16.91\wcpt\ZZ_TEST\2026\dossier.mdb`
- Instantané de référence : `C:\traceur_ref\2026\`
- Sorties : `C:\traceur_sorties\`

### Circulation des fichiers
- Le code et le `.exe` vont du PC de développement vers PC03 (copie manuelle).
- Les traces réelles reviennent de PC03 **à la main** dans `donnees_reelles\<fiche>\` du dépôt. Ce dossier est exclu de Git (`.gitignore`) : données comptables réelles.
- Lors d'une mise à jour, ne recopier que `traceur.exe`. Ne jamais écraser `config.json` ni les fiches du poste.
