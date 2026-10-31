# Entrée 15m -> 2m (agent E2M) — résultats sur le cache (dev_cache, 16/10/2026)

Idée de Jeremy : analyser en 15 min, décider d'entrer en 2 min. Testée avec toutes les confluences
disponibles, sur 1/2/3/5 min d'exécution et 15/30/60 min de signal.

## Verdict en une phrase
**Non concluant : il n'y a pas assez de données.** Le cache ne contient que **5 journées de 2 min** en
développement (29/09 → 12/10, en 3 fragments), soit **1 à 17 signaux 15m par famille**. Aucune
recette ne bat le hasard : contrôle de White p = 0,39 (MES) et 0,47 (MNQ). Le walk-forward n'a rien
à tester. En revanche, les **effets mécaniques** de l'affinage sont mesurés et réutilisables :
prix d'entrée, taille du stop, nombre de micros, coûts, signaux manqués. Tout est prêt à être relancé
sur le DATASET (voir « Relancer »).

## Méthode (aucun accès au futur)
- Signal sur l'unité S (15m ; aussi 30m et 60m). Projection sur l'unité X (2m ; aussi 1m, 3m, 5m)
  selon l'heure de **CLÔTURE** de la bougie S : la fenêtre commence à la 1re barre X qui ouvre
  à la clôture S ou après.
- **Référence (« direct »)** : achat à l'ouverture de cette barre X, c'est-à-dire l'ouverture de la bougie 15m suivante.
  Elle est exécutée sur les barres 2m (concordance vérifiée avec le moteur 15m : mêmes entrées, mêmes stops).
