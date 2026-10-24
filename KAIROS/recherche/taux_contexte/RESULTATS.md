# Taux de réussite — contexte et horaires (agent WRR)

## 1. Hypothèse PRÉ-ENREGISTRÉE (écrite le 17/10/2026 AVANT tout calcul de cet agent)

**Hypothèse H-NUIT** : les signaux pris la nuit (bougie signal qui OUVRE entre 00:00 et 08:00, heure de
Paris) sont meilleurs que ceux du reste de la journée (bougie signal qui ouvre entre 08:00 et 24:00).

Protocole figé, aucune réoptimisation :
- Données : partie développement (75 %, scellé fermé) des 3 séries 15 min du cache (MES sept.-oct.,
  NQ sept.-oct. traité en MNQ, MES1 avr.-juil.), via `donnees.charger_series` (seul accès aux données).
- Déclencheurs : union des 11 déclencheurs de `meta_ml/candidats.declencheurs` (Signator fort/moyen,
  flip Heishinator, Climax, trendline, ORB, sessions, Monday, Detector rebond/cassure, divergence), long et
  short, sans filtre. Chauffe : 150 premières barres. Long et short sur la même barre : pas de trade (moteur).
- Moteur commun, une position à la fois par série, sortie forcée 15:59 Chicago, coûts par défaut.
- Gestion 1 : stop 1,5 ATR, objectif 2 R (A15R2). Gestion 2 : stop 1,5 ATR, objectif 1 R (A15R1).
- « Nuit » et « reste » sont backtestés séparément (signaux masqués à la fenêtre).
- Placebo : mêmes stop / objectif / fenêtre, entrées au hasard sur une barre de la MÊME heure d'ouverture
  (Paris), du même sens, DANS la même fenêtre ; 1 000 tirages.
- Statistiques principales : (a) écart de R moyen nuit − reste, IC et p unilatéral par bootstrap par journée
  CME (10 000) ; (b) R moyen de la nuit contre son placebo (p = part des tirages ≥) ; (c) taux de gagnants
  de la nuit contre son placebo (écart en points, p).
- **Règle de décision** : H-NUIT est « confirmée sur le cache » si, pour A15R2 ET pour A15R1,
  l'écart nuit − reste est > 0 avec p < 0,05 ET la nuit bat son placebo en R moyen avec p < 0,05.
  Sinon : « non confirmée ». Le détail par série est descriptif (même signe attendu sur les 3 séries).
- Limite connue d'avance : l'idée vient de `meta_ml` sur ces MÊMES données (observation après coup).
  Une confirmation ici n'est donc PAS indépendante ; seule la relance sur le DATASET le serait.
  A15R2 et A15R1 ne visent pas 60-75 % de gagnants (géométrie : ≈ 33 % et ≈ 50 % au hasard).

(Résultats ci-dessous, ajoutés après le calcul.)

## 2. Résultat du test pré-enregistré H-NUIT (calculé le 17/10, 1 000 tirages placebo)

**Décision selon la règle fixée : H-NUIT NON CONFIRMÉE.** La nuit est un peu meilleure avec A15R2, mais pas
significativement, et pas du tout avec A15R1.

| gestion | fenêtre | n | % gagnants | % placebo (même fenêtre) | écart | R moyen [IC95] | R placebo | p (R) | PF |
|---|---|---|---|---|---|---|---|---|---|
| A15R2 | nuit 0-8 h | 94 | 42,6 % | 35,8 % | +6,8 pts (p 0,089) | +0,246 [−0,03 ; +0,49] | +0,039 | 0,085 | 1,54 |
| A15R2 | reste | 301 | 37,2 % | 35,3 % | +1,9 pts (p 0,23) | −0,007 [−0,18 ; +0,19] | −0,057 | 0,24 | 1,05 |
| A15R1 | nuit 0-8 h | 116 | 50,0 % | 48,7 % | +1,3 pts (p 0,41) | −0,028 [−0,20 ; +0,15] | −0,056 | 0,38 | 0,96 |
| A15R1 | reste | 404 | 49,8 % | 48,2 % | +1,6 pts (p 0,27) | −0,040 [−0,15 ; +0,08] | −0,061 | 0,32 | 0,92 |

- Écart nuit − reste (bootstrap par journée) : A15R2 **+0,25 R [−0,07 ; +0,55], p = 0,061** ;
  A15R1 **+0,01 R [−0,20 ; +0,23], p = 0,46**.
