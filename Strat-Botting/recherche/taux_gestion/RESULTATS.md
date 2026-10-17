# Taux — géométrie et gestion (agent WRS) — résultats

**État : fini sur le cache de développement (17/10). Scellé jamais ouvert. À relancer sur le DATASET.**

## La réponse courte

**Aucune gestion ne remplit les quatre critères hors échantillon.** On obtient facilement 60 à 75 % de gagnants avec
une espérance positive EN échantillon, mais :

1. **Le taux vient de la géométrie, pas de l'entrée.** Sur le panel (12 entrées réelles × 264 gestions), le taux réel
   dépasse le placebo de même gestion de **+2 points en moyenne** (maximum +5). Exemple, stop 2 ATR : objectif 0,3 R
   → 76 % réel contre 75 % placebo ; partiel 0,5 R + reste à 15:59 → 68 % contre 65 %.
2. **En walk-forward, ça ne tient pas.** La gestion choisie sur l'apprentissage (taux 60-75 %, meilleur R) donne sur
   le test 38 à 59 % de gagnants pour les 8 déclencheurs de SOR, toujours SOUS le placebo (−4 à −22 points), R < 0.
   ML-0001 : 55 % contre 55 %, R −0,02 (103 trades). Choisir une seule gestion pour tout le panel ne change rien.
3. **Biais de sélection** : bootstrap de White sur les 911 combinaisons « dans la bande » (≥ 20 trades) : meilleur R
   +0,84 (EXH-0003), **p = 0,14** → indiscernable de la chance.
4. **Propfirm** : un taux élevé obtenu par la géométrie n'aide pas. Entrées au hasard : P(réussite) Tradeify reste
   entre 0,02 et 0,28, que le taux soit 35 % ou 76 %. P suit l'espérance (R), pas le taux.

## Méthode

- Données : `donnees_wrs.charger(ut)` (seul accès ; réutilise `recherche/sorties/donnees_sor` + `etude.preparer`),
  partie développement. 15m : MES1 avr.-juin, MES et MNQ sept.-oct. ; 30m et 60m pour EXH.
- Entrées (13) : les 8 déclencheurs de SOR (dont climax BUY = SOR-0001, climax BUY + TREND 1H = SOR-0002 = préréglage A,
  flip Heishinator = SOR-0003), un témoin AU HASARD, ML-0001, EXH-0001/0002 (30m), EXH-0003 (60m) (entrées du
  registre reconstruites depuis leurs trades, 100 % retrouvées). Entrées 08:00-22:00 Paris pour les déclencheurs SOR,
  heures d'origine pour les entrées du registre ; toujours à plat 15:59 Chicago.
- Gestions (264) : stop 1,5 / 2 / 3 ATR (posé depuis la clôture du signal, comme STRATEGIE_V1) × 88 sorties :
  objectif 0,3-2 R ; break-even à 0,3 / 0,5 / 0,75 / 1 R avec +2 ou +4 ticks, puis Heishinator, 1-2 R ou suiveur ;
  partiel 50 % (ou 75 %) à 0,3 / 0,5 / 0,7 R puis stop à l'entrée +2 ticks et reste au Heishinator / suiveur 2-3 ATR /
  1,5-2 R / 15:59 / 16 barres ; suiveur ATR 1-3 (sur clôture, comme Pine) ; sortie après 4 / 8 / 16 barres ;
  objectif sur le prochain niveau (pivots, Detector, sessions, swing, ronds, tous) à ratio minimum 0,3 / 0,5 / 0,75 + Heishinator.
- **Placebo de même gestion** : chaque trade réel remplacé par une entrée au hasard (même série, même heure de Paris,
  même sens, mêmes heures autorisées, même gestion). Balayage : 2 000 tirages lus dans une table « issue de chaque
  barre » calculée par le moteur (vérifiée : 450 / 450 identiques au backtest à signal unique). Finalistes :
  `moteur.reference_hasard` exact, 500 tirages (walk-forward) et 1 000 (recettes).
- Walk-forward : 5 plis, blocs de journées, apprentissage 3 blocs, test le bloc suivant.
- Propfirm : `simulateur.py`, `tradeify_50k_select_flex` (DD 2 000 $ EOD, constance 40 %), `optimise_taille`
  (1 à 20 micros) et risque fixe 100-400 $ ; même taille pour 20 tirages au hasard.

