# Régimes / réglage adaptatif (agent REG) — résultats du 16/10/2026

**Verdict : l'aiguillage « état de marché → setup » n'apporte rien de démontrable par rapport à un setup
unique, et il surapprend fortement.** Sur l'apprentissage, les couples (état, setup) choisis font en moyenne
+0,64 R par trade de plus que sur le pli suivant. La corrélation entre le score en développement et le
score sur le pli suivant vaut −0,15 : le choix fait sur le passé ne prédit rien. Aucune variante ne bat la
référence au hasard (meilleur p = 0,29 sur 18 variantes qui tradent). Données : cache, environ 2 mois, donc
tout ceci reste fragile. Il faut relancer sur le DATASET.

## Comment relancer
```bash
cd KAIROS/recherche/regimes
~/venv-quant/bin/python aiguillage.py                    # cache (≈ 22 min sur 8 cœurs)
~/venv-quant/bin/python aiguillage.py --source dataset   # exports DATASET.pine 15 min (~/Ephore/KAIROS-data)
~/venv-quant/bin/python aiguillage.py --registre         # + lignes REG-xxxx au registre (à ne faire qu'une fois)
~/venv-quant/bin/python analyse.py                       # surapprentissage + stabilité des choix
```
Sur le DATASET, monter `--nmin` (au moins 30 trades par couple état-setup en apprentissage) et `--nref 100`.

| Fichier | Contenu |
|---|---|
| `donnees.py` | **seul** accès aux données (`charger_series`) : cache ou DATASET, développement seulement (scellé fermé) |
| `etats.py` | briques d'état et 8 partitions (définitions ci-dessous) |
| `setups.py` | catalogue : 9 déclencheurs × 3 sens × 6 filtres × 4 sorties = **648 setups** |
| `aiguillage.py` | balayage, walk-forward, rejeu exact, référence au hasard, simulateur propfirm, registre |
| `walk_forward_variantes.csv` | une ligne par variante (partition × T_MIN) : hors échantillon, développement, hasard, propfirm |
| `table_etat_setup.csv` | table état → setup apprise sur TOUT le développement, pour chaque variante |
| `choix_par_pli.csv`, `stabilite_choix.csv` | choix faits à chaque pli, et leur stabilité |
| `aiguillage_vs_unique.csv` | différence de R par jour de test entre l'aiguillage et le setup unique (bootstrap) |
| `balayage_setups.csv`, `balayage_trades.pkl` | balayage complet : les 648 setups sur tout le développement (en échantillon) |
| `trades_oos_toutes_variantes.csv` | tous les trades hors échantillon de toutes les variantes |

## États de marché (lus à la clôture de la barre, seuils fixés à l'avance)
Briques : **tendance** (ADX ≥ 20, pente de l'EMA50 sur 5 barres, clôture HA du bon côté de l'EMA50 ;
sinon « range »). **Alignement** : TREND 15, 60 et 240 dans le même sens. **Heishinator 1 h** : dernière
bougie clôturée. **Volatilité** : terciles du rang de ATR/moyenne(ATR, 100) sur les 960 barres passées.
**Séance**, à l'heure de New York : Asie 17:00-02:00, Londres 02:00-09:30, ouverture US 09:30-11:30,
après-midi US 11:30-17:00. **Jour** : journée CME. **Position** : clôture vraie par rapport à l'ORB du jour
(09:30-09:45 NY, vrais prix) et au Monday High/Low (vrais prix). **Feu** : dominant si l'écart entre voix
long et voix short est d'au moins 6 sur 29.

