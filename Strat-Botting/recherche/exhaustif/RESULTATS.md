# Explorateur exhaustif (EXH) — résultats

Données : `cache` (séries Python ≈ 2 mois, vrais prix reconstitués), **développement seulement** (75 %, scellé non ouvert). MES et NQ regroupés par unité, tradés en micros (MES / MNQ), coûts du moteur, intrajournée forcée (15:59 Chicago). Relancer sur le DATASET : `balayage.py --source dataset` puis `finalistes.py --registre` puis `rapport.py`.

## Verdict

- **5152 variantes testées** (3297 classables : ≥ 20 trades, sans doublon).
- **Reality Check de White sur toutes les variantes classables : p = 0.20** (meilleure : `zone_entree|inverse|les_deux|30m|hors_annonces|stop 1 ATR, obj 4R, sortie_hei`). Le meilleur résultat du balayage est compatible avec le hasard (biais de sélection).
- **Walk-forward de la procédure** (choisir le n°1 du classement sur 2 blocs, le jouer sur le bloc suivant, 4 plis) : R moyen hors échantillon du n°1 = -0.49 ; des 10 premiers = -0.20 ; de toutes les variantes = +0.21.
- **Deflated Sharpe** (N = 5152 essais) des 20 premiers : max 0.63 (il faudrait > 0,95).
- Monte-Carlo Tradeify Select Flex sur les 10 finalistes : P(réussite) de 86 % à 100 %, contre 23 % à 68 % pour les entrées au hasard avec la même gestion.
- **Conclusion : rien de robuste sur ces données** (aucune recette ≥ 200 trades ; IC95 larges ; sélection non distinguable du hasard). La machine est prête : même code sur le DATASET.

## Méthode

1. Étape 1 : chaque déclencheur seul × mode (suivi / inverse = jouer contre l'événement) × sens (long, short, les deux) × unité (5, 15, 30, 60 min), gestion de référence stop 2 ATR / objectif 2R.
2. Étape 2 : les 30 meilleures bases (≤ 3 par déclencheur) + chacun des filtres disponibles.
3. Étape 3 : paires parmi les 8 meilleurs filtres de chaque base (20 bases), puis 3e filtre sur les 10 meilleures.
4. Étape 4 : 12 finalistes × 6 stops (1-4 ATR, niveau de protection) × 7 objectifs (1-4R, aucun, prochain niveau) × 5 options (rien, break-even 1R, suiveur 3 ATR, sortie Heishinator, sortie après 16 barres).
5. Note robuste = borne basse de l'IC80 du R moyen (bootstrap par journée CME), −1 si < 20 trades, −0,5 si < 12 journées (le 5 min n'en a que ~6 : non classable), −0,25 si moins de la moitié des blocs chronologiques (4 par jeu) sont positifs, −0,1 si un des deux marchés est négatif.
6. Biais de sélection : Reality Check de White (bootstrap stationnaire, blocs de 5 jours) sur le R journalier de toutes les variantes classables ; Deflated Sharpe ; walk-forward de la procédure de sélection.
7. Finalistes : `simulateur.optimise_taille` (Select Flex, ordre prudent, 1 000 parcours) et référence `reference_hasard` (20 tirages, même gestion, même heure) passée au même simulateur.

## Top 20 (note robuste, toutes étapes, sans doublon)