## 1. La frontière (panel des 12 entrées réelles, moyenne par gestion)

| gestion | taux réel | taux placebo | écart | R réel | R placebo | témoin hasard : taux / R |
|---|---|---|---|---|---|---|
| 2 ATR + Heishinator (référence) | 37 % | 37 % | 0 | +0,18 | +0,15 | 35 % / +0,14 |
| 2 ATR + objectif 2 R | 44 % | 41 % | +2 | +0,16 | +0,06 | 37 % / −0,05 |
| 2 ATR + BE 1 R (+4 t) + Hei | 53 % | 48 % | +4 | +0,16 | +0,13 | 49 % / −0,02 |
| 2 ATR + objectif 1 R | 54 % | 50 % | +4 | +0,09 | −0,01 | 47 % / −0,06 |
| 2 ATR + BE 0,5 R (+4 t) + Hei | 63 % | 61 % | +2 | +0,13 | +0,08 | 63 % / −0,03 |
| 2 ATR + BE 0,5 R (+4 t) + 2 R | 64 % | 62 % | +2 | +0,10 | +0,04 | 61 % / −0,09 |
| 2 ATR + objectif niveau proche (tous, ≥ 0,3 R) + Hei | 64 % | 63 % | +1 | +0,04 | −0,01 | 65 % / +0,03 |
| 2 ATR + partiel 0,5 R + reste à 15:59 | 68 % | 65 % | +3 | +0,09 | +0,03 | 67 % / −0,01 |
| 2 ATR + objectif 0,5 R | 66 % | 65 % | +1 | +0,01 | −0,02 | 64 % / −0,02 |
| 2 ATR + partiel 0,3 R + suiveur 3 ATR | 74 % | 72 % | +2 | +0,04 | +0,02 | 76 % / −0,03 |
| 2 ATR + objectif 0,3 R | 76 % | 75 % | +1 | 0,00 | −0,02 | 76 % / −0,02 |

Par famille, écart moyen réel − placebo : partiel +2,4 pts, objectif R +2,1, temps +2,0, break-even +1,3,
objectif sur niveau +0,7, suiveur +0,6. Aucune famille ne crée de taux « vrai ». Fichiers : `frontiere_panel.csv`,
`frontiere_familles.csv`, `balayage.csv` (3 432 lignes).

À retenir sur les leviers :
- **Partiel tôt** : 0,3 R → ~74 %, 0,5 R → ~67 %, 0,7 R → ~60 % ; le reste (Hei, suiveur, 2e objectif, 15:59) change
  peu le taux, un peu le R. Pas mieux qu'un simple objectif court ou un break-even.
- **Break-even : les ticks comptent.** À +2 ticks, la sortie au BE est perdante après glissement et commission sur
  MNQ, et quasi nulle sur MES : BE 0,5 R + Hei = 47 % de gagnants à +2 ticks, 63 % à +4 ticks. Dans
  STRATEGIE_V1, `x_beTk` vaut 1 par défaut : le BE y est presque toujours une petite perte.
- **Suiveur ATR, sortie au temps** : le taux reste autour de 50 % ou moins (suiveur 39-49 %, 4-16 barres 45-51 %).
- **Objectif sur niveau proche à ratio faible** : taux = placebo (+1 pt). Le niveau n'apporte rien au taux.
- **Témoin au hasard** : même frontière que les vraies entrées. 1,5 % de ses gestions ont p ≤ 0,05 (calibrage correct).

## 2. Walk-forward (hors échantillon), placebo exact `reference_hasard` 500 tirages

