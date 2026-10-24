# Analyse des 3 ans (TV3) — préréglages 38 / 39 / 40 / 42 sur MNQ1!, 15 min, 25/10/2023 → 16/10/2026

Source : 13 exports du testeur TradingView (4 micros MNQ, commissions du testeur). Code : `charge.py`, `base.py`, `q1.py` … `q6.py`, `q5.py` (propfirm), `prop.csv`.
Heures = heure de Paris (les horodatages des exports sont en heure de Paris : entrées de 0 h à 22 h).

Limites générales : on n'a pas les bougies, seulement les trades. Le risque R de chaque trade est reconstruit : stop et objectif d'un même instant d'entrée ont la même distance dans tous les préréglages à stop 2 ATR (vérifié : écart nul sur 330 instants communs). R connu exactement pour 85 % des sorties au temps (334 sur 400 pour le 40) ; les autres sont écartées des calculs en R.

## Vue d'ensemble (MNQ1!, 4 micros)

| Préréglage | Trades | % gagnants | PF | Net $ | DD max $ | Net sans son meilleur trimestre | Trim. > 0 |
|---|---|---|---|---|---|---|---|
| 38 (biais strict, 1R) | 657 | 57,1 | 1,33 | +34 264 | 7 898 | +19 954 | 9 / 13 |
| 39 (biais strict, 1,5R) | 598 | 52,3 | 1,30 | +30 566 | 6 940 | +18 404 | 9 / 13 |
| 40 (biais large, 1R) | 1 228 | 55,3 | 1,26 | +54 488 | 15 386 | +33 842 | 10 / 13 |
| 42 (+ feu 60, sans sortie temps) | 1 092 | 55,0 | 1,22 | +51 932 | 11 382 | +31 948 | 10 / 13 |

## Question 3 — Stabilité (la plus importante pour juger le reste)

Par année (PF / % gagnants / net $) :

| | 2023-24 | 2024-25 | 2025-26 |
|---|---|---|---|
| 38 | 1,33 / 58,5 / +8 582 | 1,33 / 55,7 / +10 700 | 1,32 / 57,2 / +14 982 |
| 39 | 1,34 / 54,4 / +8 290 | 1,40 / 50,5 / +12 170 | 1,21 / 52,3 / +10 106 |
| 40 | 1,15 / 53,6 / +9 148 | 1,20 / 55,3 / +12 374 | 1,38 / 57,1 / +32 966 |
| 42 | 1,07 / 52,7 / +4 644 | 1,12 / 53,5 / +8 602 | 1,40 / 59,1 / +38 686 |

Par trimestre (PF) :

| Trim. | 38 | 39 | 40 | 42 |
|---|---|---|---|---|
| 2023T4 | 0,97 | 0,78 | 1,15 | 1,16 |
| 2024T1 | 1,55 | 1,71 | 1,18 | 1,03 |
| 2024T2 | 1,71 | 1,72 | 1,44 | 1,49 |
| 2024T3 | 1,09 | 1,02 | 1,11 | 0,95 |
| 2024T4 | 1,53 | 1,52 | 1,26 | 1,19 |
| 2025T1 | 1,07 | 1,17 | 1,12 | 1,17 |
| 2025T2 | 2,09 | 2,56 | 1,27 | 0,89 |
| 2025T3 | 1,12 | 0,95 | 0,95 | 1,05 |
| 2025T4 | 0,86 | 0,60 | 1,63 | 1,38 |
| 2026T1 | 2,30 | 1,67 | 1,85 | 1,58 |
| 2026T2 | 1,95 | 1,86 | 1,91 | 1,74 |
| 2026T3 | 0,62 | 0,71 | 0,74 | 0,91 |
| 2026T4 (2 sem.) | 0,93 | 1,26 | 0,99 | 1,80 |

Lecture : l'avantage existe les 3 années, mais il n'est pas régulier. Le 38 est le plus stable (PF identique 3 années de suite). Les 40 et 42 sont irréguliers : PF 1,07-1,20 les deux premières années, 1,4 la dernière (60 à 75 % du gain vient de 2025-26 ; le seul trimestre 2026T2 pèse +20 k$ sur 54 k$ pour le 40). Alerte : 2026T3 (juil.-sept. 2026) est négatif pour les quatre (-3 k$ à -8 k$), c'est la période la plus récente.