- Par série (A15R2, nuit) : MES sept. +0,28 R (25 trades), MES1 avr.-juil. +0,08 (43), NQ +0,49 (26) : même
  signe partout, mais petits nombres. Avec A15R1 la nuit est négative sur MES1 et NQ.
- Tradeify Select Flex (A15R2 nuit, 3 micros) : P(réussite) 84 % contre 39 % pour son placebo ; mais sur
  94 trades et environ 50 jours, c'est très fragile (le R moyen ne bat pas le hasard à 5 %).
- Lecture : l'avantage de nuit vient des gros gagnants (objectif 2 R), pas d'un taux de réussite élevé.
  Il ne survit pas à un objectif de 1 R. **La nuit ne donne pas 60-75 % de gagnants.**
- Fichiers : `sorties/test_nuit.csv`, `sorties/test_nuit.json`, `sorties/trades_nuit_*.csv`,
  `sorties/placebo_nuit_*.pkl`, `sorties/log_test_nuit.txt`.

## 3. Contextes : balayage avec placebo DANS le même contexte (500 tirages par variante)

**Verdict : aucun contexte ne donne 60-75 % de gagnants nettement au-dessus du placebo. Rien ne survit à la
correction du biais de sélection, et le walk-forward échoue.** C'est un résultat.

Ce qui a été testé (`balayage.py`, 210 variantes, `n_variantes_testees` = 214 avec le test H-NUIT) :
- tous déclencheurs (même union que §1), stop 1,5 ATR, objectif **0,5 R, 0,75 R ou 1 R** (les seules
  géométries qui visent 50-70 % de gagnants : au hasard on a déjà 64 %, 55 % et 48 %) ;
- 12 partitions, seuils fixés à l'avance (ceux de `regimes/etats.py`) : séance (nuit / Londres / US),
  tendance ADX + pente EMA50 (dans le sens / contre / range — proxy du Rangeator, absent du cache), TREND
  15/60/240 alignés, volatilité ATR relative (terciles), ADX ≥ 20, jour de la semaine, position vs Monday H/L,
  pivot weekly, jour précédent (PDH/PDL), session précédente, ORB, dernier climax (dans le sens ≤ 16 barres /
  plus vieux / contre) ; chaque état seul, puis croisé avec la nuit ;
- placebo : mêmes stop / objectif, entrées au hasard de même heure, même sens, **dans le même contexte**.

Chiffres clés (`sorties/balayage_contextes.csv`, `sorties/stabilite_mois.csv`) :
- Sans contexte : 0,5 R → 64,8 % de gagnants contre **64,5 % au hasard**, R −0,04 ; 1 R → 50,0 % contre 48,2 %.
  Le taux de réussite vient bien de la géométrie, pas des confluences.
- La nuit n'aide pas le taux : 0,5 R nuit 64,5 % contre 64,3 % ; 1 R nuit 50,0 % contre 48,7 %.
- 8 variantes sur 210 ont p < 0,05 contre leur placebo (≈ 10 attendues par pur hasard). Meilleure p ajustée
  (test du maximum sur les tirages placebo, type White / Romano-Wolf) : **0,96**.
- Seule piste cohérente d'une géométrie à l'autre : **le range** (tendance = 0). 1 R : 54,6 % contre 47,6 %
  (p 0,034, 183 trades) ; 0,75 R : +5,4 pts (p 0,06) ; 0,5 R : +3,0 pts (p 0,18). Non significatif après correction.
- Walk-forward (5 plis ancrés ; choix sur le passé du contexte au taux 60-75 %, R > 0, meilleur écart au
  placebo) : **51 trades hors échantillon, 51,0 % de gagnants contre 49,5 % au placebo (p 0,44), R −0,12
  (PF 0,88)**. Les contextes choisis changent d'un pli à l'autre (mercredi, nuit + range). Critère 1 raté
  (taux < 60 %, n < 60). Détail : `sorties/walk_forward.csv`, `sorties/trades_wf_oos.csv`.

## 4. Les 3 « meilleures » recettes (en échantillon, NON validées) — 1 000 tirages placebo

Règle de choix écrite avant le balayage complet (`finaliser.py`) : n ≥ 60, taux 60-75 %, R > 0, PF > 1,
écart positif dans presque tous les mois, classement par z contre le placebo. Aucune ne passe les 4 critères :
le R moyen ne bat pas le hasard après correction et le walk-forward échoue.

