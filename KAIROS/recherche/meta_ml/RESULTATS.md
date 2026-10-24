# Méta-modèle ML — résultats (17/10/2026, échantillon de développement « cache », scellé non lu)

## Verdict en une phrase
**Le modèle ne bat pas le hasard hors échantillon.** Aucun filtre appris (gradient boosting ou logistique)
n'améliore la politique la plus simple, « prendre tous les candidats avec la gestion A15R2 ». C'est cette
politique simple qui est la meilleure piste, et elle reste à confirmer sur le DATASET.

## Ce qui a été fait
- **Candidats** (`candidats.py`) : union de 12 déclencheurs, long et short (Signator fort/moyen, flip
  Heishinator, Climax, trendline, ORB, sessions, Monday, Detector rebond/cassure, divergence).
  1 105 candidats en 15 min : MES 15/09→06/10, NQ 18/09→07/10, MES1 29/04→18/06 (partie développement).
- **64 variables** connues au moment du signal, en 17 blocs : type de déclencheur, volatilité, heure/séance,
  prix récent, oscillateurs, TREND multi-UT, distances aux niveaux (zones, sessions, Monday, ORB, pivots, jour
  précédent, ronds). Aucune donnée future (multi-UT et pivots décalés).
- **Cible** : issue du trade par le moteur, intrajournée (fermeture 15:59 Chicago), 3 gestions :
  A15R2 (stop 1,5 ATR, objectif 2R), A1R1 (1 ATR / 1R), NIV (stop sur niveau, objectif niveau suivant).
- **Modèles** (`modele.py`) : HistGradientBoosting + logistique L2, walk-forward 5 plis par jour, purge +
  embargo, calibration. Seuil (fraction de trades prise) choisi sur le passé seulement.
- **Contrôle de la machine** : une variable « canari » (issue + bruit) est bien détectée (AUC 0,69).

## Classement (moteur, une position à la fois, puis simulateur Tradeify Select Flex)
Hasard : mêmes heures, même sens, même gestion (`moteur.reference_hasard`). 11 variantes, donc le seuil
corrigé (Bonferroni) est p < 0,0045.

| politique | n | R moyen | R hasard | p | P(réussite) | réf. hasard | registre |
|---|---|---|---|---|---|---|---|
| tous les candidats, A15R2 | 247 | +0,148 | −0,031 | **0,008** (1000 tirages) | 0,92 | 0,29 | ML-0001 |
| logistique, choix de la gestion | 89 | +0,136 | −0,011 | 0,11 | 0,42 | 0,13 | ML-0005 |
| logistique, seuil, A15R2 | 181 | +0,106 | −0,010 | 0,10 | 0,58 | 0,28 | ML-0004 |
| boosting, seuil, A15R2 | 67 | +0,089 | −0,098 | 0,05 | 0,41 | 0,18 | ML-0002 |
| boosting, choix de la gestion | 97 | −0,059 | −0,059 | 0,55 | 0,00 | 0,16 | ML-0003 |
| boosting, seuil, NIV | 136 | −0,019 | −0,097 | 0,26 | 0,79 | 0,14 | — |
| tous les candidats, A1R1 / NIV | 528 / 350 | −0,11 / −0,16 | ≈ −0,1 | 0,58 / 0,88 | 0 | ≈ 0 / 0,16 | — |

Le détail est dans `sorties/politiques_moteur.csv` et `sorties/balayage.csv`. Les trades sont dans
`sorties/trades_*.csv` et dans `registre/trades/ML-000x.csv`.

Pouvoir de classement des modèles (AUC hors échantillon, moyenne des plis) : entre 0,48 et 0,55. Seul
« boosting A15R2 » a une AUC de 0,546, avec p = 0,011, mais cela ne survit pas à la correction pour 6 essais.
Sa sélection ne fait pas mieux que le hasard (p 0,18). C'est cohérent avec l'ancien modèle à 70 variables
(AUC ≈ 0,49).