- **Déclencheurs 2m** (évalués à la clôture de chaque barre X de la fenêtre de 15 ou 30 min, entrée à
  l'ouverture suivante, annulation si rien) : flip Heishinator 2m, Heishinator 2m dans le sens,
  clôture au-delà du plus haut/bas 2m précédent, Signator 2m, rejet de l'EMA50 2m.
- **Ordres limites** posés à la clôture S, valables pendant la fenêtre : milieu de la bougie 15m, EMA50 2m,
  clôture 15m − 0,25 ATR15.
- **Stops** : swing 2m (plus bas/haut des 5 dernières barres X, ± 1 tick, au moins 0,5 ATR X),
  extrême de la bougie 15m (niveau de protection), 2 ATR15 (taille de la référence).
  **Sorties** : objectif 2R, ou flip Heishinator 15m. Fermeture obligatoire à 15:59 heure de Chicago.
- Familles S : Signator Fort, Fort+Moyen, flip Heishinator, Climax, cassure de trendline, cassure de
  zone Detector, bascule du Feu (proxy) ; chacune sans filtre ou avec le filtre TREND de l'unité au-dessus.
- Scellé : `decoupage(dfS, coupure=date_coupure(dfX))`, donc seuls les 75 % les plus anciens de la série 2m.
- Moteur commun, coûts par défaut : 1 tick de glissement par côté (rien sur les ordres limites),
  0,62 $ de commission par côté. Comparaison **à risque fixe de 200 $** par trade : micros = plancher(200 / risque d'un micro),
  plafonné à 40 (limite Tradeify).
- 4 620 variantes au total (1 428 par marché en 15→2, 126 par marché pour chacun des 7 autres couples).

## Ce que l'affinage apporte (15m → 2m, moyennes sur toutes les variantes)

| Entrée (fenêtre 30 min) | Signaux pris vs direct (MES / MNQ) | Prix gagné (ATR15) | Effet |
|---|---|---|---|
| direct (référence) | 100 % | 0 | — |
| Heishinator 2m dans le sens | ≈ 100 % | ≈ 0 (−0,07 à +0,08) | le 2m est presque toujours déjà dans le sens : cela revient à entrer 2 min plus tard |
| cassure du plus haut/bas 2m | ≈ 100 % | −0,06 à +0,08 | on paie le mouvement : pas de meilleur prix |
| flip Heishinator 2m | 2-10 % | négatif | se déclenche presque jamais (le 2m a déjà basculé) |
| Signator 2m | 0-6 % | négatif | idem, inutilisable |
| limite milieu bougie 15m | 88-108 % | **+0,16 à +0,21** | meilleur prix presque sans perte de signaux |
| limite clôture − 0,25 ATR15 | 90-103 % | **+0,24** | idem |
| limite EMA50 2m | **40-45 %** | +0,47 à +0,62 | gros gain de prix, mais un signal sur deux manqué |
| rejet de l'EMA50 2m | 50-70 % | +0,35 à +0,51 | même compromis |

**Stop et micros (entrée directe, risque fixe de 200 $)** :

| | Stop 2 ATR15 | Stop swing 2m | Stop extrême bougie 15m |
|---|---|---|---|
| MES : distance du stop | 13,7 pts | **4,2 pts** | 5,3 pts |
| MES : micros pour 200 $ | 2,6 | **12,7** | 9,8 |
| MES : coûts par trade, en R | 0,06 R | **0,22-0,25 R** | 0,19 R |
| MNQ : distance du stop | 83 pts | **27 pts** | 35 pts |
| MNQ : micros pour 200 $ | 1,0 | **4,8** | 4,1 |
| MNQ : coûts par trade, en R | 0,01 R | **0,06 R** | 0,05 R |

- Le stop serré multiplie les micros par 3 à 5 pour le même risque. Il coûte **0,2 à 0,25 R par trade sur MES**
  (en 1 min : 0,5 R). Sur MNQ, il coûte 0,06 R. **MES reste très pénalisé sous 15m**, comme on l'avait déjà mesuré.
  MNQ supporte l'affinage, MES beaucoup moins.
- Le stop serré est touché plus souvent : 38 % de gagnants contre 42 % sur MES. Sur ces 5 jours, il fait quand même
  mieux à risque fixe (MES +0,11 R contre −0,20 R ; MNQ −0,54 R contre −0,59 R). C'est sans valeur statistique.
- **Signaux manqués** : les entrées qui attendent un repli (EMA50, rejet) manquent environ la moitié des signaux.
  Sur ces 5 jours, la comparaison est mixte. Selon le marché et la fenêtre, les signaux manqués valent tantôt mieux,
  tantôt moins bien que les signaux pris (R de la référence entre −0,9 et +0,1 des deux côtés). Il faut le revérifier
  sur le DATASET : c'est le risque classique, car les meilleurs départs ne reviennent jamais sur l'EMA.

## Autres unités (tendances communes à tous les couples)
- Le gain de prix des limites est le même partout : +0,15 à +0,27 ATR S pour milieu / ATR, +0,2 à +0,7 pour l'EMA50
  (davantage en 3-5m qu'en 1-2m).
- Le 1m est le pire pour les coûts. Sur MES, le stop swing 1m fait 2 pts, soit 0,5 R de coûts par trade.
  Le 3-5m est le meilleur compromis : stop 1,9 à 2,4 fois plus court que 2 ATR15, et coûts de 0,14-0,16 R sur MES, 0,04 R sur MNQ.
- Signal 30m/60m sur MNQ : le stop de 2 ATR S dépasse 200 $ par micro, donc aucune position possible à ce risque.
  Il faut un stop affiné pour trader ces unités en propfirm.
- Aucun classement de R par couple n'est fiable : 14 à 78 signaux par couple et par marché, toutes familles confondues.

## Recettes retenues (registre) et note Tradeify Select Flex
Ce sont les 3 meilleures variantes 15→2 à risque fixe, avec des couples famille/entrée distincts. Ce sont des **maxima choisis
parmi 4 620 variantes sur 9 à 11 trades** : le biais de sélection est total (White p ≈ 0,4).

| id | Recette | n | R moyen | R risque fixe (réf. directe) | p hasard (R) | P Tradeify (risque) | P hasard | P réf. directe |
|---|---|---|---|---|---|---|---|---|
| E2M-0001 | MNQ : Feu + TREND 1H 15m ; Heishinator 2m dans le sens (15 min) ; stop swing 2m ; 2R | 9 | +0,46 | +0,56 (−0,51) | 0,09 | 1,00 (300 $) | 0,25 | 0,00 |
| E2M-0002 | MNQ : Feu 15m ; limite au milieu de la bougie 15m (15 min) ; stop swing 2m ; 2R | 11 | +0,57 | +0,48 (−0,56) | 0,14 | 0,63 (200 $) | 0,46 | 0,00 |
| E2M-0003 | MES : Feu 15m ; rejet de l'EMA50 2m (30 min) ; stop extrême bougie 15m ; sortie flip Heishinator 15m | 10 | +0,40 | +0,37 (−0,41) | 0,12 | 0,20 (200 $) | 0,31 | 0,00 |

**Note Tradeify Select Flex : aucune.** Les probabilités ci-dessus n'ont pas de sens. Le simulateur rejoue par blocs
3 à 4 journées de trades, dont 2 ou 3 gagnantes : P = 1,00 veut seulement dire « ces 4 jours ont été bons ». La référence directe
(P = 0) a perdu sur les mêmes jours. Le hasard avec la même gestion fait 0,25 à 0,46. Aucune recette n'est
distinguable du hasard : p de 0,09 à 0,14 avant correction, ~0,4 après White.
Le seul enseignement exploitable pour la propfirm est mécanique : à risque égal, le stop 2m donne **4 à 5 fois
plus de micros**. Cela rend tradables des signaux 30m/60m sur MNQ, impossibles autrement à 200 $ de risque. En contrepartie,
on paie 0,06 R (MNQ) à 0,25 R (MES) de coûts par trade.
Les trades des 3 recettes (entrée, SL, TP, sortie, niveau du stop) sont dans `registre/trades/E2M-000{1,2,3}.csv`.

## Ce qui ne marche pas / à abandonner
- Attendre un flip Heishinator 2m ou un Signator 2m après un signal 15m : il n'arrive presque jamais dans la fenêtre.
- La « confirmation » 2m (Heishinator dans le sens, cassure de la bougie précédente) : aucun meilleur prix.
  On entre plus tard au même endroit.

## Limites
- **5 journées de 2 min** en développement, avec des vrais prix **reconstitués depuis le HA**. Cette reconstitution
  n'est pas fiable sous 5 min (MEMOIRE_PROJET §15). Les R individuels en 1-3m sont donc approximatifs.
- Les variantes sont très corrélées : ~1 400 variantes = quelques dizaines de trades distincts.
- Le cache est fragmenté. Le moteur gardait une position à travers un trou de données : un trade est sorti 8 jours plus tard
  à −37 R. **Corrigé de notre côté** par un backtest par segment contigu (`affinage.backtest_segments`).
  À signaler au coordinateur : le moteur ne coupe pas une position sur un trou de données (sans effet sur un
  DATASET continu, où les seuls trous sont les week-ends, déjà à plat à 15:59).
- Feu = proxy 12 voix (le vrai Feu à 29 voix sera dans le DATASET). Signator Moyen absent du cache 15m sur la période.
- Le prix gagné est mesuré contre l'ouverture de la barre 2m qui suit la clôture 15m. Les barres 2m ne tombent pas
  toujours pile sur les quarts d'heure (décalage de 1 min au plus).

## Relancer (DATASET)
```bash
cd KAIROS/recherche/entree_2m
export E2M_SOURCE=dataset        # exports dans ~/ERGON/KAIROS-data (dataset/charger.py)
for m in MNQ MES; do ~/venv-quant/bin/python balayage.py --marche $m --us 15 --ux 2 --niveau complet; done
for m in MNQ MES; do ~/venv-quant/bin/python balayage.py --marche $m --us 15 --ux 5 --niveau complet; done
~/venv-quant/bin/python analyse.py --registre      # synthese_auto.md, recettes_retenues.csv, registre
```
Fichiers : `donnees.py` (seul accès aux données), `affinage.py` (projection, déclencheurs, stops, hasard),
`balayage.py`, `analyse.py`, `resultats/` (balayages CSV, trades, `synthese_auto.md`, `apport_par_variante.csv`).
Sur le DATASET, le seuil de classement passe à 100 trades et le walk-forward à 5 plis.
