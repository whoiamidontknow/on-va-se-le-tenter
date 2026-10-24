# Taux de réussite — classifieur haute précision (17/10/2026, dev « cache », scellé non lu)

## Verdict en une phrase
**Aucune politique ne bat clairement le taux de base hors échantillon une fois le balayage corrigé.**
Viser 65-75 % de gagnants avec un objectif à 1R ne marche pas : le seuil choisi sur le passé ne tient pas
sur le futur. Le haut du classement fait en moyenne **+5,5 points** de mieux que le taux de base, pas +15 à +25.

## Ce qui a été fait
- **Candidats et variables** : ceux du méta-modèle (`meta_ml/candidats.py`, importé, pas recopié). Union des
  12 déclencheurs, soit 1 105 candidats en 15 min (MES sept., NQ sept.-oct., MES1 mai-juin). On a les
  64 variables, plus des interactions simples : séance × déclencheur, distance aux niveaux × sens, et le niveau le
  plus proche devant / derrière le trade. Cela fait 109 variables utiles au total.
- **7 géométries fixées à l'avance** (stop en ATR, objectif en R, BE = break-even à 0,5R) :
  S1R1, S15R1, S2R1 (objectif 1R, avec et sans BE) et S2R05 (stop 2 ATR, objectif 0,5R). Chaque trade est
  joué seul dans le moteur, avec sortie forcée à 15:59 Chicago. Gagnant = PnL net > 0.
- **Modèles** : logistique L2, boosting (réglages de meta_ml) et arbre de profondeur 2. Walk-forward en
  5 plis par jour CME, avec purge et embargo d'un jour (`modele.plis`). Calibration et seuil sont choisis
  sur des prédictions hors échantillon INTERNES à l'apprentissage.
- **Politiques** : précision cible 65/70/75 % (plus grand top-k interne qui atteint la cible, ou probabilité
  calibrée ≥ cible). On trace aussi une courbe par fraction (5 à 100 %, seuil pris sur le passé). Au total,
  252 politiques, plus la règle « nuit 0h-8h » fixée à l'avance, soit **259 variantes**.
- **Placebo** : (1) le taux de base de la même géométrie sur les mêmes plis, avec une permutation conjointe
  (2 000 tirages) qui donne une p brute et une **p ajustée max-z** sur toute la famille (façon White /
  Romano-Wolf) ; (2) dans le moteur, `reference_hasard` (500 tirages, mêmes heures, même sens, même gestion),
  puis le simulateur Tradeify Select Flex.

## Résultats principaux
**La cible de précision est presque toujours hors d'atteinte.** Pour les cibles 70-75 %, la plupart des plis
ne retiennent rien. Quand des trades passent, la précision réelle tombe près du taux de base. Les détails
sont dans `sorties/politiques.csv`.

Courbe précision / nombre de trades (moyenne des 21 couples géométrie × modèle, `sorties/courbe_precision.csv`) :

| fraction gardée (seuil du passé) | n moyen | précision | taux de base | écart | R moyen |
|---|---|---|---|---|---|
| 5 % | 55 | 50,9 % | 45,4 % | +5,5 pts | +0,00 |
| 10 % | 94 | 51,0 % | 45,4 % | +5,6 pts | +0,02 |
| 20 % | 157 | 48,5 % | 45,4 % | +3,1 pts | −0,02 |
| 50 % | 370 | 46,7 % | 45,4 % | +1,4 pts | −0,03 |
| 100 % | 885 | 45,4 % | 45,4 % | 0 | −0,04 |

Test global sur le haut du classement (5 et 10 %, 42 politiques, même permutation conjointe) :
z moyen 0,98, **p = 0,0015**. Il y a donc un peu d'information, mais **ce test a été ajouté après avoir vu
la courbe** : c'est un indice, pas une preuve. Et +5 points sur une base de 45-50 % donne environ 51 %, loin des 65-75 %.

AUC hors échantillon : entre 0,47 et 0,55 selon la géométrie et le modèle, avec des plis sous 0,45. C'est la
même chose que pour le méta-modèle. Les arbres changent de variable racine à chaque pli (`sorties/arbres.txt`).

## Les 3 meilleures « recettes » (aucune n'est probante)
Les chiffres viennent du moteur (une position à la fois). Le placebo est `reference_hasard` (500 tirages).
Le simulateur utilise `optimise_taille` en micros.

| # | recette | n | gagnants | placebo | écart (p) | R moyen | PF | P(réussite) / réf. | p ajustée | registre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | boosting, top 10 %, stop 2 ATR, objectif 0,5R | 64 | 76,6 % | 61,3 % | +15,3 (0,004) | +0,129 | 2,02 | 0,83 / 0,15 | **0,86** | WRM-0003 |
| 2 | tous les déclencheurs la nuit 0h-8h, stop 2 ATR, objectif 0,5R | 87 | 70,1 % | 62,8 % | +7,3 (0,052) | +0,033 | 1,16 | 0,71 / 0,08 | 1,00 | WRM-0001 |
| 3 | logistique, top 5 %, stop 1,5 ATR, objectif 1R, BE 0,5R | 30 | 53,3 % | 35,0 % | +18,3 (0,008) | +0,162 | 1,33 | 0,34 / 0,21 | **0,019** | WRM-0002 |

