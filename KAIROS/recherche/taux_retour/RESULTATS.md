# Taux — retour à la moyenne (agent WRF) — résultats

**État : fini sur le cache de développement (17/10). Scellé non lu. À refaire sur le DATASET avant toute décision.**

## Verdict en une phrase
**Aucun setup de retour à la moyenne ne passe honnêtement les quatre critères.** La procédure walk-forward qui
choisit sur le passé parmi les 1 692 variantes échoue hors échantillon (48 % de gagnants, −0,06 R). Une seule
piste se dégage nettement de son placebo : **la divergence RSI après un excès de prix (≥ 2,5 ATR de l'EMA50)**.
Elle ne survit pas à la correction du biais de sélection (p White 0,99), et elle perd sur la série MES de septembre.

## Données et méthode
- Cache 15 min, partie développement : MES1 29/04→18/06, MES 15/09→06/10, NQ 18/09→07/10 (tradé en MNQ).
  54 journées. Signaux sur prix CAUSAUX (aucune info de la barre suivante), exécution à l'ouverture suivante
  par le moteur commun, coûts par instrument, à plat 15:59 Chicago, blackout d'annonces retiré.
- 47 setups × 3 stops (derrière l'extrême des 2 bougies + 0,1 ATR, sauté hors 0,4-2,5 ATR ; 1 ATR ; 2 ATR)
  × 6 objectifs (0,5 / 0,75 / 1 / 1,5 R, EMA50, milieu du range 20 bougies) × 2 sorties (aucune / après
  8 bougies) = **1 692 variantes** (`resultats/balayage.csv`).
  - **F1 rejet de niveau** : la mèche traverse un niveau connu à la bougie précédente, tout le corps reste de
    l'autre côté. Niveaux : jour précédent, Monday, sessions, ORB, pivots weekly, ronds 100, ronds fins, zones
    Detector, tous. Option « force » (bougie de la couleur du trade).
  - **F2 fausse cassure** : 1re clôture au-delà d'un niveau (ORB, sessions, Monday, jour précédent, pivots,
    trendline), puis clôture de retour dans les 2 ou 4 bougies -> trade dans le sens du retour.
  - **F3 épuisement** : déclencheur opposé (climax, flèche Signator, flip Heishinator, bougie de retournement,
    divergence RSI) après un écart à l'EMA50 de 0, 1,5 ou 2,5 ATR.
- **Placebo de même géométrie** : mêmes séries, sens, heures Paris et nombre de signaux
  (`moteur.reference_hasard`), même gestion ; stop et objectif de chaque entrée au hasard tirés dans les
  distances (en ATR) des vrais trades. 500 tirages.
- **Walk-forward** : 5 plis, 3 blocs de journées d'apprentissage pour 1 de test, dans chaque série. Sur
  l'apprentissage : variante éligible si ≥ 20 trades, 60-75 % de gagnants et R > 0 ; on garde la meilleure en R.
- **Biais de sélection** : bootstrap de White (stationnaire, blocs de 5 jours, 2 000 tirages) sur les 1 205
  variantes à ≥ 30 trades, version brute et studentisée.
- **Propfirm** : `simulateur.optimise_taille` sur `tradeify_50k_select_flex` (1 000 parcours, blocs de 5 jours),
  et la même chose sur 40 tirages du placebo.

## Les familles : en moyenne, rien
Moyenne des variantes à ≥ 60 trades : F1 48 % / −0,11 R ; F2 49 % / −0,11 R ; F3 51 % / −0,06 R. Par objectif :
0,5 R donne 60 % de gagnants mais −0,10 R. C'est le piège annoncé : le taux suit l'objectif, pas l'entrée.

## Walk-forward (hors échantillon) — le vrai test
| procédure (choix sur le passé) | n | gagnants | placebo | écart (p) | R moyen | PF | P(réussite) / placebo |
|---|---|---|---|---|---|---|---|
| **globale, 1 692 variantes** (WRF-0004) | 56 | 48 % | 43 % | +5 pts (0,14) | −0,06 | 1,00 | 0,27 / 0,10 |
| famille F1 rejet | 51 | 39 % | — | — | −0,22 | 0,52 | — |
| famille F2 fausse cassure | 54 | 56 % | — | — | +0,02 | 1,02 | — |
| famille F3 épuisement | 68 | 57 % | 48 % | +10 pts (0,03) | +0,07 | 1,19 | 0,47 / 0,18 |
| setup F3 divergence ≥ 2,5 ATR ¹ | 53 | 68 % | 52 % | +16 pts (0,004) | +0,23 | 2,22 | 0,81 / 0,18 |
| setup F1 rejet Detector ¹ | 68 | 62 % | 51 % | +11 pts (0,014) | +0,06 | 1,22 | 0,84 / 0,01 |
| setup F1 rejet de session ¹ | 122 | 67 % | 61 % | +6 pts (0,026) | +0,02 | 1,14 | 0,73 / 0,12 |

¹ Le setup lui-même a été repéré sur tout l'échantillon : seuls le stop, l'objectif et la sortie sont choisis
sur le passé. Ce n'est donc pas un vrai hors échantillon.
La famille F3 choisit une divergence dans 4 plis sur 5 dès que l'apprentissage est assez long : c'est le seul
signe de persistance du balayage.

## Biais de sélection
White studentisé sur tout le balayage : **p = 0,32** pour la meilleure variante (F2 fausse cassure ORB, n4,
2 ATR, 1 R). Les finalistes ci-dessous ont p White ≥ 0,99 : leur avantage est compatible avec la chance du
meilleur parmi 1 692 essais. (Contre zéro, à la journée. Contre le placebo, leur p brut de 0,002 multiplié par
1 692 dépasse aussi 1.)

## Les 3 meilleures recettes (échantillon complet, donc biaisées par le choix)
| | recette | n | gagnants | placebo | écart (p) | R moyen | PF | P(réussite) Tradeify / placebo | P(1er payout) / placebo | micros |
|---|---|---|---|---|---|---|---|---|---|---|
| WRF-0001 | divergence ≥ 2,5 ATR, stop extrême, 0,75 R, 8 bougies max | 101 | 68 % | 51 % | +17 pts (0,002) | +0,13 | 1,93 | 0,99 / 0,15 | 0,99 / 0,11 | 5 |
| WRF-0002 | divergence ≥ 2,5 ATR, stop 2 ATR, 0,5 R | 81 | 73 % | 63 % | +9 pts (0,012) | +0,09 | 1,50 | 0,88 / 0,20 | 0,84 / 0,14 | 3 |
| WRF-0003 | rejet zone Detector, stop 1 ATR, 0,5 R | 135 | 71 % | 64 % | +7 pts (0,036) | +0,03 | 1,36 | 0,94 / 0,16 | 0,91 / 0,11 | 5 |

Contrôles (`resultats/controles_finalistes.csv`) :
- **Exécution sur prix causaux** au lieu des prix lissés : l'avantage tient (WRF-0001 75 % / +0,25 R ;
  WRF-0002 74 % / +0,11 R ; WRF-0003 70 % / +0,01 R). Ce n'est pas un artefact de la reconstitution.
