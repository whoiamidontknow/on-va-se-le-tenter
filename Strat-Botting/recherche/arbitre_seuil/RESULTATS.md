# Arbitrage du seuil k (corps Dashator >= k x ATR14) - RESULTATS

Verdict : **k = 0,03**. Script : analyse.py. Tableaux bruts ci-dessous (2 micros, backtest 25/10/2023 -> 16/10/2026).

## Lecture
- Le simulateur Tradeify est saturé : P(réussite) >= 99,7 % et P(3 payouts) 98-99,9 % pour tous les k (2 micros). Il ne départage RIEN. Seul le délai bouge un peu (26 j pour k=0 contre 29 j pour k=0,03).
- Baisse max identique (783 $) et pire jour identique (-783 $) pour tous les k : le risque ne change pas.
- Les trades retirés sont gagnants à 72-82 % (base : 83 %) : le filtre retire des trades "au hasard", il ne cible pas les perdants. Net perdu à k=0,03 : 11 381 $ (-11 %), 107 trades (-17 %), dont 10 stops seulement.
- Bootstrap apparié : le net perdu est significatif pour tous les k (IC95 k=0,03 : -16 405 à -6 863 $) ; le PF n'est PAS distinguable du bruit jusqu'à 0,03 (IC95 -0,16 à +1,94) ; il devient significatif à 0,04 et 0,05 (IC > 0), mais au prix de plus de profit. Aucun k n'améliore l'edge de façon démontrée avant 0,04 : le choix est une question de fidélité, pas de performance.
- Fidélité (non mesurable ici faute des corps de bougies 1 h/4 h) : écart observé ~1 pt sur la clôture HA 15 min ; ATR 4 h de l'ordre de 100-150 pts, donc 0,01 = ~1-1,5 pt (marge nulle), 0,02 = ~2-3 pts (marge x2-3), 0,03 = ~3-4,5 pts (marge x3-4). Estimation d'ordre de grandeur à vérifier sur Pine.

## Verdict
Arguments pour 0,03 : (1) 14,8 trades/mois et 2 510 $/mois contre 17,5 et 2 785 (-10 %) ; (2) PF 7,16 contre 6,64, pire mois 330 $ (tous les mois restent positifs), risque inchangé ; (3) simulateur : P(réussite) 99,97 % et P(3 payouts) 99,8 % (2 micros), identiques au 56 ; marge de fidélité ~3x l'écart observé.
Argument contre : le gain de fidélité vs 0,02 n'est pas prouvé, et 0,02->0,03 coûte 34 trades / 2 354 $ pour rien de mesurable côté Tradeify ; 0,02 garde plus de profit. Si le test Pine montre que les trades "limites" disparaissent dès 0,02, prendre 0,02.

## 1. Statistiques globales (2 micros, 25/10/2023-16/10/2026)

| index | n | tr_mois | gagn | PF | net | net_mois | dd_max | pire_jour | pire_sem | pire_mois |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 630.0 | 17.45 | 83.49 | 6.64 | 100558.0 | 2785.25 | 783.0 | -783.0 | -565.0 | 1084.0 |
| 0.01 | 596.0 | 16.63 | 84.23 | 6.9 | 97742.0 | 2727.1 | 783.0 | -783.0 | -565.0 | 1084.0 |
| 0.02 | 563.0 | 15.71 | 83.84 | 6.84 | 92596.0 | 2583.52 | 783.0 | -783.0 | -565.0 | 913.0 |
| 0.03 | 531.0 | 14.82 | 84.75 | 7.16 | 89958.0 | 2509.92 | 783.0 | -783.0 | -751.0 | 330.0 |
| 0.04 | 488.0 | 13.62 | 86.89 | 8.28 | 87656.0 | 2445.69 | 783.0 | -783.0 | -751.0 | 377.0 |
| 0.05 | 452.0 | 12.61 | 88.27 | 8.98 | 85125.0 | 2375.07 | 783.0 | -783.0 | -751.0 | 703.0 |

## Par année (net $)

| sortie_t | 0.0 | 0.02 | 0.03 | 0.04 | 0.01 | 0.05 |
|---|---|---|---|---|---|---|
| 2023 | 4606 | 4227 | 4142 | 4026 | 4442 | 4036 |
| 2024 | 26911 | 25618 | 24591 | 23761 | 26779 | 23586 |
| 2025 | 33997 | 32371 | 31787 | 30853 | 33440 | 29570 |
| 2026 | 35044 | 30380 | 29438 | 29016 | 33081 | 27933 |

## Par trimestre (net $)

| sortie_t | 0.0 | 0.02 | 0.03 | 0.04 | 0.01 | 0.05 |
|---|---|---|---|---|---|---|
| 2023Q4 | 4606 | 4227 | 4142 | 4026 | 4442 | 4036 |
| 2024Q1 | 4965 | 5312 | 5267 | 4958 | 5433 | 4882 |
| 2024Q2 | 4823 | 3734 | 2907 | 3021 | 4229 | 3322 |
| 2024Q3 | 11494 | 11192 | 10585 | 10287 | 11737 | 10255 |
| 2024Q4 | 5629 | 5380 | 5832 | 5495 | 5380 | 5127 |
| 2025Q1 | 6170 | 5662 | 5446 | 4971 | 5959 | 5188 |
| 2025Q2 | 11192 | 11100 | 11348 | 11292 | 11236 | 11134 |
| 2025Q3 | 6165 | 5437 | 5295 | 4852 | 5886 | 3972 |
| 2025Q4 | 10470 | 10172 | 9698 | 9738 | 10359 | 9276 |
| 2026Q1 | 13054 | 11898 | 11635 | 11460 | 12442 | 11386 |
| 2026Q2 | 11727 | 9548 | 9331 | 9331 | 11011 | 8711 |
| 2026Q3 | 7661 | 6430 | 5968 | 5721 | 7124 | 5551 |
| 2026Q4 | 2602 | 2504 | 2504 | 2504 | 2504 | 2285 |

