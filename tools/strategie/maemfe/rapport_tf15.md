# Étude du stop et de la sortie par MAE/MFE

Généré le 2026-10-15 19:01. Unités : 15 min. Sources : cache commun du projet.

## Méthode

- Signaux calculés sur les bougies Heiken Ashi (comme l'indicateur), **excursions mesurées aux vrais prix** reconstitués depuis le HA (`recon.py`, fiable en 15 min) ; tout en multiples de l'ATR14 des vrais prix connu au signal.
- Entrée à l'ouverture de la barre qui suit le signal. MAE = pire excursion contre le trade, MFE = meilleure excursion en faveur, sur 4 à 48 barres. Chaque signal est étudié isolément (chevauchements possibles).
- Coûts : 1 tick de glissement par côté + 1,25 $/contrat/côté (MES 5 $/pt, NQ 20 $/pt), retirés de chaque trade. Stop et objectif dans la même barre : stop. Objectif rempli seulement s'il est dépassé d'un tick.
- Jeux : coupure à la date médiane des entrées MES du déclencheur. **APPR** = MES avant (tous les choix y sont faits) ; **VAL_T** = MES après ; **VAL_NQ** = NQ après (instrument ET temps) ; NQ_avant = mêmes journées que APPR (pas indépendant, affiché pour info) ; **VAL** = VAL_T + VAL_NQ (verdict).
- Stop recommandé = plus petit stop qui garde >= 90 % des gagnants d'APPR (gagnant = clôture nette > 0 à 16 barres). Objectif et durée = meilleure espérance en APPR. Break-even / suiveur adoptés s'ils améliorent APPR, « confirmés » s'ils améliorent aussi VAL.
- Référence aléatoire **appariée** : pour chaque trade, une barre tirée au hasard dans la même série, la même période et le même sens, gérée avec le même plan (1000 tirages). p = le plus prudent de (a) la part des tirages au moins aussi bons et (b) le bootstrap par jour de l'excès trade par trade sur la moyenne du hasard apparié (tient compte des signaux groupés le même jour). IC 95 % par bootstrap des journées (une journée vue en 5, 15, 30 et 60 min ne compte qu'une fois). Cases à n < 50 signalées « (n<50) » : pas de conclusion.
- Verdict : « bat le hasard » si p < 0,05 sur VAL et si VAL_T et VAL_NQ sont chacun au-dessus du hasard (confiance élevée) ; p < 0,10 = fragile ; sinon non.

**Séries utilisées**

| Instrument | Unité | Du | Au | Barres |
|---|---|---|---|---|
| MES (sans volume : ni climax ni Detector) | 15 | 2026-04-29 | 2026-07-07 | 4498 |
| MES | 15 | 2026-09-15 | 2026-10-15 | 2068 |
| NQ | 15 | 2026-09-18 | 2026-10-15 | 1780 |

**Contrôle de la reconstitution des vrais prix (API 15 min, vrais prix connus)** : 2364 barres x 2 sens, horizon 16 barres : erreur MAE médiane 0.07 ATR (biais +0.00), MFE médiane 0.07 ATR (biais +0.00) ; plan stop 1,5 ATR / objectif 2R : E[R] vrais prix +0.030 vs reconstitués +0.030, même issue (gain/perte) dans 98 % des trades.


## Synthèse

| Déclencheur | n APPR / VAL | Stop (ATR) | Objectif | BE / suiveur | Durée (barres) | E[R] APPR | E[R] VAL [IC 95 %] | Hasard VAL | p | e-ratio VAL / hasard | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Flèche Fort | 65 / 94 | 3 (garde 91 %) | 1R | - / -  | 8 | +0.03 | -0.09 [-0.18 ; -0.01] | -0.03 | 0.917 | 0.78 / 1.03 | ne bat pas le hasard, p=0.92 (profil MFE/MAE p=0.95) |
| Flèche Fort+Moyen | 65 / 94 | 3 (garde 91 %) | 1R | - / -  | 8 | +0.03 | -0.09 [-0.18 ; -0.01] | -0.03 | 0.917 | 0.78 / 1.03 | ne bat pas le hasard, p=0.92 (profil MFE/MAE p=0.95) |
| Cassure de trendline | 51 / 79 | 4 (garde 88 %) | 1R | - / -  | 24 | -0.01 | +0.01 [-0.17 ; +0.20] | -0.03 | 0.338 | 1.11 / 1.03 | ne bat pas le hasard, p=0.34 (profil MFE/MAE p=0.30) |
| Climax BUY | 31 (n<50) / 66 | 3.25 (garde 91 %) | aucun (temps) | - / -  | 48 | +1.26 | -0.17 [-0.74 ; +0.34] | -0.13 | 0.586 | 0.51 / 0.80 | ne bat pas le hasard, p=0.59 (profil MFE/MAE p=0.99) |
| Climax SELL | 13 (n<50) / 21 (n<50) | 2.75 (garde 100 %) | 6R | 1.5R / - (oui) | 48 | +0.01 | +0.80 [-0.63 ; +2.36] | +0.17 | 0.332 | 2.52 / 1.27 | indéterminé (n validation 21 < 50), - |
| Changement Heishinator | 119 / 168 | 2.25 (garde 90 %) | 1.5R | - / -  | 24 | +0.04 | -0.05 [-0.21 ; +0.11] | -0.05 | 0.515 | 0.98 / 1.00 | ne bat pas le hasard, p=0.52 (profil MFE/MAE p=0.53) |
| Cassure session/Monday | 254 / 367 | 2.75 (garde 92 %) | 1R | 1R / - (non confirmé) | 24 | +0.01 | -0.12 [-0.23 ; -0.00] | -0.04 | 0.951 | 0.83 / 1.00 | ne bat pas le hasard, p=0.95 (profil MFE/MAE p=0.99) |
| Rebond Detector | 155 / 282 | 2.5 (garde 93 %) | 2R | 1.5R / - (non confirmé) | 48 | +0.39 | -0.27 [-0.49 ; -0.01] | +0.01 | 1.000 | 0.81 / 1.00 | PIRE que le hasard, élevée (p=0.018) |
| Aléatoire (référence) | 3146 / 4807 | 2.5 (garde 92 %) | 3R | - / -  | 48 | -0.04 | -0.03 [-0.14 ; +0.08] | -0.03 | 0.541 | 0.99 / 1.00 | ne bat pas le hasard, p=0.54 (profil MFE/MAE p=0.62) |

La ligne « Aléatoire » est la référence elle-même (son p ne mesure que le bruit des tirages).

E[R] = espérance nette de coûts par trade, en R (R = distance du stop). e-ratio = MFE/MAE moyens à 16 barres.

## Détail par déclencheur

### Flèche Fort