| Partition | États |
|---|---|
| UNIQUE | 1 (= meilleur setup unique) |
| TENDANCE_VOL | hausse / baisse / range × volatilité basse ou non (6) |
| SEANCE_ALIGNE | 4 séances × TREND multi-unités aligné ou non (8) |
| COMPOSITE (définie à l'avance comme principale) | tendance alignée haussière, tendance alignée baissière, range calme, range agité × Asie ou séance active (8) |
| ORB_HEI60 | sous / dans / sur l'ORB × Heishinator 1 h (6) |
| MONDAY_VOL | sous / dans / sur le Monday H/L × volatilité basse ou non (6) |
| FEU_ADX | Feu short / neutre / long × ADX ≥ 20 (6) |
| JOUR_US | 5 jours × séance US ou non (10) |

Setups : déclencheurs Signator Fort, Fort+Moyen, changement de couleur Heishinator, Climax, cassure de
trendline, zone Detector cassée, cassure de l'ORB, cassure du Monday H/L, bascule du Feu. Sens : long,
short ou les deux. Filtres : aucun, TREND 1 h, Heishinator 1 h, Feu, EMA50, ADX ≥ 20. Sorties : stop 2 ATR
avec objectif 2 R ; stop 1 ATR avec objectif 1,5 R ; stop 2 ATR avec sortie Heishinator ; stop 2 ATR avec
objectif 3 R et break-even à 1 R. Le moteur commun ferme tout à 15:59 heure de Chicago.

## Protocole
- Walk-forward **ancré** sur le calendrier commun des 3 séries (MES avr.-juin, MES sep.-oct., NQ sep.-oct. traité
  en MNQ) : 8 blocs de jours. Pour chaque pli, l'apprentissage couvre tous les blocs passés et le test le bloc
  suivant (5 plis, 34 jours de test).
- Pour chaque état, on prend sur l'apprentissage seulement le setup qui a le meilleur t (R moyen divisé par
  son erreur type, avec au moins 10 trades). On ne trade cet état que si ce t est au moins égal à **T_MIN**
  (0 ; 1,5 ; 2,5). Sinon, l'état est classé **« pas de trade »**.
- Le test rejoue exactement l'aiguillage : les signaux sont masqués à l'état et aux jours de test, chaque
  setup garde sa propre gestion, et chaque série ne porte qu'une position à la fois.
- Hasard : `reference_hasard` (même heure, même sens, même gestion, mêmes jours), 30 tirages.
- Propfirm : `tradeify_50k_select_flex`, Monte-Carlo par blocs de 5 jours (2 000 parcours) sur les jours de
  test mis bout à bout, avec un **risque fixe de 200 $ par trade** en micros (règle identique pour tous).
  Le compte trade MES et MNQ.

## Résultats hors échantillon (34 jours de test, MES + MNQ)
| Variante | n | R moyen hors éch. [IC95] | R moyen en dév. | R hasard | p hasard | P(réussite) | P hasard | VE $ |
|---|---|---|---|---|---|---|---|---|
| JOUR_US, T_MIN 0 | 72 | +0,26 [−0,12 ; +0,79] | +0,61 | +0,18 | 0,32 | 58,2 % | 54,1 % | +2 413 |
| FEU_ADX, T_MIN 0 | 93 | +0,16 | +0,53 | +0,08 | 0,32 | 36,1 % | 50,6 % | — |
| ORB_HEI60, T_MIN 1,5 | 65 | +0,14 | +0,67 | +0,05 | 0,29 | 14,5 % | 40,5 % | — |
| MONDAY_VOL, T_MIN 1,5 | 22 | +0,10 | +0,63 | −0,01 | 0,35 | 11,7 % | 38,5 % | — |
| SEANCE_ALIGNE, T_MIN 1,5 | 35 | +0,06 | +0,71 | +0,06 | 0,48 | 1,2 % | 45,9 % | — |
| **UNIQUE, T_MIN 1,5** | 45 | +0,03 | +0,52 | −0,03 | 0,39 | 3,6 % | 19,1 % | −159 |
| **UNIQUE, T_MIN 0** | 52 | +0,01 | +0,47 | −0,09 | 0,32 | 3,6 % | 12,5 % | — |
| ORB_HEI60, T_MIN 0 | 94 | +0,01 | +0,47 | +0,01 | 0,55 | 4,6 % | 29,3 % | — |
| COMPOSITE, T_MIN 0 / 1,5 | 70 / 26 | −0,06 / −0,03 | +0,47 / +0,60 | −0,04 / +0,03 | 0,55 / 0,65 | 0,1 % / 0,0 % | 18,4 % / 37,5 % | −165 |
| TENDANCE_VOL, T_MIN 0 | 82 | −0,10 | +0,42 | +0,10 | 0,90 | 4,0 % | 38,2 % | — |