## Depuis 01/07/2026

| index | n | gagn | PF | net |
|---|---|---|---|---|
| 0.0 | 57.0 | 80.7 | 5.29 | 10263.0 |
| 0.02 | 51.0 | 80.39 | 4.83 | 8934.0 |
| 0.03 | 47.0 | 82.98 | 5.04 | 8472.0 |
| 0.04 | 44.0 | 84.09 | 5.26 | 8225.0 |
| 0.01 | 53.0 | 81.13 | 5.12 | 9628.0 |
| 0.05 | 40.0 | 85.0 | 5.21 | 7836.0 |

## Raisons de sortie

| sortie | 0.0 | 0.02 | 0.03 | 0.04 | 0.01 | 0.05 |
|---|---|---|---|---|---|---|
| Obj S | 224 | 201 | 197 | 189 | 217 | 179 |
| Obj L | 206 | 189 | 178 | 165 | 197 | 156 |
| Temps (16 bougies) | 109 | 93 | 83 | 69 | 100 | 62 |
| Fin de séance | 56 | 52 | 48 | 44 | 52 | 38 |
| Stop L | 21 | 15 | 15 | 14 | 17 | 12 |
| Stop S | 14 | 13 | 10 | 7 | 13 | 5 |

## 2. Trades retirés

| cran | retires | net_retires | gagn_retires_pct | moy | stops | ajoutes | net_ajoutes |
|---|---|---|---|---|---|---|---|
| 0->0.01 | 38 | 3705 | 73.7 | 97.5 | 5 | 4 | 889 |
| 0.01->0.02 | 35 | 5322 | 91.4 | 152.1 | 2 | 2 | 176 |
| 0.02->0.03 | 34 | 2354 | 67.6 | 69.2 | 3 | 2 | -284 |
| 0.03->0.04 | 46 | 2646 | 60.9 | 57.5 | 5 | 3 | 344 |
| 0.04->0.05 | 37 | 2662 | 70.3 | 71.9 | 4 | 1 | 131 |
| 0->0.01 cumul | 38 | 3705 | 73.7 | 97.5 | 5 | 4 | 889 |
| 0->0.02 cumul | 73 | 9027 | 82.2 | 123.7 | 7 | 6 | 1065 |
| 0->0.03 cumul | 107 | 11381 | 77.6 | 106.4 | 10 | 8 | 781 |
| 0->0.04 cumul | 152 | 13536 | 72.4 | 89.1 | 15 | 10 | 634 |
| 0->0.05 cumul | 189 | 16198 | 72.0 | 85.7 | 19 | 11 | 765 |

## Bootstrap apparié (5000, trades du 56 rééchantillonnés ; k vs 56)

| k | d_net_moy | ic95_net | p_net_pos | d_PF | ic95_PF | p_PF_pos |
|---|---|---|---|---|---|---|
| 0.01 | -3724.829 | [-6056;-1457] | 0.0 | 0.216 | [-0.135;0.741] | 0.851 |
| 0.02 | -9048.35 | [-13214;-5392] | 0.0 | 0.14 | [-0.398;0.861] | 0.645 |
| 0.03 | -11406.865 | [-16405;-6863] | 0.0 | 0.687 | [-0.158;1.938] | 0.931 |
| 0.04 | -13561.539 | [-19085;-8160] | 0.0 | 2.112 | [0.609;4.454] | 0.999 |
| 0.05 | -16260.012 | [-21974;-10700] | 0.0 | 2.947 | [0.993;6.202] | 1.0 |

## Simulateur Tradeify 50k Select Flex (bootstrap blocs 5 j, 3000 sims)

| k | micros | p_reussite | delai_j | p_1er_payout | p_3_payouts | ve |
|---|---|---|---|---|---|---|
| 0.0 | 2.0 | 1.0 | 26.0 | 1.0 | 0.999 | 6560.177 |
| 0.0 | 3.0 | 1.0 | 18.0 | 1.0 | 0.988 | 7916.464 |
| 0.02 | 2.0 | 1.0 | 28.0 | 1.0 | 0.999 | 6606.702 |
| 0.02 | 3.0 | 1.0 | 20.0 | 0.998 | 0.985 | 7810.371 |
| 0.03 | 2.0 | 1.0 | 29.0 | 1.0 | 0.998 | 6630.993 |
| 0.03 | 3.0 | 0.997 | 21.0 | 0.995 | 0.98 | 7713.551 |
| 0.04 | 2.0 | 1.0 | 30.0 | 1.0 | 0.998 | 6644.246 |
| 0.04 | 3.0 | 0.998 | 21.0 | 0.995 | 0.981 | 7818.506 |
| 0.01 | 2.0 | 1.0 | 26.0 | 1.0 | 0.999 | 6625.326 |
| 0.01 | 3.0 | 1.0 | 19.0 | 0.998 | 0.989 | 7920.137 |
| 0.05 | 2.0 | 1.0 | 30.5 | 1.0 | 1.0 | 6631.691 |
| 0.05 | 3.0 | 0.999 | 22.0 | 0.996 | 0.986 | 7842.662 |