## Question 1 — « Si on attendait un peu plus, il y aurait souvent un TP »

Sorties « Temps (8 bougies) » : un tiers des trades (400 sur 1 228 pour le 40) et +12,9 k$ de net (PF 1,41 ; PF par année 1,02 / 1,32 / 1,67). MFE exprimé en part du chemin vers l'objectif (1R pour 38/40 ; 1,5R pour 39) :

| Préréglage | Sorties au temps | Gagnantes à la sortie | $ moyen | ≥ 70 % du chemin | ≥ 80 % | ≥ 90 % |
|---|---|---|---|---|---|---|
| 40 | 400 (33 %) | 55,8 % | +32 $ (+0,07 R) | 34 % | 24 % | 11 % |
| 38 | 208 (32 %) | 58,2 % | +39 $ | 34 % | 26 % | 13 % |
| 39 | 271 (45 %) | 66,8 % | +135 $ | 27 % | 14 % | 6 % |

Donc « souvent un TP » est exagéré : seulement 1 sortie au temps sur 9 avait fait 90 % du chemin, 1 sur 4 avait fait 80 %. Le trade moyen sorti au temps a fait 0,56 R de MFE et finit à +0,07 R. Parmi ceux qui avaient fait ≥ 70 %, 16 à 18 % finissaient quand même perdants.

Effet d'attendre — expérience naturelle : le préréglage 42 prend les mêmes entrées que le 40 mais sans sortie temps. Pour les 333 sorties au temps du 40 retrouvées dans le 42 (même instant, même sens) on voit ce qui est arrivé en laissant courir :

| Si on laisse courir | Résultat final du 42 |
|---|---|
| Objectif touché | 152 (46 %) |
| Stop touché | 122 (37 %) |
| Fin de séance (15:59 Chicago) | 59 (18 %) |

| MFE à la sortie (40) | n | Net à 8 bougies | Net en laissant courir |
|---|---|---|---|
| < 0,4 R | 88 | -10 222 | -6 606 |
| 0,4 à 0,7 R | 107 | +4 528 | -1 412 |
| 0,7 à 0,9 R | 70 | +11 132 | +8 702 |
| ≥ 0,9 R | 33 | +8 362 | +11 486 |

