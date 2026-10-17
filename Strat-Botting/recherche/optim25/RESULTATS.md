# Optimiseur 25 (OPT) — voisinage du préréglage 25

Une commande, 6 minutes sur le cache (10 coeurs) :

```
cd Strat-Botting/recherche/optim25
~/venv-quant/bin/python optimiser.py --source cache      # essai à blanc (fait le 17/10/2026)
~/venv-quant/bin/python optimiser.py --source dataset    # dès que le DATASET 15 min est exporté (même code)
# options : --recalcul (refaire les tables d'issues), --registre (écrit la meilleure au registre, préfixe OPT)
```
Le DATASET est lu comme pour les autres agents : `~/Ephore/Strat-Botting-data/*.csv` via `dataset/charger.py`
(fonction `charger()` du script = seul point d'accès). Il faut des fichiers 15 min MES et/ou NQ. Sur le DATASET,
la règle exige n >= 80 (30 sur le cache) ; pense à regarder aussi `sorties/resume_dataset.txt`. Le premier
passage refait les tables (quelques minutes de plus avec 1,7 an). Sorties : `presets_pine.txt` (3 lignes pour
`f_pr_def()`, écrasé à chaque lancement), `sorties/resume_<source>.txt`, `sorties/balayage_<source>.csv.gz`
(toutes les variantes, avec placebo, P(réussite), P(1er payout), valeur espérée, micros, score lissé).

## Ce que fait le script
1. Données : jeux 15 min du développement (scellé fermé). Fenêtre 00:20-22:15 Paris : signal refusé si la bougie
   finit à 22:15 ou après ou ouvre avant 00:20 (comme `fen_apres` du Pine) ; moteur : à plat à la clôture de la
   bougie qui finit à 22:15, ni position ni entrée de 22:15 à 00:20.
2. Tables d'issues refaites avec le procédé de `taux_combinatoire` (le moteur, un signal toutes les K barres),
   car les anciennes ne couvrent ni stop 2,5, ni objectifs 1,25 / 2, ni sorties 4 / 12 bougies, ni BE + 4 ticks, ni
   22:15. `trades_table`, `glouton`, `placebo_moyen` sont importés tels quels. Les 3 retenues sont rejouées par le
   moteur : n et R identiques.
3. Voisinage : 2 488 variantes = toutes celles qui diffèrent du préréglage 25 de 3 réglages au plus (déclencheur :
   chacun seul + union ; TREND aucun / 60 / 240 ; Detector aucun / 1 / 1,5 / 2 / 2,5 ; Feu aucun / 50 / 60 ; plage
   entière / 9h / 15h30 / 0h20-8h ; stop 1,5-3 ; objectif 0,75-2 ; sortie 0 / 4 / 8 / 12 bougies ; BE aucun /
   0,5R + 4 ticks). `n_variantes_testees` = 2 488.
4. Note : % gagnants, R, PF, placebo exact de même géométrie (moyenne par heure et sens, z), Tradeify Select Flex
   (`optimise_taille`, 1-10 micros, 300 tirages, ordre prudent). Les jeux sont posés bout à bout dans le temps
   (décalage en semaines entières) : le simulateur voit un compte, un instrument à la fois, sans trou de mois.
5. Règle FIXÉE avant de regarder : éligible = >= 55 % de gagnants, R > 0, n >= 30 ; score = moyenne de la valeur
   espérée de la variante et de ses voisines à un pas sur un réglage (voisine à R <= 0 ou n trop petit = 0) ;
   on prend le meilleur score. Les 3 lignes sont sans doublon de trades.
6. Walk-forward : 7 blocs de journées par jeu, choix sur 3 blocs (même règle, Tradeify sur l'apprentissage),
   test sur le suivant, 4 plis. White : bootstrap studentisé (blocs de 5 jours, 1 000 tirages) sur l'écart de R
   et de taux contre le placebo, pour les 2 137 variantes à >= 20 trades.

## Résultat de l'essai à blanc (cache, dev. seulement, 67 jours en tout) — NON CONCLUANT
- Préréglage 25 avec la fenêtre 22:15 : 73 trades, 72,6 % de gagnants (placebo 50,0 %), R +0,32, PF 2,58.
- Meilleur choix (OPT-0001) : union, TREND 4 h, Detector 2,5 ATR, Feu >= 60 %, 15h30-22h15, stop 2 ATR, objectif
  2R, sortie après 8 bougies : 63 trades, 66,7 % (placebo 46,3 %), R +0,44, PF 2,77 ; Tradeify 4 micros,
  P(réussite) 0,99, P(1er payout) 0,98, valeur espérée +8 046 $ (score lissé +7 883 $). Gain moyen gagnant-perdant
  cohérent avec l'objectif 1,5-2R. Les rangs 2 et 3 sont de la même famille (objectif 1,5R ; stop 1,5 sans Feu).
- Walk-forward : 24 trades hors échantillon, 58,3 % de gagnants (placebo 44,3 %), R +0,37 — mais 4 choix
  différents d'un pli à l'autre et seulement 1 à 16 trades par test : aucune conclusion.
- White : meilleure statistique du balayage p = 0,06 (R) et 0,03 (taux) ; pour OPT-0001, p = 0,10 / 0,11. Mieux que
  l'ancien balayage (0,17) parce qu'il est bien plus petit, mais pas significatif sur 67 jours.
- P(réussite) 0,99 vient du rééchantillonnage de 3 semaines à 2 mois de trades : ne vaut pas plus que le R.

## Limites
- 2 mois (3 jeux) : tout est fragile. Le résultat ne vaut que comme essai de la machine.
- Fenêtre 22:15 Paris = 16:15 Chicago pendant ~2 semaines (mars et fin octobre, décalage horaire 6 h) : le moteur ne
  gère qu'une heure de sortie ; garder `pf=1` (à plat 15:59 Chicago) dans les préréglages, comme le fait la ligne 25.
- Pas de volume sur MES1 (Detector et climax laissent tout passer), Feu de substitution, zones Detector sur HA.
- Voisines des variantes à 3 changements : celles à 4 changements ne sont pas calculées (moyenne sur moins de
  voisines au bord du voisinage).
- Réglages à faire à la main dans TradingView : « Niveaux mesurés sur » = Vrais prix (lvl=1), unité TREND 4 h.