Tableau complet : `walk_forward_variantes.csv`. Avec T_MIN 2,5, presque toutes les partitions ne tradent
plus (aucun couple n'atteint ce t sur le passé). C'est la réponse honnête « pas de trade » dans tous les
états.

**Aiguillage contre setup unique** (même T_MIN, différence de R par jour de test, bootstrap) : aucune
différence significative. La meilleure est JOUR_US 0 : +0,54 R par jour [−0,30 ; +1,60], p unilatéral 0,12.
Vient ensuite ORB_HEI60 1,5 : +0,22 [−0,22 ; +0,66], p 0,16. Ce sont les meilleures de 21 comparaisons,
donc rien de significatif.

**Surapprentissage** : décote moyenne de +0,64 R par trade entre le développement et le pli suivant (médiane
+0,57). Corrélation entre les deux de −0,15. Choix instables : avec T_MIN 0, seulement 42 à 62 % des états
gardent le même setup d'un pli au suivant. Le « meilleur setup unique » change à presque chaque pli
(heiflip long → orb long → Signator short → Detector).

**JOUR_US (+0,26 R, P 58 %)** ne doit pas être retenue. Elle sort première d'un classement de 24 variantes
fait sur le hors échantillon lui-même. Son IC contient 0. Le hasard fait presque aussi bien (P 54 %, p 0,32).
Et un aiguillage par jour de semaine × séance n'a aucune raison économique solide.

**Pourquoi le hasard a souvent une meilleure P(réussite)** : sur 34 jours seulement, la P(réussite) dépend
surtout du nombre de trades et du sens dans un marché haussier. Les tirages au hasard gardent la même
fréquence et le même sens, mais ils évitent la sélection perdante. Lire avant tout le R moyen et le p
hasard.

## Ce qui marche / ne marche pas
- Marche : la machine (états causaux, sélection sur le passé, rejeu exact, hasard, propfirm, registre), prête pour le DATASET.
- Ne marche pas : choisir un setup par état sur 2 mois. Chaque état n'a que 10 à 20 trades par setup en apprentissage,
  et le maximum sur 648 setups est du bruit. L'option « pas de trade » (T_MIN élevé) est la plus sûre :
  elle supprime presque tous les trades.

## Limites
- Cache : environ 2 mois. MES avr.-juin n'a pas de volume (ni Climax ni Detector). Le Feu est un PROXY à 12
  voix ramené sur 29. Le Signator Moyen est absent. TREND et Heishinator 60/240 viennent des vrais prix
  agrégés. Le TREND 1D n'est pas utilisé (historique trop court).
- La sélection en apprentissage utilise les trades du balayage sans masque, étiquetés par l'état de la barre
  signal (approximation : effets de blocage entre positions). Le test, lui, est rejoué exactement.
- Le Monte-Carlo propfirm est fait sur 34 jours de test mis bout à bout : ordre de grandeur seulement.
- Registre : REG-0004 (JOUR_US 0, meilleur hors échantillon, sélectionné a posteriori), REG-0005
  (COMPOSITE 1,5, partition définie à l'avance) et REG-0006 (setup unique 1,5). Ces lignes REMPLACENT
  REG-0001 à 0003, calculées avant la correction du moteur (trous de données). Les chiffres de ces trois
  recettes sont identiques, mais d'autres variantes ont un peu bougé. Tout ce fichier vient de la relance
  avec le moteur corrigé ; aucun trade hors échantillon ne dure plus d'une journée. `p_ref_hasard` = P(réussite)
  de la référence au hasard. Les trades écrits sont ceux du hors échantillon.
- Rien n'a été lu du scellé.
