# Étude du stop et de la sortie par MAE/MFE

Généré le 2026-10-15 19:01. Unités : 5, 15, 30, 60 min. Sources : cache commun du projet.

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
| MES | 5 | 2026-10-07 | 2026-10-15 | 1704 |
| MES (sans volume : ni climax ni Detector) | 15 | 2026-04-29 | 2026-07-07 | 4498 |
| MES | 15 | 2026-09-15 | 2026-10-15 | 2068 |
| MES | 30 | 2026-09-14 | 2026-10-15 | 1063 |
| MES | 60 | 2026-08-13 | 2026-10-15 | 1039 |
| NQ | 5 | 2026-10-07 | 2026-10-12 | 970 |
| NQ | 5 | 2026-10-13 | 2026-10-15 | 641 |
| NQ | 15 | 2026-09-18 | 2026-10-15 | 1780 |
| NQ | 30 | 2026-09-11 | 2026-10-15 | 1113 |
| NQ | 60 | 2026-08-13 | 2026-10-15 | 1039 |

**Contrôle de la reconstitution des vrais prix (API 15 min, vrais prix connus)** : 2364 barres x 2 sens, horizon 16 barres : erreur MAE médiane 0.07 ATR (biais +0.00), MFE médiane 0.07 ATR (biais +0.00) ; plan stop 1,5 ATR / objectif 2R : E[R] vrais prix +0.030 vs reconstitués +0.030, même issue (gain/perte) dans 98 % des trades.


## Synthèse

| Déclencheur | n APPR / VAL | Stop (ATR) | Objectif | BE / suiveur | Durée (barres) | E[R] APPR | E[R] VAL [IC 95 %] | Hasard VAL | p | e-ratio VAL / hasard | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Flèche Fort | 99 / 191 | 3 (garde 91 %) | 1R | - / -  | 8 | -0.02 | -0.07 [-0.17 ; +0.03] | -0.03 | 0.794 | 0.94 / 1.04 | ne bat pas le hasard, p=0.79 (profil MFE/MAE p=0.77) |
| Flèche Fort+Moyen | 99 / 192 | 3 (garde 91 %) | 1R | - / -  | 8 | -0.02 | -0.07 [-0.16 ; +0.03] | -0.03 | 0.763 | 0.97 / 1.04 | ne bat pas le hasard, p=0.76 (profil MFE/MAE p=0.69) |
| Cassure de trendline | 80 / 148 | 3.75 (garde 92 %) | 1R | - / -  | 48 | +0.04 | +0.08 [-0.09 ; +0.27] | -0.02 | 0.143 | 1.27 / 1.05 | ne bat pas le hasard, p=0.14 (profil MFE/MAE p=0.06) |
| Climax BUY | 87 / 169 | 2.5 (garde 92 %) | aucun (temps) | - / -  | 32 | +0.46 | -0.11 [-0.54 ; +0.35] | -0.18 | 0.472 | 0.65 / 0.72 | ne bat pas le hasard, p=0.47 (profil MFE/MAE p=0.81) |
| Climax SELL | 34 (n<50) / 58 | 2.75 (garde 91 %) | 0.5R | - / 2 ATR (non confirmé) | 8 | -0.16 | +0.18 [-0.12 ; +0.32] | -0.04 | 0.081 | 2.60 / 1.38 | non concluant (VAL > hasard mais APPR < hasard : effet de régime), faible (p VAL=0.081) |
| Changement Heishinator | 182 / 356 | 2.75 (garde 92 %) | 1.25R | - / -  | 48 | -0.02 | +0.01 [-0.12 ; +0.14] | -0.03 | 0.272 | 1.02 / 1.00 | ne bat pas le hasard, p=0.27 (profil MFE/MAE p=0.39) |
| Cassure session/Monday | 419 / 755 | 2.5 (garde 91 %) | 1R | 1R / - (non confirmé) | 48 | -0.01 | -0.05 [-0.20 ; +0.09] | -0.04 | 0.591 | 0.91 / 1.00 | ne bat pas le hasard, p=0.59 (profil MFE/MAE p=0.93) |
| Rebond Detector | 407 / 725 | 2.5 (garde 93 %) | aucun (temps) | 1.5R / - (oui) | 48 | +0.22 | -0.07 [-0.17 ; +0.03] | +0.02 | 0.994 | 0.98 / 0.99 | ne bat pas le hasard, p=0.99 (profil MFE/MAE p=0.58) |
| Aléatoire (référence) | 4862 / 9309 | 2.5 (garde 92 %) | 0.5R | - / -  | 8 | -0.05 | -0.05 [-0.07 ; -0.03] | -0.06 | 0.210 | 0.99 / 1.00 | ne bat pas le hasard, p=0.21 (profil MFE/MAE p=0.67) |

La ligne « Aléatoire » est la référence elle-même (son p ne mesure que le bruit des tirages).

E[R] = espérance nette de coûts par trade, en R (R = distance du stop). e-ratio = MFE/MAE moyens à 16 barres.

## Détail par déclencheur

### Flèche Fort