## Pourquoi « tous les candidats A15R2 » est prometteur, mais pas acquis
- p = 0,008 contre le hasard, mais pas sous le seuil corrigé de 0,0045.
- Le résultat dépend de la série : NQ +0,43 R (76 trades), MES sept. +0,08, MES1 mai-juin **−0,08**. Il ne
  tient donc pas sur l'autre période.
- Long +0,19 et short +0,11 : les deux sens contribuent.
- P(réussite) 0,92 sur environ 4 mois de trades : ce chiffre est fragile et sans doute trop optimiste.

## Importance des variables (permutation, perte d'AUC hors échantillon, 5 plis)
Fichiers : `sorties/importance_{hgb,logit}_A15R2.csv`, `importance_hgb_A1R1.csv`, `importance_hgb_NIV.csv`.
- **Seul bloc stable : l'heure et la séance.** Il est en tête pour le boosting (+0,022) et pour la logistique
  (+0,028) sur A15R2, et il est positif dans les 5 plis pour les deux modèles. ORB est aussi positif dans
  les 5 plis pour la logistique (+0,015).
- Les autres blocs (oscillateurs, ronds, pivots, jour précédent) ont une importance moyenne faible, et
  elle est négative dans certains plis. C'est du bruit.
- Le type de déclencheur, le sens et le TREND multi-UT ont une importance d'environ 0. Le modèle n'arrive
  pas à distinguer un déclencheur d'un autre.
- Pour A1R1 et NIV, aucun bloc n'est positif dans tous les plis.

**Dans quel sens joue la séance (A15R2, R moyen par candidat, heure de Paris)** :
| séance | n | R moyen | % gagnants | MES1 | MES | NQ |
|---|---|---|---|---|---|---|
| nuit 0h–8h (Asie) | 288 | **+0,20** | 41 % | +0,10 | +0,27 | +0,20 |
| Londres 8h–14h30 | 328 | −0,09 | 32 % | −0,59 | +0,25 | −0,04 |
| US 15h30–22h | 409 | 0,00 | 41 % | −0,03 | +0,04 | −0,01 |
| autre | 64 | −0,18 | 21 % | | | |

La nuit est la seule séance positive sur les 3 séries, et les meilleures heures vont de 3h à 5h (+0,3 à
+0,7 R). Dans le moteur, les 63 trades de nuit de « tous les candidats A15R2 » font +0,31 R, contre +0,09
pour les 184 autres. Ces trades restent conformes, car ils sont fermés avant 15:59 Chicago. Mais **cette
observation vient après coup**. C'est une hypothèse à tester sur le DATASET, pas une recette.

## Ce qui ne marche pas
- Le filtrage par probabilité ne fait pas mieux que de tout prendre, quels que soient le modèle et la gestion.
- Les gestions A1R1 et NIV perdent quel que soit le filtre.
- Choisir la gestion à partir des probabilités ne bat pas le hasard.

## Limites
Avec environ 4 mois de données en 15 min et 1 105 candidats, chaque pli de test contient 60 à 340 candidats.
Il y a eu 100 tirages au hasard par politique, sauf pour ML-0001 (1 000). Les conclusions sont fragiles.

## Relancer sur le DATASET
```
~/venv-quant/bin/python construire.py --source dataset          # ou evaluer.py --reconstruire --source dataset
~/venv-quant/bin/python evaluer.py --source dataset --registre  # tout, plus les lignes ML (dev_dataset)
~/venv-quant/bin/python evaluer.py --registre-seul              # registre depuis sorties/, sans recalcul
```
Tout l'accès aux données passe par `donnees.charger_series(source)`. Le hasard est maintenant réglé à 1 000
tirages (`N_HASARD`). Sur le DATASET, il faut tester d'abord, et comme hypothèses fixées à l'avance :
(1) tous les candidats A15R2, (2) la même politique la nuit seulement.
