# Optimiseur final (FIN) — essai à blanc sur le cache (2 mois), 17/10/2026

**Verdict honnête : NON CONCLUANT.** 67 jours de développement, 3 jeux 15 min. Rien de ce qui suit n'est une décision :
c'est une machine complète, vérifiée, qui a donné ses premiers classements et qui doit être relancée sur le DATASET.

## Relancer (une commande)

    cd KAIROS/recherche/final
    ~/venv-quant/bin/python final.py --source dataset --registre      # ~1,7 an en 15 min
    # options : --recalcul (ignore le cache disque sorties/brut_*.pkl), --rangs 3 (n'écrit que ce rang au registre), --petit

- Cache : 6 min 15 s au premier lancement (balayage 195 s + walk-forward ~170 s), 3 min ensuite (le balayage est relu).
- DATASET : le balayage grossit à peu près comme le nombre de barres (≈ 20 fois plus). Compter 20 à 40 min la 1re fois
  (le plus lent est la table d'issues en Python pur ; elle se calcule sur les 8 cœurs). Rien à modifier : N_MIN passe
  seul de 30 à 80 trades, les colonnes DATASET (votes, niveaux) sont lues telles quelles.
- Fichiers : `final.py` (balayage, règle, walk-forward, White, Pine, registre), `sim_fin.py` (simulateur), `presets_pine.txt`
  (3 lignes), `sorties/balayage_<source>.csv.gz` (toutes les variantes), `sorties/resume_<source>.txt` (rapport complet),
  registre FIN-0001 à 0003 (trades détaillés : prix d'entrée, stop, objectifs, sortie, motif, niveau utilisé).

## Ce qui a été construit
- **Simulateur FIN** (`sim_fin.py`) : la boucle du moteur commun, plus ce qu'il ne savait pas faire : objectif « Prochain niveau »
  (miroir de `f_tp_niveau` : pivots A/M/W, zone Detector opposée, Monday, sessions ; rrMin ; marge 4 ticks ; repli « Objectif en R » 1,5),
  sortie partielle 50 % au 1er niveau avec stop à l'entrée + 4 ticks (partBE), reste au 2e niveau ou « Stop seulement » (+ Heishinator),
  Heishinator opposé, break-even 1 R + 4 ticks, sortie après N bougies. **Vérifié contre `moteur.backtest` : 1 404 trades comparés,
  0 écart** (R fixe, tBar, BE, Heishinator, objectif niveau, partiel). Fenêtre 00:20-22:15 Paris ET à plat avant 15:59 Chicago (le plus tôt des deux).
- **Entrées** (50 candidates + 12 références sans biais) : 4 crans de biais x {Signator F+M ; union} x 6 confirmations
  {aucune ; Detector 1,5 ; +climax ; +Feu 60 ; +TREND 4 h ; +ADX 25} ; le préréglage 25 tel quel (15:30-22:15) et filtré par le biais.
- **Sorties** (39 formes x stop 1,5 / 2 / 2,5 ATR = 117) : R 1 / 1,5 / 2 ; 2R + BE 1R ; N=8/12 bougies ; niveaux rrMin 1 / 1,5 x 3 familles
  x {simple ; +Heishinator ; partiel->2e niveau ; idem +Heishinator ; partiel->reste Heishinator}.
- **5 850 variantes candidates**, règle, profils, walk-forward, White : voir l'en-tête de `final.py` (tout fixé avant de regarder).
- Placebo = entrées au hasard (même heure, même sens, dans le sens du biais) avec EXACTEMENT la même gestion.

## Résultats (cache)
Agrégats sur les variantes n >= 30 (3 615) :

| | trades/jour | gagnants | R moyen | écart au placebo | VE Tradeify moy. |
|---|---|---|---|---|---|
| sortie R fixe | 1,27 | 55,0 % | +0,19 | **+0,07 R** | 4 593 $ |
| sortie sur niveaux (sans partiel) | 1,04 | 44,9 % | +0,28 | +0,02 R | 4 075 $ |
| sortie sur niveaux + partiel | 0,95 | 43,6 % | +0,27 | **−0,05 R** | 3 061 $ |

- **Le biais** : à déclencheurs, confirmation et sortie égaux, +5,5 points de gagnants et +0,19 R (99 % des variantes sont meilleures avec le biais). C'est le gros effet, comme dans l'étude BIA.
- **Les déclencheurs** dans le sens du biais ne battent pas le hasard dans le biais (−0,002 R, 48 % des variantes au-dessus) : la direction fait presque tout.
- **Les objectifs sur niveaux** donnent plus de R par trade (+0,27 contre +0,19) mais **beaucoup moins de gagnants (44 % contre 55 %)** : **aucune des 311 variantes éligibles à la règle (>= 1/jour, >= 55 %, R > 0) n'est une sortie sur niveaux.** Contre le placebo, le partiel est même négatif (−0,05 R) : même des entrées au hasard dans le biais gagnent +0,36 R avec cette gestion ; le gain vient de la gestion et du biais, pas du choix de l'entrée. Le partiel n'ajoute pas de R (+0,27 contre +0,28 sans partiel) et baisse la valeur espérée Tradeify (3 061 $ contre 4 075 $). Même constat que SOR.
- Stops : 1,5 / 2 / 2,5 ATR donnent R +0,27 / +0,25 / +0,25 ; la valeur espérée baisse à 2,5 ATR (3 403 $ contre 3 998 $ à 2 ATR).
- Le préréglage 25 tel quel (15:30-22:15, 2 ATR, 1R, 8 bougies) : 73 trades, 1,09/jour, 72,6 % gagnants, R +0,32, P(réussite) 1,00 ; il reste très difficile à battre sur ces 2 mois (il a été choisi sur ces mêmes données par OPT : biais de sélection).
- White (5 031 variantes) : meilleure p = 0,04 en R brut et contre placebo, mais la meilleure est une variante du préréglage 25 lui-même, déjà sélectionnée sur ces données.
- Walk-forward (4 plis, la règle complète refaite à chaque pli) : 46 trades, 54,3 % gagnants (placebo 51,0 %), R +0,066, PF 1,29. Les choix changent à chaque pli (préréglage 25 deux fois, biais + TREND 4 h une fois) : pas de zone stable démontrée.

## Les 3 livrés (`presets_pine.txt`, noms 43 à 45 ; à ajouter dans options=[…] puis coller la ligne)
| | n (par jour) | gagnants | R | PF | placebo (R) | Tradeify : micros, P(réussite), VE |
|---|---|---|---|---|---|---|
| **1. RECOMMANDÉ** préréglage 25, stop 1,5 ATR, 2R, 8 bougies (FIN-0001) | 67 (1,00) | 62,7 % | +0,50 | 2,43 | +0,02 → écart +0,49 | 4 ; 0,99 ; +7 585 $ |
| **2. PLUS DE TRADES** biais F>=0,55 I>=0,45, union, Detector+Feu 60, 2 ATR, 1R (FIN-0002) | 104 (1,55) | 63,5 % | +0,25 | 1,80 | +0,12 → écart +0,13 (p=0,07) | 4 ; 0,99 ; +7 571 $ |
| **3. NIVEAUX + PARTIEL** biais F>=0,55 I>=0,45, union, Detector+Feu 60, 1,5 ATR, prochain niveau rrMin 1 (tous niveaux) partiel 50 % -> 2e niveau, BE +4 ticks (FIN-0003) | 76 (1,13) | **50,0 %** | +0,46 | 2,30 | +0,36 → écart +0,10 (p=0,30) | 4 ; 0,89 ; +6 477 $ |

- Le profil 3 ne passe PAS le seuil de 55 % de gagnants : il est livré parce que Jeremy veut voir la gestion sur niveaux avec partiel (règle ajoutée le 17/10 après l'essai : « s'il n'y a pas de variante éligible avec nettement plus de R, montrer la meilleure sur niveaux + partiel »).
- Différents entre eux : 1 = préréglage 25 (sans biais, TREND 4 h), 2 = biais + union + R fixe, 3 = biais + union + niveaux avec partiel.
- Le recommandé est surtout le préréglage 25 légèrement ré-accordé : c'est pour cela qu'il gagne sur 2 mois ; il n'utilise ni le biais ni les niveaux. Le meilleur « tout biais » est le profil 2.

## Pine : ce qui existe et ce qui manque
Tout ce qui est utilisé existe dans `STRATEGIE_V1.pine` (tp=Prochain niveau, tpA/M/W/D/Mo/Se, rrMin, tpMarge, tpSans, part, partPct, partRest, partBE, beTk, oppHei, be, beR, tBar, bias/bF/bI). Écarts de modélisation à connaître :
- Le Pine mesure les niveaux et le risque depuis la CLÔTURE de la bougie signal ; le simulateur (comme le moteur) depuis l'ouverture suivante + 1 tick de glissement. Écart de quelques ticks sur l'objectif.
- Zones Detector utilisées comme objectif : seulement la plus proche de chaque côté (bord bas de la zone baissière au-dessus pour un long, bord haut de la zone haussière en dessous pour un short) ; le Pine liste toutes les zones, donc le 2e niveau peut différer.
- Pivots : prix réels (réglage à la main « Niveaux mesurés sur » = Vrais prix), pivots HA si les réels manquent.
- Le partiel exige >= 2 micros, nombre pair (le simulateur est fractionnaire à 50 %) : les lignes avec partiel ont `fixe` pair. Le Tradeify des variantes avec partiel est évalué avec 2, 4, 6, 8, 10 micros.
- Rien à ajouter au Pine.

## Limites
- 67 jours (3 jeux, MES avr.-juin, MES sept.-oct., MNQ sept.-oct.) ; n minimum 30 ; 5 850 variantes sélectionnées sur ces mêmes jours ; ADX 25 et TREND 4 h dépendent des colonnes du cache.
- Cache : 2 voix sur 11 du biais intraday à 0 (TREND/Dashator 5 min) ; ORB et PDH/PDL souvent neutres ; le jeu MES avr.-juin n'a ni Detector ni climax (le filtre Detector n'y bloque rien).
- 5 min non traité (inexploitable en BIA). Un seul instrument à la fois, jeux posés bout à bout pour le simulateur.
- Walk-forward allégé : la note Tradeify d'apprentissage n'est calculée qu'à partir de 50 % de gagnants à l'apprentissage et avec 120 tirages.
- Les VE Tradeify (4 micros, P proche de 1) viennent du rééchantillonnage de ~70 trades : très optimistes. Compter les ordres de grandeur, pas les chiffres.
- À refaire sur le DATASET avant toute décision, puis comparer les 3 profils sur le scellé (avocat du diable).