Coupure APPR/validation : 2026-06-12 (médiane des entrées MES). n : APPR 65 (29 j), VAL_T 65 (31 j), VAL_NQ 29 (12 j), NQ_avant 0 (0 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.30 | 1.26 | 0.97 | +0.05 | 1.28 | 1.16 | 0.90 | -0.11 |
| 8 | 1.83 | 1.84 | 1.00 | +0.06 | 1.80 | 1.41 | 0.78 | -0.46 |
| 12 | 2.19 | 2.13 | 0.97 | -0.07 | 2.26 | 1.55 | 0.69 | -0.62 |
| 16 | 2.44 | 2.50 | 1.03 | -0.07 | 2.48 | 1.95 | 0.78 | -0.37 |
| 24 | 3.01 | 2.96 | 0.98 | -0.40 | 2.98 | 2.51 | 0.84 | -0.36 |
| 32 | 3.48 | 3.57 | 1.02 | -0.37 | 3.39 | 3.16 | 0.93 | +0.02 |
| 48 | 3.68 | 3.52 | 0.96 | -0.42 | 3.75 | 3.83 | 1.02 | +0.20 |

**Instant du MFE sur 48 barres** — APPR : médiane 16 barres (q25 6.25, q75 29.75) ; atteint avant 8 barres : 34 %, avant 16 : 53 %. VAL : médiane 23 barres (q25 7, q75 39) ; atteint avant 8 barres : 31 %, avant 16 : 44 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 34 | 1.15 / 1.95 / 2.70 / 3.42 | 28 | 3.40 / 4.77 / 6.92 / 7.18 |
| VAL_T | 27 | 1.07 / 1.57 / 2.86 / 2.98 | 34 | 2.73 / 4.52 / 5.51 / 7.51 |
| VAL_NQ | 17 | 1.59 / 2.10 / 2.68 / 2.97 | 12 | 2.13 / 4.83 / 7.43 / 8.36 |
| VAL | 44 | 1.13 / 1.93 / 2.77 / 2.99 | 46 | 2.65 / 4.52 / 6.81 / 7.92 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 3 % | 0 % | 5 % |
| 0.5 | 21 % | 0 % | 9 % |
| 0.75 | 35 % | 4 % | 30 % |
| 1 | 47 % | 7 % | 41 % |
| 1.25 | 53 % | 11 % | 55 % |
| 1.5 | 59 % | 21 % | 61 % |
| 1.75 | 68 % | 21 % | 70 % |
| 2 | 79 % | 32 % | 77 % |
| 2.25 | 85 % | 32 % | 82 % |
| 2.5 | 88 % | 39 % | 84 % |
| 2.75 | 88 % | 39 % | 89 % |
| 3 <- retenu | 91 % | 39 % | 95 % |
| 3.25 | 94 % | 43 % | 95 % |
| 3.5 | 94 % | 54 % | 95 % |
| 3.75 | 94 % | 57 % | 95 % |
| 4 | 97 % | 57 % | 95 % |

**Espérance vs taille du stop** (objectif 1R, 8 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.139 | -0.964 | -0.285 | -0.241 |
| 0.5 | -0.531 | -0.556 | -0.266 | -0.278 |
| 0.75 | -0.393 | -0.319 | -0.294 | -0.239 |
| 1 | -0.224 | -0.321 | -0.224 | -0.321 |
| 1.25 | -0.172 | -0.245 | -0.215 | -0.306 |
| 1.5 | -0.174 | -0.188 | -0.261 | -0.283 |
| 1.75 | -0.133 | -0.155 | -0.232 | -0.271 |
| 2 | -0.093 | -0.130 | -0.187 | -0.259 |
| 2.25 | -0.017 | -0.110 | -0.038 | -0.248 |
| 2.5 | +0.014 | -0.100 | +0.036 | -0.249 |
| 2.75 | +0.003 | -0.113 | +0.007 | -0.311 |
| 3 <- retenu | +0.034 | -0.094 | +0.102 | -0.282 |
| 3.25 | +0.051 | -0.105 | +0.167 | -0.342 |
| 3.5 | +0.022 | -0.097 | +0.075 | -0.339 |
| 3.75 | +0.013 | -0.093 | +0.049 | -0.350 |
| 4 | +0.013 | -0.099 | +0.053 | -0.395 |

**Espérance (R nets) vs objectif**, stop 3 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.093 | -0.024 |
| 0.75R | -0.053 | -0.009 |
| 1R <- retenu | +0.032 | -0.083 |
| 1.25R | -0.118 | -0.114 |
| 1.5R | -0.143 | -0.154 |
| 2R | -0.157 | -0.180 |
| 2.5R | -0.149 | -0.212 |
| 3R | -0.195 | -0.195 |
| 4R | -0.175 | -0.168 |
| 6R | -0.158 | -0.135 |
| aucun (temps) | -0.111 | -0.135 |

**Espérance vs durée maximale de détention** (stop 3 ATR, objectif 1R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.056 | -0.057 |
| 4 | -0.013 | -0.019 |
| 8 <- retenu | +0.034 | -0.094 |
| 12 | +0.003 | -0.119 |
| 16 | -0.007 | -0.067 |
| 24 | +0.026 | -0.095 |
| 32 | +0.028 | -0.063 |
| 48 | +0.032 | -0.083 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.053 [-0.11 ; -0.00] | +0.002 [-0.03 ; +0.03] |
| break-even à +1R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | -0.115 [-0.27 ; +0.02] | +0.040 [-0.06 ; +0.13] |
| suiveur 1 ATR | -0.084 [-0.22 ; +0.04] | +0.011 [-0.07 ; +0.09] |
| suiveur 1.5 ATR | -0.077 [-0.23 ; +0.05] | -0.000 [-0.07 ; +0.07] |
| suiveur 2 ATR | -0.127 [-0.27 ; -0.01] | -0.017 [-0.07 ; +0.04] |
| suiveur 3 ATR | -0.045 [-0.12 ; +0.02] | +0.004 [-0.03 ; +0.04] |

Gestion retenue : BE 1R : inutile ; suiveur 3 ATR : inutile.

**Plan final (stop 3 ATR, objectif 1R, BE -, suiveur -, sortie au temps 8 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 65 | 29 | +0.034 [-0.10 ; +0.19] | 52 % | -0.042 | +0.079 [-0.06 ; +0.24] | 0.132 | 1.03 | 1.03 | 0.479 |
| VAL_T | 65 | 31 | -0.096 [-0.20 ; +0.02] | 40 % | -0.049 | -0.046 [-0.16 ; +0.07] | 0.772 | 0.73 | 1.05 | 0.969 |
| VAL_NQ | 29 (n<50) | 12 | -0.089 [-0.26 ; +0.12] | 34 % | -0.006 | -0.084 [-0.25 ; +0.12] | 0.789 | 0.90 | 1.04 | 0.622 |
| NQ_avant | 0 | | | | | | | | | |
| VAL | 94 | 32 | -0.094 [-0.18 ; -0.01] | 38 % | -0.035 | -0.058 [-0.14 ; +0.03] | 0.917 | 0.78 | 1.03 | 0.949 |

Verdict : **ne bat pas le hasard** — confiance p=0.92 (profil MFE/MAE p=0.95).

### Flèche Fort+Moyen

Coupure APPR/validation : 2026-06-12 (médiane des entrées MES). n : APPR 65 (29 j), VAL_T 65 (31 j), VAL_NQ 29 (12 j), NQ_avant 0 (0 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.30 | 1.26 | 0.97 | +0.05 | 1.28 | 1.16 | 0.90 | -0.11 |
| 8 | 1.83 | 1.84 | 1.00 | +0.06 | 1.80 | 1.41 | 0.78 | -0.46 |
| 12 | 2.19 | 2.13 | 0.97 | -0.07 | 2.26 | 1.55 | 0.69 | -0.62 |
| 16 | 2.44 | 2.50 | 1.03 | -0.07 | 2.48 | 1.95 | 0.78 | -0.37 |
| 24 | 3.01 | 2.96 | 0.98 | -0.40 | 2.98 | 2.51 | 0.84 | -0.36 |
| 32 | 3.48 | 3.57 | 1.02 | -0.37 | 3.39 | 3.16 | 0.93 | +0.02 |
| 48 | 3.68 | 3.52 | 0.96 | -0.42 | 3.75 | 3.83 | 1.02 | +0.20 |

**Instant du MFE sur 48 barres** — APPR : médiane 16 barres (q25 6.25, q75 29.75) ; atteint avant 8 barres : 34 %, avant 16 : 53 %. VAL : médiane 23 barres (q25 7, q75 39) ; atteint avant 8 barres : 31 %, avant 16 : 44 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 34 | 1.15 / 1.95 / 2.70 / 3.42 | 28 | 3.40 / 4.77 / 6.92 / 7.18 |
| VAL_T | 27 | 1.07 / 1.57 / 2.86 / 2.98 | 34 | 2.73 / 4.52 / 5.51 / 7.51 |
| VAL_NQ | 17 | 1.59 / 2.10 / 2.68 / 2.97 | 12 | 2.13 / 4.83 / 7.43 / 8.36 |
| VAL | 44 | 1.13 / 1.93 / 2.77 / 2.99 | 46 | 2.65 / 4.52 / 6.81 / 7.92 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 3 % | 0 % | 5 % |
| 0.5 | 21 % | 0 % | 9 % |
| 0.75 | 35 % | 4 % | 30 % |
| 1 | 47 % | 7 % | 41 % |
| 1.25 | 53 % | 11 % | 55 % |
| 1.5 | 59 % | 21 % | 61 % |
| 1.75 | 68 % | 21 % | 70 % |
| 2 | 79 % | 32 % | 77 % |
| 2.25 | 85 % | 32 % | 82 % |
| 2.5 | 88 % | 39 % | 84 % |
| 2.75 | 88 % | 39 % | 89 % |
| 3 <- retenu | 91 % | 39 % | 95 % |
| 3.25 | 94 % | 43 % | 95 % |
| 3.5 | 94 % | 54 % | 95 % |
| 3.75 | 94 % | 57 % | 95 % |
| 4 | 97 % | 57 % | 95 % |

**Espérance vs taille du stop** (objectif 1R, 8 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.139 | -0.964 | -0.285 | -0.241 |
| 0.5 | -0.531 | -0.556 | -0.266 | -0.278 |
| 0.75 | -0.393 | -0.319 | -0.294 | -0.239 |
| 1 | -0.224 | -0.321 | -0.224 | -0.321 |
| 1.25 | -0.172 | -0.245 | -0.215 | -0.306 |
| 1.5 | -0.174 | -0.188 | -0.261 | -0.283 |
| 1.75 | -0.133 | -0.155 | -0.232 | -0.271 |
| 2 | -0.093 | -0.130 | -0.187 | -0.259 |
| 2.25 | -0.017 | -0.110 | -0.038 | -0.248 |
| 2.5 | +0.014 | -0.100 | +0.036 | -0.249 |
| 2.75 | +0.003 | -0.113 | +0.007 | -0.311 |
| 3 <- retenu | +0.034 | -0.094 | +0.102 | -0.282 |
| 3.25 | +0.051 | -0.105 | +0.167 | -0.342 |
| 3.5 | +0.022 | -0.097 | +0.075 | -0.339 |
| 3.75 | +0.013 | -0.093 | +0.049 | -0.350 |
| 4 | +0.013 | -0.099 | +0.053 | -0.395 |

**Espérance (R nets) vs objectif**, stop 3 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.093 | -0.024 |
| 0.75R | -0.053 | -0.009 |
| 1R <- retenu | +0.032 | -0.083 |
| 1.25R | -0.118 | -0.114 |
| 1.5R | -0.143 | -0.154 |
| 2R | -0.157 | -0.180 |
| 2.5R | -0.149 | -0.212 |
| 3R | -0.195 | -0.195 |
| 4R | -0.175 | -0.168 |
| 6R | -0.158 | -0.135 |
| aucun (temps) | -0.111 | -0.135 |

**Espérance vs durée maximale de détention** (stop 3 ATR, objectif 1R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.056 | -0.057 |
| 4 | -0.013 | -0.019 |
| 8 <- retenu | +0.034 | -0.094 |
| 12 | +0.003 | -0.119 |
| 16 | -0.007 | -0.067 |
| 24 | +0.026 | -0.095 |
| 32 | +0.028 | -0.063 |
| 48 | +0.032 | -0.083 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.053 [-0.11 ; -0.00] | +0.002 [-0.03 ; +0.03] |
| break-even à +1R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | -0.115 [-0.27 ; +0.02] | +0.040 [-0.06 ; +0.13] |
| suiveur 1 ATR | -0.084 [-0.22 ; +0.04] | +0.011 [-0.07 ; +0.09] |
| suiveur 1.5 ATR | -0.077 [-0.23 ; +0.05] | -0.000 [-0.07 ; +0.07] |
| suiveur 2 ATR | -0.127 [-0.27 ; -0.01] | -0.017 [-0.07 ; +0.04] |
| suiveur 3 ATR | -0.045 [-0.12 ; +0.02] | +0.004 [-0.03 ; +0.04] |

Gestion retenue : BE 1R : inutile ; suiveur 3 ATR : inutile.

**Plan final (stop 3 ATR, objectif 1R, BE -, suiveur -, sortie au temps 8 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 65 | 29 | +0.034 [-0.10 ; +0.19] | 52 % | -0.042 | +0.079 [-0.06 ; +0.24] | 0.132 | 1.03 | 1.03 | 0.479 |
| VAL_T | 65 | 31 | -0.096 [-0.20 ; +0.02] | 40 % | -0.049 | -0.046 [-0.16 ; +0.07] | 0.772 | 0.73 | 1.05 | 0.969 |
| VAL_NQ | 29 (n<50) | 12 | -0.089 [-0.26 ; +0.12] | 34 % | -0.006 | -0.084 [-0.25 ; +0.12] | 0.789 | 0.90 | 1.04 | 0.622 |
| NQ_avant | 0 | | | | | | | | | |
| VAL | 94 | 32 | -0.094 [-0.18 ; -0.01] | 38 % | -0.035 | -0.058 [-0.14 ; +0.03] | 0.917 | 0.78 | 1.03 | 0.949 |

Verdict : **ne bat pas le hasard** — confiance p=0.92 (profil MFE/MAE p=0.95).

### Cassure de trendline

Coupure APPR/validation : 2026-06-23 (médiane des entrées MES). n : APPR 51 (26 j), VAL_T 52 (28 j), VAL_NQ 27 (14 j), NQ_avant 0 (0 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.43 | 1.14 | 0.80 | -0.33 | 1.07 | 1.41 | 1.32 | -0.02 |
| 8 | 1.97 | 1.70 | 0.86 | -0.15 | 1.74 | 1.82 | 1.05 | -0.15 |
| 12 | 2.29 | 2.19 | 0.96 | +0.15 | 2.24 | 2.40 | 1.07 | -0.02 |
| 16 | 2.55 | 2.76 | 1.08 | +0.24 | 2.45 | 2.72 | 1.11 | -0.02 |
| 24 | 3.14 | 3.45 | 1.10 | +0.28 | 3.01 | 3.46 | 1.15 | +0.15 |
| 32 | 3.72 | 3.84 | 1.03 | -0.09 | 3.84 | 4.23 | 1.10 | -0.09 |
| 48 | 4.16 | 4.63 | 1.11 | +0.27 | 4.76 | 4.96 | 1.04 | +0.24 |

**Instant du MFE sur 48 barres** — APPR : médiane 18 barres (q25 6, q75 33.5) ; atteint avant 8 barres : 32 %, avant 16 : 40 %. VAL : médiane 20 barres (q25 9, q75 37) ; atteint avant 8 barres : 23 %, avant 16 : 40 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 25 | 1.09 / 2.02 / 3.87 / 4.16 | 25 | 2.86 / 4.74 / 6.69 / 7.44 |
| VAL_T | 25 | 0.87 / 1.24 / 2.32 / 2.54 | 26 | 2.90 / 4.70 / 7.10 / 7.40 |
| VAL_NQ | 14 | 0.76 / 1.33 / 1.62 / 1.65 | 13 | 3.97 / 5.78 / 7.68 / 8.31 |
| VAL | 39 | 0.84 / 1.26 / 1.79 / 2.41 | 39 | 3.31 / 5.56 / 7.26 / 8.08 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 12 % | 0 % | 8 % |
| 0.5 | 16 % | 0 % | 18 % |
| 0.75 | 24 % | 0 % | 41 % |
| 1 | 36 % | 8 % | 59 % |
| 1.25 | 64 % | 12 % | 74 % |
| 1.5 | 64 % | 16 % | 79 % |
| 1.75 | 68 % | 20 % | 90 % |
| 2 | 72 % | 20 % | 90 % |
| 2.25 | 84 % | 40 % | 92 % |
| 2.5 | 84 % | 48 % | 95 % |
| 2.75 | 84 % | 48 % | 97 % |
| 3 | 84 % | 56 % | 100 % |
| 3.25 | 84 % | 64 % | 100 % |
| 3.5 | 84 % | 64 % | 100 % |
| 3.75 | 88 % | 64 % | 100 % |
| 4 <- retenu | 88 % | 64 % | 100 % |

**Espérance vs taille du stop** (objectif 1R, 24 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.145 | -0.875 | -0.286 | -0.219 |
| 0.5 | -0.720 | -0.330 | -0.360 | -0.165 |
| 0.75 | -0.356 | -0.055 | -0.267 | -0.041 |
| 1 | -0.350 | -0.019 | -0.350 | -0.019 |
| 1.25 | -0.284 | +0.021 | -0.355 | +0.026 |
| 1.5 | -0.275 | +0.018 | -0.412 | +0.028 |
| 1.75 | -0.185 | +0.036 | -0.324 | +0.063 |
| 2 | -0.240 | -0.002 | -0.481 | -0.005 |
| 2.25 | -0.095 | +0.006 | -0.213 | +0.015 |
| 2.5 | -0.133 | +0.052 | -0.332 | +0.131 |
| 2.75 | -0.165 | +0.091 | -0.453 | +0.249 |
| 3 | -0.056 | +0.121 | -0.167 | +0.362 |
| 3.25 | -0.045 | +0.114 | -0.146 | +0.372 |
| 3.5 | -0.044 | +0.042 | -0.154 | +0.147 |
| 3.75 | -0.008 | +0.056 | -0.031 | +0.210 |
| 4 <- retenu | -0.008 | +0.011 | -0.032 | +0.046 |

**Espérance (R nets) vs objectif**, stop 4 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.081 | -0.074 |
| 0.75R | -0.109 | -0.010 |
| 1R <- retenu | -0.027 | -0.084 |
| 1.25R | -0.182 | -0.070 |
| 1.5R | -0.138 | -0.106 |
| 2R | -0.074 | -0.113 |
| 2.5R | -0.133 | -0.112 |
| 3R | -0.127 | -0.108 |
| 4R | -0.107 | -0.063 |
| 6R | -0.068 | -0.080 |
| aucun (temps) | -0.069 | -0.080 |

**Espérance vs durée maximale de détention** (stop 4 ATR, objectif 1R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.071 | +0.042 |
| 4 | -0.075 | +0.014 |
| 8 | -0.077 | -0.034 |
| 12 | -0.081 | +0.014 |
| 16 | -0.094 | +0.021 |
| 24 <- retenu | -0.008 | +0.011 |
| 32 | -0.065 | -0.052 |
| 48 | -0.027 | -0.084 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.076 [-0.16 ; -0.01] | -0.098 [-0.19 ; -0.02] |
| break-even à +1R | +0.000 [+0.00 ; +0.00] | +0.008 [+0.00 ; +0.02] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | -0.067 [-0.31 ; +0.14] | -0.006 [-0.18 ; +0.16] |
| suiveur 1 ATR | -0.051 [-0.27 ; +0.13] | -0.025 [-0.20 ; +0.14] |
| suiveur 1.5 ATR | -0.057 [-0.27 ; +0.12] | -0.059 [-0.23 ; +0.10] |
| suiveur 2 ATR | -0.105 [-0.29 ; +0.06] | -0.088 [-0.26 ; +0.07] |
| suiveur 3 ATR | -0.093 [-0.25 ; +0.04] | +0.012 [-0.09 ; +0.11] |

Gestion retenue : BE 1R : inutile ; suiveur 1 ATR : inutile.

**Plan final (stop 4 ATR, objectif 1R, BE -, suiveur -, sortie au temps 24 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 51 | 26 | -0.008 [-0.21 ; +0.22] | 49 % | -0.041 | +0.029 [-0.18 ; +0.26] | 0.386 | 1.08 | 1.01 | 0.344 |
| VAL_T | 52 | 28 | -0.042 [-0.24 ; +0.14] | 42 % | -0.039 | -0.003 [-0.19 ; +0.18] | 0.514 | 1.16 | 1.03 | 0.246 |
| VAL_NQ | 27 (n<50) | 14 | +0.115 [-0.14 ; +0.45] | 63 % | -0.007 | +0.115 [-0.14 ; +0.45] | 0.210 | 1.02 | 1.06 | 0.474 |
| NQ_avant | 0 | | | | | | | | | |
| VAL | 79 | 29 | +0.011 [-0.17 ; +0.20] | 49 % | -0.026 | +0.038 [-0.14 ; +0.23] | 0.338 | 1.11 | 1.03 | 0.305 |

Verdict : **ne bat pas le hasard** — confiance p=0.34 (profil MFE/MAE p=0.30).

### Climax BUY

Coupure APPR/validation : 2026-09-27 (médiane des entrées MES). n : APPR 31 (7 j), VAL_T 31 (9 j), VAL_NQ 35 (11 j), NQ_avant 19 (4 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.14 | 1.50 | 1.31 | +0.26 | 1.76 | 1.13 | 0.64 | -0.44 |
| 8 | 1.69 | 2.37 | 1.40 | +0.81 | 2.49 | 1.49 | 0.60 | -1.04 |
| 12 | 1.90 | 3.07 | 1.62 | +1.80 | 3.41 | 1.81 | 0.53 | -1.42 |
| 16 | 2.53 | 3.64 | 1.44 | +1.45 | 4.03 | 2.05 | 0.51 | -1.46 |
| 24 | 2.92 | 4.93 | 1.69 | +1.73 | 4.39 | 2.86 | 0.65 | -1.02 |
| 32 | 3.75 | 6.10 | 1.63 | +2.83 | 4.75 | 3.21 | 0.68 | -1.25 |
| 48 | 3.99 | 7.60 | 1.90 | +4.43 | 5.25 | 3.45 | 0.66 | -1.00 |

**Instant du MFE sur 48 barres** — APPR : médiane 19.5 barres (q25 10.25, q75 29.25) ; atteint avant 8 barres : 23 %, avant 16 : 40 %. VAL : médiane 13.5 barres (q25 5.25, q75 25.75) ; atteint avant 8 barres : 41 %, avant 16 : 59 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 22 | 1.12 / 1.97 / 3.09 / 3.25 | 9 | 3.31 / 4.83 / 9.64 / 11.26 |
| VAL_T | 12 | 1.17 / 1.51 / 2.20 / 2.31 | 19 | 4.01 / 6.38 / 7.13 / 8.94 |
| VAL_NQ | 10 | 0.81 / 0.99 / 1.13 / 1.54 | 25 | 3.93 / 8.59 / 10.62 / 14.42 |
| VAL | 22 | 1.04 / 1.28 / 2.10 / 2.20 | 44 | 3.97 / 7.15 / 9.86 / 14.64 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 9 % | 0 % | 9 % |
| 0.5 | 27 % | 0 % | 14 % |
| 0.75 | 32 % | 0 % | 23 % |
| 1 | 45 % | 0 % | 45 % |
| 1.25 | 59 % | 11 % | 68 % |
| 1.5 | 59 % | 11 % | 82 % |
| 1.75 | 73 % | 11 % | 82 % |
| 2 | 73 % | 11 % | 86 % |
| 2.25 | 77 % | 33 % | 95 % |
| 2.5 | 82 % | 33 % | 100 % |
| 2.75 | 82 % | 33 % | 100 % |
| 3 | 82 % | 33 % | 100 % |
| 3.25 <- retenu | 91 % | 44 % | 100 % |
| 3.5 | 95 % | 56 % | 100 % |
| 3.75 | 95 % | 56 % | 100 % |
| 4 | 95 % | 56 % | 100 % |

**Espérance vs taille du stop** (objectif aucun (temps), 48 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | +0.628 | -0.878 | +0.157 | -0.219 |
| 0.5 | +1.239 | -0.841 | +0.619 | -0.420 |
| 0.75 | +1.316 | -0.745 | +0.987 | -0.559 |
| 1 | +1.705 | -0.508 | +1.705 | -0.508 |
| 1.25 | +2.929 | -0.443 | +3.661 | -0.554 |
| 1.5 | +2.344 | -0.338 | +3.516 | -0.507 |
| 1.75 | +1.926 | -0.296 | +3.370 | -0.519 |
| 2 | +1.613 | -0.285 | +3.225 | -0.569 |
| 2.25 | +1.731 | -0.233 | +3.895 | -0.524 |
| 2.5 | +1.572 | -0.239 | +3.930 | -0.599 |
| 2.75 | +1.397 | -0.202 | +3.842 | -0.555 |
| 3 | +1.341 | -0.204 | +4.024 | -0.613 |
| 3.25 <- retenu | +1.257 | -0.167 | +4.085 | -0.542 |
| 3.5 | +1.213 | -0.171 | +4.246 | -0.599 |
| 3.75 | +1.117 | -0.168 | +4.190 | -0.630 |
| 4 | +1.033 | -0.141 | +4.133 | -0.565 |

**Espérance (R nets) vs objectif**, stop 3.25 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | +0.167 | -0.109 |
| 0.75R | +0.304 | -0.112 |
| 1R | +0.230 | -0.171 |
| 1.25R | +0.338 | -0.123 |
| 1.5R | +0.454 | -0.105 |
| 2R | +0.614 | -0.084 |
| 2.5R | +0.729 | -0.164 |
| 3R | +0.821 | -0.163 |
| 4R | +1.001 | -0.167 |
| 6R | +1.243 | -0.167 |
| aucun (temps) <- retenu | +1.257 | -0.167 |

**Espérance vs durée maximale de détention** (stop 3.25 ATR, objectif aucun (temps))

| Barres | APPR | VAL |
|---|---|---|
| 2 | +0.023 | -0.094 |
| 4 | +0.080 | -0.082 |
| 8 | +0.203 | -0.176 |
| 12 | +0.439 | -0.209 |
| 16 | +0.433 | -0.196 |
| 24 | +0.479 | -0.086 |
| 32 | +0.855 | -0.202 |
| 48 <- retenu | +1.257 | -0.167 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.429 [-0.74 ; +0.04] | +0.069 [-0.03 ; +0.19] |
| break-even à +1R | -0.136 [-0.35 ; -0.01] | -0.043 [-0.12 ; +0.05] |
| break-even à +1.5R | -0.121 [-0.33 ; +0.00] | -0.047 [-0.12 ; +0.00] |
| suiveur 0.5 ATR | -1.259 [-2.68 ; +0.21] | +0.092 [-0.36 ; +0.59] |
| suiveur 1 ATR | -1.267 [-2.64 ; +0.13] | +0.087 [-0.27 ; +0.53] |
| suiveur 1.5 ATR | -1.210 [-2.44 ; +0.10] | +0.038 [-0.30 ; +0.47] |
| suiveur 2 ATR | -1.025 [-1.97 ; +0.05] | -0.016 [-0.29 ; +0.38] |
| suiveur 3 ATR | -0.919 [-1.77 ; +0.08] | +0.052 [-0.13 ; +0.25] |

Gestion retenue : BE 1.5R : inutile ; suiveur 3 ATR : inutile.

**Plan final (stop 3.25 ATR, objectif aucun (temps), BE -, suiveur -, sortie au temps 48 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 31 (n<50) | 7 | +1.257 [-0.31 ; +2.73] | 61 % | +0.304 | +0.950 [-0.62 ; +2.43] | 0.340 | 1.44 | 1.08 | 0.163 |
| VAL_T | 31 (n<50) | 9 | -0.104 [-1.04 ; +0.54] | 35 % | -0.129 | +0.021 [-0.91 ; +0.67] | 0.494 | 0.69 | 0.87 | 0.733 |
| VAL_NQ | 35 (n<50) | 11 | -0.223 [-0.68 ; +0.24] | 40 % | -0.128 | -0.101 [-0.56 ; +0.36] | 0.688 | 0.37 | 0.79 | 0.999 |
| NQ_avant | 19 (n<50) | 4 | +2.191 [-0.39 ; +3.87] | 79 % | +0.638 | +1.603 [-0.98 ; +3.28] | 0.250 | 4.45 | 1.27 | 0.004 |
| VAL | 66 | 11 | -0.167 [-0.74 ; +0.34] | 38 % | -0.131 | -0.043 [-0.61 ; +0.46] | 0.586 | 0.51 | 0.80 | 0.989 |

Verdict : **ne bat pas le hasard** — confiance p=0.59 (profil MFE/MAE p=0.99).

### Climax SELL

Coupure APPR/validation : 2026-09-29 (médiane des entrées MES). n : APPR 13 (7 j), VAL_T 13 (6 j), VAL_NQ 8 (4 j), NQ_avant 9 (4 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 2.44 | 0.85 | 0.35 | -1.35 | 0.99 | 1.94 | 1.96 | +0.83 |
| 8 | 3.27 | 1.23 | 0.37 | -1.42 | 1.14 | 2.77 | 2.42 | +1.39 |
| 12 | 3.37 | 2.41 | 0.71 | -0.81 | 1.44 | 3.54 | 2.45 | +2.00 |
| 16 | 3.49 | 2.52 | 0.72 | -1.07 | 1.74 | 4.38 | 2.52 | +2.24 |
| 24 | 4.09 | 2.87 | 0.70 | -1.08 | 1.90 | 4.98 | 2.62 | +2.00 |
| 32 | 4.15 | 3.25 | 0.78 | -0.22 | 2.13 | 6.12 | 2.88 | +2.29 |
| 48 | 4.17 | 3.26 | 0.78 | +0.70 | 2.30 | 7.42 | 3.22 | +3.40 |

**Instant du MFE sur 48 barres** — APPR : médiane 12 barres (q25 1, q75 43.75) ; atteint avant 8 barres : 50 %, avant 16 : 50 %. VAL : médiane 30 barres (q25 15.25, q75 47) ; atteint avant 8 barres : 15 %, avant 16 : 30 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 5 | 1.81 / 2.29 / 2.45 / 2.50 | 8 | 4.86 / 5.50 / 6.38 / 6.80 |
| VAL_T | 8 | 0.86 / 1.08 / 1.33 / 1.41 | 5 | 2.62 / 3.67 / 3.86 / 3.92 |
| VAL_NQ | 4 | 0.90 / 1.30 / 1.60 / 1.71 | 4 | 2.14 / 3.06 / 4.68 / 5.22 |
| VAL | 12 | 0.86 / 1.16 / 1.47 / 1.64 | 9 | 2.48 / 3.67 / 4.34 / 5.05 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 0 % | 0 % | 0 % |
| 0.5 | 0 % | 0 % | 17 % |
| 0.75 | 0 % | 0 % | 50 % |
| 1 | 0 % | 0 % | 58 % |
| 1.25 | 0 % | 0 % | 75 % |
| 1.5 | 20 % | 12 % | 92 % |
| 1.75 | 40 % | 12 % | 92 % |
| 2 | 60 % | 12 % | 100 % |
| 2.25 | 60 % | 25 % | 100 % |
| 2.5 | 80 % | 25 % | 100 % |
| 2.75 <- retenu | 100 % | 25 % | 100 % |
| 3 | 100 % | 25 % | 100 % |
| 3.25 | 100 % | 25 % | 100 % |
| 3.5 | 100 % | 25 % | 100 % |
| 3.75 | 100 % | 25 % | 100 % |
| 4 | 100 % | 25 % | 100 % |

**Espérance vs taille du stop** (objectif 6R, 48 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.579 | -0.715 | -0.395 | -0.179 |
| 0.5 | -1.290 | -0.524 | -0.645 | -0.262 |
| 0.75 | -1.193 | +0.873 | -0.895 | +0.655 |
| 1 | -1.145 | +0.905 | -1.145 | +0.905 |
| 1.25 | -1.116 | +1.161 | -1.395 | +1.451 |
| 1.5 | -0.558 | +1.095 | -0.837 | +1.642 |
| 1.75 | -0.296 | +0.722 | -0.517 | +1.263 |
| 2 | -0.091 | +0.914 | -0.183 | +1.827 |
| 2.25 | -0.115 | +0.828 | -0.260 | +1.863 |
| 2.5 | -0.008 | +0.744 | -0.019 | +1.860 |
| 2.75 <- retenu | -0.070 | +0.648 | -0.192 | +1.781 |
| 3 | -0.084 | +0.779 | -0.253 | +2.338 |
| 3.25 | -0.125 | +0.701 | -0.407 | +2.279 |
| 3.5 | -0.160 | +0.634 | -0.561 | +2.219 |
| 3.75 | -0.191 | +0.723 | -0.715 | +2.711 |
| 4 | -0.217 | +0.669 | -0.869 | +2.675 |

**Espérance (R nets) vs objectif**, stop 2.75 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.245 | +0.190 |
| 0.75R | -0.245 | +0.309 |
| 1R | -0.283 | +0.499 |
| 1.25R | -0.196 | +0.618 |
| 1.5R | -0.134 | +0.605 |
| 2R | -0.294 | +0.628 |
| 2.5R | -0.255 | +0.590 |
| 3R | -0.217 | +0.757 |
| 4R | -0.140 | +0.621 |
| 6R <- retenu | -0.070 | +0.648 |
| aucun (temps) | -0.070 | +0.648 |

**Espérance vs durée maximale de détention** (stop 2.75 ATR, objectif 6R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.346 | +0.145 |
| 4 | -0.471 | +0.300 |
| 8 | -0.312 | +0.507 |
| 12 | -0.134 | +0.720 |
| 16 | -0.167 | +0.838 |
| 24 | -0.236 | +0.653 |
| 32 | -0.238 | +0.465 |
| 48 <- retenu | -0.070 | +0.648 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | +0.057 [-0.37 ; +0.58] | -0.112 [-0.82 ; +0.56] |
| break-even à +1R | -0.002 [-0.18 ; +0.25] | +0.225 [+0.05 ; +0.43] |
| break-even à +1.5R | +0.082 [+0.00 ; +0.27] | +0.156 [-0.02 ; +0.39] |
| suiveur 0.5 ATR | -0.114 [-1.27 ; +0.91] | -0.557 [-2.32 ; +1.06] |
| suiveur 1 ATR | -0.195 [-1.35 ; +0.86] | -0.588 [-2.24 ; +0.94] |
| suiveur 1.5 ATR | -0.341 [-1.49 ; +0.71] | -0.613 [-2.12 ; +0.77] |
| suiveur 2 ATR | -0.112 [-0.85 ; +0.58] | -0.511 [-2.10 ; +0.86] |
| suiveur 3 ATR | -0.329 [-1.01 ; +0.32] | +0.332 [-0.18 ; +0.98] |

Gestion retenue : BE 1.5R : utile (confirmé en validation) ; suiveur 2 ATR : inutile.

**Plan final (stop 2.75 ATR, objectif 6R, BE 1.5R, suiveur -, sortie au temps 48 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 13 (n<50) | 7 | +0.012 [-1.06 ; +1.14] | 31 % | -0.022 | +0.070 [-1.00 ; +1.20] | 0.459 | 0.72 | 1.18 | 0.769 |
| VAL_T | 13 (n<50) | 6 | +0.605 [-0.70 ; +2.00] | 31 % | +0.089 | +0.538 [-0.77 ; +1.93] | 0.341 | 3.05 | 1.29 | 0.022 |
| VAL_NQ | 8 (n<50) | 4 | +1.128 [-0.70 ; +3.47] | 38 % | +0.312 | +0.823 [-1.01 ; +3.16] | 0.310 | 1.80 | 1.43 | 0.245 |
| NQ_avant | 9 (n<50) | 4 | -0.547 [-1.00 ; -0.29] | 22 % | +0.043 | -0.606 [-1.06 ; -0.35] | 1.000 | 1.16 | 1.15 | 0.392 |
| VAL | 21 (n<50) | 7 | +0.804 [-0.63 ; +2.36] | 33 % | +0.171 | +0.647 [-0.80 ; +2.19] | 0.332 | 2.52 | 1.27 | 0.011 |

Verdict : **indéterminé (n validation 21 < 50)** — confiance -.

### Changement Heishinator

Coupure APPR/validation : 2026-06-18 (médiane des entrées MES). n : APPR 119 (37 j), VAL_T 119 (36 j), VAL_NQ 49 (18 j), NQ_avant 0 (0 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.16 | 1.04 | 0.90 | -0.13 | 1.09 | 1.06 | 0.97 | -0.12 |
| 8 | 1.66 | 1.66 | 1.00 | -0.00 | 1.54 | 1.46 | 0.95 | -0.23 |
| 12 | 2.13 | 2.00 | 0.94 | -0.22 | 1.96 | 1.84 | 0.94 | -0.23 |
| 16 | 2.36 | 2.39 | 1.01 | -0.06 | 2.26 | 2.22 | 0.98 | +0.01 |
| 24 | 2.78 | 2.90 | 1.04 | -0.06 | 2.79 | 2.91 | 1.04 | -0.05 |
| 32 | 3.19 | 3.50 | 1.10 | +0.13 | 3.19 | 3.51 | 1.10 | +0.27 |
| 48 | 3.59 | 3.94 | 1.10 | +0.09 | 3.86 | 4.07 | 1.06 | +0.12 |

**Instant du MFE sur 48 barres** — APPR : médiane 26 barres (q25 8, q75 39) ; atteint avant 8 barres : 27 %, avant 16 : 38 %. VAL : médiane 24 barres (q25 7.5, q75 40) ; atteint avant 8 barres : 27 %, avant 16 : 40 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 61 | 0.98 / 1.37 / 2.17 / 3.29 | 52 | 2.93 / 5.48 / 8.45 / 9.01 |
| VAL_T | 55 | 0.88 / 1.38 / 2.56 / 3.34 | 56 | 2.64 / 3.78 / 6.12 / 7.57 |
| VAL_NQ | 25 | 1.02 / 1.76 / 1.96 / 2.23 | 19 | 2.99 / 4.38 / 6.45 / 7.86 |
| VAL | 80 | 0.96 / 1.53 / 2.40 / 3.31 | 75 | 2.86 / 4.10 / 6.19 / 7.65 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 13 % | 0 % | 8 % |
| 0.5 | 31 % | 2 % | 20 % |
| 0.75 | 43 % | 2 % | 34 % |
| 1 | 56 % | 8 % | 52 % |
| 1.25 | 69 % | 19 % | 68 % |
| 1.5 | 79 % | 21 % | 74 % |
| 1.75 | 85 % | 25 % | 79 % |
| 2 | 87 % | 37 % | 85 % |
| 2.25 <- retenu | 90 % | 40 % | 88 % |
| 2.5 | 92 % | 44 % | 91 % |
| 2.75 | 93 % | 46 % | 92 % |
| 3 | 93 % | 52 % | 94 % |
| 3.25 | 93 % | 54 % | 94 % |
| 3.5 | 95 % | 56 % | 96 % |
| 3.75 | 97 % | 56 % | 98 % |
| 4 | 98 % | 58 % | 99 % |

**Espérance vs taille du stop** (objectif 1.5R, 24 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.160 | -1.098 | -0.290 | -0.275 |
| 0.5 | -0.531 | -0.513 | -0.265 | -0.257 |
| 0.75 | -0.337 | -0.335 | -0.253 | -0.251 |
| 1 | -0.179 | -0.191 | -0.179 | -0.191 |
| 1.25 | -0.118 | -0.044 | -0.147 | -0.055 |
| 1.5 | +0.017 | -0.049 | +0.025 | -0.074 |
| 1.75 | +0.019 | -0.097 | +0.034 | -0.169 |
| 2 | +0.017 | -0.070 | +0.033 | -0.141 |
| 2.25 <- retenu | +0.037 | -0.049 | +0.084 | -0.111 |
| 2.5 | +0.053 | -0.006 | +0.131 | -0.014 |
| 2.75 | +0.021 | -0.015 | +0.057 | -0.040 |
| 3 | -0.014 | -0.021 | -0.042 | -0.062 |
| 3.25 | -0.030 | -0.036 | -0.098 | -0.116 |
| 3.5 | +0.007 | -0.066 | +0.024 | -0.231 |
| 3.75 | +0.026 | -0.053 | +0.099 | -0.198 |
| 4 | +0.034 | -0.037 | +0.134 | -0.147 |

**Espérance (R nets) vs objectif**, stop 2.25 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.049 | -0.040 |
| 0.75R | -0.054 | -0.025 |
| 1R | +0.005 | -0.024 |
| 1.25R | -0.019 | -0.031 |
| 1.5R <- retenu | +0.023 | -0.039 |
| 2R | -0.030 | -0.108 |
| 2.5R | -0.007 | -0.151 |
| 3R | -0.074 | -0.110 |
| 4R | -0.041 | -0.129 |
| 6R | -0.067 | -0.127 |
| aucun (temps) | -0.001 | -0.109 |

**Espérance vs durée maximale de détention** (stop 2.25 ATR, objectif 1.5R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.109 | -0.032 |
| 4 | -0.044 | -0.062 |
| 8 | -0.012 | -0.093 |
| 12 | -0.035 | -0.101 |
| 16 | -0.024 | -0.040 |
| 24 <- retenu | +0.037 | -0.049 |
| 32 | +0.035 | -0.040 |
| 48 | +0.023 | -0.039 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.108 [-0.21 ; -0.01] | +0.013 [-0.08 ; +0.10] |
| break-even à +1R | -0.039 [-0.12 ; +0.04] | -0.008 [-0.06 ; +0.03] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | -0.129 [-0.29 ; +0.02] | -0.011 [-0.17 ; +0.14] |
| suiveur 1 ATR | -0.112 [-0.28 ; +0.04] | +0.000 [-0.14 ; +0.13] |
| suiveur 1.5 ATR | -0.103 [-0.24 ; +0.03] | +0.005 [-0.13 ; +0.12] |
| suiveur 2 ATR | -0.114 [-0.25 ; +0.01] | -0.020 [-0.14 ; +0.09] |
| suiveur 3 ATR | -0.074 [-0.16 ; +0.01] | -0.006 [-0.06 ; +0.05] |

Gestion retenue : BE 1.5R : inutile ; suiveur 3 ATR : inutile.

**Plan final (stop 2.25 ATR, objectif 1.5R, BE -, suiveur -, sortie au temps 24 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 119 | 37 | +0.037 [-0.11 ; +0.20] | 46 % | -0.076 | +0.111 [-0.04 ; +0.27] | 0.103 | 1.01 | 1.01 | 0.474 |
| VAL_T | 119 | 36 | -0.115 [-0.28 ; +0.06] | 39 % | -0.077 | -0.045 [-0.20 ; +0.13] | 0.702 | 1.02 | 1.00 | 0.396 |
| VAL_NQ | 49 (n<50) | 18 | +0.110 [-0.17 ; +0.47] | 53 % | +0.012 | +0.092 [-0.19 ; +0.45] | 0.281 | 0.89 | 1.02 | 0.676 |
| NQ_avant | 0 | | | | | | | | | |
| VAL | 168 | 38 | -0.049 [-0.21 ; +0.11] | 43 % | -0.047 | -0.005 [-0.16 ; +0.16] | 0.515 | 0.98 | 1.00 | 0.528 |

Verdict : **ne bat pas le hasard** — confiance p=0.52 (profil MFE/MAE p=0.53).

### Cassure session/Monday

Coupure APPR/validation : 2026-06-19 (médiane des entrées MES). n : APPR 254 (42 j), VAL_T 255 (37 j), VAL_NQ 112 (20 j), NQ_avant 0 (0 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.12 | 1.15 | 1.02 | -0.05 | 1.16 | 1.11 | 0.96 | -0.17 |
| 8 | 1.52 | 1.64 | 1.08 | +0.06 | 1.74 | 1.50 | 0.87 | -0.36 |
| 12 | 1.84 | 2.04 | 1.11 | +0.05 | 2.14 | 1.87 | 0.87 | -0.32 |
| 16 | 2.14 | 2.43 | 1.13 | +0.12 | 2.56 | 2.13 | 0.83 | -0.50 |
| 24 | 2.68 | 3.14 | 1.17 | +0.27 | 3.27 | 2.68 | 0.82 | -0.56 |
| 32 | 3.12 | 3.52 | 1.13 | +0.23 | 3.80 | 3.10 | 0.82 | -0.59 |
| 48 | 3.70 | 4.15 | 1.12 | +0.29 | 4.65 | 3.72 | 0.80 | -0.91 |

**Instant du MFE sur 48 barres** — APPR : médiane 21 barres (q25 7, q75 36) ; atteint avant 8 barres : 27 %, avant 16 : 38 %. VAL : médiane 15.5 barres (q25 4, q75 38.25) ; atteint avant 8 barres : 38 %, avant 16 : 50 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 132 | 1.07 / 1.81 / 2.55 / 2.84 | 111 | 2.80 / 3.94 / 5.66 / 7.55 |
| VAL_T | 96 | 0.91 / 1.45 / 2.42 / 3.04 | 153 | 2.56 / 4.49 / 6.66 / 10.03 |
| VAL_NQ | 59 | 0.85 / 1.57 / 1.84 / 2.09 | 49 | 2.97 / 5.12 / 6.70 / 6.91 |
| VAL | 155 | 0.87 / 1.48 / 2.27 / 2.87 | 202 | 2.69 / 4.52 / 6.72 / 9.55 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 11 % | 0 % | 6 % |
| 0.5 | 23 % | 1 % | 19 % |
| 0.75 | 36 % | 5 % | 41 % |
| 1 | 44 % | 9 % | 57 % |
| 1.25 | 57 % | 14 % | 70 % |
| 1.5 | 67 % | 18 % | 75 % |
| 1.75 | 73 % | 23 % | 83 % |
| 2 | 78 % | 27 % | 87 % |
| 2.25 | 82 % | 32 % | 90 % |
| 2.5 | 89 % | 42 % | 93 % |
| 2.75 <- retenu | 92 % | 49 % | 94 % |
| 3 | 95 % | 57 % | 95 % |
| 3.25 | 97 % | 67 % | 97 % |
| 3.5 | 98 % | 71 % | 97 % |
| 3.75 | 99 % | 73 % | 98 % |
| 4 | 100 % | 76 % | 99 % |

**Espérance vs taille du stop** (objectif 1R, 24 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.063 | -0.911 | -0.266 | -0.228 |
| 0.5 | -0.508 | -0.449 | -0.254 | -0.225 |
| 0.75 | -0.320 | -0.251 | -0.240 | -0.189 |
| 1 | -0.283 | -0.122 | -0.283 | -0.122 |
| 1.25 | -0.214 | -0.126 | -0.268 | -0.157 |
| 1.5 | -0.124 | -0.153 | -0.187 | -0.229 |
| 1.75 | -0.072 | -0.129 | -0.125 | -0.226 |
| 2 | -0.067 | -0.136 | -0.135 | -0.271 |
| 2.25 | -0.069 | -0.132 | -0.156 | -0.297 |
| 2.5 | -0.001 | -0.099 | -0.003 | -0.248 |
| 2.75 <- retenu | +0.008 | -0.117 | +0.021 | -0.321 |
| 3 | +0.033 | -0.133 | +0.098 | -0.399 |
| 3.25 | +0.029 | -0.128 | +0.095 | -0.417 |
| 3.5 | +0.049 | -0.136 | +0.173 | -0.478 |
| 3.75 | +0.044 | -0.126 | +0.165 | -0.473 |
| 4 | +0.047 | -0.123 | +0.186 | -0.490 |

**Espérance (R nets) vs objectif**, stop 2.75 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.042 | -0.075 |
| 0.75R | -0.029 | -0.106 |
| 1R <- retenu | -0.022 | -0.118 |
| 1.25R | -0.050 | -0.170 |
| 1.5R | -0.054 | -0.152 |
| 2R | -0.093 | -0.167 |
| 2.5R | -0.090 | -0.153 |
| 3R | -0.125 | -0.150 |
| 4R | -0.137 | -0.154 |
| 6R | -0.134 | -0.187 |
| aucun (temps) | -0.132 | -0.177 |

**Espérance vs durée maximale de détention** (stop 2.75 ATR, objectif 1R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.040 | -0.026 |
| 4 | -0.024 | -0.025 |
| 8 | -0.017 | -0.071 |
| 12 | -0.019 | -0.081 |
| 16 | +0.004 | -0.091 |
| 24 <- retenu | +0.008 | -0.117 |
| 32 | -0.016 | -0.126 |
| 48 | -0.022 | -0.118 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.070 [-0.15 ; +0.00] | +0.021 [-0.03 ; +0.07] |
| break-even à +1R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | -0.080 [-0.20 ; +0.04] | +0.076 [-0.04 ; +0.19] |
| suiveur 1 ATR | -0.067 [-0.19 ; +0.04] | +0.055 [-0.07 ; +0.17] |
| suiveur 1.5 ATR | -0.083 [-0.20 ; +0.03] | +0.036 [-0.07 ; +0.14] |
| suiveur 2 ATR | -0.102 [-0.22 ; +0.01] | +0.037 [-0.04 ; +0.12] |
| suiveur 3 ATR | -0.048 [-0.11 ; +0.01] | -0.009 [-0.05 ; +0.03] |

Gestion retenue : BE 1R : adopté en APPR, NON confirmé en validation ; suiveur 3 ATR : inutile.

**Plan final (stop 2.75 ATR, objectif 1R, BE 1R, suiveur -, sortie au temps 24 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 254 | 42 | +0.008 [-0.12 ; +0.14] | 52 % | -0.050 | +0.059 [-0.07 ; +0.19] | 0.167 | 1.13 | 1.00 | 0.101 |
| VAL_T | 255 | 37 | -0.192 [-0.32 ; -0.06] | 42 % | -0.058 | -0.134 [-0.26 ; -0.00] | 0.995 | 0.75 | 1.00 | 0.996 |
| VAL_NQ | 112 | 20 | +0.054 [-0.11 ; +0.23] | 51 % | -0.007 | +0.063 [-0.10 ; +0.24] | 0.233 | 1.06 | 1.00 | 0.319 |
| NQ_avant | 0 | | | | | | | | | |
| VAL | 367 | 37 | -0.117 [-0.23 ; -0.00] | 45 % | -0.044 | -0.073 [-0.19 ; +0.04] | 0.951 | 0.83 | 1.00 | 0.988 |

Verdict : **ne bat pas le hasard** — confiance p=0.95 (profil MFE/MAE p=0.99).

### Rebond Detector

Coupure APPR/validation : 2026-09-30 (médiane des entrées MES). n : APPR 155 (11 j), VAL_T 155 (12 j), VAL_NQ 127 (12 j), NQ_avant 118 (9 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.05 | 1.06 | 1.01 | -0.22 | 1.10 | 1.03 | 0.93 | -0.22 |
| 8 | 1.46 | 1.78 | 1.22 | +0.01 | 1.63 | 1.48 | 0.91 | -0.33 |
| 12 | 1.77 | 2.26 | 1.28 | +0.18 | 2.11 | 1.78 | 0.84 | -0.53 |
| 16 | 2.18 | 2.79 | 1.28 | +0.08 | 2.53 | 2.05 | 0.81 | -0.66 |
| 24 | 2.83 | 4.41 | 1.56 | +0.82 | 3.30 | 2.49 | 0.76 | -0.87 |
| 32 | 3.45 | 5.50 | 1.59 | +1.23 | 3.93 | 2.81 | 0.71 | -0.97 |
| 48 | 4.07 | 7.28 | 1.79 | +1.97 | 4.84 | 3.84 | 0.79 | -1.03 |

**Instant du MFE sur 48 barres** — APPR : médiane 23 barres (q25 9, q75 35) ; atteint avant 8 barres : 23 %, avant 16 : 38 %. VAL : médiane 10 barres (q25 4, q75 38) ; atteint avant 8 barres : 44 %, avant 16 : 57 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 72 | 0.99 / 1.64 / 2.33 / 2.55 | 83 | 2.32 / 4.06 / 5.94 / 6.96 |
| VAL_T | 57 | 0.56 / 0.92 / 2.27 / 2.59 | 98 | 2.87 / 5.39 / 6.90 / 7.62 |
| VAL_NQ | 43 | 0.97 / 1.52 / 2.31 / 3.22 | 81 | 2.62 / 4.88 / 6.19 / 7.28 |
| VAL | 100 | 0.68 / 1.36 / 2.33 / 2.65 | 179 | 2.74 / 5.23 / 6.82 / 7.61 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 14 % | 0 % | 22 % |
| 0.5 | 29 % | 1 % | 37 % |
| 0.75 | 38 % | 4 % | 54 % |
| 1 | 50 % | 11 % | 67 % |
| 1.25 | 67 % | 24 % | 72 % |
| 1.5 | 74 % | 30 % | 80 % |
| 1.75 | 75 % | 37 % | 85 % |
| 2 | 79 % | 43 % | 86 % |
| 2.25 | 86 % | 48 % | 88 % |
| 2.5 <- retenu | 93 % | 54 % | 92 % |
| 2.75 | 96 % | 59 % | 95 % |
| 3 | 99 % | 63 % | 95 % |
| 3.25 | 99 % | 67 % | 96 % |
| 3.5 | 100 % | 67 % | 98 % |
| 3.75 | 100 % | 71 % | 98 % |
| 4 | 100 % | 73 % | 99 % |

**Espérance vs taille du stop** (objectif 2R, 48 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -0.957 | -0.618 | -0.239 | -0.155 |
| 0.5 | -0.466 | -0.309 | -0.233 | -0.155 |
| 0.75 | -0.328 | -0.264 | -0.246 | -0.198 |
| 1 | -0.055 | -0.286 | -0.055 | -0.286 |
| 1.25 | +0.157 | -0.309 | +0.196 | -0.386 |
| 1.5 | +0.263 | -0.372 | +0.394 | -0.558 |
| 1.75 | +0.340 | -0.372 | +0.595 | -0.652 |
| 2 | +0.371 | -0.376 | +0.742 | -0.752 |
| 2.25 | +0.394 | -0.323 | +0.887 | -0.728 |
| 2.5 <- retenu | +0.371 | -0.268 | +0.928 | -0.671 |
| 2.75 | +0.284 | -0.241 | +0.780 | -0.662 |
| 3 | +0.186 | -0.233 | +0.557 | -0.699 |
| 3.25 | +0.157 | -0.216 | +0.509 | -0.703 |
| 3.5 | +0.112 | -0.202 | +0.393 | -0.708 |
| 3.75 | +0.056 | -0.189 | +0.210 | -0.709 |
| 4 | +0.005 | -0.177 | +0.019 | -0.710 |

**Espérance (R nets) vs objectif**, stop 2.5 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.030 | -0.217 |
| 0.75R | +0.048 | -0.261 |
| 1R | +0.095 | -0.298 |
| 1.25R | +0.226 | -0.339 |
| 1.5R | +0.338 | -0.314 |
| 2R <- retenu | +0.371 | -0.268 |
| 2.5R | +0.263 | -0.292 |
| 3R | +0.140 | -0.263 |
| 4R | +0.024 | -0.228 |
| 6R | +0.194 | -0.202 |
| aucun (temps) | +0.238 | -0.232 |

**Espérance vs durée maximale de détention** (stop 2.5 ATR, objectif 2R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.064 | -0.034 |
| 4 | -0.055 | -0.083 |
| 8 | +0.071 | -0.097 |
| 12 | +0.150 | -0.168 |
| 16 | +0.180 | -0.186 |
| 24 | +0.316 | -0.245 |
| 32 | +0.370 | -0.258 |
| 48 <- retenu | +0.371 | -0.268 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.090 [-0.28 ; +0.09] | +0.091 [-0.02 ; +0.18] |
| break-even à +1R | -0.056 [-0.16 ; +0.00] | +0.004 [-0.05 ; +0.06] |
| break-even à +1.5R | +0.022 [-0.07 ; +0.12] | -0.004 [-0.04 ; +0.02] |
| suiveur 0.5 ATR | -0.462 [-1.01 ; +0.13] | +0.233 [-0.02 ; +0.45] |
| suiveur 1 ATR | -0.445 [-0.96 ; +0.11] | +0.226 [+0.02 ; +0.40] |
| suiveur 1.5 ATR | -0.344 [-0.78 ; +0.12] | +0.195 [+0.03 ; +0.34] |
| suiveur 2 ATR | -0.240 [-0.54 ; +0.08] | +0.129 [-0.00 ; +0.24] |
| suiveur 3 ATR | -0.085 [-0.24 ; +0.06] | +0.047 [-0.03 ; +0.11] |

Gestion retenue : BE 1.5R : adopté en APPR, NON confirmé en validation ; suiveur 3 ATR : inutile.

**Plan final (stop 2.5 ATR, objectif 2R, BE 1.5R, suiveur -, sortie au temps 48 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 155 | 11 | +0.393 [-0.23 ; +0.94] | 50 % | +0.014 | +0.389 [-0.24 ; +0.94] | 0.105 | 1.28 | 1.02 | 0.032 |
| VAL_T | 155 | 12 | -0.178 [-0.48 ; +0.26] | 30 % | -0.046 | -0.129 [-0.43 ; +0.31] | 0.914 | 0.90 | 1.07 | 0.888 |
| VAL_NQ | 127 | 12 | -0.388 [-0.61 ; -0.15] | 22 % | +0.073 | -0.462 [-0.67 ; -0.25] | 1.000 | 0.69 | 0.93 | 0.986 |
| NQ_avant | 118 | 9 | +0.026 [-0.29 ; +0.36] | 40 % | -0.038 | +0.065 [-0.26 ; +0.40] | 0.352 | 0.96 | 0.99 | 0.536 |
| VAL | 282 | 13 | -0.273 [-0.49 ; -0.01] | 26 % | +0.006 | -0.279 [-0.49 ; -0.02] | 1.000 | 0.81 | 1.00 | 0.983 |

Verdict : **PIRE que le hasard** — confiance élevée (p=0.018).

### Aléatoire (référence)

Coupure APPR/validation : 2026-06-18 (médiane des entrées MES). n : APPR 3146 (43 j), VAL_T 3147 (42 j), VAL_NQ 1660 (22 j), NQ_avant 0 (0 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.05 | 1.00 | 0.96 | -0.17 | 1.02 | 1.05 | 1.03 | -0.09 |
| 8 | 1.50 | 1.45 | 0.97 | -0.20 | 1.50 | 1.52 | 1.02 | -0.09 |
| 12 | 1.90 | 1.80 | 0.95 | -0.21 | 1.90 | 1.91 | 1.00 | -0.11 |
| 16 | 2.23 | 2.13 | 0.95 | -0.18 | 2.27 | 2.25 | 0.99 | -0.16 |
| 24 | 2.79 | 2.78 | 1.00 | -0.08 | 2.92 | 2.87 | 0.98 | -0.18 |
| 32 | 3.32 | 3.34 | 1.01 | -0.06 | 3.53 | 3.41 | 0.97 | -0.25 |
| 48 | 4.17 | 4.22 | 1.01 | -0.05 | 4.48 | 4.37 | 0.97 | -0.22 |

**Instant du MFE sur 48 barres** — APPR : médiane 26 barres (q25 7, q75 41) ; atteint avant 8 barres : 27 %, avant 16 : 38 %. VAL : médiane 23 barres (q25 7, q75 41) ; atteint avant 8 barres : 29 %, avant 16 : 42 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 1393 | 0.84 / 1.54 / 2.38 / 2.95 | 1648 | 2.46 / 4.04 / 6.09 / 8.28 |
| VAL_T | 1426 | 0.79 / 1.40 / 2.21 / 3.02 | 1586 | 2.51 / 4.19 / 6.68 / 8.28 |
| VAL_NQ | 807 | 0.76 / 1.32 / 1.98 / 2.60 | 793 | 2.77 / 4.67 / 6.79 / 8.24 |
| VAL | 2233 | 0.78 / 1.37 / 2.12 / 2.89 | 2379 | 2.64 / 4.35 / 6.75 / 8.27 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 16 % | 0 % | 14 % |
| 0.5 | 34 % | 2 % | 31 % |
| 0.75 | 46 % | 4 % | 49 % |
| 1 | 58 % | 9 % | 62 % |
| 1.25 | 67 % | 16 % | 71 % |
| 1.5 | 74 % | 23 % | 79 % |
| 1.75 | 81 % | 31 % | 84 % |
| 2 | 84 % | 39 % | 89 % |
| 2.25 | 88 % | 44 % | 91 % |
| 2.5 <- retenu | 92 % | 51 % | 93 % |
| 2.75 | 93 % | 56 % | 94 % |
| 3 | 95 % | 61 % | 95 % |
| 3.25 | 96 % | 66 % | 96 % |
| 3.5 | 97 % | 70 % | 97 % |
| 3.75 | 97 % | 72 % | 97 % |
| 4 | 98 % | 74 % | 98 % |

**Espérance vs taille du stop** (objectif 3R, 48 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -0.728 | -0.649 | -0.182 | -0.162 |
| 0.5 | -0.349 | -0.287 | -0.175 | -0.144 |
| 0.75 | -0.284 | -0.089 | -0.213 | -0.067 |
| 1 | -0.243 | -0.017 | -0.243 | -0.017 |
| 1.25 | -0.194 | -0.006 | -0.243 | -0.007 |
| 1.5 | -0.150 | -0.013 | -0.225 | -0.020 |
| 1.75 | -0.104 | +0.000 | -0.183 | +0.001 |
| 2 | -0.094 | -0.009 | -0.189 | -0.018 |
| 2.25 | -0.061 | -0.009 | -0.137 | -0.021 |
| 2.5 <- retenu | -0.040 | -0.031 | -0.099 | -0.078 |
| 2.75 | -0.029 | -0.043 | -0.081 | -0.119 |
| 3 | -0.033 | -0.036 | -0.098 | -0.108 |
| 3.25 | -0.027 | -0.040 | -0.089 | -0.131 |
| 3.5 | -0.029 | -0.040 | -0.101 | -0.140 |
| 3.75 | -0.039 | -0.037 | -0.147 | -0.138 |
| 4 | -0.044 | -0.041 | -0.175 | -0.165 |

**Espérance (R nets) vs objectif**, stop 2.5 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.064 | -0.047 |
| 0.75R | -0.070 | -0.049 |
| 1R | -0.082 | -0.034 |
| 1.25R | -0.079 | -0.029 |
| 1.5R | -0.066 | -0.035 |
| 2R | -0.048 | -0.030 |
| 2.5R | -0.042 | -0.030 |
| 3R <- retenu | -0.040 | -0.031 |
| 4R | -0.057 | -0.030 |
| 6R | -0.071 | -0.013 |
| aucun (temps) | -0.061 | -0.002 |

**Espérance vs durée maximale de détention** (stop 2.5 ATR, objectif 3R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.063 | -0.030 |
| 4 | -0.068 | -0.029 |
| 8 | -0.072 | -0.018 |
| 12 | -0.072 | -0.014 |
| 16 | -0.069 | -0.016 |
| 24 | -0.059 | -0.021 |
| 32 | -0.055 | -0.027 |
| 48 <- retenu | -0.040 | -0.031 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.049 [-0.15 ; +0.04] | +0.014 [-0.05 ; +0.08] |
| break-even à +1R | -0.023 [-0.09 ; +0.04] | +0.038 [+0.01 ; +0.07] |
| break-even à +1.5R | -0.002 [-0.04 ; +0.03] | +0.025 [+0.01 ; +0.04] |
| suiveur 0.5 ATR | -0.025 [-0.15 ; +0.09] | -0.010 [-0.12 ; +0.10] |
| suiveur 1 ATR | -0.035 [-0.16 ; +0.09] | -0.006 [-0.12 ; +0.11] |
| suiveur 1.5 ATR | -0.058 [-0.18 ; +0.06] | +0.012 [-0.11 ; +0.13] |
| suiveur 2 ATR | -0.083 [-0.21 ; +0.04] | +0.001 [-0.11 ; +0.10] |
| suiveur 3 ATR | -0.070 [-0.17 ; +0.02] | +0.027 [-0.04 ; +0.09] |

Gestion retenue : BE 1.5R : inutile ; suiveur 0.5 ATR : inutile.

**Plan final (stop 2.5 ATR, objectif 3R, BE -, suiveur -, sortie au temps 48 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 3146 | 43 | -0.040 [-0.16 ; +0.08] | 37 % | -0.027 | -0.016 [-0.13 ; +0.11] | 0.696 | 0.95 | 1.00 | 0.966 |
| VAL_T | 3147 | 42 | -0.104 [-0.21 ; +0.01] | 36 % | -0.100 | -0.006 [-0.12 ; +0.10] | 0.535 | 0.97 | 1.00 | 0.850 |
| VAL_NQ | 1660 | 22 | +0.107 [-0.02 ; +0.25] | 39 % | +0.106 | +0.004 [-0.12 ; +0.15] | 0.500 | 1.02 | 0.99 | 0.230 |
| NQ_avant | 0 | | | | | | | | | |
| VAL | 4807 | 42 | -0.031 [-0.14 ; +0.08] | 37 % | -0.029 | -0.002 [-0.11 ; +0.11] | 0.541 | 0.99 | 1.00 | 0.623 |

Verdict : **ne bat pas le hasard** — confiance p=0.54 (profil MFE/MAE p=0.62).

