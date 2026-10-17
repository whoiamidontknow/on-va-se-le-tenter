# Gestion adaptative (ADA) — résultats (17/10/2026)

Code : `ada.py` (règle, 1 seule fonction d'accès aux données `charger_dev`), `decl.py` (déclencheurs), `etude_ada.py`
(`principal`, `robustesse`). Sorties dans `resultats/`. Données : cache 15 m, 75 % développement (scellé intact),
MES1 avr.-juil., MES et MNQ sept.-oct. Entrées 08h-22h Paris, à plat 15:59 Chicago, risque fixe 150 $,
Tradeify Select Flex. Précisions du coordinateur appliquées (obstacle : annuel, mensuel, weekly, Detector, Monday,
sessions, pas les ronds ; marge 4 ticks ; TREND 60 min).

Limites à lire avant les chiffres :
- Très peu de trades (11 à 81). Les écarts sont du bruit tant que le DATASET n'est pas là.
- Le « Feu » est un PROXY (9-12 voix simplifiées, pas les 29 de l'original). ADX/DI : vrais calculs du cache.
- Le prix de stop/objectif est fixé à la clôture du signal ; le moteur entre à l'ouverture suivante : le R réel
  diffère un peu du R planifié. Les pivots et zones Detector du cache sont ceux de l'unique reconstruction.
- Quand il y a peu de trades, la P(réussite) du simulateur est peu fiable (ex. 1,00 avec 9 trades).

## 1. Réglages par défaut de la spécification (adFeu=60, adAdx=25, adNiv=0, adSaute=1, objectifs 1/1,5/2)

| Entrée | Gestion | n | % gagn. | R moy. | PF | P(réuss.) | P(1er payout) | VE $ | sautés |
|---|---|---|---|---|---|---|---|---|---|
| A climax BUY + TREND 1H | (a) adaptatif | 11 | 55 | +0,30 | 1,64 | 1,00* | 1,00* | +5961* | 66 % |
| | (b) 2 ATR / 1,5R | 29 | 55 | +0,40 | 2,01 | 1,00* | 1,00* | +6482* | |
| | (c) 2 ATR / 1R | 36 | 64 | +0,31 | 1,99 | 1,00* | 1,00* | +9324* | |
| | (d) placebo adapt. | 10 | 53 | +0,16 | 1,75 | 0,57 | 0,57 | +2312 | |
| flip Heishinator | (a) | 21 | 38 | −0,31 | 0,52 | 0,00 | 0,00 | −165 | 83 % |
| | (b) | 110 | 43 | −0,06 | 0,88 | 0,00 | 0,00 | −165 | |
| | (c) | 115 | 50 | −0,03 | 0,94 | 0,00 | 0,00 | −165 | |
| | (d) | 24 | 44 | −0,12 | 0,83 | 0,03 | 0,03 | −137 | |
| Signator Fort | (a) | 13 | 38 | −0,23 | 0,63 | 0,00 | 0,00 | −165 | 84 % |
| | (b) | 80 | 40 | −0,06 | 0,89 | 0,00 | 0,00 | −165 | |
| | (c) | 80 | 48 | −0,07 | 0,86 | 0,00 | 0,00 | −165 | |
| | (d) | 16 | 43 | −0,12 | 0,89 | 0,00 | 0,00 | −164 | |
| cassure trendline | (a) | 11 | 45 | −0,14 | 0,75 | 0,00 | 0,00 | −165 | 84 % |
| | (b) | 64 | 42 | −0,01 | 0,98 | 0,01 | 0,01 | −163 | |
| | (c) | 65 | 46 | −0,12 | 0,78 | 0,00 | 0,00 | −165 | |
| | (d) | 13 | 41 | −0,15 | 0,87 | 0,01 | 0,01 | −157 | |
| union | (a) | 67 | 49 | +0,003 | 1,01 | 0,15 | 0,12 | −23 | 79 % |
| | (b) | 223 | 41 | −0,03 | 0,95 | 0,08 | 0,04 | −129 | |
| | (c) | 251 | 49 | −0,04 | 0,91 | 0,09 | 0,04 | −129 | |
| | (d) | 66 | 45 | −0,09 | 0,85 | 0,14 | 0,12 | +2 | |

(* échantillon de 9 à 24 trades : chiffres propfirm sans valeur.) Placebo = 500 tirages (propfirm : 20 premiers).
p-valeur contre le placebo (R moyen) pour (a) : A 0,33 ; Heishinator 0,83 ; Signator 0,84 ; trendline 0,49 ;
union 0,20. **Aucune entrée ne bat son placebo avec les réglages par défaut.**

Distribution des objectifs (défaut) : union 36 % à 1R, 13 % à 1,5R, 24 % à 2R, 27 % « obstacle ». Score C :
union C0 18 %, C1 18 %, C2 24 %, C3 40 %. Fichiers : `resultats/principal.csv`, `distribution_objectifs.csv`.
Walk-forward 5 plis (`walk_forward.csv`, réglages non ajustés donc mesure de stabilité) : union (a) négatif sur
5 plis sur 5 (−0,66 ; −0,61 ; −0,17 ; −0,02 ; −0,23), contre (b) 2 plis positifs sur 5.

## 2. Robustesse (16 variantes, tableau complet `resultats/robustesse.csv`)
Variantes : adNiv 0/1 × adSaute 0/1, adFeu 50/70, adAdx 20/30, objectifs (1;1,25;1,5), à adNiv 0 et 1.
Résumé (R moyen, 5 entrées regroupées / union) :
- adSaute=0 (ne pas sauter) : R −0,04 / −0,07 : le gain apparent vient seulement de la sélection par saut, sans
  saut l'adaptatif perd comme le fixe.
- adNiv=1 mieux que adNiv=0 (union +0,06 contre +0,00) ; adFeu et adAdx : aucun effet net (variations ≤ 0,02 R).
- Objectifs (1;1,25;1,5) mieux que (1;1,5;2) : union +0,08 (adNiv=1) ; P(1er payout) 0,22.
- **Bootstrap de White** (gain par signal contre fixe 2 ATR/1,5R, signal sauté = 0 R, 16 variantes) : meilleure =
  `adNiv=1, adSaute=1, objectifs 1;1,25;1,5`, gain +0,036 R par signal, **p = 0,49**. Rien n'est significatif.

## 3. Variante à garder (provisoire)
`adFeu=60;adAdx=25;adK=2;adKbas=2.5;adKhaut=1.5;adR1=1;adR2=1.25;adR3=1.5;adNiv=1;adSaute=1`
Chiffres (union, n=81) : 54 % gagnants, R +0,08, PF 1,17 ; placebo même gestion 44,7 % gagnants, R −0,12 (écart
+9,6 points, p = 0,038 gagnants, p = 0,030 R) ; Tradeify : P(réussite) 0,27, P(1er payout) 0,21, VE +98 $
(le fixe 2 ATR/1,5R : P 0,08, VE −129 $). 76 % des signaux sautés. Walk-forward : 4 plis sur 5 négatifs
(−0,41 ; −0,54 ; +0,09 ; −0,22 ; −0,40). Par entrée : climax+TREND 61 % gagnants (n=13, p=0,06 contre placebo),
les autres entrées ne battent pas le placebo.
Pour `f_pr_def` : `stop=Adaptatif;tp=Adaptatif;adFeu=60;adAdx=25;adK=2;adKbas=2.5;adKhaut=1.5;adR1=1;adR2=1.25;adR3=1.5;adNiv=1;adSaute=1;slA=1;slM=1;slW=1;slD=1;slMo=1;slSe=1;slRo=0;slMin=1;slMax=3;slMarge=0.1;prio=annuel > mensuel > detector > weekly > monday > session;tpA=1;tpM=1;tpW=1;tpD=1;tpMo=1;tpSe=1;tpRo=0;tpMarge=0.1;taille=Risque fixe en $;risque=150;pf=1` (marge 4 ticks = 1 point sur MES/MNQ : à régler en ticks, `margeU=Ticks`).

## 4. Verdict honnête
1. L'adaptatif **ne bat pas clairement le fixe** : avec les réglages de la spécification il fait à peine mieux que
   le fixe sur l'union (R 0,00 contre −0,03) et pire sur les entrées isolées. Son « avantage » vient du filtre
   (on saute 65 à 84 % des signaux quand un niveau est à moins de 1R) et non de la gestion du stop ou de l'objectif.
2. Le taux de gagnants monte (49 à 54 % contre 41 % pour 2 ATR/1,5R) surtout parce que l'objectif est plus court.
   À 1R fixe on gagne aussi 49 % : l'adaptatif n'ajoute rien de net à géométrie égale.
3. Contre le placebo : seule la variante retenue passe (p ≈ 0,03), mais elle a été choisie parmi 16 et White
   donne p = 0,49 ; walk-forward négatif sur 4 plis sur 5. **Non prouvé.** À refaire sur le DATASET (≈ 1,7 an).
4. Seul fait utile : le saut quand un niveau bloque à moins de 1R n'est pas mauvais, mais il divise le nombre de
   trades par 3 à 5, ce qui pose un problème de fréquence pour la propfirm.