| choix de la gestion | entrée | n | taux | placebo | écart pts | p | R | R placebo | P Tradeify / hasard |
|---|---|---|---|---|---|---|---|---|---|
| par entrée | ML-0001 | 103 | 55 % | 55 % | +0,5 | 0,45 | −0,02 | −0,02 | 0,11 / 0,11 |
| par entrée | flip Hei (SOR-0003) | 87 | 49 % | 57 % | −7,3 | 0,89 | −0,19 | −0,06 | 0,07 / 0,04 |
| par entrée | climax BUY (SOR-0001) | 36 | 50 % | 60 % | −10,0 | 0,95 | −0,25 | −0,06 | 0,00 / 0,06 |
| par entrée | préréglage A (SOR-0002) | 26 | 46 % | 59 % | −13,2 | 0,96 | −0,09 | +0,07 | 0,00 / 0,24 |
| par entrée | Signator Fort | 56 | 59 % | 63 % | −4,2 | 0,75 | −0,09 | −0,05 | — |
| par entrée | témoin hasard | 129 | 57 % | 60 % | −2,4 | 0,74 | −0,11 | −0,03 | 0,11 / 0,08 |
| par entrée | EXH-0001 | 22 | 73 % | 51 % | +22,0 | 0,004 | +0,34 | −0,02 | 1,00 / 0,27 |
| par entrée | EXH-0003 | 16 | 75 % | 55 % | +19,5 | 0,04 | +0,58 | +0,26 | 1,00 / 0,66 |
| une pour tout le panel | ML-0001 | 169 | 63 % | 62 % | +0,5 | 0,47 | −0,01 | +0,02 | 0,25 / 0,34 |
| une pour tout le panel | EXH-0001 | 23 | 78 % | 65 % | +13,6 | 0,06 | +0,12 | −0,02 | 1,00 / 0,31 |

Les autres lignes (tl, orb, mon, clx SELL, EXH-0002) sont pires : `final.csv`. EXH-0001/0003 sont les seules pistes,
mais 16 à 23 trades (critère : 60) et leurs ENTRÉES ont été choisies parmi 5 152 variantes sur ces mêmes données
(seule la gestion est hors échantillon ici).

## 3. Hypothèse fixée à l'avance : « la nuit (0-8 h Paris) est meilleure »

Testée sur ML-0001 (seule entrée qui trade la nuit), pour chacune des 264 gestions, sans réglage (`nuit.py`) :
la nuit fait MOINS bien que le jour dans 79 % des gestions (R moyen nuit +0,02 contre placebo −0,02 ; jour +0,08
contre −0,02 ; gestions à p ≤ 0,05 : nuit 1 %, jour 20 %). **Non confirmée.**

## 4. Les 3 recettes « les moins mauvaises » (aucune ne passe ; registre WRS-0001 à 0003)

Gestion FIXE (telle qu'écrite dans le préréglage). « Éch. » = tout le développement (choix fait sur ces données,
donc optimiste) ; placebo exact `reference_hasard` 1 000 tirages ; « WF » = gestion choisie à chaque pli.
P Tradeify en échantillon, taille `optimise_taille`.

| | recette | n | taux / placebo | écart (p) | R / placebo (p) | PF $ | WF : taux / placebo, R | P Tradeify / hasard |
|---|---|---|---|---|---|---|---|---|
| WRS-0001 | ML-1, stop 3 ATR, objectif 0,5 R | 177 | 69 % / 61 % | +7,8 (0,013) | +0,07 / −0,05 (0,008) | 1,36 | 55 % / 55 %, −0,02 | 0,96 / 0,19 (2 micros) |
| WRS-0002 | ML-1, stop 3 ATR, BE 0,5 R +4 ticks, objectif 2 R | 127 | 68 % / 60 % | +7,5 (0,035) | +0,16 / −0,02 (0,021) | 1,48 | 55 % / 55 %, −0,02 | 0,86 / 0,28 (1 micro) |
| WRS-0003 | préréglage A, stop 3 ATR, BE 0,5 R +2 ticks, objectif 1 R | 29 | 69 % / 55 % | +14,2 (0,013) | +0,36 / +0,06 (0,002) | 3,18 | 46 % / 59 %, −0,09 | 1,00 / 0,28 (3 micros) |

WRS-0001/0002 remplissent les critères 1 à 3 EN échantillon (n ≥ 60, taux dans la bande, R > 0, écart significatif),
mais pas en walk-forward, et pas après la correction de White : **piste à revérifier sur le DATASET, pas une
recette.** WRS-0003 : 29 trades, échoue en walk-forward.

### Lignes de préréglage pour `f_pr_def()` (STRATEGIE_V1.pine, à ajouter aussi au menu)

