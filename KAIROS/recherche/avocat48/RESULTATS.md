# Avocat du diable : préréglage 48 (ADV), MNQ1! 15 min, 2 micros, 25/10/2023 → 16/10/2026

Code : `charge.py`, `a1.py` à `a4.py` (relancer avec `~/venv-quant/bin/python -I`, depuis ce dossier). Net = après commissions, tel que l'export TradingView. Jour = jour de bourse CME (coupure 23 h Paris). Le 45 a deux exports identiques (4eb81 = 9588f).
Rappel : 45 = stop 2 ATR / objectif 2 ATR ; 47 = stop 2,5 ; 48 = stop 3 ; 50 = stop 3,5 ; 49 = stop 3 et objectif 3 (autre objectif, pas comparable). Seul le stop change, donc les entrées sont les mêmes à 1 % près.

| Préréglage | Trades | % gagnants | PF | Net $ |
|---|---|---|---|---|
| 45 | 656 | 75,5 | 4,51 | 78 439 |
| 47 | 652 | 77,3 | 5,03 | 81 909 |
| **48** | 651 | 78,5 | 5,54 | 84 437 |
| 49 | 634 | 75,4 | 5,06 | 87 921 |
| 50 | 651 | 78,8 | 5,87 | 85 696 |

## 1. Biais de sélection : 45 → 48 est-il du bruit ?

Bootstrap apparié par trade (5 000 tirages), trades communs (649 sur 651).

| Comparaison | Gain net $ | IC 95 % | p (gain ≤ 0) |
|---|---|---|---|
| 47 − 45 | +3 548 | 877 à 6 706 | 0,004 |
| **48 − 45** | **+6 094** | 2 611 à 9 942 | < 0,0002 |
| 50 − 45 | +7 353 | 3 648 à 11 503 | < 0,0002 |
| 48 − 47 | +2 506 | 275 à 5 059 | 0,012 |
| 48 − 50 | −1 259 | −2 937 à +113 | (50 pas mieux de façon sûre) |

Correction du « meilleur de 4 » (maximum des 4 écarts, bootstrap centré sur 0) : p < 0,0002. Le gain n'est pas du bruit de sélection.
Mécanisme : seuls 67 trades changent (65 stops du 45 + 2 objectifs). 30 des 65 deviennent des sorties au temps, 12 des objectifs, 22 restent des stops (plus gros). Le gain vient donc de 65 trades, pas de 651 : l'IC est large en proportion (la perte moyenne d'un stop passe de -207 à -368 $).
Régularité (gain 48 − 45 sur les trades communs) : année 1 +1 371 $, année 2 +2 700 $, année 3 +2 023 $ (3 années positives). Long +2 738 $, short +3 356 $. Trimestres : 9 positifs, 3 négatifs (-165, -341, -171 $), 1 nul (trimestre incomplet). Gain régulier mais petit : environ +9 $ par trade.

## 2. Risque de queue (2 micros ; ×1,5 pour 3 micros)

| | 45 | **48** | 50 |
|---|---|---|---|
| Pire trade | -524 $ (5/3/2026) | **-783 $** (5/3/2026, stop long) | -912 $ |
| Pire excursion défavorable (flottant) | -664 $ | -781 $ | -910 $ |
| Pire jour | -749 $ (22/5/2025) | **-932 $ (5/2/2026)** | -1 042 $ |
| Pire semaine | -777 $ (20-26/7/2026) | -777 $ | -844 $ |
| Pire série de pertes | -1 096 $ (4 trades, 5-11/2/2026) | -1 091 $ (4 trades, même série) | -1 201 $ |
| Plus longue série de perdants | 6 | 4 | 4 |
| Baisse max (jours clos) | 1 162 $ | **1 157 $** (17/2/2026) | 1 267 $ |

