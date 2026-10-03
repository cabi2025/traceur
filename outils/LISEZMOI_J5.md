# J5 — Rapports, captures d'écran et dépôt : ce que vous pouvez vérifier sur Windows

J5 est testé sous Linux (293 tests). Seule la **vraie capture d'écran** (Pillow) et un **vrai partage réseau** demandent votre poste. Aucune base Access n'est utilisée ici : la démonstration fabrique une trace avec des données fictives.

## 1. Installer Pillow (captures d'écran)

Dans l'environnement du guide J4 (`.venv` activé, dans `C:\Traceur\traceur`) :

```bat
pip install Pillow
```

## 2. Trace d'exemple, en local

```bat
python outils\demo_j5.py --sorties C:\Traceur\sorties --capture
```

**Résultat attendu :**

```
Capture debut : faite
Capture fin : faite
Trace déposée : C:\Traceur\sorties\traces\S-DEMO_AAAAMMJJ-HHMMSS
Index : C:\Traceur\sorties\index.html
```

- Ouvrez `C:\Traceur\sorties\index.html` : une ligne « S-DEMO » avec le statut **Terminée** et un lien « Ouvrir le rapport ».
- Dans le rapport, vérifiez : le texte est en français ; « 3 tables modifiées, 2 lignes ajoutées, 1 modifiée » ; les tableaux avant/après ; les deux **captures d'écran** en bas de page (votre écran au moment du lancement).
- Dossier de la trace : `trace.json`, `rapport.html`, `remarques.txt`, `capture_debut.png`, `capture_fin.png` (pas de `depot.json`).
- Si « Capture … IMPOSSIBLE (voir journal) » s'affiche : Pillow est absent ou l'écran est inaccessible (session distante verrouillée). La trace est tout de même déposée avec « Aucune capture disponible » (la capture ne bloque jamais une fiche).

## 3. Écart de saisie

```bat
python outils\demo_j5.py --sorties C:\Traceur\sorties --ecart
```

Le rapport porte le bandeau orange **« Écart de saisie »**, la section « Écarts de saisie » (valeur attendue 1234.56 introuvable) et la proposition de réinitialiser puis rejouer. Dans l'index, le statut est « Écart de saisie ». Deux traces sont maintenant listées, la plus récente d'abord.

## 4. Partage indisponible, puis rétabli

Avec un vrai partage réseau (ou un lecteur réseau que vous pouvez déconnecter) :

```bat
python outils\demo_j5.py --sorties \\SERVEUR\Partage\Traceur\sorties
```

Puis **coupez l'accès** (déconnectez le lecteur, débranchez le câble, ou utilisez un chemin inexistant comme `Z:\inexistant`) et relancez :

```bat
python outils\demo_j5.py --sorties Z:\inexistant
```

**Résultat attendu :**

```
Partage indisponible (...) : la trace reste en local, en_attente_depot.
Relancez cette commande quand le partage est revenu : la reprise est automatique.
```

- Le dossier `traces_locales\S-DEMO_…` existe et contient la trace complète, plus `depot.json` (`"depot": "en_attente_depot"`, `"tentatives": 1`, la dernière erreur).
- Rétablissez le partage et relancez **la commande avec le chemin du partage** :

```
Reprise d'un dépôt en attente : S-DEMO_… → deposee
Trace déposée : \\SERVEUR\Partage\Traceur\sorties\traces\S-DEMO_…
```

- `traces_locales\` est maintenant vide, le dossier de la trace est sur le partage, `index.html` liste les deux traces.
- Pendant une coupure en plein dépôt, rien de visible n'apparaît sur le partage (la copie se fait sous un nom caché, vérifiée, puis renommée d'un coup).

## À m'envoyer

1. La sortie des commandes des étapes 2, 3 et 4.
2. Une capture d'écran du rapport ouvert (ou dites-moi ce qui n'est pas clair pour un non-technicien : c'est le critère « lisible » de J5).
3. `journal.log` si une capture ou un dépôt a échoué.