Gagnants ou perdants à la sortie ? 184 gagnants au temps (+38,9 k$) et 149 perdants (-26,7 k$). Laisser courir les gagnants les dégrade (+31,3 k$ au final, soit -7,6 k$) ; laisser courir les perdants les améliore (-17,0 k$, soit +9,6 k$). Les gagnants au temps sont donc plutôt à encaisser, les perdants à laisser vivre (retour vers l'entrée). Seuls les trades ≥ 0,9 R gagnent à attendre (+3,1 k$ sur 33 trades, trop peu pour conclure).

Effet d'une sortie à 12 / 16 bougies ou « jamais » (333 trades, net à 8 bougies = +12 264 $) :
- Jamais de sortie temps : +14 254 $ (+2 k$), mais l'écart-type de la somme est ±9 k$ : c'est du bruit. Par année : -1,6 k$ / -2,0 k$ / +17,8 k$ contre +0,3 / +3,1 / +8,9 k$ à 8 bougies ; ne gagne qu'en 2025-26.
- 12 bougies : 140 trades se terminent avant (+6,2 k$ exact) ; pour les 193 restants le prix à la bougie 12 est inconnu (entre +6,5 k$ à 8 bougies et +8,1 k$ à la fin) : total estimé entre +12,7 k$ et +14,3 k$, soit +0,4 à +2 k$.
- 16 bougies : 208 se terminent avant (+10,4 k$ exact) ; 125 restants (entre +2,9 et +3,9 k$) : total entre +13,3 et +14,3 k$, soit +1 à +2 k$.
- « Pas de sortie temps si en gain » : c'est l'inverse de ce qui marche (-7,6 k$ sur les gagnants). En revanche « pas de sortie temps si en perte » donne +9,6 k$ ±6 k$ sur le 40 et +5,7 k$ ±4,4 k$ sur le 38, mais par année : +1,8 / -2,3 / +10,2 k$ (40) et -0,1 / -0,2 / +6,0 k$ (38) : seule 2025-26 en profite, donc NON retenu.

Conclusion Q1 : garder tBar=8. Allonger ne fait pas gagner de façon démontrable.

## Question 2 — Les shorts

| Préréglage | Sens | Trades | % gagn. | PF | R moyen | MAE moy. (en fraction du stop) | MAE ≥ 80 % du stop | Stop en points (médiane) |
|---|---|---|---|---|---|---|---|---|
| 40 | Long | 830 | 55,1 | 1,20 | +0,05 | 0,60 | 37 % | 47,5 |
| 40 | Short | 398 | 55,8 | 1,34 | +0,12 | 0,60 | 35 % | 75,5 |
| 38 | Long | 527 | 56,9 | 1,30 | +0,08 | 0,59 | 36 % | 48,8 |
| 38 | Short | 130 | 57,7 | 1,38 | +0,16 | 0,60 | 35 % | 92,0 |
| 42 | Long | 746 | 54,0 | 1,17 | +0,06 | 0,68 | 48 % | 48,0 |
| 42 | Short | 346 | 57,2 | 1,29 | +0,11 | 0,66 | 46 % | 77,5 |

Constat : l'impression est fausse en proportion du stop. Les shorts frôlent le stop exactement comme les longs (MAE 0,60 du stop dans les deux cas ; pour les seuls gagnants 0,38 contre 0,36). Ce qui change : le stop des shorts est plus loin en points (marché plus nerveux quand il baisse) donc chaque perte vaut ~680 $ contre ~410 $ pour un long à 4 micros fixes ; l'œil voit de plus gros mouvements.

Les shorts paient mieux que les longs : PF 1,34 contre 1,20 (40), R moyen deux fois plus grand, et en 40 les shorts font +31,5 k$ contre +22,9 k$ pour les longs avec deux fois moins de trades. Par année (40, PF short / long) : 2023-24 1,37 / 1,04 ; 2024-25 1,32 / 1,12 ; 2025-26 1,34 / 1,42. Les shorts sont supérieurs ou égaux chaque année. Dans le 38 : 1,57 / 1,22, 1,67 / 1,21, 1,15 / 1,42.

Réglages différents pour les shorts ? Non : pas de preuve. Stop plus large ou objectif plus court ne peut pas se tester sans les bougies, et rien n'indique un problème (MAE identique, 39 à objectif 1,5R donne des shorts aussi bons : PF 1,33). « Longs seulement » ferait perdre 58 % du gain du 40 : à éviter. Seul point utile : taille en risque fixe en $ pour égaliser (non testé ici).

## Question 4 — Filtres sur les vrais trades (préréglage 40 ; contrôle sur 38, 42, 39 et MES)

Seuls les filtres cohérents sur les 3 années séparément sont gardés.

Heure d'entrée (Paris), 40, PF 2023-24 / 2024-25 / 2025-26 :

| Heure | n | Net $ | PF par année | Verdict |
|---|---|---|---|---|
| 8 h | 94 | -4 424 | 0,86 / 0,67 / 0,69 | perdant les 3 années |
| 9 h | 85 | -3 816 | 0,72 / 0,76 / 0,76 | perdant les 3 années |
| 15 h | 130 | -1 850 | 0,84 / 1,93 / 0,62 | incohérent, ignoré |
| 16 h | 190 | +18 960 | 1,24 / 1,66 / 1,71 | positif les 3 années (à garder) |
| 17 h | 60 | +13 314 | 1,35 / 0,72 / 4,88 | irrégulier |
| 2 h, 4 h | 25 et 31 | -1 372 et -1 558 | < 1 sur 2 années sur 3 | trop peu de trades |

Le filtre « pas d'entrée de 8 h à 9 h 59 » (ouverture de Londres) est confirmé par : 38 (8 h PF 0,78/0,61/0,41), 39, 42 (9 h 0,53/0,58/1,26), le MES (les 5 préréglages perdent aux heures 8-9), et un test à deux étapes (années 1-2 : -4,5 k$ ; année 3 : -3,8 k$). Effet sur le 40 : PF 1,26 → 1,35, net +54,5 → +62,7 k$, DD 15,4 → 13,3 k$, trimestres positifs 10/13 → 12/13, PF par année 1,15/1,20/1,38 → 1,20/1,30/1,50. Même amélioration sur 38 (PF 1,33 → 1,43), 39 (1,30 → 1,40), 42 (1,22 → 1,27) et 43. Ce sont les shorts de 8-10 h qui font mal (-7,6 k$ pour 61 trades). Réserve : l'heure a été choisie en regardant ces 3 ans (surapprentissage possible, mais 5 préréglages et 2 marchés concordent).

Jour de la semaine, 40 (PF 2023-24 / 24-25 / 25-26) :

| Jour | n | Net $ | PF par année |
|---|---|---|---|
| Lundi | 239 | +22 450 | 1,30 / 2,03 / 1,75 |
| Mardi | 248 | +5 208 | 1,10 / 0,88 / 1,36 |
| Mercredi | 258 | +2 570 | 1,01 / 0,98 / 1,12 |
| Jeudi | 229 | +22 092 | 1,36 / 1,48 / 1,72 |
| Vendredi | 254 | +2 168 | 1,06 / 0,93 / 1,13 |

Lundi et jeudi portent 82 % du gain, mais le lundi du 38 a un PF de 0,84 la 1re année et du 42 de 1,00 : pas assez de recul, aucune cause plausible, 15 comparaisons faites. Non retenu (à surveiller). Éviter mercredi/vendredi ne fait que retirer des trades à ~zéro.

Long / short : voir Q2, pas de filtre. Raison de sortie (40) : Obj L +107 k$, Obj S +104 k$, Stop L -99 k$, Stop S -73 k$, Temps +12,9 k$ (PF 1,41, positif les 3 années), Fin de séance +1,9 k$ (PF 1,37) : rien à retirer.

## Question 5 — Propfirm Tradeify Select Flex (`simulateur.py`, règles `tradeify_50k_select_flex`, drawdown 2 000 $ EOD, constance 40 %, micros)

Trades rejoués à la taille donnée (P&L du testeur ramené à 1 micro, commission micro 1,30 $ aller-retour, ordre prudent MAE avant MFE). Seulement 0,2 % des trades traversent la fermeture : les trades sont bien à plat avant 15:59 Chicago. Méthodes : « chrono » = départ à chaque jour possible, rejoué dans l'ordre réel (les parcours qui dépassent les données sont censurés, donc P légèrement sous-estimée) ; « bootstrap » = blocs de 5 jours mélangés (2 000 tirages, perd l'ordre : c'est le plus pessimiste ici car les gains arrivent par séries).

Tout l'historique (3 ans), P(réussite eval) / P(1er payout) / valeur espérée $ :

| Config | Micros | Chrono | Bootstrap |
|---|---|---|---|
| 40 | 1 | 0,80 / 0,73 / +1 987 | 0,89 / 0,87 / +2 393 |
| 40 | 2 | 0,83 / 0,81 / +3 313 | 0,68 / 0,59 / +1 823 |
| 40 | 3 | 0,66 / 0,61 / +3 233 | 0,51 / 0,38 / +1 311 |
| 40 | 4 | 0,54 / 0,46 / +2 747 | 0,40 / 0,24 / +876 |
| 38 | 1 | 0,76 / 0,70 / +1 260 | 0,65 / 0,64 / +1 216 |
| 38 | 2 | 0,85 / 0,85 / +2 899 | 0,76 / 0,68 / +2 220 |
| 38 | 3 | 0,64 / 0,56 / +1 666 | 0,59 / 0,46 / +1 635 |
| 38 | 4 | 0,45 / 0,30 / +976 | 0,47 / 0,30 / +1 142 |
| 40 sans 8-10 h | 2 | 0,83 / 0,81 / +3 428 | 0,74 / 0,65 / +2 208 |
| 40 sans 8-10 h | 4 | 0,64 / 0,57 / +3 476 | 0,46 / 0,28 / +1 200 |
| 38 sans 8-10 h | 2 | 0,85 / 0,84 / +2 898 | 0,82 / 0,77 / +2 770 |

Au-delà de 4 micros, P(réussite) tombe sous 0,3 (le DD de 2 000 $ est vite atteint : une perte moyenne de 4 micros vaut ~410 à 680 $). La bonne taille est 1 à 2 micros (le 1 micro est lent : ~100 jours).

Par année (chrono, P(réussite) / P(1er payout) / valeur espérée $, 2 puis 4 micros) :

| Config | 2023-24 | 2024-25 | 2025-26 |
|---|---|---|---|
| 40, 2 micros | 0,74 / 0,70 / +2 189 | 0,44 / 0,34 / +498 (56 % censuré) | 0,66 / 0,64 / +2 839 |
| 40, 4 micros | 0,74 / 0,74 / +3 578 | 0,29 / 0,05 / -57 | 0,46 / 0,42 / +3 179 |
| 38, 2 micros | 0,52 / 0,49 / +421 | 0,48 / 0,48 / +438 | 0,55 / 0,54 / +1 728 |
| 38, 4 micros | 0,65 / 0,63 / +2 293 | 0,28 / 0,15 / +18 | 0,36 / 0,11 / +333 |
| 40 sans 8-10 h, 2 micros | 0,74 / 0,69 / +2 276 | 0,45 / 0,38 / +644 | 0,66 / 0,65 / +2 767 |
| 40 sans 8-10 h, 4 micros | 0,75 / 0,74 / +3 730 | 0,35 / 0,16 / +114 | 0,53 / 0,49 / +4 017 |

Lecture : positif chaque année, mais 2024-25 est une année faible (valeur espérée proche de zéro à 4 micros). Le 40 filtré est meilleur ou égal au 40 brut chaque année. La valeur espérée du 40 sans 8-10 h à 2 micros (+3,4 k$ par tentative, dont ~83 % de réussite) est la meilleure en taille prudente ; le 38 est un peu moins rentable mais ses chiffres bougent moins entre tailles. Ce sont des estimations sur un seul historique de 3 ans.

## Recommandation

Base : préréglage 40 (BIA-3). Le 38 est plus régulier (PF 1,33 chaque année) mais gagne 20 k$ de moins, 2 fois moins de trades et ne fait pas mieux au propfirm ; le 40 garde un net > 0 sans son meilleur trimestre et 12/13 trimestres positifs une fois filtré. Garder tBar=8, sens=Les deux, tpR=1, atrK=2.

Modifications (2 retenues, 1 de taille) :
1. Pas d'entrée de 08:00 à 09:59 Paris : `hr=1;hr1On=1;hr1=0020-0800;hr2On=1;hr2=1000-2215` (filtre cohérent sur les 3 années, confirmé sur 38/39/42/43 et MES).
2. Taille propfirm : `taille=Contrats fixes;fixe=2` (2 micros ; avec 4 micros P(réussite) chute à 0,5-0,6 et la valeur espérée ne monte plus).
3. (Facultatif, seulement à tester) rien d'autre : le tBar, le sens, le stop et l'objectif ne sont pas à modifier d'après les 3 ans.

Ligne complète : `bias=1;bF=0.55;bI=0.2;sens=Les deux;sig=1;sigNiv=Fort + Moyen;hei=1;tl=1;lvl=1;clx=1;div=0;tr=0;feu=0;ema=0;adx=0;det=1;detK=1.5;clxF=0;bo=0;maxJour=0;be=0;trail=Aucun;oppArr=0;oppHei=0;fin=0;part=0;hr=1;hr1On=1;hr1=0020-0800;hr2On=1;hr2=1000-2215;stop=ATR × k;atrK=2;tp=En R;tpR=1;tBar=8;pf=1;taille=Contrats fixes;fixe=2`

Modification qui n'existe pas dans le Pine, décrite pour mémoire (non recommandée à ce stade) : « à la bougie 8, si le trade est en perte, ne pas sortir et laisser stop et objectif courir (jusqu'à la fin de séance) ; si en gain, sortir comme aujourd'hui ». Gain estimé +9,6 k$ (±6 k$) sur le 40 mais seulement en 2025-26 : à retester avec des données plus récentes avant de l'ajouter.

Réserve générale : l'avantage du 40 est surtout récent, et le trimestre juillet-septembre 2026 est négatif pour tous les préréglages ; à surveiller avant de s'engager.