| # | recette (déclencheur·mode·sens·UT·filtres·sortie) | n | R moyen | IC95 | PF | blocs + | R MES | R NQ | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `asie_cassure|suivi|long|30m|dash240_avec+hors_annonces|stop 2 ATR, obj 2R` | 21 | +1.06 | [+0.36 ; +1.63] | 7.25 | 100 % | +0.90 | +1.15 | +0.62 |
| 2 | `zone_entree|inverse|les_deux|30m|espace_lt1|stop 1 ATR, obj 4R` | 35 | +1.30 | [+0.32 ; +2.28] | 3.92 | 100 % | +1.47 | +1.13 | +0.62 |
| 3 | `feu_0.5|suivi|short|60m|adx_ge20+hei_avec+trend1D_contre|stop 2 ATR, obj 2R` | 20 | +0.90 | [+0.42 ; +1.34] | 4.69 | 100 % | +0.87 | +0.94 | +0.60 |
| 4 | `orb_cassure|inverse|les_deux|30m|hei_contre+sauf_lundi|stop 2 ATR, obj 2R` | 21 | +0.85 | [+0.47 ; +1.20] | 11.62 | 100 % | +0.83 | +0.87 | +0.60 |
| 5 | `feu_0.3|suivi|short|60m|hei_avec+sauf_vendredi+trend1D_contre|stop 2 ATR, obj 2R` | 24 | +0.89 | [+0.45 ; +1.29] | 7.90 | 100 % | +0.98 | +0.80 | +0.60 |
| 6 | `zone_cassee|suivi|long|30m|dash60_avec+hors_annonces|stop 1 ATR, obj 4R` | 34 | +1.09 | [+0.42 ; +1.78] | 3.40 | 67 % | +0.88 | +1.28 | +0.60 |
| 7 | `asie_cassure|suivi|long|30m|dash240_avec+hei_avec|stop 2 ATR, obj 2R` | 21 | +1.01 | [+0.35 ; +1.58] | 6.76 | 100 % | +0.92 | +1.08 | +0.58 |
| 8 | `asie_cassure|suivi|long|30m|dash240_avec|stop 2 ATR, obj 2R` | 23 | +0.97 | [+0.32 ; +1.51] | 6.33 | 100 % | +0.72 | +1.15 | +0.58 |
| 9 | `feu_0.5|suivi|short|60m|di_avec+hei_avec+trend1D_contre|stop niveau, sans obj` | 31 | +1.31 | [+0.21 ; +2.62] | 3.18 | 67 % | +1.08 | +1.56 | +0.57 |
| 10 | `zone_cassee|suivi|long|30m|dash60_avec+hors_annonces|stop 1 ATR, obj 4R, suiveur3` | 34 | +1.07 | [+0.36 ; +1.76] | 3.31 | 67 % | +0.95 | +1.17 | +0.56 |
| 11 | `orb_cassure|inverse|les_deux|30m|sauf_lundi|stop 1.5 ATR, sans obj, suiveur3` | 29 | +0.97 | [+0.38 ; +1.70] | 6.73 | 100 % | +1.08 | +0.87 | +0.55 |
| 12 | `asie_cassure|suivi|long|30m|dash240_avec+hei_avec+hors_annonces|stop 2 ATR, obj 2R` | 20 | +1.01 | [+0.32 ; +1.60] | 6.57 | 100 % | +0.90 | +1.08 | +0.55 |
| 13 | `zone_entree|inverse|les_deux|30m|espace_lt1|stop 1 ATR, obj 4R, suiveur3` | 36 | +1.22 | [+0.26 ; +2.18] | 3.74 | 100 % | +1.57 | +0.86 | +0.55 |
| 14 | `orb_cassure|inverse|les_deux|30m|sauf_lundi|stop 1.5 ATR, obj 4R, suiveur3` | 30 | +0.91 | [+0.37 ; +1.50] | 5.89 | 100 % | +0.89 | +0.92 | +0.54 |
| 15 | `zone_cassee|suivi|long|30m|dash60_avec+hors_annonces|stop 1 ATR, obj 4R, sortie_hei` | 34 | +1.04 | [+0.33 ; +1.74] | 3.22 | 67 % | +0.88 | +1.18 | +0.54 |
| 16 | `feu_0.5|suivi|short|60m|di_avec+hei_avec+trend1D_contre|stop niveau, obj 4R` | 33 | +1.13 | [+0.23 ; +2.14] | 2.84 | 83 % | +0.96 | +1.30 | +0.54 |
| 17 | `zone_entree|inverse|les_deux|30m|hors_annonces|stop 1 ATR, obj 4R, sortie_hei` | 45 | +1.06 | [+0.27 ; +1.90] | 3.61 | 100 % | +0.80 | +1.32 | +0.53 |
| 18 | `zone_entree|inverse|les_deux|30m|espace_lt1|stop niveau, obj niveau, sortie_hei` | 33 | +0.92 | [+0.32 ; +1.48] | 3.81 | 100 % | +1.06 | +0.78 | +0.53 |
| 19 | `feu_0.5|suivi|short|60m|hei_avec+trend1D_contre|stop niveau, sans obj` | 32 | +1.24 | [+0.14 ; +2.59] | 2.88 | 71 % | +1.08 | +1.40 | +0.53 |
| 20 | `orb_cassure|inverse|les_deux|30m|sauf_lundi|stop 1.5 ATR, sans obj` | 29 | +0.95 | [+0.34 ; +1.70] | 6.10 | 100 % | +1.04 | +0.86 | +0.52 |