```
nom == "25 WRS-1 ML-1 · SL 3 ATR · TP 0,5R" ? "sens=Les deux;clx=1;sig=1;sigNiv=Fort + Moyen;hei=1;tl=1;lvl=1;tr=0;feu=0;ema=0;adx=0;det=0;clxF=0;bo=0;maxJour=0;be=0;trail=Aucun;oppArr=0;fin=0;pf=1;part=0;hr=0;taille=Contrats fixes;stop=ATR × k;atrK=3;tp=En R;tpR=0.5;oppHei=0" :
nom == "26 WRS-2 ML-1 · SL 3 ATR · BE 0,5R · 2R" ? "sens=Les deux;clx=1;sig=1;sigNiv=Fort + Moyen;hei=1;tl=1;lvl=1;tr=0;feu=0;ema=0;adx=0;det=0;clxF=0;bo=0;maxJour=0;be=1;beR=0.5;beTk=4;trail=Aucun;oppArr=0;fin=0;pf=1;part=0;hr=0;taille=Contrats fixes;stop=ATR × k;atrK=3;tp=En R;tpR=2;oppHei=0" :
nom == "27 WRS-3 A · SL 3 ATR · BE 0,5R · 1R" ? "sens=Long seulement;clx=1;sig=0;hei=0;tl=0;lvl=0;tr=1;feu=0;ema=0;adx=0;det=0;clxF=0;bo=0;maxJour=0;be=1;beR=0.5;beTk=2;trail=Aucun;oppArr=0;fin=0;pf=1;part=0;hr=1;hr1On=1;hr1=0800-2200;hr2On=0;taille=Contrats fixes;stop=ATR × k;atrK=3;tp=En R;tpR=1;oppHei=0" :
```
Taille : « Contrats fixes » = 2 (WRS-1), 1 (WRS-2), 3 (WRS-3) dans la boîte de dialogue, faute de clé (voir plus bas).
Le risque fixe en $ est moins bon ici : avec un stop de 3 ATR, 1 micro risque déjà ~160 $ (médiane), donc un risque
fixe de 150-200 $ saute la moitié des trades. Les entrées ML-1 reprennent celles du préréglage 23.

### Options à ajouter dans STRATEGIE_V1.pine (pour le coordinateur)

1. **Clé `beTk`** (indispensable pour WRS-2 et WRS-3) : lire `x_beTk` par le préréglage, comme les autres
   nombres : `var int x_beTkE = int(f_gf("beTk", x_beTk))`, et utiliser `x_beTkE` aux deux endroits du stop au
   break-even (≈ lignes 1717 et 1722). Sans elle, le BE garde 1 tick et devient une perte après frais.
2. **Clé `qFixe`** : nombre de contrats fixes (`q_fixe`) réglable par préréglage.
3. (Testée, pas retenue, utile pour comparer au testeur) **Sortie partielle en R** : clé `partR` (0 = coupé) ;
   quand le gain latent atteint `partR` × risque, sortir `partPct` % de la position (au moins 1 contrat, il en faut
   2), puis stop à l'entrée + `beTk` ticks si `partBE` ; le reste sort par l'objectif (En R), le suiveur, les signaux
   ou 15:59. Aujourd'hui la partielle n'existe qu'avec « Prochain niveau ».
4. (Testée, pas retenue) **Sortie temporelle** : clé `nBar`, sortie à l'ouverture après N bougies en position.
   Le suiveur « sous chaque nouveau swing » n'a pas pu être testé (absent du moteur commun).

## Limites

Cache seulement (MES1 avr.-juin, MES/MNQ 3 semaines en sept.-oct.), 13 à 250 trades par entrée, période plutôt
haussière (le placebo long a souvent un R positif). Les P Tradeify en échantillon (0,86-1,00) sont très optimistes ;
ceux du walk-forward sont la bonne lecture. Placebo restreint à la même période que les signaux pour les recettes,
au même bloc de test pour le walk-forward. Le partiel est fractionnaire dans le moteur (arrondi aux contrats en vrai).

## Reproduire (DATASET : préfixer `WRS_SOURCE=dataset`)

    ~/venv-quant/bin/python etude_wrs.py            # verif, balayage, synthese, wf, final (~4 min)
    ~/venv-quant/bin/python nuit.py                 # hypothèse nuit
    ~/venv-quant/bin/python propfirm_frontiere.py   # taux contre P(réussite)
    ~/venv-quant/bin/python recettes.py --registre  # 3 recettes + registre

Fichiers : `resultats/balayage.csv` (tout le balayage), `frontiere_*.csv`, `wf_*.csv`, `final.csv`, `recettes.csv`,
`propfirm_frontiere.csv`, `nuit_ML-0001.csv`, `white.pkl`.
