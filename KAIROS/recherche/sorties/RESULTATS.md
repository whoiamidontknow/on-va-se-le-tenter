# Sorties et protection (agent SOR) — résultats

**État : fini sur le cache de développement (17/10). À refaire sur le DATASET avant toute décision.**

Code : `donnees_sor.py` (accès unique aux données), `etude.py` (étapes A, A2, B à G), `rapport.py` (tous les
tableaux chiffrés -> `resultats/rapport.md`), `registre_sor.py` (lignes SOR du registre).
Relancer sur le DATASET :

    SOR_SOURCE=dataset ~/venv-quant/bin/python etude.py      # toutes les étapes
    ~/venv-quant/bin/python rapport.py && ~/venv-quant/bin/python registre_sor.py

Données : cache 15m, partie développement seulement (MES1! 29/04→18/06, MES 15/09→06/10, MNQ 18/09→07/10).
8 déclencheurs réels (Signator Fort, climax BUY, climax SELL, climax BUY + TREND 1H, cassure de trendline, flip
Heishinator, cassure ORB, cassure Monday) + 1 témoin au hasard. Entrées 08:00-22:00 Paris, à plat 15:59 Chicago.
Propfirm : Tradeify Select Flex (drawdown 2 000 $ EOD), simulateur commun, taille = nombre de micros pour un
risque fixe en $ (trade sauté si 1 micro dépasse ce risque).

## La réponse courte

| Question | Réponse |
|---|---|
| Stop | **ATR fixe, 2 à 3 ATR.** 1 ATR est nettement pire (−0,24 R). Le stop « derrière le niveau le plus proche » est le PIRE choix (SOR-0004). |
| Stop sur niveau qui vaut la peine | Une seule piste : **pivot weekly, marge 0,25 ATR, distance 0,75-2 ATR, trade sauté s'il n'y a pas de pivot**. Il bat son placebo, mais sur ~70 trades. À confirmer sur le DATASET. |
| Objectif | **Sortie Heishinator** (ou prochaine zone Detector à ≥ 1,5 R, puis Heishinator : +0,04 R). Les R fixes (1 à 4 R), le partiel et les suiveurs font moins bien en R. |
| Break-even | Coûte en R (−0,03 à −0,04 R) ; aide parfois en propfirm (moins de grosses pertes), pas de façon régulière. |
| Taille | **Risque 100 à 150 $ par trade** (5 à 7,5 % du drawdown de 2 000 $). Au-delà de 200 $, P(réussite) s'effondre (0,51 à 100 $ → 0,04 à 500 $ avec 2 ATR + Heishinator). |
| Gestion selon la situation | **Non.** Choisie sur les 2/3 anciens, elle ne bat pas 2 ATR + Heishinator sur le 1/3 récent (8 fois sur 10 pire). Une seule règle pour tout. |
| Les niveaux battent-ils le placebo ? | **Globalement non.** Écarts petits (±0,1 R), rarement significatifs. Exceptions modestes : stop pivot weekly sauté (+0,31 R), objectif sur pivots (+0,05 R, 7 déclencheurs sur 8). |

## A. Stops (257 stops × 2 sorties × 9 déclencheurs)

- ATR fixes (R moyen, panel) : 1 ATR −0,21 ; 1,5 ATR +0,01 ; 2 ATR +0,03 ; 2,5 ATR +0,01 ; 3 ATR +0,04.
- Niveau le plus proche toutes familles : −0,30 R, stop à 1 ATR en moyenne, 78 % des trades stoppés, et moins bon
  que son placebo. Mêmes défauts pour swing, ronds fins, sessions, pivots mensuels.
- Le classement brut est trompeur : les « meilleurs » stops sur niveau (Monday sauté +0,32 R) gagnent parce
  qu'ils FILTRENT les trades ; leur placebo (mêmes trades, distance du stop permutée) fait aussi bien ou mieux
  (Monday : réel +0,01 R, placebo +0,11 R).
- Trendlines : absentes du cache (prix des droites non exportés) → stop TL = repli ATR, testable seulement sur le
  DATASET. Pivots annuels : quasi jamais assez près, même chose.

### A2. Placebo des 15 meilleurs stops sur niveau (20 tirages, 6 à 8 déclencheurs × 2 sorties)