Pour le 48 en 3 micros : pire trade -1 175 $, pire jour **-1 398 $** (5/2/2026), pire semaine -1 166 $, pire série -1 637 $, baisse max 1 736 $.
Contre les limites : le drawdown Tradeify de 2 000 $ n'est jamais atteint (2 micros 1 157 $ = 58 %, 3 micros 1 736 $ = 87 %). Perte journalière Growth de 1 250 $ : 0 jour en 2 micros ; **1 jour en 3 micros (5/2/2026, -1 398 $)**, donc une violation sur 3 ans. Le 50 en 3 micros en aurait 2. Départ à n'importe quelle date, 60 jours de bourse : 0 / 447 départs touchent -2 000 $ (2 ou 3 micros), pire cas 1 157 / 1 736 $.
Aucun trade ne perd plus de 783 $ car le stop est à 3 ATR. Mais le backtest remplit le stop au prix exact ; un vrai stop sur un gap ou une annonce glisse.

## 3. Dépendance à une période (3e année = entrées du 24/10/2025 au 16/10/2026)

| | Trades | % gagnants | PF | Net $ | $/trade |
|---|---|---|---|---|---|
| 45, 2 premières années | 459 | 76,7 | 4,94 | 49 874 | 108,7 |
| 45, 3e année | 197 | 72,6 | 3,95 | 28 565 | 145,0 |
| 48, 2 premières années | 454 | 80,2 | 6,50 | 53 849 | 118,6 |
| **48, 3e année** | 197 | **74,6** | **4,47** | 30 588 | 155,3 |

La 3e année tient (net en hausse) mais le taux de gagnants baisse de 5,6 points (80,2 → 74,6 ; test de Fisher p = 0,12, pas significatif) et le PF de 6,5 à 4,5. IC 95 % du 3e an (bootstrap) : gagnants 68,5 à 80,7 %, PF 2,9 à 7,3.
Trimestres du 48 (taux / PF) : 2025T4 75,6 % / 5,2 ; 2026T1 73,3 % / 3,7 ; 2026T2 89,2 % / 15,0 ; **2026T3 69,4 % / 2,6** ; 2026T4 (10 trades) 50 % / 7,1.
Dernier trimestre : oui, en baisse. Depuis le 1/7/2026 : 59 trades, 66,1 % gagnants, PF 2,8, +6 546 $ (45 : 64,4 %, PF 2,4). Les 50 derniers trades : 64 %, PF 2,7. Août 2026 : 58,8 %. Reste rentable, mais c'est le plus bas du backtest. Le trimestre 2026T2 (PF 15) gonfle la 3e année.

## 4. Exécution manuelle (48)

| Mesure | Valeur |
|---|---|
| Entrées de nuit (00:20-08:00 Paris) | 137 / 651 = **21 %** (gagnants/PF identiques au jour : 80,4 % / 5,85 sans elles) |
| Sorties de nuit (toutes raisons) | 115 = 17,7 % ; dont **sorties au temps de nuit : 86 = 13,2 % des trades** (34,5 % des 249 sorties au temps) |
| Sorties de nuit : résultats | 73,9 % gagnants, PF 5,3, +10 367 $ |
| Trades de 0 bougie (entrée et sortie dans la même bougie) | 50 (7,7 %), 96 % gagnants |
| Trades de ≤ 1 bougie | **139 (21 %)**, 93,5 % gagnants, PF 15,3, **+30 026 $ = 36 % du net** |
| Sans ces 139 trades | 512 trades, 74,4 %, PF 4,30, +54 411 $ |

Glissement supplémentaire par trade (tick = 0,50 $ par micro, 2 micros) :

| Glissement | Net $ | PF | % gagnants | Si compté par côté (×2) : net / PF |
|---|---|---|---|---|
| 0 | 84 437 | 5,54 | 78,5 | idem |
| 2 ticks (2 $) | 83 135 | 5,40 | 78,0 | 81 833 / 5,27 |
| 4 ticks (4 $) | 81 833 | 5,27 | 77,9 | 79 229 / 5,01 |
| 8 ticks (8 $) | 79 229 | 5,01 | 76,7 | 74 021 / 4,52 |

