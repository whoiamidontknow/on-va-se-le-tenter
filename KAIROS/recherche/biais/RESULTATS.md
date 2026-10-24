# Biais global (BIA) — essai à blanc sur le cache (2 mois), 17/10/2026

Relancer : `~/venv-quant/bin/python biais.py --source cache|dataset [--registre]` (46 s). Code : `votes.py` (20 votes),
`biais.py` (balayage de 432 variantes fixé à l'avance, comparaisons, règle, walk-forward, White, Pine).
Détail chiffré : `sorties/resume_cache.txt`, `sorties/balayage_cache.csv.gz`, `presets_pine.txt`. Registre : BIA-0001 à 0003.

## Ce que le cache ne permet pas (votes mis à 0)
- 15 min : TREND/Dashator 5 min (2 voix sur 11) ; ORB et PDH/PDL souvent neutres (70-80 % de zéros, normal : prix dans la plage).
- STRENGTH recalculé sur séries HA ; SuperTrend/VWAP en version de repli ; CPR, Lin Regress, ORB, PDH/PDL recalculés. Sur le DATASET les colonnes exportées sont lues telles quelles.
- 5 min : seulement ~9 jours de développement (2 jeux). Aucun enseignement possible.

## Résultats (15 min ; le 5 min est inexploitable : 43 % gagnants, R négatif)
- Biais seul, à déclencheurs égaux (a) : +4,5 points de gagnants et +0,06 R en moyenne ; 89 % des variantes meilleures qu'sans biais.
- Déclencheurs vs entrées au hasard dans le sens du biais (b) : +1,6 point, +0,045 R. Le biais fait l'essentiel, les déclencheurs ajoutent peu (non significatif).
- Préréglage 25 (00:20-22:15) (c) : 73 trades (1,09 /jour), 72,6 % gagnants, R +0,32. Le biais donne 1,0-1,9 trade/jour mais 57-61 % et R +0,17 : plus de trades, nettement moins de qualité par trade.
- Choisies (palier 1 de la règle, 67 variantes éligibles) : F>=0,78 I>=0,45 union Detector 1R (73 tr, 60 %, R +0,18) ; idem 1,5R (67 tr, 57 %, R +0,19) ; F>=0,55 I>=0,2 union Detector 1R (124 tr, 61 %, R +0,17).
- Walk-forward : 41 trades, 43,9 % gagnants (hasard-biais 51,5 %), R -0,07. White : meilleure p = 0,30 (R brut), 0,39 (contre hasard). Rien de prouvé.

## Verdict
Le biais global améliore nettement les signaux bruts (plus de trades, meilleur taux), mais ne bat pas le préréglage 25 en qualité, et la sélection ne tient pas en walk-forward sur 2 mois. À refaire sur le DATASET (1,7 an, 15 min puis 5 min).