- **Par série** : la divergence gagne sur MES1 (78 %, +0,30 R) et NQ (75 %, +0,28 R), **perd sur MES sept.**
  (50 %, −0,21 R). Le rejet Detector : NQ +0,17 R, MES sept. −0,07 R.
- **Nuit 0-8 h Paris** (hypothèse fixée à l'avance) : pas meilleure ici (WRF-0001 nuit +0,06 R sur 25 trades,
  jour +0,16 R sur 76).
- P(réussite) ≈ 0,9-0,99 vient d'un bootstrap de 54 journées de trades CHOISIS : très optimiste. En risque fixe
  150 $ : WRF-0001 0,71 ; WRF-0002 0,10 ; WRF-0003 0,99.
- Le placebo prend un peu plus de trades que la recette (les vrais signaux arrivent en grappes, une seule
  position à la fois) : comparaison en taux et en R moyen, pas en total.

## Préréglages pour STRATEGIE_V1.pine — options À AJOUTER (aucune n'existe)
Aucun setup de retour n'existe dans la stratégie. Ne pas approcher avec les entrées actuelles. Règles exactes,
à la clôture de la bougie, sans futur. Notations de la stratégie : `r_o r_h r_l r_c` vraies bougies, `r_atr`,
`close` = HA, `sg_ema50 = ta.ema(close, 50)` (HA).

**Entrée « Divergence après excès »** (clés proposées `div` ⓘ, `divX`) :
`ecart = (r_c - sg_ema50) / r_atr`, `rsi = ta.rsi(close, 14)`.
- SHORT si `math.max(r_h, r_h[1]) >= ta.highest(r_h, 20)` et `ta.highest(rsi, 3) < ta.highest(rsi[3], 17)` et
  `r_c < r_o` et `ta.highest(ecart, 3) >= divX`.
- LONG si `math.min(r_l, r_l[1]) <= ta.lowest(r_l, 20)` et `ta.lowest(rsi, 3) > ta.lowest(rsi[3], 17)` et
  `r_c > r_o` et `ta.lowest(ecart, 3) <= -divX`.
- Pas de filtre EMA50 (`ema=0`) : il bloquerait tout retour.

