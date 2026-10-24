# Taux — combinatoire de confluences (WRX) — résultats

Données : `cache` (séries Python, vrais prix reconstitués), **développement seulement** (75 %, scellé non ouvert) :
15 min MES (15/09→06/10), NQ (18/09→07/10), MES1 (29/04→18/06) ; 30 min MES/NQ (sept.) ; 60 min MES/NQ
(13/08→29/09). Micros MES / MNQ, coûts du moteur, à plat 15:59 Chicago. 17/10/2026.

## Verdict

**Rien ne passe les quatre critères.** Le critère 1 (60-75 % de gagnants HORS échantillon, au-dessus du placebo)
échoue nettement :

- **Walk-forward de la procédure** (choisir sur 3 blocs la variante éligible — 60-75 % de gagnants, R > 0,
  PF > 1, n ≥ 25 — de plus fort écart de taux contre son placebo, la jouer sur le bloc suivant, 4 plis) :
  **39 % de gagnants contre 49 % au placebo (−9 points), R −0,29, PF 0,46, n = 99**. Les 10 premières de chaque
  pli : 40 % contre 47 %, R −0,26 (n = 538).
- **Bootstrap de White** (studentisé, blocs de 5 jours, 1 000 tirages) sur les 488 002 variantes à ≥ 30 trades :
  meilleure t = 4,2, **p = 0,17** pour l'écart de taux, **p = 0,21** pour l'écart de R. Le meilleur résultat du
  balayage s'explique par le nombre d'essais.
- Les trois meilleures recettes du développement battent leur placebo une à une (p = 0,002 sur 500 tirages du
  moteur), mais leur p corrigée par White vaut 0,51 à 0,60.

C'est le piège annoncé : on trouve facilement 70 % de gagnants et un écart de +20 points sur le passé quand on
essaie 1,5 million de combinaisons ; cela ne tient pas sur la période suivante.

## Méthode

1. **Tables d'issues par le moteur commun** (`tables.py`) : pour chaque jeu × géométrie, issue d'un trade pris sur
   CHAQUE bougie, dans chaque sens, calculée par `moteur.backtest` (un signal toutes les K > 1 jour de bougies,
   K passes). Les trades d'une variante = les lignes de la table à ses signaux, avec la règle « une position à la
   fois » du moteur. **Vérifié : 126 / 126 cas identiques au moteur** (barre, sens, R au 1e-9). Les 3 finalistes
   sont rejoués directement par le moteur (mêmes n et R).
2. **Placebo exact de même géométrie** : `moteur.reference_hasard` tire, pour chaque signal, une bougie de même
   heure (Paris) et de même sens ; sa moyenne exacte est la moyenne de la table sur ces bougies. Écart de taux =
   taux réel − taux placebo, avec son z. Contrôle : sur les finalistes, placebo analytique 50,0 / 59,3 / 44,6 % et
   moyenne de 500 tirages du moteur 50,2 / 59,6 / 44,6 %.