| recette (registre) | n | % gagnants | % placebo | écart (p) | R moyen [IC95] | PF | P(réussite) Tradeify / placebo |
|---|---|---|---|---|---|---|---|
| WRR-0001 : mercredi, 1,5 ATR / 0,5 R | 138 | 69,6 % | 62,5 % | +7,0 pts (p 0,035) | +0,031 [−0,04 ; +0,10] | 1,28 | 80 % / 8 % (3 micros) |
| WRR-0002 : nuit 0-8 h + range, 1,5 ATR / 0,5 R | 61 | 72,1 % | 62,8 % | +9,3 pts (p 0,065) | +0,055 [−0,09 ; +0,20] | 1,30 | 93 % / 20 % (5 micros) |
| WRR-0003 : dernier climax dans le sens ≤ 16 barres, 1,5 ATR / 0,5 R | 168 | 67,9 % | 65,0 % | +2,8 pts (p 0,14) | +0,012 [−0,10 ; +0,12] | 1,10 | 75 % / 35 % (1 micro) |

p ajustée sur les 210 variantes : 1,00 pour les trois. Les P(réussite) Tradeify sont calculées sur les
trades en échantillon (choisis parmi 210) et sur ≈ 50 jours : elles sont **très optimistes**. Le mercredi n'a
aucune raison économique ; WRR-0003 n'existe que sur sept.-oct. (pas de climax sur MES1).
Registre : WRR-0004 / 0005 (test H-NUIT A15R2 / A15R1), WRR-0006 (walk-forward des contextes).

### Lignes de préréglage (pour tester au testeur sur 3 ans seulement, pas pour trader)
Base commune (= préréglage 23, objectif 0,5 R) :
`sens=Les deux;clx=1;sig=1;sigNiv=Fort + Moyen;hei=1;tl=1;lvl=1;tr=0;feu=0;ema=0;adx=0;det=0;clxF=0;bo=0;maxJour=0;be=0;trail=Aucun;oppArr=0;fin=0;pf=1;part=0;taille=Risque fixe en $;stop=ATR × k;atrK=1.5;tp=En R;tpR=0.5;oppHei=0;risque=150`
1. **Nuit + range** : base + `hr=1;hr1On=1;hr1=0000-0800;hr2On=0`. **Option manquante** : filtre « range » =
   pas d'entrée si (ADX ≥ 20 ET pente EMA50 sur 5 barres > 0 ET clôture HA > EMA50) ni dans le cas miroir
   (pente < 0, clôture HA < EMA50). Sans elle, la ligne n'est que la nuit à 0,5 R (64,5 % = hasard).
2. **Mercredi** : base + `hr=0`. **Option manquante** : filtre jour de la semaine (journée CME, la séance du
   mardi soir 17:00 Chicago compte pour mercredi), clé suggérée `jours=mer`.
3. **Climax récent dans le sens** : base + `hr=0`. **Option manquante** : `clxF` actuel bloque seulement les
   trades CONTRE un climax récent ; il faut un mode qui EXIGE un dernier climax dans le sens de moins de
   16 barres (clé suggérée `clxExige=1;clxAge=16`).
Écart Pine / Python : la stratégie Pine n'a pas les déclencheurs ORB, Detector (rebond, cassure) ni divergence
de l'union Python.

## 5. Limites
- Cache : ≈ 54 journées distinctes en développement (MES1 37, MES 16, NQ 14). Les plus petits effets
  détectables sont ≈ 8-10 points de taux : tout ce qui est plus fin est invisible ici.
- Le Rangeator n'est pas répliqué : « range » = proxy ADX + pente EMA50 + clôture HA (regimes).
- Contextes calculés sur prix causaux ; moteur sur les vrais prix reconstitués (lissés).
- Simulateur : la période MES1 est rapprochée de sept.-oct. par un décalage d'un nombre entier de semaines
  (`commun.pour_simulateur`), pour ne pas compter ~50 journées vides.
- Rien n'a été lu du scellé.

## 6. Relancer (sur le DATASET : ajouter `--source dataset`)
```bash
cd Strat-Botting/recherche/taux_contexte
~/venv-quant/bin/python test_nuit.py            # test pré-enregistré H-NUIT (≈ 1 min)
~/venv-quant/bin/python balayage.py --n 500     # 210 contextes + placebo + walk-forward (≈ 15 min, 9 cœurs)
~/venv-quant/bin/python finaliser.py --registre # 3 recettes, 1 000 tirages, Tradeify, registre
~/venv-quant/bin/python registre_lignes.py      # lignes H-NUIT et walk-forward
```
Seul accès aux données : `commun.charger_series`. Sur le DATASET, H-NUIT (A15R2) et « range » (1 R / 0,75 R)
sont les deux seules hypothèses à retester telles quelles, sans rien rechoisir.