## Finalistes : Monte-Carlo Tradeify

| recette | n | R moyen | taille (micros) | P(réussite) Flex | P hasard | P(1er payout) | VE $ | P Growth | p hasard (R) |
|---|---|---|---|---|---|---|---|---|---|
| `zone_entree|inverse|les_deux|30m|espace_lt1|stop 1 ATR, obj 4R` | 35 | +1.30 | 2 | 100 % | 54 % | 100 % | +10850 | 100 % | 0.05 |
| `zone_cassee|suivi|long|30m|dash60_avec+hors_annonces|stop 1 ATR, obj 4R` | 34 | +1.09 | 2 | 87 % | 48 % | 81 % | +7172 | 100 % | 0.05 |
| `feu_0.5|suivi|short|60m|di_avec+hei_avec+trend1D_contre|stop niveau, sans obj` | 31 | +1.31 | 2 | 90 % | 24 % | 86 % | +8665 | 100 % | 0.05 |
| `orb_cassure|inverse|les_deux|30m|sauf_lundi|stop 1.5 ATR, obj 4R, suiveur3` | 30 | +0.91 | 2 | 100 % | 29 % | 100 % | +10370 | 100 % | 0.05 |
| `zone_cassee|suivi|les_deux|15m|hors_annonces+vol_0.9_1.2|stop 1.5 ATR, obj 3R, suiveur3` | 31 | +1.02 | 2 | 100 % | 24 % | 100 % | +10788 | 100 % | 0.05 |
| `feu_0.3|suivi|short|60m|hei_avec+hors_annonces|stop 1.5 ATR, obj 3R, temps16` | 33 | +0.85 | 2 | 100 % | 23 % | 100 % | +10669 | 100 % | 0.05 |
| `londres_cassure|suivi|long|15m|hei60_avec+hors_londres|stop 2 ATR, obj 2R` | 35 | +0.56 | 3 | 93 % | 46 % | 92 % | +5930 | 84 % | 0.05 |
| `feu_0.5|suivi|les_deux|60m|trend1D_contre|stop 2 ATR, obj 2R` | 46 | +0.42 | 1 | 96 % | 30 % | 94 % | +4988 | 96 % | 0.05 |
| `zone_entree|inverse|long|30m|hors_annonces|stop 2 ATR, obj 2R` | 30 | +0.49 | 1 | 91 % | 68 % | 87 % | +4395 | 91 % | 0.14 |
| `adx20_croise|suivi|les_deux|15m|dash60_avec|stop 2 ATR, obj 2R` | 57 | +0.37 | 2 | 86 % | 33 % | 81 % | +2932 | 86 % | 0.10 |