| stop | R réel | R placebo | écart | cas réel > placebo | cas p ≤ 0,10 |
|---|---|---|---|---|---|
| pivot weekly, 0,25 ATR, 0,75-2 ATR, sauté | +0,21 | −0,10 | **+0,31** | 10/12 | 6/12 |
| pivots W/M/A, 0,25 ATR, 0,75-2 ATR, sauté | +0,10 | −0,07 | +0,17 | 10/12 | 2/12 |
| Monday 2 ticks, 0,5-3 ATR, sauté | +0,15 | +0,08 | +0,07 | 11/14 | 2/14 |
| zone Detector 0,1 ATR, 1-3 ATR, sauté | +0,15 | +0,09 | +0,06 | 10/14 | 4/14 |
| rond 0,25 ATR, 1-3 ATR, repli 2 ATR | +0,07 | +0,01 | +0,06 | 12/16 | 5/16 |
| ORB 2 ticks, 0,5-3 ATR, repli 2 ATR | +0,07 | +0,03 | +0,04 | 14/16 | 6/16 |
| ORB 0,25 ATR / Monday 0,25 ATR / pivot W 0,1 ATR, sautés | | | −0,01 à −0,07 | | |

Le pivot weekly ressort, mais : 5 à 14 trades par déclencheur, choisi parmi 257 stops, et sur Signator Fort il
est pire que son placebo. C'est une piste, pas un résultat. Sur le témoin au hasard il fait aussi un peu mieux
que son placebo (+0,06 R), ce qui irait dans le bon sens (effet du niveau, pas de l'entrée).

**Correction de l'étape B** : les stops sur niveau gardés pour B sont maintenant choisis sur l'écart contre le
placebo (A2) et non plus sur le R brut, qui retenait 3 variantes de Monday « sauté » (pur effet de filtre).
Gardés : ATR 1,5 / 2 / 3, rond 0,25 ATR repli 2, ORB 2 ticks repli 2, pivot weekly sauté, pivots W/M/A sautés.

## B. Objectifs et gestion (stop 2 ATR, 399 gestions)

R moyen du panel, référence 2 ATR + Heishinator = +0,10 R :

| sortie | R | écart réf. | déclencheurs mieux |
|---|---|---|---|
| prochaine zone Detector ≥ 1,5 R + Heishinator | +0,14 | +0,04 | 7/8 |
| Heishinator seul | +0,10 | — | — |
| sortie à l'heure (15:59 Chicago) | +0,10 | 0,00 | 2/8 |
| break-even 1 R + Heishinator | +0,07 | −0,03 | 4/8 |
| suiveur 3 ATR | +0,05 | −0,05 | 3/8 |
| prochain pivot ≥ 1,5 R + Heishinator | +0,04 | −0,06 | 2/8 |
| partiel 1 R + break-even + Heishinator | +0,03 | −0,08 | 3/8 |
| 4 R / 3 R / 2 R / 1 R fixes | +0,01 / −0,01 / −0,04 / −0,05 | | ≤ 3/8 |
| partiel 1 R + suiveur 2 ATR | −0,07 | −0,17 | 2/8 |

Objectif sur niveau contre placebo (multiple de R permuté) : pivots +0,05 R (7 à 8 déclencheurs sur 8), toutes
familles +0,05 R, Detector +0,02 R, ronds −0,02 à −0,04 R. Le gain des pivots est réel contre placebo, mais
l'objectif pivot reste moins bon que Heishinator seul.

## C/F. Propfirm (chaque déclencheur à sa meilleure taille)

| gestion | VE moy. $ | VE médiane $ | P(réussite) | P(1er payout) | mieux que 2 ATR + Hei |
|---|---|---|---|---|---|
| **3 ATR + Heishinator** | 3 661 | 1 368 | 0,63 | 0,60 | 6/8 |
| 2 ATR + break-even 1 R + Heishinator | 3 200 | 112 | 0,45 | 0,42 | 2/8 |
| 2 ATR + suiveur 3 ATR | 3 144 | 63 | 0,47 | 0,43 | 4/8 |
| 2 ATR + Heishinator (référence) | 2 740 | 405 | 0,50 | 0,45 | — |
| rond repli 2 ATR + Heishinator | 2 280 | 671 | 0,55 | 0,49 | 3/8 |
| pivot weekly sauté + Heishinator | 1 897 | 153 | 0,39 | 0,29 | 3/8 |
| 2 ATR + 2 R | 1 276 | −65 | 0,44 | 0,39 | 1/8 |
| 1,5 ATR + 2 R | 346 | −127 | 0,23 | 0,17 | 2/8 |

En propfirm, à risque égal, les stops/objectifs sur niveau battent souvent leur placebo (rond repli 2 ATR + 2R :
P 0,39 contre 0,22 à 150 $ ; pivot weekly sauté + Hei : P 0,33 contre 0,19 à 200 $), mais avec 5 tirages de
placebo et peu de trades : à revérifier.

Taille (2 ATR + Heishinator) : 100 $ → P 0,51 ; 150 $ → 0,42 ; 200 $ → 0,26 ; 300 $ → 0,12 ; 500 $ → 0,04.
Attention : à 100 $, la moitié des trades est sautée (1 micro dépasse 100 $ de risque) ; une partie du gain vient
de ce filtre (stops étroits seulement).

## D. Situations (choix sur les 2/3 anciens, test sur le 1/3 récent)

Par type de déclencheur, volatilité, séance, tendance 1H : la gestion choisie fait sur la période test
moins bien que 2 ATR + Heishinator dans 8 cas sur 10 (ex. volatilité basse : 0,74 R contre 1,06 R ; avec la
tendance 1H : 0,25 contre 0,80). Pas de gestion « selon la situation » à retenir.

## E. Recettes par déclencheur (meilleure VE) et contrôle du hasard

| déclencheur | gestion | risque | trades | R | P(réussite) | VE $ | réf. hasard P | p hasard |
|---|---|---|---|---|---|---|---|---|
| climax BUY + TREND 1H (SOR-0002) | 2 ATR + BE 1 R + 3 R | 300 $ | 23 | +0,85 | 1,00 | 10 607 | 0,38 | 0,05 |
| climax BUY (SOR-0001) | 3 ATR + Heishinator | 150 $ | 31 | +0,48 | 1,00 | 10 452 | 0,59 | 0,05 |
| climax SELL | rond repli 2 + BE 0,5 R + Hei | 150 $ | 19 | +0,01 | 1,00 | 9 107 | 0,12 | 0,10 |
| flip Heishinator (SOR-0003) | pivot weekly sauté + BE 1 R + 2 R | 500 $ | 14 | +0,45 | 0,96 | 5 054 | 0,34 | 0,05 |
| témoin AU HASARD | rond repli 2 + suiveur 3 ATR | 100 $ | 143 | +0,30 | 0,80 | 3 775 | 0,34 | 0,10 |
| cassure ORB | 3 ATR + Hei | 200 $ | 77 | +0,03 | 0,75 | 1 836 | 0,18 | 0,10 |
| trendline | 1,5 ATR + swing ≥ 2 R + Hei | 100 $ | 66 | +0,46 | 0,69 | 1 409 | 0,22 | 0,10 |
| Signator Fort | ORB repli 2 + Detector ≥ 1,5 R + Hei | 100 $ | 83 | +0,12 | 0,54 | 807 | 0,17 | 0,19 |
| cassure Monday | 2 ATR + 2 R | 500 $ | 34 | 0,00 | 0,10 | −125 | 0,29 | 0,76 |

**À lire avec méfiance** : bootstrap de White sur 399 gestions, p = 0,28 → la meilleure gestion du panel n'est
pas distinguable du hasard de sélection. Le témoin aux entrées AU HASARD atteint P 0,80 avec sa meilleure
gestion : choisir la gestion par déclencheur gonfle fortement P(réussite). Les P = 1,00 sur 13 à 31 trades
(climax) viennent du rééchantillonnage d'un tout petit échantillon, pas d'une certitude.

## G. Entrées publiées par les autres agents (EXH, REG ; aucune ligne ML au registre au 17/10)

- EXH-0001/0002 : leur gestion d'origine (1 ATR + 4 R) reste la meilleure (R +1,15 à +1,30) ; 2 ATR + 2 R
  moins bon mais positif (+0,66 à +0,73). EXH-0003 : bon avec toutes les gestions (2 ATR + Heishinator R +0,62). ~30 trades chacun.
- REG-0004/0005 : aucune gestion ne les rend jouables en propfirm (P ≤ 0,46).
- REG-0006 : seul le break-even (2 ATR + BE 1 R + Hei, ou partiel + BE + suiveur) le fait passer (P 1,00 contre 0,57-0,82 avec les
  autres stops 2-3 ATR), avec un R de +0,02 à +0,10 : fragile.

## Registre

SOR-0001 à SOR-0003 : recettes retenues (prometteuses, non confirmées) avec trades ; SOR-0004 : stop derrière le
niveau le plus proche toutes familles, rejeté (R −0,20 contre +0,07 avec 2 ATR, 79 % de stops).

## Limites

Cache seulement (5 mois sur MES, 3 semaines sur MNQ), 14 à 140 trades par déclencheur, trendlines absentes,
placebo à 20 tirages (p minimum 0,05) et 5 tirages en propfirm. Les choix « meilleure gestion par déclencheur »
sont optimistes. Rien n'est validé sur le scellé.
