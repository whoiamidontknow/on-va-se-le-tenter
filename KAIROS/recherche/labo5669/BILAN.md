# Labo 5669 — bilan (19/11/2026, complété le 25/11)

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

## 7. Relevé complet : toutes les bougies, sans fuite (19/11 au soir)
Données : Relevé complet (KAIROS/dataset/RELEVE_COMPLET.pine, KAIROS-data/releve_complet), 177 729
bougies MNQ et 177 735 MES, 31 champs et 35 bits par bougie, toutes lectures sans fuite.
- **Chargeur** `KAIROS/dataset/releve_complet.py` : OHLC identique au Relevé 5669 à 100 % ; bits go =
  lecture k1/k4 à 99,4 % (8 écarts, tous dus à l'arrondi 0.000 du Relevé 5669).
- **Moteur générique** `complet/moteur.py` : redonne simu56 trade pour trade (368/368 en MNQ) ; seuls
  écarts = sorties `fin` dont simu56 estimait l'ouverture.
- **Témoin C1** (gradient boosting, tous les champs, cible R à géométrie fixe) : l'arrêt précoce garde
  1 à 11 itérations ; la corrélation de rang (+0,05 à +0,18) est plus faible que celle du seul coût
  fixe en R (+0,25) ; la stratégie témoin, très bonne en échantillon (p = 0,001), tombe en contrôle
  (MNQ p = 0,056, MES −998 $, p = 0,47). Aucun avantage hors échantillon.
- **Familles F1-F4** (66 tests, écrites avant dans HYPOTHESES.md) : tendance, retour à la moyenne,
  cassure, filtres de régime. 65 ne passent pas la construction. MNQ M1 (climax) passe le critère
  formel mais perd de l'argent dans les deux périodes : rejeté, scellé fermé.

## 8. Bilan des 190 essais
| Bloc | Essais | Résultat |
|---|---|---|
| Validation du moteur (56, MES, lecture b, témoins) | 7 | validé |
| 56 tel quel : hasard, évaluations propfirm, contrôle du réel | 17 | lecture o au-dessus du hasard (fuite) ; lecture b dans la masse ; les alertes réelles suivent b |
| Variantes du 56 en lecture b (1, 2, 3, 5, 6) + références | 98 | aucune ne passe la construction |
| Témoin C1 sur le Relevé complet | 2 | rien hors échantillon |
| Familles F1-F4 sur le Relevé complet | 66 | rien de rentable hors échantillon (M1 rejeté) |

Conclusion : avec nos indicateurs lus sans fuite, sur MNQ et MES en 15 min, aucune règle testée ne
gagne d'argent hors échantillon. Le protocole exige désormais un P&L net positif en construction ET en
contrôle, en plus de battre le hasard et la référence « long seulement ».

Suite probable, selon la décision de Jeremy : le même relevé en 5 min (l'unité du bot) et en 1 h.

## 9. Journée du 25/11 : MNQ et MES, 17/10/2023 → 13/11/2026 (Relevés complets 5 et 15 min)
Consigne de Jeremy : MNQ et MES seulement, données 2023 → aujourd'hui, lecture alertes (b) ou bougie terminée (k).
Protocole partout : hypothèse écrite et commitée avant le test, choix sur H1 (→ 01/05/2025), contrôle sur H2, hasard
B (sens du déclencheur) et L (long seulement), correction pour essais multiples. Scellé 2025-26 ouvert par Jeremy.
| Piste | Essais | Résultat |
|---|---|---|
| Décision du 56 reconstituée sur toutes les bougies | — | o 99,7 %, b 98,5-98,9 % contre le Relevé 5669 |
| Seuils de fiabilité 0-95 % (15 / 5 min) | 80 | P&L > 0 pour plusieurs seuils, mais 5 min MNQ 70 % ne bat pas B / L sur H1 (p 0,15 / 0,07) |
| Programme objectifs : sorties, lecture k, filtres, combinaisons | 541 + 5 | 5 finalistes, aucun ne bat le hasard sur H2 (p 0,11-0,25) |
| H-ORACLE : prévoir la couleur finale 1 h / 4 h | 8 | pas mieux que la persistance (−0,5 point) |
| H-SORTIE : couper les fantômes, entrée confirmée | 24 | pas mieux qu'une sortie au hasard ; E1 perd partout |
| Familles F1-F5 et témoin C1 en 5 min | 86 | aucun candidat ; C1 sur-appris |
| CLX-ADX, test unique sur H2 | 1 | −11 215 $, p_B 0,29 |
| Niveaux (pivots, Detector) et biais du jour en séance US | 52 | aucun candidat |
| PIVC-K4, test unique sur H2 | 1 | −3 920 $ |
EXAMEN-1 (2019-2023) gelé puis suspendu sur consigne de Jeremy, jamais exécuté. Registre : 1 006 essais. Programme clos le 25/11.

**Conclusion.** Avec nos indicateurs lus sans fuite, sur MNQ et MES 5 et 15 min de 2023 à 2026, aucune règle testée ne
bat le hasard une fois corrigé le nombre d'essais. Les meilleurs résultats gagnent un peu d'argent (R/C de 0,5 à 1,1 sur
H2), soit de l'ordre de 10 % par an dans les règles FTMO, loin des 25-40 % par an et des 4-6 % par mois visés, et sans
preuve que ce gain vienne d'autre chose que de la chance ou de la hausse du marché. L'avantage du graphique vient de la
couleur finale des bougies 1 h / 4 h, qu'aucune variable connue au moment du signal ne permet de prévoir.
