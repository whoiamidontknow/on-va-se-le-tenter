# TL LAB — protocole de test des trendlines

## D'où vient la règle
Le module trendlines d'Ephore reprend le script public **« Trendlines » d'Amphibiantrading**
(open source, MPL 2.0 : https://www.tradingview.com/script/RQ1D3gHZ-Trendlines/). Les
réglages sont les mêmes et portent les mêmes libellés anglais. Ephore y a apporté deux changements :

1. Le 2e point de la droite est un **pivot confirmé**, alors que le script public prend la bougie courante.
2. Il a ajouté un **support ascendant** en miroir sur les bas.

Cette règle a été rejouée en Python sur les 8 droites de référence (MES + NQ, 15m + 1h,
Heiken Ashi, CSV coupés à l'heure des screens). Elle les retrouve toutes : **8/8**, avec les
réglages visibles de l'original, sans rien ajuster.

## Réglages par défaut (= original)
| Réglage TL Lab | Libellé original | Valeur |
|---|---|---|
| Pivot : barres de chaque côté | Pivot High Bars Required for Anchor | 10 |
| Tampon % | Price Buffer % | 0.1 |
| Touches minimum | Minimum Number of Touches | 3 |
| Nouvelle ancre après X barres | Look for New Pivot High after X Bars | 100 |
| 2e point de la droite | (modifié par Ephore) | Pivot confirmé |
| Cassure mesurée sur | (points verts / rouges) | Clôture (HA) |

## Valeurs attendues (état au 29/09, 22:45 en 15m et 22:00 en 1h)
Il faut un graphique en Heiken Ashi. Avec les nouvelles bougies, les droites évoluent,
mais elles doivent rester **identiques aux droites noires de l'original**.

| Graphique | Résistance (tableau « Droite ») | Support |
|---|---|---|
| SP500 15m | 7814.75 → 7786 | 7716 → 7736.25 |
| Nasdaq 15m | 30759.25 → 30722 | 30356.75 → 30372.25 |
| SP500 1h | 7848.5 → 7814.75 | 7710 → 7726 |
| Nasdaq 1h | 31094.75 → 30999.5 | 29107.25 → 29207.5 |

## Combinaisons à tester (un seul changement à la fois)
| # | Changement | Ce que ça teste | Résultat simulé /8 |
|---|---|---|---|
| 0 | **Aucun (défaut)** | La règle retrouvée | **8** |
| 1 | 2e point = Bougie courante | Le script public tel quel | 0 |
| 2 | Tampon 0.2 | Tolérance plus large | 7 |
| 3 | Tampon 0.05 | Tolérance plus stricte | 5 |
| 4 | Touches 2 | Validation plus facile | 7 |
| 5 | Touches 4 | Validation plus dure | ≤ 6 |
| 6 | X barres 120 | Durée de vie de l'ancre | 7 |
| 7 | X barres 50 | Durée de vie de l'ancre | 3 |
| 8 | X barres 150 à 200 | Durée de vie de l'ancre | 4 |
| 9 | Pivot 11 | Force des pivots | 7 |
| 10 | Cassure = Mèche + tampon | Où tombent les points | n'affecte pas les droites |

Les combinaisons 1 à 9 servent de contre-épreuve : chacune doit **dégrader** la
ressemblance. Si l'une d'elles colle mieux à l'original sur ton graphique, note laquelle,
avec le symbole et la timeframe.

## Lire le tableau de diagnostic
- **Droite** : les prix du point 1 et du point 2, à comparer avec la droite noire de l'original.
- **Points (heure)** : l'heure de ces deux points. Mets le curseur sur la droite noire pour vérifier.
- **Touches / état** : le nombre de touches à la validation, et si la droite est active ou déjà cassée.
  Une droite cassée reste affichée, comme sur l'original.
- **Ancre actuelle / âge** : le sommet (ou le creux) à partir duquel la prochaine droite partira.
  Au-delà de X barres, le pivot suivant devient la nouvelle ancre.
- **Écart au prix** : si la droite n'est pas visible à l'écran, cet écart dit où elle se trouve.
- **Losanges ◆** : une nouvelle ancre. **Points verts / rouges** : cassure par une clôture.
