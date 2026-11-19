# Labo 5669 — bilan (19/11/2026)

**Objectif.** Reconstruire la Strat5669 (préréglage 56) en Python, la valider contre TradingView,
puis chercher une amélioration qui tienne sans lire l'avenir. Données : exports « Relevé 5669 »
(KAIROS-data/dataset5669, Relevé a7d2173), MNQ1! et MES1! 15 min HA, 05/2019 → 11/2026.

## 1. Moteur : validé
- `KAIROS/dataset/releve.py` charge le relevé ; `simu56.py` simule le 56 (une position à la fois,
  remplissage à l'ouverture + 1 tick, stop et objectif recalés sur le prix obtenu, stop d'abord si
  stop et objectif tombent dans la même bougie, sortie au temps et sortie `fin`).
- Contre les exports du testeur (`valide56.py`) : MNQ 631/631 trades identiques, P&L −0,5 % ;
  MES 693/694, −0,4 % ; témoins « ancien calcul » 99,9 à 100 %. Bougies ambiguës : 2 à 4 sur 3 ans.
- Trois lectures du Dashator 1 h / 4 h : **o** origine (valeur finale de la bougie en cours = la fuite,
  c'est le graphique), **b** bougie en cours (direct), **k** dernière bougie terminée.
  b est validée contre SANSFUITE mode b (99,0 à 99,6 % de trades identiques) ; k n'a pas d'export témoin.

## 2. Ce que fait le 56 tel quel (recherche 2019-2024, scellé 2025-2026 fermé)
| | Lecture o (graphique) | Lecture b (direct) |
|---|---|---|
| MNQ, 2 contrats | 1 203 trades, 82 %, +121 848 $ | 856 trades, 53 %, −8 432 $ |
| MES, 2 contrats | 1 217 trades, 80 %, +73 652 $ | 901 trades, 53 %, −3 939 $ |
| Contre 1 000 tirages au hasard | au-dessus de 100 % des tirages | dans la masse (p de 0,13 à 0,82) |
| Évaluations Tradeify / FTMO / Lucid* | 96 à 99 % réussies | 0 à 4 % réussies |

\* Lucid simulé avec les signaux du 56 en MNQ 15 min, pas avec le bot.

## 3. Laquelle décrit les alertes réelles (20/10 → 12/11, 21 alertes)
Lecture b : 20/21 alertes retrouvées (même bougie, même sens), sorties identiques 20/20, et
13 objectifs / 2 stops comme le compteur. Lecture o : 15/21. Lecture k : 2/21.
Le compteur 13/2 ne compte que les messages objectif / stop (7 sorties au temps ou en fin de séance
exclues, une sortie orpheline incluse). 14 gagnants sur 21 ce mois-ci, avec un vrai taux de 53 % :
cela arrive dans 15 % des cas. C'est un bon mois, pas une contradiction.

## 4. Variantes testées en lecture b (construction 2019-2022, contrôle 2023-2024)
| Idée | Méthode | Résultat | Pourquoi c'est invalidé |
|---|---|---|---|
| 1. Dashator sur la dernière bougie terminée (k) | règle fixe, contre le hasard | MNQ ~58 %, p = 0,25 / 0,51 ; MES 45 % en contrôle | pas mieux que le hasard |
| 2. Entrée seulement à hh:00 (b ou k) | règle fixe | 4 à 5 fois moins de trades, p ≥ 0,61 (meilleur cas : V2b MNQ GODLIKE, p = 0,24 en construction, 0,94 en contrôle) | pas mieux que le hasard |
| 5. Confiance que la 1 h / 4 h finira dans le sens | régression logistique ajustée sur 2019-2022, seuils 50/60/70 % | AUC 0,99 (1 h) et 0,95 (4 h), mais = « la couleur en cours reste » ; sur les signaux, AUC 0,56 à 0,60 | aucun seuil < 0,05/6 en construction |
| 6. Géométrie de sortie (24 cases) | hasard avec la même géométrie | meilleur p = 0,22 ; pas de plateau | aucune case < 0,05/48 |
| 3. Tri des déclencheurs | 7 × 2 sens × 2 instruments | meilleur p = 0,061 (MES short T) | aucun < 0,05/28 |

Idées 4, 7, 8, 9, 10 non lancées (décision de DAEMON) : sans signal même en construction après
122 essais, elles n'auraient fait qu'augmenter le risque de faux positif.

## 5. Ce qu'on en retient
- L'avantage de la lecture d'origine vient de la couleur FINALE des bougies 1 h / 4 h, dans les cas
  où la bougie en cours se retourne. Aucune variable connue au moment du signal ne le prédit mieux
  que « la couleur en cours reste ».
- En lecture direct, le 56 et ses variantes simples ne font pas mieux qu'un tirage au hasard.
- Réserves : la lecture k n'est pas validée par un export ; quelques bougies ont b = 0.000 dans le
  commentaire ; les sorties `fin` ont parfois une ouverture estimée (voir NOTES.md).

## 6. Fichiers
`registre.csv` (122 essais : date, nature, lecture, période, résultat, verdict, commit) ·
`resultats_*.csv` · `banc.py` (hasard, propfirm) · `reel.py` (alertes réelles) · `variantes.py`,
`variante5.py`, `variante6.py`, `variante3.py` · `NOTES.md` (améliorations du Relevé pour TALOS).

Suite possible, en attente de la décision de Jeremy : un relevé de toutes les bougies, pour
chercher d'autres familles de signaux.
