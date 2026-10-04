# Guide du comptable — le Traceur en une page

**À quoi ça sert.** Vous refaites sur la **base de TEST** une petite saisie décrite par une *fiche*. Le Traceur regarde ce que le logiciel de comptabilité écrit dans la base et en fait un rapport. Il ne modifie jamais la base : il la lit seulement.

**Avant de commencer.** Fermez les fenêtres qui montrent des informations confidentielles (mails, banque…) : le Traceur prend des **captures de tous vos écrans** au début et à la fin, et elles figurent dans le rapport. Ouvrez le logiciel de comptabilité **sur la base de TEST**, jamais sur la vraie base. Le Traceur affiche en haut « Base de TEST active : … » : vérifiez que c'est bien elle.

## Faire une fiche
1. Lancez `traceur.exe`. Attendez « Connectée en lecture seule » (en vert) dans le bandeau.
2. Sélectionnez une fiche dans la liste puis cliquez **Choisir une fiche**. Lisez les prérequis et les étapes.
3. Si la fiche le propose, acceptez de **réinitialiser la base** : elle revient à son état de départ.
4. Cliquez **Début**. **Attendez** que la barre de progression s'arrête et que le bouton **Fin** devienne actif (non grisé) : la photo « avant » est alors terminée. Ne touchez pas au logiciel avant.
5. Faites les étapes dans le logiciel, **exactement** comme écrites (mêmes valeurs, même ordre). Cochez-les au fur et à mesure si vous le souhaitez. Si le logiciel affiche un message ou un numéro, notez-le dans le cadre **Remarques / messages affichés** (recopiez-le tel quel).
6. Cliquez **Fin**. Patientez quelques secondes : le Traceur laisse le logiciel finir ses écritures, puis calcule le rapport. Ne touchez à rien pendant ce temps.
7. Une fenêtre vous résume le résultat. Cliquez **Ouvrir le rapport** pour le consulter, ou **Fermer**.

## Si quelque chose ne va pas
| Situation | Que faire |
|---|---|
| Vous vous êtes trompé de saisie en cours de route | Cliquez **Annuler la fiche**, puis **Oui**. La fiche est notée « annulée », sans comparaison. Réinitialisez la base et recommencez. |
| Fenêtre orange **« Écart de saisie »** | Une valeur de la fiche n'a pas été retrouvée dans la base : vous avez saisi autre chose, ou le logiciel l'a transformée. Cliquez **Réinitialiser puis rejouer** et refaites la fiche en recopiant les valeurs. Si l'écart revient, gardez le rapport et prévenez le responsable du projet. |
| **« Réinitialisation refusée : la base semble utilisée »** | Fermez le logiciel de comptabilité (sur tous les postes) puis recommencez. |
| **« Le partage est indisponible »** | Rien à faire : le rapport est gardé sur ce poste et sera déposé tout seul au prochain démarrage du Traceur. |
| Le Traceur refuse de démarrer (« base de PRODUCTION », etc.) | **Ne forcez rien.** Prévenez le responsable : le fichier `config.json` est faux. |

## Où trouver les rapports
Dans le dossier de sorties : `traces\…\rapport.html` (un dossier par fiche) et `index.html` qui les liste tous. Un rapport s'ouvre dans le navigateur et se lit sans connaissance technique : **ce que la fiche a écrit**, les **valeurs que vous avez saisies et retrouvées**, et les **valeurs calculées par le logiciel** (celles-ci sont des *hypothèses*, à confirmer).

## À retenir
- Une fiche = une saisie courte, **une seule fois** entre Début et Fin.
- Ne lancez **aucune autre action** dans le logiciel pendant la fiche.
- En cas de doute : **Annuler la fiche**, réinitialiser, recommencer. Rien n'est cassé : la base de TEST se remet à zéro d'un clic.