Simulateur : recette 1 → 3 micros, 1er payout 0,76, VE +4 279 $ (réf. +45 $) ; recette 2 → 3 micros, 1er
payout 0,60, VE +1 251 $ (réf. −98 $) ; recette 3 → 8 micros, 1er payout 0,11, VE +75 $ (réf. +428 $).
Le simulateur tourne sur 2 à 4 mois de trades : ses chiffres sont fragiles.

Lecture honnête :
- **Recette 1** : elle remplit les 4 critères en apparence (76,6 % > 60 %, n = 64, espérance positive,
  +15 points). Mais c'est la meilleure de 259 variantes, et sa p ajustée vaut 0,86. Un pli fait 0 sur 6. Les
  trades sont surtout des shorts (48 sur 64). L'objectif à 0,5R donne déjà ≈ 62-66 % de gagnants au hasard :
  c'est le piège décrit dans les consignes. **À rejeter en l'état.**
- **Recette 2** : c'est l'hypothèse « nuit » FIXÉE À L'AVANCE, sans modèle. Elle atteint 70 % de gagnants
  (n = 87), mais l'écart au placebo n'est pas net (p = 0,052). Au niveau des candidats, la nuit ne fait que
  +1,9 point au-dessus du taux de base de la géométrie. Avec 1R, la nuit fait 55 % contre 51 % (+4,5 pts, p 0,06).
  C'est **la seule piste traduisible en Pine** : elle est à tester sur le DATASET, pas à trader.
- **Recette 3** : c'est la seule qui survit à la correction (p ajustée 0,019, au niveau des candidats).
  Mais n = 30 dans le moteur et 39 en candidats, et 27 des 39 viennent d'un seul pli. Ce sont uniquement des
  longs, et la précision de 53 % est sous les 60 %. Elle **ne remplit pas le critère 1**.

## Préréglages pour `f_pr_def()` (STRATEGIE_V1.pine) — à NE PAS considérer comme validés
Recette 2 (la seule exprimable par des règles) :
```
nom == "25 WRM-1 nuit 0-8h · SL 2 ATR · 0,5R" ? "sens=Les deux;clx=1;sig=1;sigNiv=Fort + Moyen;hei=1;tl=1;lvl=1;tr=0;feu=0;ema=0;adx=0;det=0;clxF=0;bo=0;maxJour=0;be=0;trail=Aucun;oppArr=0;fin=0;pf=1;part=0;hr=1;hr1On=1;hr1=0000-0800;hr2On=0;taille=Risque fixe en $;stop=ATR × k;atrK=2;tp=En R;tpR=0.5;oppHei=0;risque=200" :
```
Elle reprend le préréglage 24 avec atrK=2 et tpR=0.5. `risque=200` correspond à 3 micros MES (risque médian
62 $ par contrat). Pour MNQ, il faut ≈ 450 (151 $ par contrat). Comme pour le 24, l'union Pine des
déclencheurs (sig/hei/tl/lvl/clx) ne couvre pas exactement les 12 déclencheurs Python (ORB, cassures de
session, Monday, rebond/cassure Detector, divergence) : **écart à signaler au coordinateur**.

Recettes 1 et 3 : **pas de ligne possible**. Elles reposent sur un score de boosting ou de logistique à
109 variables. Aucun arbre peu profond ne les résume de façon stable : la variable racine change à chaque pli.
Il faudrait une option « filtre par score ML » qui n'existe pas en Pine, et elle ne se justifie pas au vu
des p ajustées.

## Hypothèses à tester sur le DATASET (fixées maintenant, à ne pas réoptimiser)
1. Nuit 0h-8h, tous les déclencheurs, stop 2 ATR : objectif 0,5R et objectif 1R.
2. Le haut du classement (top 10 %) d'une logistique bat-il le taux de base de plus de 5 points ?
3. Volatilité très basse (`atr_pct` ≤ 5,2 pb du prix) avec stop 2 ATR / 1R. L'arbre sur tout le dev donne
   91 % de gagnants (39 sur 43), mais c'est **dans l'échantillon**, quasi uniquement sur MES en septembre, et
   la règle n'apparaît qu'au dernier pli.

## Limites
Le dev ne contient que 1 105 candidats sur environ 4 mois, avec 60 à 340 candidats de test par pli. Les
séries ne se chevauchent qu'en partie. Le BE à 0,5R fait tomber le taux de base à 33-36 % (les sorties au BE
coûtent les frais) : viser 65 % y est irréaliste.

## Relancer
```
~/venv-quant/bin/python construire.py [--source dataset]     # table candidats x issues (cache/table_taux.pkl)
~/venv-quant/bin/python evaluer.py [--source dataset] [--registre]   # A modèles, B politiques, C moteur
~/venv-quant/bin/python evaluer.py --etape B|C               # reprise sur disque
```
L'accès aux données passe uniquement par `meta_ml/donnees.charger_series(source)`. Pour passer au DATASET,
il faut lancer `construire.py --source dataset`, puis `evaluer.py --source dataset`. Note technique :
`evaluer.py` remplace `modele.GESTIONS` à l'exécution par nos géométries, pour que la purge de meta_ml lise
nos sorties. Le fichier meta_ml n'est pas modifié.