Coupure APPR/validation : 2026-07-06 (médiane des entrées MES). n : APPR 99 (43 j), VAL_T 100 (31 j), VAL_NQ 91 (26 j), NQ_avant 0 (0 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.30 | 1.12 | 0.86 | -0.06 | 1.22 | 1.26 | 1.03 | -0.12 |
| 8 | 1.78 | 1.57 | 0.88 | -0.14 | 1.75 | 1.60 | 0.92 | -0.33 |
| 12 | 2.20 | 1.79 | 0.81 | -0.38 | 2.15 | 1.96 | 0.91 | -0.39 |
| 16 | 2.46 | 2.14 | 0.87 | -0.34 | 2.45 | 2.30 | 0.94 | -0.21 |
| 24 | 3.02 | 2.58 | 0.85 | -0.66 | 2.97 | 2.79 | 0.94 | -0.34 |
| 32 | 3.50 | 3.14 | 0.90 | -0.58 | 3.38 | 3.26 | 0.97 | -0.16 |
| 48 | 3.80 | 3.37 | 0.89 | -0.39 | 3.96 | 4.13 | 1.04 | -0.01 |

**Instant du MFE sur 48 barres** — APPR : médiane 19 barres (q25 7, q75 36) ; atteint avant 8 barres : 32 %, avant 16 : 48 %. VAL : médiane 20.5 barres (q25 5, q75 38) ; atteint avant 8 barres : 33 %, avant 16 : 48 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 47 | 1.18 / 1.81 / 2.53 / 3.62 | 47 | 3.05 / 4.68 / 6.71 / 7.19 |
| VAL_T | 39 | 0.77 / 1.29 / 2.38 / 2.93 | 54 | 3.01 / 4.84 / 6.83 / 8.19 |
| VAL_NQ | 46 | 1.13 / 1.95 / 2.67 / 2.82 | 36 | 2.74 / 4.16 / 5.51 / 8.00 |
| VAL | 85 | 1.00 / 1.74 / 2.67 / 2.91 | 90 | 2.88 / 4.45 / 6.47 / 8.28 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 6 % | 0 % | 7 % |
| 0.5 | 19 % | 0 % | 16 % |
| 0.75 | 34 % | 2 % | 38 % |
| 1 | 47 % | 4 % | 51 % |
| 1.25 | 55 % | 6 % | 64 % |
| 1.5 | 62 % | 19 % | 71 % |
| 1.75 | 72 % | 21 % | 75 % |
| 2 | 83 % | 28 % | 81 % |
| 2.25 | 87 % | 30 % | 87 % |
| 2.5 | 89 % | 38 % | 88 % |
| 2.75 | 89 % | 43 % | 92 % |
| 3 <- retenu | 91 % | 49 % | 98 % |
| 3.25 | 94 % | 51 % | 99 % |
| 3.5 | 94 % | 57 % | 99 % |
| 3.75 | 94 % | 60 % | 99 % |
| 4 | 96 % | 62 % | 99 % |

**Espérance vs taille du stop** (objectif 1R, 8 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.053 | -1.000 | -0.263 | -0.250 |
| 0.5 | -0.501 | -0.514 | -0.251 | -0.257 |
| 0.75 | -0.365 | -0.266 | -0.274 | -0.200 |
| 1 | -0.282 | -0.195 | -0.282 | -0.195 |
| 1.25 | -0.207 | -0.111 | -0.259 | -0.138 |
| 1.5 | -0.200 | -0.072 | -0.300 | -0.108 |
| 1.75 | -0.165 | -0.097 | -0.289 | -0.169 |
| 2 | -0.120 | -0.117 | -0.240 | -0.234 |
| 2.25 | -0.081 | -0.085 | -0.182 | -0.192 |
| 2.5 | -0.045 | -0.094 | -0.112 | -0.234 |
| 2.75 | -0.052 | -0.094 | -0.144 | -0.258 |
| 3 <- retenu | -0.024 | -0.072 | -0.073 | -0.216 |
| 3.25 | -0.024 | -0.072 | -0.078 | -0.233 |
| 3.5 | -0.040 | -0.063 | -0.141 | -0.221 |
| 3.75 | -0.045 | -0.058 | -0.169 | -0.219 |
| 4 | -0.044 | -0.064 | -0.176 | -0.255 |

**Espérance (R nets) vs objectif**, stop 3 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.145 | +0.009 |
| 0.75R | -0.142 | +0.000 |
| 1R <- retenu | -0.112 | -0.032 |
| 1.25R | -0.220 | -0.046 |
| 1.5R | -0.240 | -0.049 |
| 2R | -0.276 | -0.011 |
| 2.5R | -0.301 | +0.015 |
| 3R | -0.331 | +0.032 |
| 4R | -0.318 | +0.039 |
| 6R | -0.307 | +0.053 |
| aucun (temps) | -0.276 | +0.053 |

**Espérance vs durée maximale de détention** (stop 3 ATR, objectif 1R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.078 | -0.020 |
| 4 | -0.028 | -0.020 |
| 8 <- retenu | -0.024 | -0.072 |
| 12 | -0.079 | -0.071 |
| 16 | -0.095 | -0.046 |
| 24 | -0.116 | -0.046 |
| 32 | -0.106 | -0.039 |
| 48 | -0.112 | -0.032 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.049 [-0.09 ; -0.01] | +0.022 [-0.01 ; +0.05] |
| break-even à +1R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | -0.062 [-0.16 ; +0.03] | +0.038 [-0.06 ; +0.14] |
| suiveur 1 ATR | -0.047 [-0.14 ; +0.03] | +0.036 [-0.05 ; +0.13] |
| suiveur 1.5 ATR | -0.060 [-0.16 ; +0.03] | +0.047 [-0.01 ; +0.11] |
| suiveur 2 ATR | -0.089 [-0.18 ; -0.01] | +0.026 [-0.01 ; +0.06] |
| suiveur 3 ATR | -0.023 [-0.08 ; +0.02] | -0.003 [-0.03 ; +0.02] |

Gestion retenue : BE 1R : inutile ; suiveur 3 ATR : inutile.

**Plan final (stop 3 ATR, objectif 1R, BE -, suiveur -, sortie au temps 8 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 99 | 43 | -0.024 [-0.12 ; +0.09] | 48 % | -0.046 | +0.020 [-0.08 ; +0.13] | 0.354 | 0.87 | 1.01 | 0.823 |
| VAL_T | 100 | 31 | -0.130 [-0.24 ; -0.02] | 37 % | -0.064 | -0.063 [-0.17 ; +0.04] | 0.872 | 0.83 | 1.05 | 0.898 |
| VAL_NQ | 91 | 26 | -0.009 [-0.15 ; +0.14] | 45 % | -0.002 | -0.005 [-0.14 ; +0.14] | 0.546 | 1.09 | 1.04 | 0.363 |
| NQ_avant | 0 | | | | | | | | | |
| VAL | 191 | 34 | -0.072 [-0.17 ; +0.03] | 41 % | -0.035 | -0.035 [-0.13 ; +0.07] | 0.794 | 0.94 | 1.04 | 0.773 |

Verdict : **ne bat pas le hasard** — confiance p=0.79 (profil MFE/MAE p=0.77).

### Flèche Fort+Moyen

Coupure APPR/validation : 2026-07-06 (médiane des entrées MES). n : APPR 99 (43 j), VAL_T 100 (31 j), VAL_NQ 92 (26 j), NQ_avant 0 (0 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.30 | 1.12 | 0.86 | -0.06 | 1.22 | 1.27 | 1.04 | -0.11 |
| 8 | 1.78 | 1.57 | 0.88 | -0.14 | 1.74 | 1.64 | 0.94 | -0.29 |
| 12 | 2.20 | 1.79 | 0.81 | -0.38 | 2.15 | 2.00 | 0.93 | -0.34 |
| 16 | 2.46 | 2.14 | 0.87 | -0.34 | 2.44 | 2.36 | 0.97 | -0.14 |
| 24 | 3.02 | 2.58 | 0.85 | -0.66 | 2.96 | 2.85 | 0.97 | -0.27 |
| 32 | 3.50 | 3.14 | 0.90 | -0.58 | 3.38 | 3.26 | 0.97 | -0.16 |
| 48 | 3.80 | 3.37 | 0.89 | -0.39 | 3.96 | 4.13 | 1.04 | -0.01 |

**Instant du MFE sur 48 barres** — APPR : médiane 19 barres (q25 7, q75 36) ; atteint avant 8 barres : 32 %, avant 16 : 48 %. VAL : médiane 20.5 barres (q25 5, q75 38) ; atteint avant 8 barres : 33 %, avant 16 : 48 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 47 | 1.18 / 1.81 / 2.53 / 3.62 | 47 | 3.05 / 4.68 / 6.71 / 7.19 |
| VAL_T | 39 | 0.77 / 1.29 / 2.38 / 2.93 | 54 | 3.01 / 4.84 / 6.83 / 8.19 |
| VAL_NQ | 47 | 1.13 / 1.93 / 2.67 / 2.81 | 36 | 2.74 / 4.16 / 5.51 / 8.00 |
| VAL | 86 | 0.99 / 1.71 / 2.67 / 2.91 | 90 | 2.88 / 4.45 / 6.47 / 8.28 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 6 % | 0 % | 7 % |
| 0.5 | 19 % | 0 % | 16 % |
| 0.75 | 34 % | 2 % | 37 % |
| 1 | 47 % | 4 % | 51 % |
| 1.25 | 55 % | 6 % | 64 % |
| 1.5 | 62 % | 19 % | 71 % |
| 1.75 | 72 % | 21 % | 76 % |
| 2 | 83 % | 28 % | 81 % |
| 2.25 | 87 % | 30 % | 87 % |
| 2.5 | 89 % | 38 % | 88 % |
| 2.75 | 89 % | 43 % | 92 % |
| 3 <- retenu | 91 % | 49 % | 98 % |
| 3.25 | 94 % | 51 % | 99 % |
| 3.5 | 94 % | 57 % | 99 % |
| 3.75 | 94 % | 60 % | 99 % |
| 4 | 96 % | 62 % | 99 % |

**Espérance vs taille du stop** (objectif 1R, 8 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.053 | -1.000 | -0.263 | -0.250 |
| 0.5 | -0.501 | -0.506 | -0.251 | -0.253 |
| 0.75 | -0.365 | -0.260 | -0.274 | -0.195 |
| 1 | -0.282 | -0.188 | -0.282 | -0.188 |
| 1.25 | -0.207 | -0.105 | -0.259 | -0.131 |
| 1.5 | -0.200 | -0.067 | -0.300 | -0.100 |
| 1.75 | -0.165 | -0.091 | -0.289 | -0.159 |
| 2 | -0.120 | -0.111 | -0.240 | -0.223 |
| 2.25 | -0.081 | -0.080 | -0.182 | -0.179 |
| 2.5 | -0.045 | -0.088 | -0.112 | -0.220 |
| 2.75 | -0.052 | -0.088 | -0.144 | -0.243 |
| 3 <- retenu | -0.024 | -0.067 | -0.073 | -0.200 |
| 3.25 | -0.024 | -0.066 | -0.078 | -0.215 |
| 3.5 | -0.040 | -0.058 | -0.141 | -0.201 |
| 3.75 | -0.045 | -0.053 | -0.169 | -0.198 |
| 4 | -0.044 | -0.058 | -0.176 | -0.233 |

**Espérance (R nets) vs objectif**, stop 3 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.145 | +0.011 |
| 0.75R | -0.142 | +0.004 |
| 1R <- retenu | -0.112 | -0.027 |
| 1.25R | -0.220 | -0.039 |
| 1.5R | -0.240 | -0.041 |
| 2R | -0.276 | -0.000 |
| 2.5R | -0.301 | +0.028 |
| 3R | -0.331 | +0.048 |
| 4R | -0.318 | +0.060 |
| 6R | -0.307 | +0.074 |
| aucun (temps) | -0.276 | +0.074 |

**Espérance vs durée maximale de détention** (stop 3 ATR, objectif 1R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.078 | -0.020 |
| 4 | -0.028 | -0.014 |
| 8 <- retenu | -0.024 | -0.067 |
| 12 | -0.079 | -0.066 |
| 16 | -0.095 | -0.040 |
| 24 | -0.116 | -0.040 |
| 32 | -0.106 | -0.034 |
| 48 | -0.112 | -0.027 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.049 [-0.09 ; -0.01] | +0.022 [-0.01 ; +0.05] |
| break-even à +1R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | -0.062 [-0.16 ; +0.03] | +0.032 [-0.07 ; +0.13] |
| suiveur 1 ATR | -0.047 [-0.14 ; +0.03] | +0.031 [-0.05 ; +0.13] |
| suiveur 1.5 ATR | -0.060 [-0.16 ; +0.03] | +0.040 [-0.02 ; +0.10] |
| suiveur 2 ATR | -0.089 [-0.18 ; -0.01] | +0.026 [-0.01 ; +0.06] |
| suiveur 3 ATR | -0.023 [-0.08 ; +0.02] | -0.003 [-0.03 ; +0.02] |

Gestion retenue : BE 1R : inutile ; suiveur 3 ATR : inutile.

**Plan final (stop 3 ATR, objectif 1R, BE -, suiveur -, sortie au temps 8 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 99 | 43 | -0.024 [-0.12 ; +0.09] | 48 % | -0.046 | +0.020 [-0.08 ; +0.13] | 0.354 | 0.87 | 1.01 | 0.823 |
| VAL_T | 100 | 31 | -0.130 [-0.24 ; -0.02] | 37 % | -0.064 | -0.063 [-0.17 ; +0.04] | 0.872 | 0.83 | 1.05 | 0.898 |
| VAL_NQ | 92 | 26 | +0.002 [-0.13 ; +0.14] | 46 % | -0.002 | +0.006 [-0.13 ; +0.14] | 0.475 | 1.15 | 1.04 | 0.245 |
| NQ_avant | 0 | | | | | | | | | |
| VAL | 192 | 34 | -0.067 [-0.16 ; +0.03] | 41 % | -0.035 | -0.030 [-0.13 ; +0.07] | 0.763 | 0.97 | 1.04 | 0.692 |

Verdict : **ne bat pas le hasard** — confiance p=0.76 (profil MFE/MAE p=0.69).

### Cassure de trendline

Coupure APPR/validation : 2026-09-16 (médiane des entrées MES). n : APPR 80 (43 j), VAL_T 80 (21 j), VAL_NQ 68 (20 j), NQ_avant 9 (8 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.34 | 1.18 | 0.88 | -0.23 | 1.04 | 1.35 | 1.30 | +0.00 |
| 8 | 1.97 | 1.68 | 0.85 | -0.21 | 1.61 | 1.87 | 1.16 | +0.01 |
| 12 | 2.27 | 2.21 | 0.97 | +0.12 | 1.95 | 2.36 | 1.21 | +0.20 |
| 16 | 2.51 | 2.65 | 1.06 | +0.09 | 2.15 | 2.74 | 1.27 | +0.25 |
| 24 | 3.18 | 3.36 | 1.06 | +0.07 | 2.59 | 3.50 | 1.35 | +0.59 |
| 32 | 3.88 | 3.77 | 0.97 | -0.24 | 3.14 | 4.15 | 1.32 | +0.44 |
| 48 | 4.36 | 4.66 | 1.07 | +0.28 | 4.07 | 4.95 | 1.22 | +0.71 |

**Instant du MFE sur 48 barres** — APPR : médiane 19.5 barres (q25 9, q75 37.75) ; atteint avant 8 barres : 24 %, avant 16 : 37 %. VAL : médiane 24.5 barres (q25 9.25, q75 41) ; atteint avant 8 barres : 24 %, avant 16 : 37 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 38 | 1.09 / 1.95 / 2.87 / 4.10 | 39 | 2.71 / 4.58 / 7.26 / 7.63 |
| VAL_T | 36 | 0.84 / 1.13 / 1.88 / 2.60 | 40 | 2.85 / 3.76 / 5.91 / 6.84 |
| VAL_NQ | 36 | 0.78 / 1.46 / 2.49 / 2.69 | 31 | 3.39 / 4.85 / 5.78 / 7.11 |
| VAL | 72 | 0.81 / 1.31 / 2.42 / 2.72 | 71 | 3.00 / 4.50 / 5.86 / 6.91 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 11 % | 0 % | 10 % |
| 0.5 | 13 % | 0 % | 24 % |
| 0.75 | 26 % | 0 % | 46 % |
| 1 | 39 % | 5 % | 61 % |
| 1.25 | 66 % | 10 % | 74 % |
| 1.5 | 66 % | 15 % | 81 % |
| 1.75 | 71 % | 21 % | 86 % |
| 2 | 76 % | 21 % | 88 % |
| 2.25 | 84 % | 38 % | 89 % |
| 2.5 | 87 % | 49 % | 90 % |
| 2.75 | 89 % | 51 % | 94 % |
| 3 | 89 % | 59 % | 99 % |
| 3.25 | 89 % | 64 % | 99 % |
| 3.5 | 89 % | 67 % | 100 % |
| 3.75 <- retenu | 92 % | 69 % | 100 % |
| 4 | 92 % | 69 % | 100 % |

**Espérance vs taille du stop** (objectif 1R, 48 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.082 | -1.038 | -0.270 | -0.259 |
| 0.5 | -0.603 | -0.438 | -0.302 | -0.219 |
| 0.75 | -0.269 | -0.184 | -0.202 | -0.138 |
| 1 | -0.252 | -0.050 | -0.252 | -0.050 |
| 1.25 | -0.176 | -0.009 | -0.220 | -0.012 |
| 1.5 | -0.180 | +0.074 | -0.270 | +0.112 |
| 1.75 | -0.092 | +0.050 | -0.161 | +0.088 |
| 2 | -0.128 | +0.072 | -0.255 | +0.143 |
| 2.25 | -0.087 | +0.086 | -0.195 | +0.193 |
| 2.5 | -0.041 | +0.081 | -0.101 | +0.203 |
| 2.75 | -0.093 | +0.073 | -0.254 | +0.200 |
| 3 | -0.015 | +0.084 | -0.045 | +0.252 |
| 3.25 | +0.002 | +0.081 | +0.007 | +0.264 |
| 3.5 | -0.007 | +0.081 | -0.025 | +0.283 |
| 3.75 <- retenu | +0.042 | +0.081 | +0.156 | +0.304 |
| 4 | +0.041 | +0.039 | +0.165 | +0.157 |

**Espérance (R nets) vs objectif**, stop 3.75 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.036 | +0.032 |
| 0.75R | -0.029 | +0.066 |
| 1R <- retenu | +0.042 | +0.081 |
| 1.25R | -0.029 | +0.027 |
| 1.5R | -0.099 | +0.087 |
| 2R | -0.120 | +0.102 |
| 2.5R | -0.149 | +0.079 |
| 3R | -0.158 | +0.087 |
| 4R | -0.149 | +0.107 |
| 6R | -0.124 | +0.104 |
| aucun (temps) | -0.120 | +0.104 |

**Espérance vs durée maximale de détention** (stop 3.75 ATR, objectif 1R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.051 | +0.034 |
| 4 | -0.060 | +0.015 |
| 8 | -0.068 | +0.013 |
| 12 | -0.035 | +0.055 |
| 16 | -0.031 | +0.074 |
| 24 | +0.038 | +0.083 |
| 32 | -0.017 | +0.055 |
| 48 <- retenu | +0.042 | +0.081 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.104 [-0.20 ; -0.01] | -0.083 [-0.17 ; +0.00] |
| break-even à +1R | -0.007 [-0.02 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | -0.097 [-0.28 ; +0.08] | -0.082 [-0.28 ; +0.09] |
| suiveur 1 ATR | -0.089 [-0.26 ; +0.08] | -0.085 [-0.28 ; +0.09] |
| suiveur 1.5 ATR | -0.109 [-0.29 ; +0.06] | -0.085 [-0.27 ; +0.08] |
| suiveur 2 ATR | -0.157 [-0.33 ; +0.01] | -0.088 [-0.27 ; +0.07] |
| suiveur 3 ATR | -0.115 [-0.25 ; +0.01] | -0.034 [-0.15 ; +0.07] |

Gestion retenue : BE 1.5R : inutile ; suiveur 1 ATR : inutile.

**Plan final (stop 3.75 ATR, objectif 1R, BE -, suiveur -, sortie au temps 48 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 80 | 43 | +0.042 [-0.14 ; +0.22] | 50 % | -0.035 | +0.074 [-0.11 ; +0.25] | 0.216 | 1.06 | 1.01 | 0.367 |
| VAL_T | 80 | 21 | -0.016 [-0.20 ; +0.20] | 49 % | -0.044 | +0.030 [-0.15 ; +0.24] | 0.411 | 1.20 | 1.05 | 0.198 |
| VAL_NQ | 68 | 20 | +0.195 [-0.03 ; +0.45] | 63 % | +0.005 | +0.190 [-0.04 ; +0.44] | 0.062 | 1.35 | 1.07 | 0.102 |
| NQ_avant | 9 (n<50) | 8 | +0.058 [-0.40 ; +0.54] | 56 % | -0.025 | +0.092 [-0.31 ; +0.58] | 0.388 | 1.26 | 1.10 | 0.282 |
| VAL | 148 | 21 | +0.081 [-0.09 ; +0.27] | 55 % | -0.021 | +0.103 [-0.07 ; +0.30] | 0.143 | 1.27 | 1.05 | 0.059 |

Verdict : **ne bat pas le hasard** — confiance p=0.14 (profil MFE/MAE p=0.06).

### Climax BUY

Coupure APPR/validation : 2026-09-30 (médiane des entrées MES). n : APPR 87 (19 j), VAL_T 89 (12 j), VAL_NQ 80 (11 j), NQ_avant 86 (22 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.17 | 1.36 | 1.16 | +0.14 | 1.40 | 1.02 | 0.73 | -0.35 |
| 8 | 1.68 | 1.93 | 1.15 | +0.24 | 2.14 | 1.36 | 0.64 | -0.79 |
| 12 | 1.89 | 2.25 | 1.19 | +0.61 | 2.63 | 1.65 | 0.63 | -0.88 |
| 16 | 2.41 | 2.60 | 1.08 | +0.62 | 3.00 | 1.94 | 0.65 | -0.92 |
| 24 | 2.71 | 3.48 | 1.28 | +0.87 | 3.54 | 2.61 | 0.74 | -0.76 |
| 32 | 3.41 | 4.28 | 1.26 | +1.67 | 3.90 | 2.88 | 0.74 | -0.90 |
| 48 | 3.93 | 5.27 | 1.34 | +1.93 | 5.15 | 3.52 | 0.68 | -1.41 |

**Instant du MFE sur 48 barres** — APPR : médiane 22.5 barres (q25 15, q75 41.75) ; atteint avant 8 barres : 19 %, avant 16 : 29 %. VAL : médiane 23 barres (q25 6, q75 41.5) ; atteint avant 8 barres : 30 %, avant 16 : 39 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 50 | 0.89 / 1.53 / 2.46 / 3.07 | 31 | 3.40 / 4.87 / 8.83 / 12.45 |
| VAL_T | 38 | 0.93 / 1.28 / 2.14 / 2.44 | 47 | 3.02 / 4.50 / 7.22 / 14.31 |
| VAL_NQ | 35 | 0.81 / 1.40 / 2.57 / 3.16 | 41 | 3.16 / 7.64 / 10.98 / 12.13 |
| VAL | 73 | 0.89 / 1.29 / 2.39 / 2.66 | 88 | 3.12 / 4.91 / 9.56 / 14.18 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 16 % | 0 % | 11 % |
| 0.5 | 30 % | 0 % | 26 % |
| 0.75 | 42 % | 3 % | 42 % |
| 1 | 60 % | 3 % | 59 % |
| 1.25 | 70 % | 13 % | 70 % |
| 1.5 | 74 % | 13 % | 81 % |
| 1.75 | 82 % | 16 % | 84 % |
| 2 | 82 % | 19 % | 86 % |
| 2.25 | 86 % | 32 % | 89 % |
| 2.5 <- retenu | 92 % | 32 % | 92 % |
| 2.75 | 92 % | 32 % | 96 % |
| 3 | 92 % | 35 % | 96 % |
| 3.25 | 96 % | 45 % | 97 % |
| 3.5 | 98 % | 52 % | 99 % |
| 3.75 | 98 % | 58 % | 100 % |
| 4 | 98 % | 61 % | 100 % |

**Espérance vs taille du stop** (objectif aucun (temps), 32 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -0.262 | -0.618 | -0.065 | -0.155 |
| 0.5 | +0.354 | -0.408 | +0.177 | -0.204 |
| 0.75 | +0.514 | -0.294 | +0.385 | -0.221 |
| 1 | +0.647 | -0.182 | +0.647 | -0.182 |
| 1.25 | +0.901 | -0.129 | +1.126 | -0.161 |
| 1.5 | +0.739 | -0.098 | +1.109 | -0.147 |
| 1.75 | +0.589 | -0.102 | +1.030 | -0.178 |
| 2 | +0.492 | -0.108 | +0.983 | -0.216 |
| 2.25 | +0.500 | -0.115 | +1.126 | -0.258 |
| 2.5 <- retenu | +0.458 | -0.106 | +1.145 | -0.266 |
| 2.75 | +0.386 | -0.093 | +1.061 | -0.255 |
| 3 | +0.343 | -0.108 | +1.029 | -0.324 |
| 3.25 | +0.328 | -0.104 | +1.064 | -0.337 |
| 3.5 | +0.315 | -0.091 | +1.104 | -0.319 |
| 3.75 | +0.293 | -0.090 | +1.100 | -0.338 |
| 4 | +0.275 | -0.089 | +1.099 | -0.354 |

**Espérance (R nets) vs objectif**, stop 2.5 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | +0.063 | -0.017 |
| 0.75R | +0.075 | -0.021 |
| 1R | +0.149 | -0.031 |
| 1.25R | +0.052 | -0.031 |
| 1.5R | +0.060 | -0.027 |
| 2R | +0.105 | -0.072 |
| 2.5R | +0.111 | -0.059 |
| 3R | +0.183 | -0.081 |
| 4R | +0.231 | -0.109 |
| 6R | +0.343 | -0.109 |
| aucun (temps) <- retenu | +0.423 | -0.109 |

**Espérance vs durée maximale de détention** (stop 2.5 ATR, objectif aucun (temps))

| Barres | APPR | VAL |
|---|---|---|
| 2 | +0.033 | -0.060 |
| 4 | +0.062 | -0.070 |
| 8 | +0.074 | -0.147 |
| 12 | +0.139 | -0.156 |
| 16 | +0.207 | -0.154 |
| 24 | +0.265 | -0.042 |
| 32 <- retenu | +0.458 | -0.106 |
| 48 | +0.423 | -0.109 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.105 [-0.39 ; +0.24] | +0.027 [-0.10 ; +0.23] |
| break-even à +1R | -0.050 [-0.14 ; +0.09] | +0.002 [-0.07 ; +0.10] |
| break-even à +1.5R | -0.032 [-0.08 ; +0.00] | -0.029 [-0.08 ; +0.00] |
| suiveur 0.5 ATR | -0.456 [-1.32 ; +0.42] | +0.023 [-0.37 ; +0.42] |
| suiveur 1 ATR | -0.464 [-1.24 ; +0.35] | +0.060 [-0.21 ; +0.39] |
| suiveur 1.5 ATR | -0.436 [-1.06 ; +0.25] | +0.050 [-0.13 ; +0.31] |
| suiveur 2 ATR | -0.374 [-0.87 ; +0.17] | -0.010 [-0.14 ; +0.19] |
| suiveur 3 ATR | -0.250 [-0.64 ; +0.12] | +0.054 [-0.05 ; +0.19] |

Gestion retenue : BE 1.5R : inutile ; suiveur 3 ATR : inutile.

**Plan final (stop 2.5 ATR, objectif aucun (temps), BE -, suiveur -, sortie au temps 32 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 87 | 19 | +0.458 [-0.49 ; +1.40] | 54 % | +0.030 | +0.415 [-0.53 ; +1.35] | 0.341 | 1.08 | 0.94 | 0.191 |
| VAL_T | 89 | 12 | -0.080 [-0.55 ; +0.41] | 44 % | -0.130 | +0.020 [-0.44 ; +0.49] | 0.513 | 0.71 | 0.77 | 0.636 |
| VAL_NQ | 80 | 11 | -0.135 [-0.59 ; +0.32] | 42 % | -0.236 | +0.073 [-0.38 ; +0.52] | 0.408 | 0.58 | 0.68 | 0.799 |
| NQ_avant | 86 | 22 | +0.863 [-0.26 ; +1.88] | 60 % | +0.326 | +0.562 [-0.55 ; +1.58] | 0.288 | 1.50 | 1.12 | 0.043 |
| VAL | 169 | 12 | -0.106 [-0.54 ; +0.35] | 43 % | -0.175 | +0.045 [-0.39 ; +0.48] | 0.472 | 0.65 | 0.72 | 0.814 |

Verdict : **ne bat pas le hasard** — confiance p=0.47 (profil MFE/MAE p=0.81).

### Climax SELL

Coupure APPR/validation : 2026-10-01 (médiane des entrées MES). n : APPR 34 (15 j), VAL_T 34 (8 j), VAL_NQ 24 (5 j), NQ_avant 27 (13 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.73 | 0.79 | 0.46 | -0.68 | 1.03 | 1.89 | 1.84 | +0.86 |
| 8 | 2.38 | 1.14 | 0.48 | -0.86 | 1.17 | 2.78 | 2.38 | +1.42 |
| 12 | 2.60 | 1.77 | 0.68 | -0.64 | 1.36 | 3.32 | 2.45 | +1.73 |
| 16 | 2.70 | 2.01 | 0.74 | -0.71 | 1.54 | 4.02 | 2.60 | +2.09 |
| 24 | 3.35 | 2.20 | 0.66 | -0.97 | 1.90 | 4.39 | 2.31 | +1.87 |
| 32 | 3.30 | 2.91 | 0.88 | -0.19 | 2.01 | 5.04 | 2.51 | +2.00 |
| 48 | 3.66 | 3.17 | 0.87 | -0.34 | 2.86 | 5.87 | 2.05 | +2.17 |

**Instant du MFE sur 48 barres** — APPR : médiane 25 barres (q25 4.5, q75 41) ; atteint avant 8 barres : 30 %, avant 16 : 41 %. VAL : médiane 26.5 barres (q25 6, q75 46) ; atteint avant 8 barres : 34 %, avant 16 : 42 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 11 | 1.66 / 2.05 / 2.55 / 2.76 | 20 | 2.99 / 4.41 / 5.40 / 6.08 |
| VAL_T | 22 | 0.78 / 0.98 / 1.27 / 1.48 | 10 | 3.09 / 3.57 / 3.92 / 3.95 |
| VAL_NQ | 15 | 0.94 / 1.32 / 1.75 / 1.90 | 8 | 2.38 / 3.11 / 3.91 / 4.84 |
| VAL | 37 | 0.86 / 1.10 / 1.53 / 1.69 | 18 | 2.75 / 3.48 / 3.93 / 4.25 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 0 % | 0 % | 8 % |
| 0.5 | 0 % | 0 % | 19 % |
| 0.75 | 0 % | 5 % | 32 % |
| 1 | 9 % | 5 % | 68 % |
| 1.25 | 27 % | 15 % | 78 % |
| 1.5 | 45 % | 20 % | 89 % |
| 1.75 | 55 % | 25 % | 95 % |
| 2 | 73 % | 30 % | 97 % |
| 2.25 | 73 % | 35 % | 100 % |
| 2.5 | 82 % | 40 % | 100 % |
| 2.75 <- retenu | 91 % | 45 % | 100 % |
| 3 | 100 % | 50 % | 100 % |
| 3.25 | 100 % | 55 % | 100 % |
| 3.5 | 100 % | 55 % | 100 % |
| 3.75 | 100 % | 60 % | 100 % |
| 4 | 100 % | 65 % | 100 % |

**Espérance vs taille du stop** (objectif 0.5R, 8 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.237 | -1.046 | -0.309 | -0.262 |
| 0.5 | -0.854 | -0.777 | -0.427 | -0.389 |
| 0.75 | -0.829 | -0.541 | -0.622 | -0.406 |
| 1 | -0.523 | -0.166 | -0.523 | -0.166 |
| 1.25 | -0.413 | -0.004 | -0.516 | -0.006 |
| 1.5 | -0.284 | +0.091 | -0.426 | +0.136 |
| 1.75 | -0.286 | +0.200 | -0.501 | +0.351 |
| 2 | -0.139 | +0.189 | -0.278 | +0.377 |
| 2.25 | -0.185 | +0.207 | -0.417 | +0.467 |
| 2.5 | -0.149 | +0.178 | -0.372 | +0.445 |
| 2.75 <- retenu | -0.168 | +0.189 | -0.461 | +0.520 |
| 3 | -0.178 | +0.201 | -0.535 | +0.604 |
| 3.25 | -0.168 | +0.205 | -0.546 | +0.665 |
| 3.5 | -0.163 | +0.213 | -0.572 | +0.745 |
| 3.75 | -0.162 | +0.220 | -0.606 | +0.824 |
| 4 | -0.136 | +0.221 | -0.543 | +0.885 |

**Espérance (R nets) vs objectif**, stop 2.75 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R <- retenu | -0.224 | +0.104 |
| 0.75R | -0.238 | +0.255 |
| 1R | -0.298 | +0.387 |
| 1.25R | -0.330 | +0.476 |
| 1.5R | -0.292 | +0.514 |
| 2R | -0.412 | +0.604 |
| 2.5R | -0.382 | +0.725 |
| 3R | -0.376 | +0.793 |
| 4R | -0.347 | +0.739 |
| 6R | -0.320 | +0.749 |
| aucun (temps) | -0.320 | +0.749 |

**Espérance vs durée maximale de détention** (stop 2.75 ATR, objectif 0.5R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.188 | +0.121 |
| 4 | -0.177 | +0.203 |
| 8 <- retenu | -0.168 | +0.189 |
| 12 | -0.168 | +0.169 |
| 16 | -0.189 | +0.142 |
| 24 | -0.244 | +0.113 |
| 32 | -0.224 | +0.108 |
| 48 | -0.224 | +0.104 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| break-even à +1R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | +0.000 [-0.23 ; +0.27] | -0.151 [-0.28 ; +0.17] |
| suiveur 1 ATR | -0.037 [-0.26 ; +0.22] | -0.187 [-0.29 ; +0.12] |
| suiveur 1.5 ATR | -0.065 [-0.28 ; +0.18] | -0.120 [-0.20 ; +0.06] |
| suiveur 2 ATR | +0.003 [-0.09 ; +0.12] | -0.009 [-0.07 ; +0.14] |
| suiveur 3 ATR | -0.032 [-0.11 ; +0.01] | +0.009 [+0.00 ; +0.03] |

Gestion retenue : BE 0.5R : inutile ; suiveur 2 ATR : adopté en APPR, NON confirmé en validation.

**Plan final (stop 2.75 ATR, objectif 0.5R, BE -, suiveur 2 ATR, sortie au temps 8 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 34 (n<50) | 15 | -0.165 [-0.39 ; +0.01] | 47 % | -0.054 | -0.101 [-0.32 ; +0.07] | 0.921 | 0.74 | 1.21 | 0.928 |
| VAL_T | 34 (n<50) | 8 | +0.209 [-0.07 ; +0.35] | 74 % | -0.081 | +0.296 [+0.01 ; +0.43] | 0.015 | 2.93 | 1.31 | 0.002 |
| VAL_NQ | 24 (n<50) | 5 | +0.139 [-0.22 ; +0.36] | 62 % | +0.024 | +0.118 [-0.24 ; +0.33] | 0.227 | 2.22 | 1.54 | 0.091 |
| NQ_avant | 27 (n<50) | 13 | -0.067 [-0.20 ; +0.10] | 44 % | -0.040 | -0.028 [-0.16 ; +0.13] | 0.625 | 1.02 | 0.98 | 0.378 |
| VAL | 58 | 9 | +0.180 [-0.12 ; +0.32] | 69 % | -0.035 | +0.222 [-0.07 ; +0.36] | 0.081 | 2.60 | 1.38 | 0.001 |

Verdict : **non concluant (VAL > hasard mais APPR < hasard : effet de régime)** — confiance faible (p VAL=0.081).

### Changement Heishinator

Coupure APPR/validation : 2026-08-26 (médiane des entrées MES). n : APPR 182 (57 j), VAL_T 183 (29 j), VAL_NQ 173 (31 j), NQ_avant 7 (4 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.13 | 1.03 | 0.91 | -0.15 | 1.06 | 1.13 | 1.07 | -0.01 |
| 8 | 1.62 | 1.55 | 0.96 | -0.14 | 1.59 | 1.62 | 1.02 | -0.11 |
| 12 | 2.05 | 1.89 | 0.92 | -0.24 | 2.00 | 2.03 | 1.01 | -0.13 |
| 16 | 2.29 | 2.25 | 0.98 | -0.06 | 2.39 | 2.43 | 1.02 | -0.05 |
| 24 | 2.78 | 2.70 | 0.97 | -0.25 | 2.95 | 3.06 | 1.04 | -0.07 |
| 32 | 3.14 | 3.23 | 1.03 | +0.00 | 3.36 | 3.57 | 1.07 | +0.10 |
| 48 | 3.50 | 3.72 | 1.06 | +0.10 | 4.14 | 4.28 | 1.03 | -0.13 |

**Instant du MFE sur 48 barres** — APPR : médiane 26 barres (q25 9, q75 40) ; atteint avant 8 barres : 25 %, avant 16 : 36 %. VAL : médiane 22 barres (q25 6, q75 39) ; atteint avant 8 barres : 30 %, avant 16 : 43 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 89 | 0.98 / 1.45 / 2.43 / 3.29 | 82 | 2.75 / 4.91 / 8.01 / 8.88 |
| VAL_T | 82 | 0.83 / 1.11 / 1.71 / 2.46 | 91 | 3.47 / 4.77 / 6.55 / 7.98 |
| VAL_NQ | 86 | 0.99 / 1.64 / 2.11 / 2.63 | 73 | 2.99 / 4.71 / 6.83 / 8.78 |
| VAL | 168 | 0.90 / 1.40 / 2.02 / 2.62 | 164 | 3.23 / 4.74 / 6.62 / 8.04 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 12 % | 0 % | 12 % |
| 0.5 | 26 % | 1 % | 29 % |
| 0.75 | 42 % | 2 % | 39 % |
| 1 | 53 % | 6 % | 56 % |
| 1.25 | 67 % | 17 % | 72 % |
| 1.5 | 76 % | 18 % | 78 % |
| 1.75 | 83 % | 24 % | 83 % |
| 2 | 85 % | 34 % | 89 % |
| 2.25 | 88 % | 39 % | 92 % |
| 2.5 | 90 % | 44 % | 94 % |
| 2.75 <- retenu | 92 % | 50 % | 95 % |
| 3 | 93 % | 56 % | 97 % |
| 3.25 | 93 % | 61 % | 98 % |
| 3.5 | 96 % | 65 % | 98 % |
| 3.75 | 97 % | 67 % | 99 % |
| 4 | 98 % | 68 % | 99 % |

**Espérance vs taille du stop** (objectif 1.25R, 48 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.121 | -1.037 | -0.280 | -0.259 |
| 0.5 | -0.559 | -0.473 | -0.279 | -0.237 |
| 0.75 | -0.339 | -0.218 | -0.254 | -0.164 |
| 1 | -0.264 | -0.079 | -0.264 | -0.079 |
| 1.25 | -0.158 | +0.055 | -0.198 | +0.069 |
| 1.5 | -0.090 | +0.046 | -0.135 | +0.070 |
| 1.75 | -0.025 | +0.028 | -0.043 | +0.049 |
| 2 | -0.095 | +0.019 | -0.191 | +0.037 |
| 2.25 | -0.057 | +0.030 | -0.129 | +0.067 |
| 2.5 | -0.040 | +0.022 | -0.100 | +0.055 |
| 2.75 <- retenu | -0.018 | +0.005 | -0.051 | +0.014 |
| 3 | -0.038 | +0.015 | -0.113 | +0.046 |
| 3.25 | -0.055 | +0.014 | -0.178 | +0.047 |
| 3.5 | -0.051 | -0.005 | -0.179 | -0.019 |
| 3.75 | -0.054 | +0.009 | -0.202 | +0.033 |
| 4 | -0.041 | +0.004 | -0.165 | +0.017 |

**Espérance (R nets) vs objectif**, stop 2.75 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.083 | +0.003 |
| 0.75R | -0.049 | +0.032 |
| 1R | -0.030 | -0.003 |
| 1.25R <- retenu | -0.018 | +0.005 |
| 1.5R | -0.020 | +0.013 |
| 2R | -0.090 | +0.015 |
| 2.5R | -0.108 | +0.041 |
| 3R | -0.130 | +0.058 |
| 4R | -0.131 | +0.039 |
| 6R | -0.144 | +0.066 |
| aucun (temps) | -0.114 | +0.060 |

**Espérance vs durée maximale de détention** (stop 2.75 ATR, objectif 1.25R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.069 | -0.026 |
| 4 | -0.046 | -0.001 |
| 8 | -0.035 | -0.037 |
| 12 | -0.076 | -0.033 |
| 16 | -0.048 | -0.035 |
| 24 | -0.042 | -0.020 |
| 32 | -0.038 | +0.016 |
| 48 <- retenu | -0.018 | +0.005 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.085 [-0.16 ; -0.01] | -0.015 [-0.10 ; +0.06] |
| break-even à +1R | -0.027 [-0.07 ; +0.02] | -0.008 [-0.03 ; +0.02] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | -0.041 [-0.14 ; +0.06] | -0.042 [-0.18 ; +0.09] |
| suiveur 1 ATR | -0.034 [-0.13 ; +0.07] | -0.027 [-0.16 ; +0.09] |
| suiveur 1.5 ATR | -0.055 [-0.15 ; +0.05] | -0.007 [-0.11 ; +0.09] |
| suiveur 2 ATR | -0.071 [-0.17 ; +0.03] | -0.000 [-0.09 ; +0.08] |
| suiveur 3 ATR | -0.083 [-0.16 ; -0.00] | +0.001 [-0.05 ; +0.05] |

Gestion retenue : BE 1.5R : inutile ; suiveur 1 ATR : inutile.

**Plan final (stop 2.75 ATR, objectif 1.25R, BE -, suiveur -, sortie au temps 48 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 182 | 57 | -0.018 [-0.13 ; +0.09] | 46 % | -0.056 | +0.041 [-0.07 ; +0.15] | 0.330 | 0.98 | 1.01 | 0.554 |
| VAL_T | 183 | 29 | -0.051 [-0.20 ; +0.11] | 46 % | -0.068 | +0.014 [-0.12 ; +0.16] | 0.422 | 1.00 | 1.00 | 0.460 |
| VAL_NQ | 173 | 31 | +0.064 [-0.06 ; +0.21] | 50 % | +0.009 | +0.061 [-0.07 ; +0.21] | 0.240 | 1.04 | 1.00 | 0.371 |
| NQ_avant | 7 (n<50) | 4 | -0.039 [-1.00 ; +0.68] | 43 % | -0.065 | +0.008 [-0.96 ; +0.73] | 0.487 | 0.78 | 1.04 | 0.615 |
| VAL | 356 | 34 | +0.005 [-0.12 ; +0.14] | 48 % | -0.032 | +0.037 [-0.09 ; +0.17] | 0.272 | 1.02 | 1.00 | 0.394 |

Verdict : **ne bat pas le hasard** — confiance p=0.27 (profil MFE/MAE p=0.39).

### Cassure session/Monday

Coupure APPR/validation : 2026-09-11 (médiane des entrées MES). n : APPR 419 (73 j), VAL_T 420 (27 j), VAL_NQ 335 (26 j), NQ_avant 62 (19 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.16 | 1.12 | 0.97 | -0.15 | 1.15 | 1.14 | 0.99 | -0.08 |
| 8 | 1.59 | 1.56 | 0.98 | -0.10 | 1.72 | 1.60 | 0.93 | -0.21 |
| 12 | 1.93 | 1.88 | 0.98 | -0.13 | 2.14 | 1.98 | 0.92 | -0.23 |
| 16 | 2.24 | 2.20 | 0.98 | -0.17 | 2.50 | 2.29 | 0.91 | -0.27 |
| 24 | 2.78 | 2.83 | 1.02 | -0.03 | 3.22 | 2.78 | 0.86 | -0.48 |
| 32 | 3.24 | 3.22 | 0.99 | -0.11 | 3.64 | 3.30 | 0.91 | -0.34 |
| 48 | 3.81 | 3.87 | 1.02 | -0.02 | 4.42 | 4.04 | 0.91 | -0.53 |

**Instant du MFE sur 48 barres** — APPR : médiane 21 barres (q25 6, q75 38) ; atteint avant 8 barres : 30 %, avant 16 : 42 %. VAL : médiane 21 barres (q25 5, q75 39) ; atteint avant 8 barres : 32 %, avant 16 : 43 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 199 | 1.04 / 1.64 / 2.41 / 2.79 | 195 | 2.77 / 4.31 / 6.24 / 8.22 |
| VAL_T | 161 | 0.93 / 1.50 / 2.52 / 3.16 | 226 | 2.82 / 4.33 / 6.54 / 11.56 |
| VAL_NQ | 169 | 0.80 / 1.41 / 1.96 / 2.57 | 144 | 3.02 / 4.67 / 6.77 / 8.87 |
| VAL | 330 | 0.85 / 1.47 / 2.25 / 2.90 | 370 | 2.89 / 4.42 / 6.78 / 9.83 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 9 % | 1 % | 8 % |
| 0.5 | 22 % | 1 % | 25 % |
| 0.75 | 35 % | 5 % | 45 % |
| 1 | 46 % | 9 % | 59 % |
| 1.25 | 60 % | 14 % | 69 % |
| 1.5 | 70 % | 21 % | 76 % |
| 1.75 | 76 % | 26 % | 82 % |
| 2 | 81 % | 31 % | 86 % |
| 2.25 | 86 % | 35 % | 90 % |
| 2.5 <- retenu | 91 % | 45 % | 92 % |
| 2.75 | 94 % | 50 % | 94 % |
| 3 | 96 % | 55 % | 95 % |
| 3.25 | 97 % | 63 % | 96 % |
| 3.5 | 99 % | 68 % | 97 % |
| 3.75 | 99 % | 70 % | 98 % |
| 4 | 100 % | 72 % | 98 % |

**Espérance vs taille du stop** (objectif 1R, 48 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.007 | -0.863 | -0.252 | -0.216 |
| 0.5 | -0.538 | -0.396 | -0.269 | -0.198 |
| 0.75 | -0.349 | -0.189 | -0.262 | -0.142 |
| 1 | -0.249 | -0.098 | -0.249 | -0.098 |
| 1.25 | -0.207 | -0.083 | -0.258 | -0.104 |
| 1.5 | -0.128 | -0.093 | -0.192 | -0.140 |
| 1.75 | -0.094 | -0.060 | -0.165 | -0.104 |
| 2 | -0.089 | -0.060 | -0.177 | -0.120 |
| 2.25 | -0.079 | -0.047 | -0.179 | -0.105 |
| 2.5 <- retenu | -0.007 | -0.051 | -0.016 | -0.128 |
| 2.75 | -0.020 | -0.086 | -0.055 | -0.238 |
| 3 | -0.006 | -0.083 | -0.019 | -0.249 |
| 3.25 | -0.012 | -0.078 | -0.038 | -0.253 |
| 3.5 | -0.006 | -0.084 | -0.021 | -0.293 |
| 3.75 | -0.021 | -0.074 | -0.080 | -0.276 |
| 4 | -0.035 | -0.068 | -0.139 | -0.271 |

**Espérance (R nets) vs objectif**, stop 2.5 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.042 | -0.066 |
| 0.75R | -0.032 | -0.049 |
| 1R <- retenu | -0.007 | -0.051 |
| 1.25R | -0.014 | -0.067 |
| 1.5R | -0.032 | -0.065 |
| 2R | -0.058 | -0.062 |
| 2.5R | -0.104 | -0.064 |
| 3R | -0.094 | -0.051 |
| 4R | -0.134 | -0.056 |
| 6R | -0.146 | -0.072 |
| aucun (temps) | -0.137 | -0.071 |

**Espérance vs durée maximale de détention** (stop 2.5 ATR, objectif 1R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.041 | -0.016 |
| 4 | -0.038 | -0.006 |
| 8 | -0.033 | -0.036 |
| 12 | -0.034 | -0.056 |
| 16 | -0.025 | -0.055 |
| 24 | -0.016 | -0.068 |
| 32 | -0.011 | -0.059 |
| 48 <- retenu | -0.007 | -0.051 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.069 [-0.14 ; +0.00] | +0.003 [-0.05 ; +0.06] |
| break-even à +1R | +0.000 [-0.01 ; +0.01] | -0.001 [-0.01 ; +0.00] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | -0.065 [-0.19 ; +0.05] | +0.022 [-0.11 ; +0.15] |
| suiveur 1 ATR | -0.070 [-0.19 ; +0.04] | +0.002 [-0.12 ; +0.13] |
| suiveur 1.5 ATR | -0.092 [-0.20 ; +0.01] | +0.033 [-0.07 ; +0.13] |
| suiveur 2 ATR | -0.106 [-0.21 ; -0.01] | +0.052 [-0.03 ; +0.14] |
| suiveur 3 ATR | -0.045 [-0.10 ; +0.00] | +0.006 [-0.03 ; +0.04] |

Gestion retenue : BE 1R : adopté en APPR, NON confirmé en validation ; suiveur 3 ATR : inutile.

**Plan final (stop 2.5 ATR, objectif 1R, BE 1R, suiveur -, sortie au temps 48 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 419 | 73 | -0.006 [-0.12 ; +0.11] | 51 % | -0.051 | +0.047 [-0.07 ; +0.17] | 0.233 | 0.98 | 1.00 | 0.607 |
| VAL_T | 420 | 27 | -0.179 [-0.38 ; +0.03] | 44 % | -0.072 | -0.108 [-0.30 ; +0.09] | 0.990 | 0.80 | 1.01 | 0.999 |
| VAL_NQ | 335 | 26 | +0.107 [-0.03 ; +0.26] | 55 % | -0.008 | +0.115 [-0.02 ; +0.27] | 0.064 | 1.08 | 0.98 | 0.109 |
| NQ_avant | 62 | 19 | -0.127 [-0.38 ; +0.16] | 37 % | -0.009 | -0.115 [-0.37 ; +0.17] | 0.833 | 0.67 | 1.01 | 0.981 |
| VAL | 755 | 27 | -0.052 [-0.20 ; +0.09] | 49 % | -0.043 | -0.009 [-0.15 ; +0.13] | 0.591 | 0.91 | 1.00 | 0.925 |

Verdict : **ne bat pas le hasard** — confiance p=0.59 (profil MFE/MAE p=0.93).

### Rebond Detector

Coupure APPR/validation : 2026-10-05 (médiane des entrées MES). n : APPR 407 (34 j), VAL_T 408 (10 j), VAL_NQ 317 (10 j), NQ_avant 333 (33 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.14 | 1.10 | 0.96 | -0.18 | 1.04 | 1.02 | 0.98 | -0.20 |
| 8 | 1.58 | 1.75 | 1.11 | +0.03 | 1.50 | 1.47 | 0.98 | -0.20 |
| 12 | 1.96 | 2.28 | 1.17 | +0.05 | 1.95 | 1.86 | 0.96 | -0.24 |
| 16 | 2.40 | 2.69 | 1.12 | -0.07 | 2.24 | 2.19 | 0.98 | -0.22 |
| 24 | 2.99 | 3.64 | 1.22 | +0.28 | 2.77 | 2.79 | 1.01 | -0.10 |
| 32 | 3.48 | 4.35 | 1.25 | +0.62 | 3.24 | 3.26 | 1.00 | -0.22 |
| 48 | 3.89 | 6.18 | 1.59 | +1.65 | 4.16 | 4.19 | 1.01 | -0.15 |

**Instant du MFE sur 48 barres** — APPR : médiane 23 barres (q25 8, q75 39) ; atteint avant 8 barres : 26 %, avant 16 : 40 %. VAL : médiane 21 barres (q25 5.75, q75 40) ; atteint avant 8 barres : 33 %, avant 16 : 46 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 161 | 0.76 / 1.42 / 2.25 / 2.62 | 219 | 2.94 / 4.71 / 6.47 / 7.18 |
| VAL_T | 171 | 0.72 / 1.24 / 2.48 / 3.18 | 235 | 2.36 / 3.34 / 5.61 / 6.95 |
| VAL_NQ | 129 | 0.83 / 1.55 / 2.48 / 3.56 | 175 | 2.71 / 4.98 / 6.38 / 7.65 |
| VAL | 300 | 0.75 / 1.47 / 2.48 / 3.29 | 410 | 2.51 / 3.87 / 5.95 / 7.43 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 19 % | 0 % | 23 % |
| 0.5 | 37 % | 0 % | 37 % |
| 0.75 | 49 % | 2 % | 50 % |
| 1 | 61 % | 8 % | 60 % |
| 1.25 | 71 % | 15 % | 70 % |
| 1.5 | 79 % | 23 % | 76 % |
| 1.75 | 83 % | 26 % | 81 % |
| 2 | 84 % | 32 % | 84 % |
| 2.25 | 89 % | 38 % | 86 % |
| 2.5 <- retenu | 93 % | 42 % | 90 % |
| 2.75 | 96 % | 47 % | 93 % |
| 3 | 98 % | 52 % | 93 % |
| 3.25 | 99 % | 58 % | 95 % |
| 3.5 | 99 % | 59 % | 96 % |
| 3.75 | 99 % | 64 % | 97 % |
| 4 | 99 % | 66 % | 99 % |

**Espérance vs taille du stop** (objectif aucun (temps), 48 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -0.102 | -0.056 | -0.026 | -0.014 |
| 0.5 | +0.319 | -0.123 | +0.160 | -0.062 |
| 0.75 | +0.419 | -0.115 | +0.314 | -0.086 |
| 1 | +0.507 | -0.084 | +0.507 | -0.084 |
| 1.25 | +0.576 | -0.056 | +0.720 | -0.071 |
| 1.5 | +0.461 | -0.084 | +0.692 | -0.126 |
| 1.75 | +0.363 | -0.082 | +0.636 | -0.144 |
| 2 | +0.270 | -0.095 | +0.540 | -0.190 |
| 2.25 | +0.215 | -0.116 | +0.484 | -0.262 |
| 2.5 <- retenu | +0.150 | -0.080 | +0.376 | -0.199 |
| 2.75 | +0.109 | -0.053 | +0.301 | -0.147 |
| 3 | +0.074 | -0.032 | +0.221 | -0.096 |
| 3.25 | +0.049 | -0.023 | +0.159 | -0.076 |
| 3.5 | +0.042 | -0.016 | +0.147 | -0.055 |
| 3.75 | +0.046 | -0.010 | +0.173 | -0.036 |
| 4 | +0.028 | +0.005 | +0.113 | +0.021 |

**Espérance (R nets) vs objectif**, stop 2.5 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R | -0.115 | -0.141 |
| 0.75R | -0.076 | -0.165 |
| 1R | -0.038 | -0.198 |
| 1.25R | -0.004 | -0.182 |
| 1.5R | +0.039 | -0.165 |
| 2R | +0.056 | -0.162 |
| 2.5R | +0.026 | -0.150 |
| 3R | +0.001 | -0.130 |
| 4R | -0.008 | -0.108 |
| 6R | +0.098 | -0.092 |
| aucun (temps) <- retenu | +0.150 | -0.080 |

**Espérance vs durée maximale de détention** (stop 2.5 ATR, objectif aucun (temps))

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.048 | -0.058 |
| 4 | -0.047 | -0.079 |
| 8 | +0.033 | -0.079 |
| 12 | +0.033 | -0.107 |
| 16 | -0.005 | -0.111 |
| 24 | +0.055 | -0.083 |
| 32 | +0.098 | -0.102 |
| 48 <- retenu | +0.150 | -0.080 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.018 [-0.39 ; +0.25] | +0.056 [-0.02 ; +0.12] |
| break-even à +1R | +0.065 [-0.09 ; +0.21] | +0.015 [-0.03 ; +0.08] |
| break-even à +1.5R | +0.067 [-0.06 ; +0.18] | +0.006 [-0.01 ; +0.03] |
| suiveur 0.5 ATR | -0.210 [-1.35 ; +0.44] | +0.016 [-0.06 ; +0.08] |
| suiveur 1 ATR | -0.198 [-1.34 ; +0.44] | -0.000 [-0.08 ; +0.07] |
| suiveur 1.5 ATR | -0.150 [-1.25 ; +0.45] | -0.008 [-0.08 ; +0.06] |
| suiveur 2 ATR | -0.059 [-0.91 ; +0.44] | -0.025 [-0.11 ; +0.05] |
| suiveur 3 ATR | +0.019 [-0.53 ; +0.39] | -0.043 [-0.12 ; +0.03] |

Gestion retenue : BE 1.5R : utile (confirmé en validation) ; suiveur 3 ATR : inutile.

**Plan final (stop 2.5 ATR, objectif aucun (temps), BE 1.5R, suiveur -, sortie au temps 48 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 407 | 34 | +0.218 [-0.45 ; +1.36] | 30 % | -0.044 | +0.270 [-0.39 ; +1.40] | 0.365 | 1.12 | 1.03 | 0.133 |
| VAL_T | 408 | 10 | -0.131 [-0.28 ; +0.08] | 27 % | -0.047 | -0.078 [-0.20 ; +0.10] | 0.872 | 1.08 | 1.03 | 0.259 |
| VAL_NQ | 317 | 10 | +0.001 [-0.22 ; +0.22] | 29 % | +0.103 | -0.092 [-0.31 ; +0.11] | 0.892 | 0.87 | 0.95 | 0.863 |
| NQ_avant | 333 | 33 | +0.030 [-0.20 ; +0.30] | 33 % | -0.015 | +0.054 [-0.20 ; +0.34] | 0.341 | 1.11 | 0.99 | 0.107 |
| VAL | 725 | 10 | -0.074 [-0.17 ; +0.03] | 28 % | +0.017 | -0.084 [-0.15 ; -0.02] | 0.994 | 0.98 | 0.99 | 0.578 |

Verdict : **ne bat pas le hasard** — confiance p=0.99 (profil MFE/MAE p=0.58).

### Aléatoire (référence)

Coupure APPR/validation : 2026-09-16 (médiane des entrées MES). n : APPR 4862 (83 j), VAL_T 4863 (26 j), VAL_NQ 4446 (26 j), NQ_avant 501 (25 j).

**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.

| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |
|---|---|---|---|---|---|---|---|---|
| 4 | 1.05 | 1.02 | 0.97 | -0.15 | 1.03 | 1.04 | 1.01 | -0.11 |
| 8 | 1.51 | 1.48 | 0.98 | -0.16 | 1.50 | 1.53 | 1.02 | -0.09 |
| 12 | 1.91 | 1.83 | 0.96 | -0.17 | 1.90 | 1.91 | 1.01 | -0.11 |
| 16 | 2.25 | 2.15 | 0.96 | -0.18 | 2.26 | 2.24 | 0.99 | -0.14 |
| 24 | 2.82 | 2.77 | 0.98 | -0.13 | 2.87 | 2.82 | 0.98 | -0.18 |
| 32 | 3.35 | 3.30 | 0.99 | -0.14 | 3.40 | 3.33 | 0.98 | -0.18 |
| 48 | 4.18 | 4.17 | 1.00 | -0.10 | 4.30 | 4.20 | 0.98 | -0.18 |

**Instant du MFE sur 48 barres** — APPR : médiane 26 barres (q25 7, q75 41) ; atteint avant 8 barres : 27 %, avant 16 : 38 %. VAL : médiane 24 barres (q25 7, q75 41) ; atteint avant 8 barres : 29 %, avant 16 : 41 %.

**MAE (ATR) des gagnants vs perdants à 16 barres** (quantiles 50/75/90/95 %)

| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |
|---|---|---|---|---|
| APPR | 2148 | 0.85 / 1.55 / 2.37 / 3.07 | 2489 | 2.55 / 4.00 / 6.11 / 8.21 |
| VAL_T | 2165 | 0.75 / 1.36 / 2.19 / 2.86 | 2444 | 2.56 / 4.13 / 6.30 / 8.18 |
| VAL_NQ | 2092 | 0.79 / 1.37 / 2.15 / 2.69 | 2100 | 2.89 / 4.53 / 6.55 / 8.24 |
| VAL | 4257 | 0.78 / 1.36 / 2.18 / 2.76 | 4544 | 2.73 / 4.32 / 6.45 / 8.22 |

**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)

| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |
|---|---|---|---|
| 0.25 | 15 % | 0 % | 15 % |
| 0.5 | 32 % | 1 % | 32 % |
| 0.75 | 46 % | 4 % | 49 % |
| 1 | 57 % | 9 % | 62 % |
| 1.25 | 67 % | 15 % | 72 % |
| 1.5 | 74 % | 22 % | 79 % |
| 1.75 | 81 % | 29 % | 84 % |
| 2 | 84 % | 37 % | 88 % |
| 2.25 | 88 % | 43 % | 91 % |
| 2.5 <- retenu | 92 % | 49 % | 93 % |
| 2.75 | 93 % | 55 % | 95 % |
| 3 | 95 % | 60 % | 96 % |
| 3.25 | 96 % | 65 % | 97 % |
| 3.5 | 97 % | 69 % | 97 % |
| 3.75 | 97 % | 72 % | 98 % |
| 4 | 98 % | 75 % | 98 % |

**Espérance vs taille du stop** (objectif 0.5R, 8 barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)

| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |
|---|---|---|---|---|
| 0.25 | -1.028 | -0.967 | -0.257 | -0.242 |
| 0.5 | -0.443 | -0.406 | -0.222 | -0.203 |
| 0.75 | -0.258 | -0.200 | -0.194 | -0.150 |
| 1 | -0.178 | -0.118 | -0.178 | -0.118 |
| 1.25 | -0.135 | -0.086 | -0.169 | -0.108 |
| 1.5 | -0.106 | -0.069 | -0.159 | -0.104 |
| 1.75 | -0.084 | -0.063 | -0.148 | -0.109 |
| 2 | -0.070 | -0.057 | -0.140 | -0.115 |
| 2.25 | -0.059 | -0.052 | -0.132 | -0.117 |
| 2.5 <- retenu | -0.052 | -0.048 | -0.131 | -0.120 |
| 2.75 | -0.056 | -0.043 | -0.153 | -0.119 |
| 3 | -0.054 | -0.040 | -0.161 | -0.120 |
| 3.25 | -0.050 | -0.040 | -0.161 | -0.129 |
| 3.5 | -0.043 | -0.038 | -0.152 | -0.132 |
| 3.75 | -0.042 | -0.035 | -0.158 | -0.130 |
| 4 | -0.039 | -0.033 | -0.157 | -0.131 |

**Espérance (R nets) vs objectif**, stop 2.5 ATR, sortie au temps à 48 barres

| Objectif | APPR | VAL |
|---|---|---|
| 0.5R <- retenu | -0.054 | -0.067 |
| 0.75R | -0.067 | -0.063 |
| 1R | -0.071 | -0.048 |
| 1.25R | -0.069 | -0.039 |
| 1.5R | -0.071 | -0.032 |
| 2R | -0.064 | -0.025 |
| 2.5R | -0.075 | -0.014 |
| 3R | -0.084 | -0.008 |
| 4R | -0.110 | +0.009 |
| 6R | -0.130 | +0.023 |
| aucun (temps) | -0.125 | +0.038 |

**Espérance vs durée maximale de détention** (stop 2.5 ATR, objectif 0.5R)

| Barres | APPR | VAL |
|---|---|---|
| 2 | -0.060 | -0.042 |
| 4 | -0.058 | -0.041 |
| 8 <- retenu | -0.052 | -0.048 |
| 12 | -0.053 | -0.049 |
| 16 | -0.057 | -0.053 |
| 24 | -0.053 | -0.063 |
| 32 | -0.055 | -0.066 |
| 48 | -0.054 | -0.067 |

**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour

| Gestion | APPR delta [IC] | VAL delta [IC] |
|---|---|---|
| break-even à +0.5R | -0.000 [-0.00 ; +0.00] | -0.000 [-0.00 ; +0.00] |
| break-even à +1R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| break-even à +1.5R | +0.000 [+0.00 ; +0.00] | +0.000 [+0.00 ; +0.00] |
| suiveur 0.5 ATR | -0.009 [-0.02 ; +0.01] | -0.002 [-0.02 ; +0.02] |
| suiveur 1 ATR | -0.017 [-0.03 ; -0.00] | -0.000 [-0.02 ; +0.02] |
| suiveur 1.5 ATR | -0.014 [-0.03 ; -0.00] | +0.007 [-0.01 ; +0.02] |
| suiveur 2 ATR | -0.014 [-0.03 ; -0.00] | +0.003 [-0.01 ; +0.01] |
| suiveur 3 ATR | -0.002 [-0.01 ; +0.00] | +0.001 [-0.00 ; +0.00] |

Gestion retenue : BE 1R : inutile ; suiveur 3 ATR : inutile.

**Plan final (stop 2.5 ATR, objectif 0.5R, BE -, suiveur -, sortie au temps 8 barres) vs hasard apparié** (même série, même période, même sens ; 1000 tirages)

| Jeu | n | jours | E[R] net [IC 95 %] | % gagnants | E[R] hasard | excès sur hasard [IC 95 %] | p | e-ratio 16 | e-ratio hasard | p e-ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| APPR | 4862 | 83 | -0.052 [-0.07 ; -0.04] | 54 % | -0.042 | -0.008 [-0.02 ; +0.01] | 0.893 | 0.96 | 1.00 | 0.979 |
| VAL_T | 4863 | 26 | -0.080 [-0.10 ; -0.06] | 53 % | -0.092 | +0.010 [-0.01 ; +0.03] | 0.176 | 0.99 | 1.00 | 0.723 |
| VAL_NQ | 4446 | 26 | -0.013 [-0.03 ; +0.01] | 57 % | -0.019 | +0.005 [-0.02 ; +0.03] | 0.333 | 1.00 | 1.00 | 0.510 |
| NQ_avant | 501 | 25 | +0.003 [-0.03 ; +0.03] | 58 % | +0.003 | +0.002 [-0.03 ; +0.03] | 0.506 | 0.91 | 0.99 | 0.897 |
| VAL | 9309 | 26 | -0.048 [-0.07 ; -0.03] | 55 % | -0.057 | +0.008 [-0.01 ; +0.03] | 0.210 | 0.99 | 1.00 | 0.667 |

Verdict : **ne bat pas le hasard** — confiance p=0.21 (profil MFE/MAE p=0.67).