3. **Balayage** (`balayage.py`) : 6 déclencheurs de STRATEGIE_V1 (Signator Fort, flip Heishinator, cassure
   trendline, cassure sessions/Monday « une fois par niveau », climax, et l'union des cinq) × 3 sens × 3 UT
   (15/30/60 min) × 527 jeux de 0 à 3 filtres (au plus un par groupe : Feu 50/60/70 %, TREND 60/240, EMA50,
   ADX ≥ 20/25, Detector place ≥ 1/2 ATR, climax pas contre, blackout, plages 0-8 h / 8-14 h 30 / 14 h 30-8 h /
   15 h 30-22 h) × 56 géométries (stop 1/1,5/2/3 ATR × objectif 0,5/0,75/1/1,5 R × rien / break-even 0,5 R /
   sortie Heishinator / sortie après 2 h). **n_variantes_testees = 1 497 888** ; 735 840 avec ≥ 20 signaux.
4. **Sélection** (`analyse.py`) : White sur les séries journalières d'écart (taux et R) ; walk-forward 7 blocs de
   journées par jeu (`walk_forward(k=4, ratio=3)`). `complements.py` : contrôles déclarés à l'avance.
5. **Finalistes** (`finalistes.py`) : 3 meilleures du développement (une par famille), moteur, 500 tirages de
   `reference_hasard` par jeu, `optimise_taille` Tradeify Select Flex (1-10 micros), même simulateur sur 100
   tirages au hasard à la même taille.

## Ce que montre la carte (développement, variantes à ≥ 30 trades, toutes très corrélées)

- La **géométrie** fixe le taux : objectif 0,5 R → 65 % de gagnants (placebo 62 %) ; 1 R → 50 % (48 %) ;
  1,5 R → 43 % (42 %). Le placebo seul est dans la bande 60-75 % pour 16 % des variantes.
- Écart médian contre le placebo : +3,6 points de taux, +0,07 R ; positif pour 72 % des variantes **sur le
  passé**. Par déclencheur : cassure sessions/Monday +6,3 pts, Heishinator +3,8, union +3,6, climax +1,3,
  Signator Fort −1,6, trendline −1,9. Sortie après 2 h : +5,1 pts ; break-even : +1,7 pts.
- **Mais cela ne se prolonge pas** : les variantes éligibles sur l'apprentissage font, sur le bloc suivant,
  un écart médian de −9,8 / −4,7 / +6,0 / +2,6 points selon le pli (`sorties/complements.txt`, §2).
- Sensibilité du walk-forward (déclarée à l'avance, 6 versions) : la meilleure version (n ≥ 80 à
  l'apprentissage, classement prudent) donne 54 % contre 52 % au placebo, R −0,00, n = 104. Aucune n'atteint
  60 % hors échantillon.

## Hypothèse fixée à l'avance : la nuit (0 h-8 h Paris) est meilleure

Testée sans rien régler (même déclencheur, même géométrie, trades de nuit contre les autres, chacun contre son
placebo de même heure) : **la nuit fait mieux dans 76 % des 1 567 cas**, écart de taux +5,8 points et R +0,10 en
médiane (15 min : 80 % des cas ; 30 min : 92 % ; 60 min : 57 %). Exception nette : le climax (pire la nuit dans
100 % des cas). Les cas ne sont pas indépendants (mêmes trades vus par 56 géométries) : c'est un signe cohérent
avec `meta_ml`, pas une preuve. **À tester en premier sur le DATASET**, tel quel.

## Les 3 meilleures recettes du développement — REJETÉES (registre WRX-0001 à 0003)

Chiffres sur tout le développement (dans l'échantillon). Placebo = 500 tirages `reference_hasard`. Tradeify =
Select Flex, taille optimisée en micros, comparée au hasard à la même taille. Hors échantillon : voir le verdict
(la procédure qui les choisit échoue).

| # | recette | n | gagnants | placebo | écart | p | R | PF | White p | Tradeify P / 1er payout / VE | hasard |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | union des 5, 15 min, TREND 240 + Detector 2 ATR + 15 h 30-22 h, SL 2 ATR, TP 1 R, sortie 2 h | 74 | 74 % | 50 % | +24 | 0,002 | +0,32 | 2,55 | 0,51 | 0,99 / 0,99 / +7 616 $ (4 micros) | 0,18 / 0,11 / +136 $ |
| 2 | union des 5, 15 min, Feu ≥ 60 % + Detector 2 ATR + 14 h 30-8 h, SL 2 ATR, TP 0,5 R, sortie 2 h | 238 | 71 % | 60 % | +11 | 0,002 | +0,09 | 1,45 | 0,57 | 0,95 / 0,94 / +4 505 $ (2) | 0,22 / 0,17 / +225 $ |
| 3 | flip Heishinator, 15 min, Detector 2 ATR + blackout + 14 h 30-8 h, SL 3 ATR, TP 1,5 R | 71 | 65 % | 45 % | +20 | 0,002 | +0,28 | 2,38 | 0,60 | 0,92 / 0,88 / +4 530 $ (2) | 0,30 / 0,22 / +463 $ |

La n° 2 est la plus « large » (238 trades, écart positif dans les 7 blocs chronologiques, MES 69 % / NQ 78 %) :
c'est celle à regarder en premier au testeur, mais elle reste un produit du balayage (White p = 0,57). Les
P(réussite) Tradeify de 0,92-0,99 viennent du rééchantillonnage de 3 à 7 semaines de trades : ils ne valent pas
plus que le R qui les produit.

### Lignes de préréglage (`f_pr_def`) — pour le testeur TradingView, PAS pour du réel

1. `sens=Les deux;clx=1;sig=1;sigNiv=Fort seulement;hei=1;tl=1;lvl=1;feu=0;tr=1;ema=0;adx=0;det=1;detK=2;clxF=0;bo=0;hr=1;hr1On=1;hr1=1530-2200;hr2On=0;maxJour=0;taille=Contrats fixes;stop=ATR × k;atrK=2;tp=En R;tpR=1;trail=Aucun;oppArr=0;fin=0;pf=1;part=0;be=0;oppHei=0`
2. `sens=Les deux;clx=1;sig=1;sigNiv=Fort seulement;hei=1;tl=1;lvl=1;feu=1;feuMode=Part dans le sens ≥ seuil;feuSeuil=60;tr=0;ema=0;adx=0;det=1;detK=2;clxF=0;bo=0;hr=1;hr1On=1;hr1=1430-0800;hr2On=0;maxJour=0;taille=Contrats fixes;stop=ATR × k;atrK=2;tp=En R;tpR=0.5;trail=Aucun;oppArr=0;fin=0;pf=1;part=0;be=0;oppHei=0`
3. `sens=Les deux;clx=0;sig=0;hei=1;tl=0;lvl=0;feu=0;tr=0;ema=0;adx=0;det=1;detK=2;clxF=0;bo=1;hr=1;hr1On=1;hr1=1430-0800;hr2On=0;maxJour=0;taille=Contrats fixes;stop=ATR × k;atrK=3;tp=En R;tpR=1.5;trail=Aucun;oppArr=0;fin=0;pf=1;part=0;be=0;oppHei=0`

**Options manquantes ou réglages à la main (ne pas approcher en silence)** :
- **Sortie temporelle (recettes 1 et 2)** : absente de STRATEGIE_V1. Il faut une option « sortir au marché à
  l'ouverture de la bougie qui suit N bougies de position » (N = 8 en 15 min = 2 h ; moteur : `sortie_barres`,
  priorité heure propfirm > signal > temps), avec sa clé de préréglage (ex. `tps=1;tpsN=8`). Sans elle, les
  lignes 1 et 2 ne reproduisent PAS la recette.
- Recette 1 : « TREND : unité » = 240 à régler à la main (non pilotable par préréglage).
- Recettes 1 et 2 : « Niveaux mesurés sur » = Vrais prix à la main (cassures de sessions/Monday mesurées sur vrais
  prix ici) ; Feu : le cache n'a qu'un substitut de Feu (8-16 voix), le seuil 60 % du Pine porte sur 29 voix.
- Taille : 4 / 2 / 2 micros dans « Contrats fixes » (non pilotable par préréglage).

## Limites

- 3 à 7 semaines par jeu ; 15/30 min surtout en septembre (haussier). Les blocs de walk-forward font 2 à 5 jours :
  les tests hors échantillon sont petits (8 à 65 trades par pli).
- Cache : pas de flèches Signator « Moyen » (Fort + Moyen = Fort ici), pas de volume sur MES1 (ni climax ni
  Detector : ces filtres y laissent tout passer), Feu de substitution, zones Detector sur bougies HA.
- Placebo des plis du walk-forward : moyenne sur tout le développement (pas seulement le bloc test). Vu l'écart
  (−9 points), cela ne change pas la conclusion.
- p minimum = 0,002 avec 500 tirages.

## Relancer sur le DATASET (environ 3 minutes ici)

```
cd KAIROS/recherche/taux_combinatoire
WRX_SOURCE=dataset ~/venv-quant/bin/python tables.py        # tables + vérification contre le moteur
WRX_SOURCE=dataset ~/venv-quant/bin/python balayage.py
WRX_SOURCE=dataset ~/venv-quant/bin/python analyse.py
WRX_SOURCE=dataset ~/venv-quant/bin/python complements.py
WRX_SOURCE=dataset ~/venv-quant/bin/python finalistes.py --registre
```
Tout l'accès aux données passe par `donnees_wrx.charger_jeux(source)` (qui réutilise `exhaustif/donnees_exh`).

## Fichiers

Code : `donnees_wrx.py`, `bib_wrx.py` (déclencheurs, filtres, géométries, table d'issues), `tables.py`,
`balayage.py`, `analyse.py`, `complements.py`, `finalistes.py`. Sorties : `sorties/balayage_complet.csv.gz`
(735 840 variantes évaluées, 38 Mo), `candidats.csv` (200 premières éligibles), `wf_procedure.csv`,
`complements.txt`, `finalistes.csv` ; intermédiaires recalculables ignorés par git (`sorties/.gitignore`).