Le coût est faible : le net tombe à 0 vers 190 ticks (~47 points) par trade. Le vrai risque est ailleurs : un trade sur cinq se règle en moins de 15 minutes, il faut être devant l'écran à la clôture de la bougie et entrer en quelques secondes ; le backtest entre à l'ouverture de la bougie suivante et ordonne haut/bas dans la bougie avec 4 ticks. Si les entrées rapides sont ratées ou mal exécutées (cas pessimiste : on les perd toutes), il reste 54 411 $, PF 4,3, et avec 8 ticks de glissement 50 315 $, PF 3,9. Rater l'objectif de ces trades est le vrai coût, pas le glissement.
Le 48 exige aussi 21 % d'entrées entre 00:20 et 08:00, et 13 % de sorties au temps de nuit : à la main, il faut des alertes et un réveil, ou accepter de les sauter (sans elles : 514 trades, PF 5,85, +73 547 $, donc on perd 13 % du net seulement).

## 5. Verdict

**Garder 48 pour le test réel, mais à 2 micros fixes et sans promettre 78 % / PF 5,5 : attendre plutôt ~72 % / PF 3,5-4,5** (3e année et dernier trimestre). Pourquoi pas 45 : le 48 est meilleur de +6 094 $ (p < 0,0002) mais le pire trade passe de -524 à -783 $. Pourquoi pas 50 : +1 259 $ de mieux sur le 48, non significatif, pire jour -1 042 $ (-1 563 $ en 3 micros) et PF qui profite du même effet de tri. Pourquoi pas 47 : moins bon que 48 (p = 0,01). 49 : autre objectif, pire pour le taux de gagnants (75,4 %) et 356 trades diffèrent du 45 : pas comparable, à revoir à part.
Raisons de ne PAS passer en 3 micros : le 5/2/2026 aurait coûté -1 398 $ sur Growth (limite 1 250 $) ; la baisse max atteindrait 87 % du budget de 2 000 $. Si 3 micros, seulement en Select Flex, ou avec un arrêt journalier à -800 $.
Raisons de ne pas lancer tout de suite en compte payant : (a) tendance du taux de gagnants à la baisse en 2026T3 (69 %) ; (b) un tiers du net vient de trades terminés en ≤ 1 bougie, les plus durs à exécuter à la main ; (c) un seul backtest, aucun test hors échantillon réel. Faire d'abord 30 trades en simulation / démo ; la méthode de sélection (stop) est solide statistiquement, l'exécution est le point faible.

### Trois garde-fous (calculés sur les 651 trades du 48, 2 micros)
1. **Taux de gagnants** : arrêter et réexaminer si ≤ 18 gagnants sur les 30 premiers (60 %), ≤ 32 sur 50 (64 %), ≤ 69 sur 100 (69 %). Seuil binomial à 1 % avec p = 78,5 % ; le minimum jamais vu en backtest est 60 % / 64 % / 73 % sur 30 / 50 / 100 trades glissants. Alerte jaune : ≤ 20/30, ≤ 34/50, ≤ 72/100 (5 %).
2. **Pertes en dollars** : arrêt de la journée à -700 $ (pire jour du backtest -932 $, 2e -783 $) ; pause de 2 jours si 4 perdants d'affilée (maximum du backtest) ; arrêt et revue si la baisse depuis le plus haut dépasse 1 200 $ (maximum du backtest 1 157 $, budget Tradeify 2 000 $).
3. **Exécution** : noter pour chaque trade le prix de signal et le prix réel. Si le glissement moyen dépasse 8 ticks sur 30 trades, ou si plus de 20 % des trades sont manqués, ou si le PF des 30 derniers trades réels est < 2 : revenir en simulation. Comparer aussi le PF des trades de ≤ 1 bougie réels au backtest (15,3) : s'ils tombent sous 5, retirer cette partie de l'espérance.