Lecture : le Monte-Carlo ré-échantillonne par blocs de journées les ~30 trades de ~3 semaines : une P(réussite) proche de 100 % veut seulement dire « si l'avenir ressemblait exactement à ces 3 semaines ». La référence au hasard (même gestion, mêmes heures) est elle aussi très haute sur cette période haussière : c'est l'écart à la référence qui compte, et il n'est pas confirmé par le walk-forward.

## Walk-forward de la procédure de sélection

Approximation : les variantes des étapes 2-4 ont été construites en regardant tout le développement ; le walk-forward refait seulement le CHOIX final (il est donc plutôt optimiste).

| pli | candidats | n°1 choisi sur l'apprentissage | note app. | R test n°1 (n) | R test top 10 | R test tous |
|---|---|---|---|---|---|---|
| 0 | 1721 | `zone_entree|inverse|les_deux|30m|hors_annonces|stop 1 ATR, obj 3R` | +1.07 | -1.04 (3) | -0.39 | +0.02 |
| 1 | 1720 | `adx20_croise|suivi|les_deux|15m|sauf_lundi|stop 2 ATR, obj 2R` | +1.16 | -0.59 (15) | -0.28 | +0.08 |
| 2 | 1951 | `monday_cassure|inverse|les_deux|15m|-|stop 2 ATR, obj 2R` | +0.99 | -0.31 (12) | -0.72 | +0.16 |
| 3 | 1783 | `us_rejet|suivi|long|15m|-|stop 2 ATR, obj 2R` | +0.86 | -0.03 (5) | +0.60 | +0.57 |

## Carte : ce qui ne marche jamais

**Déclencheurs dont AUCUNE variante classable n'a une note positive** (borne basse IC80 < 0 partout, toutes UT, modes, sens, filtres, sorties) : `climax`, `hei60_change`, `londres_rejet`, `monday_rejet`, `orb_rejet`, `supertrend_flip`, `trend15_change`, `trend60_change`, `us_cassure`, `us_rejet`, `veille_cassure`.

Lecture : « suivi » et « inverse » sont presque des images miroir avant coûts ; un déclencheur sans aucune note positive n'a donc d'avantage dans AUCUN des deux sens une fois les coûts payés.