**Entrée « Rejet de zone Detector »** (clé `detRej` ⓘ) : `zt` = haut de la zone Detector HAUSSIÈRE la plus
haute dont le haut est sous `close` (HA) ; `zb` = bas de la zone BAISSIÈRE la plus basse dont le bas est
au-dessus de `close`. Le niveau doit être le même qu'à la bougie précédente (`zt == zt[1]`).
LONG si `r_l < zt` et `math.min(r_o, r_c) > zt` ; SHORT si `r_h > zb` et `math.max(r_o, r_c) < zb`.

**Stop « Extrême 2 bougies + marge »** (mode de `stop`, clés `extMarge`, `extMin`, `extMax`) : long =
`math.min(r_l, r_l[1]) - 0.1 * r_atr`, short = `math.max(r_h, r_h[1]) + 0.1 * r_atr`, niveau FIXE ; trade non
pris si la distance au prix d'entrée est < 0,4 ou > 2,5 × `r_atr`.

**Sortie temporelle** (clé `tBar`) : fermer au marché à l'ouverture qui suit la clôture de la 8e bougie en
position (bougie d'entrée comprise).

Lignes de `f_pr_def()` une fois ces options ajoutées (taille : « Contrats fixes » = 5, 3, 5 micros à régler à
la main, `q_fixe` n'est pas pilotable par préréglage) :
```
nom == "25 WRF-1 divergence excès · SL extrême · 0,75R · 8 bougies" ? "sens=Les deux;clx=0;sig=0;hei=0;tl=0;lvl=0;div=1;divX=2.5;detRej=0;tr=0;feu=0;ema=0;adx=0;det=0;clxF=0;bo=1;maxJour=0;be=0;trail=Aucun;oppArr=0;oppHei=0;fin=0;pf=1;part=0;hr=0;taille=Contrats fixes;stop=Extrême 2 bougies + marge;extMarge=0.1;extMin=0.4;extMax=2.5;tp=En R;tpR=0.75;tBar=8" :
nom == "26 WRF-2 divergence excès · SL 2 ATR · 0,5R" ? "sens=Les deux;clx=0;sig=0;hei=0;tl=0;lvl=0;div=1;divX=2.5;detRej=0;tr=0;feu=0;ema=0;adx=0;det=0;clxF=0;bo=1;maxJour=0;be=0;trail=Aucun;oppArr=0;oppHei=0;fin=0;pf=1;part=0;hr=0;taille=Contrats fixes;stop=ATR × k;atrK=2;tp=En R;tpR=0.5;tBar=0" :
nom == "27 WRF-3 rejet zone Detector · SL 1 ATR · 0,5R" ? "sens=Les deux;clx=0;sig=0;hei=0;tl=0;lvl=0;div=0;detRej=1;tr=0;feu=0;ema=0;adx=0;det=0;clxF=0;bo=1;maxJour=0;be=0;trail=Aucun;oppArr=0;oppHei=0;fin=0;pf=1;part=0;hr=0;taille=Contrats fixes;stop=ATR × k;atrK=1;tp=En R;tpR=0.5;tBar=0" :
```
Le préréglage 26 n'a besoin que de l'entrée « divergence » ; le 27 que de l'entrée « rejet Detector ».

## Limites
54 journées, une série (MES sept.) contre les deux autres ; prix reconstitués depuis le HA (mèches estimées) ;
pas de Detector ni de climax sur MES1 ; trendlines sans prix de droite dans le cache (F2 trendline approchée par
la clôture d'avant la cassure). Tout est à relancer sur le DATASET (≈ 1,7 an) : c'est là que la divergence
après excès doit être confirmée ou enterrée, en testant UNIQUEMENT les 3 recettes ci-dessus (pas un nouveau
balayage).

## Relancer
```
cd KAIROS/recherche/taux_retour
WRF_SOURCE=dataset ~/venv-quant/bin/python balayage.py
WRF_SOURCE=dataset ~/venv-quant/bin/python analyse.py wf
WRF_SOURCE=dataset ~/venv-quant/bin/python analyse.py white
WRF_SOURCE=dataset ~/venv-quant/bin/python analyse.py finalistes 'F3_div_x2.5|ext|R0.75|t8' 'F3_div_x2.5|a2|R0.5|t0' 'F1_det|a1|R0.5|t0' 'proc=global' 'proc=F3 épuisement'
```
Fichiers : `setups.py` (setups et gestions), `donnees_wrf.py` (accès unique aux données), `analyse.py`
(walk-forward, White, placebo, simulateur, contrôles), `registre_wrf.py` (lignes WRF-0001 à 0004),
`resultats/` (balayage, plis, finalistes, trades).