Attention : les déclencheurs promus aux étapes 2-4 ont beaucoup plus de variantes (et donc plus de chances d'avoir un « gagnant » par hasard). La colonne « étape 1 » compare à armes égales (déclencheur seul, 12 à 24 combinaisons UT × mode × sens, ≥ 10 trades).

| déclencheur | étape 1 : combinaisons | étape 1 : part R > 0 | étape 1 : R médian | variantes classables (toutes étapes) | meilleur R | meilleure note |
|---|---|---|---|---|---|---|
| adx20_croise | 20 | 35 % | -0.18 | 58 | +0.73 | +0.37 |
| orb_cassure | 14 | 29 % | -0.13 | 164 | +0.97 | +0.60 |
| monday_cassure | 16 | 31 % | -0.10 | 20 | +0.47 | +0.13 |
| trend15_change | 6 | 33 % | -0.08 | 6 | +0.66 | -0.11 |
| supertrend_flip | 24 | 38 % | -0.06 | 12 | +0.08 | -0.23 |
| londres_cassure | 20 | 45 % | -0.05 | 480 | +0.68 | +0.31 |
| climax | 24 | 38 % | -0.05 | 20 | +0.44 | -0.10 |
| trend240_change | 14 | 43 % | -0.05 | 22 | +0.46 | +0.24 |
| veille_rejet | 18 | 44 % | -0.04 | 62 | +0.62 | +0.29 |
| asie_cassure | 22 | 36 % | -0.04 | 44 | +1.06 | +0.62 |
| sig_tous | 24 | 38 % | -0.04 | 0 | — | — |
| sig_fort | 24 | 38 % | -0.04 | 29 | +1.02 | +0.36 |
| ema50_croise | 24 | 42 % | -0.04 | 43 | +0.47 | +0.19 |
| feu_0.3 | 24 | 42 % | -0.04 | 436 | +1.04 | +0.60 |
| londres_rejet | 20 | 40 % | -0.04 | 16 | +0.20 | -0.22 |
| ema60_croise | 24 | 46 % | -0.04 | 92 | +0.44 | +0.22 |
| orb_rejet | 13 | 38 % | -0.03 | 9 | +0.17 | -0.07 |
| veille_cassure | 18 | 44 % | -0.03 | 16 | +0.31 | -0.07 |
| trend60_change | 14 | 43 % | -0.03 | 10 | +0.26 | -0.32 |
| feu_0.5 | 24 | 46 % | -0.02 | 391 | +1.31 | +0.60 |
| tl_cassure | 20 | 40 % | -0.02 | 14 | +0.48 | +0.03 |
| zone_cassee | 24 | 46 % | -0.02 | 678 | +1.09 | +0.60 |
| us_cassure | 20 | 40 % | -0.02 | 18 | +0.25 | -0.08 |
| asie_rejet | 22 | 45 % | -0.01 | 70 | +0.30 | +0.08 |
| hei60_change | 14 | 50 % | +0.00 | 8 | +0.17 | -0.20 |
| hei_flip | 24 | 58 % | +0.01 | 74 | +0.52 | +0.10 |
| us_rejet | 20 | 55 % | +0.04 | 14 | +0.22 | -0.06 |
| zone_entree | 24 | 62 % | +0.04 | 441 | +1.30 | +0.62 |
| monday_rejet | 13 | 69 % | +0.07 | 8 | +0.18 | -0.07 |
| zone_sortie | 21 | 62 % | +0.14 | 42 | +0.48 | +0.12 |

Étape 1 (déclencheur seul) — R médian : suivi -0.02 / inverse -0.03 ; long -0.04 / short -0.03 / les deux -0.01 ; par UT : 5m -0.05, 15m -0.03, 30m -0.01, 60m -0.01.

**Effet moyen de chaque filtre** (étape 2, Δ R moyen par rapport à la base sans filtre, bases avec ≥ 10 trades). Les filtres en tête de liste dégradent presque toujours :

| filtre | bases | Δ R moyen | part des bases améliorées |
|---|---|---|---|
| trend15_avec | 1 | -0.85 | 0 % |
| mercredi | 12 | -0.24 | 17 % |
| espace_ge2 | 7 | -0.23 | 14 % |
| us_1430_22 | 26 | -0.23 | 15 % |
| vol_ge1.2 | 18 | -0.20 | 11 % |
| us_apm_1730_22 | 12 | -0.19 | 17 % |
| trend1D_avec | 26 | -0.15 | 31 % |
| hei240_avec | 28 | -0.15 | 29 % |
| hei_contre | 21 | -0.14 | 29 % |
| dash60_contre | 12 | -0.13 | 33 % |
| supertrend_contre | 24 | -0.11 | 38 % |
| trend240_avec | 27 | -0.11 | 30 % |
| pas_nuit_8_22 | 30 | -0.08 | 17 % |
| us_ouv_1530_1730 | 12 | -0.08 | 50 % |
| dash240_contre | 24 | -0.07 | 38 % |
| ema50_contre | 15 | -0.07 | 40 % |
| hei60_contre | 16 | -0.07 | 38 % |
| vol_ge0.9 | 30 | -0.06 | 33 % |
| vol_0.9_1.2 | 27 | -0.06 | 44 % |
| vwap_contre | 18 | -0.06 | 39 % |
| adx_lt20 | 14 | -0.06 | 36 % |
| hors_londres | 30 | -0.06 | 37 % |
| adx_ge20 | 30 | -0.04 | 27 % |
| hei60_avec | 18 | -0.04 | 50 % |
| trend60_avec | 18 | -0.04 | 39 % |
| sauf_lundi | 30 | -0.04 | 30 % |
| espace_lt1 | 30 | -0.04 | 33 % |
| feu_avec_0.3 | 23 | -0.02 | 26 % |
| espace_ge1 | 19 | -0.02 | 42 % |
| trend60_contre | 16 | -0.02 | 38 % |
| rsi_avec | 24 | -0.02 | 33 % |
| vwap_avec | 24 | -0.02 | 46 % |
| sauf_vendredi | 30 | -0.02 | 50 % |
| feu_avec_0 | 23 | -0.01 | 35 % |
| adx_ge25 | 26 | -0.01 | 38 % |
| di_avec | 24 | -0.01 | 46 % |
| ema50_avec | 24 | -0.01 | 33 % |
| dash240_avec | 27 | +0.00 | 59 % |
| vol_lt0.9 | 16 | +0.01 | 50 % |
| dash60_avec | 17 | +0.01 | 65 % |
| supertrend_avec | 29 | +0.01 | 48 % |
| mardi | 12 | +0.02 | 58 % |
| londres_8_1430 | 21 | +0.03 | 52 % |
| hors_annonces | 30 | +0.03 | 70 % |
| feu_contre_0.3 | 11 | +0.03 | 45 % |
| feu_avec_0.5 | 23 | +0.04 | 52 % |
| jeudi | 13 | +0.05 | 46 % |
| trend240_contre | 26 | +0.06 | 50 % |
| hei_avec | 26 | +0.06 | 62 % |
| hei240_contre | 27 | +0.07 | 59 % |
| lundi | 10 | +0.08 | 60 % |
| asie_0_8 | 22 | +0.10 | 73 % |
| trend1D_contre | 22 | +0.11 | 64 % |
| vendredi | 7 | +0.25 | 86 % |
| trend15_contre | 1 | +0.38 | 100 % |

**Sorties (étape 4, R moyen médian sur les finalistes)** — stop : ('atr', 1.0) +0.34, ('atr', 1.5) +0.46, ('atr', 2.0) +0.46, ('atr', 3.0) +0.37, ('atr', 4.0) +0.30, ('niveau', None) +0.34 ; objectif : ('R', 1.0) +0.28, ('R', 1.5) +0.35, ('R', 2.0) +0.39, ('R', 3.0) +0.42, ('R', 4.0) +0.41, ('aucun', None) +0.41, ('niveau', None) +0.42 ; option : be1R +0.35, rien +0.41, sortie_hei +0.36, suiveur3 +0.39, temps16 +0.35.

## Limites

- ≈ 3 semaines de développement par jeu en 15/30 min (7 semaines pour MES1 avril-juin, 6 semaines en 60 min), ~6 jours en 5 min : toutes les recettes ont < 200 trades, aucune ne peut être « probante » au sens de SPEC.md.
- Régime : surtout haussier (sept.-oct.) ; MES1 n'a ni volume (pas de climax ni Detector) ni flèches recalculées (flèches de l'original).
- Feu = **substitut** (vote par le sens de 8 à 16 états disponibles) tant que le DATASET n'est pas là ; blocs SuperTrader/SIGNAL (VIDYA, MACD 10 min, PA, LinReg, ORB du SIGNAL) et divergences RSI absents du cache : leurs filtres/déclencheurs s'activent tout seuls avec le DATASET.
- Niveaux de session / ORB / Monday / veille recalculés sur vrais prix (dernière fenêtre terminée) ; ORB non défini au-dessus de 30 min.
- MES et NQ sur des périodes en partie communes : trades corrélés, l'IC par journée en tient compte en partie.

## Fichiers

`donnees_exh.py` (accès données, une seule fonction `charger_jeux`), `bibliotheque.py` (déclencheurs, filtres, sorties), `balayage.py` (étapes 1-4, notation, White, DSR, walk-forward), `finalistes.py` (Monte-Carlo, registre), `rapport.py` ; sorties : `balayage_complet.csv`, `wf_procedure.csv`, `finalistes.csv`, `meta_balayage.json`, `journal_balayage.txt`.
