# Climax / Climator — état du calage (10/10/2026)

Premier calage du module, jusque-là listé « jamais traité » (MEMOIRE_PROJET.md §6.4).
Vérité terrain : marqueurs `clx_` de `api_vitrine_instantane.json` (copie du 02/10),
**86 événements en 15m, 96 en 2m**, chacun avec `sens` (buy/sell) et `niveau` (HIGH/PREMIUM).
Alignement vérifié : les 182 `t` tombent tous sur un `bougie['t']//1000`.

## La règle retenue

Toutes les valeurs sur bougies **Heiken Ashi**, sauf le volume.

```
rg   = h - l                       (HA)
vr   = volume / SMA20(volume)      (barre courante incluse)
body = (c - o) / rg                (HA)

BUY   si o == l  et  body >=  0.55  et  vr >= 1.5
        niveau PREMIUM si vr >= 2.0 et body >= 0.70, sinon HIGH
SELL  si o == h  et -body >=  0.65  et  vr >= 2.0
        niveau TOUJOURS HIGH
```

Script : `sim_climax.py` (dépend de `sim_climax_feat.py`, qui réutilise `ema`/`rma` de
`sig_api.py`). Oracle extrait par `sim_climax_base.py` vers `oracle_climax.csv`.

## Résultats (barres >= 300, vérifiés deux fois)

| unité | exactes | en trop | manquées | rappel | précision | niveau correct |
|---|---:|---:|---:|---:|---:|---:|
| 15m | 63 | 7 | 6 | 91 % | 90 % | 57/63 (90 %) |
| 2m | 84 | 7 | 2 | 98 % | 92 % | 77/84 (92 %) |

Hold-out (barres 30-299, jamais utilisées pour le calage) : 15m 14 exactes / 1 trop / 3 manquées,
niveau 14/14 ; 2m 8 exactes / 5 trop / 2 manquées, niveau 8/8.

Robustesse : sur 8 000 combinaisons de la grille finale, 380 donnent <= 28 erreurs. Le plateau
est large autour de 0.55 / 1.5 / 0.65 / 2.0. Le meilleur point était `sell body >= 0.675`
(20 erreurs) ; 0.65 a été gardé par prudence.

## Faits structurels établis

1. **Quasi-condition nécessaire : bougie HA sans mèche du côté du sens** — buy `o == l`,
   sell `o == h`. Vrai pour 52/56 buys et 13/13 sells en 15m. Mais cette condition seule laisse
   291 faux candidats buy en 15m : ce n'est donc pas un simple « marubozu HA ».
2. **Le volume est le discriminant le plus fort** : AUC 0.96 sur les candidats sans mèche.
   SMA20 incluant la barre courante bat toutes les variantes testées (SMA/EMA de 10, 14, 20, 30,
   50, avec ou sans la barre courante).
3. **Le corps HA est une vraie porte, pas un compromis** : dans la bande 0.50-0.55, même avec un
   volume > 4x la moyenne, on compte 0 vrai pour 14 faux.
4. **Les sells sont plus exigeants que les buys** (volume 2.0 vs 1.5, corps 0.65 vs 0.55) et
   **aucun sell n'est jamais PREMIUM**, même à volume 12x et corps 0.76. Les buys sont 3 à 4 fois
   plus nombreux que les sells.
5. **Les événements s'enchaînent** : beaucoup de climax sont sur des barres consécutives.

## LA PISTE N°1 — les faux positifs sont de deux natures

Analyse faite après le rapport de l'agent, et c'est le point le plus actionnable. Pour chacun
des 14 faux positifs, on a cherché s'il existait un climax de l'original à +-3 barres :

| nature | effectif | détail |
|---|---:|---|
| **Calage temporel** (un climax original est à +-3 barres) | **5 / 14** | 15m 650 (+2), 655 (-3 et -1), 1434 (+1) ; 2m 658 (+1), 1323 (+1) |
| **Vrai faux** (original muet sur des dizaines de barres) | **9 / 14** | 15m 623, 1226, 1349, 1371 ; 2m 618, 635, 663, 894, 1234 |

Conséquence : **~35 % des faux tomberaient avec une règle de déduplication** (un seul climax par
vague), et non avec un critère supplémentaire. Cela recoupe le commit `984bdff`
(« un seul climax par vague — hystérèse + cooldown ») et la formation, qui décrit une
**fenêtre de confirmation de 3 barres**. En 15m la barre 655 est le cas d'école : l'original a
déjà déclenché deux fois juste avant, on en ajoute une troisième.

Les 9 vrais faux, eux, sont presque tous en limite de seuil (volume 1.5-2.0, corps 0.55-0.60) :
une troisième variable manque bien pour ceux-là.

## Pistes ÉPUISÉES — ne pas refaire

Environ 17 700 combinaisons testées au total (1 800 position x volume, 5 390 corps^p x volume,
5 120 en séparé buy/sell, 8 000 pour la grille finale, 15 en bougies réelles), plus 32 490 paires
de seuils pour le niveau PREMIUM.

- Proxys de pression 0-100 (MFI-like, ratio), lissés RMA/EMA/SMA, périodes 5 et 14, sur HA et sur
  réel : AUC 0.70-0.97 mais **toujours moins bons** que « sans mèche + volume + corps ».
- La pression de `CLIMAX.pine` (période 14) : AUC 0.78-0.89. **Ce proxy n'est pas la bonne piste.**
- Règle sur bougies **réelles** (`cr/hr/lr`, position du close + volume, 15 combinaisons) :
  171 erreurs sur 155 événements. Inutilisable.
- Volume contre SMA/EMA de longueur != 20.
- Régression logistique sur 9 features, entraînée sur une unité et testée sur l'autre :
  fait à peu près aussi bien, sans dépasser la règle à seuils.
- Distinction HIGH/PREMIUM par un seul seuil : au mieux 15 erreurs sur 56-69.
- Lien avec le caractère consécutif du signal : pas d'effet net au premier examen
  (mais voir la piste n°1 ci-dessus, qui le réexamine autrement).

## Réserves honnêtes

- **Un seul instrument** (XYZ100) et **une seule période** (~1 500 barres par unité, copie du
  02/10). Rien n'est confirmé sur les CSV TradingView.
- **Les seuils sell reposent sur 13 et 19 exemples** : entre 0.625 et 0.70 on ne distingue rien.
- **Le niveau PREMIUM repose sur 40 événements**, choisis parmi 32 490 paires de seuils :
  surapprentissage possible, même si les deux unités donnent les mêmes seuils.
- **Aucun paramètre de la formation retrouvé** (14, 5, 0.3, 70/30, 40/55/70/85, fenêtre 3 barres).
  L'hypothèse du preset EMU (HIGH = Fort, PREMIUM = Premium) est compatible mais non prouvée :
  le ratio des seuils PREMIUM/HIGH vaut 1.33 en volume et 1.27 en corps, contre 85/70 = 1.21.
- La copie d'API date du **02/10**, et Ephore a changé de version le 30/09 : non revérifié.

## Ce qu'il faut pour aller plus loin

1. **Une règle de déduplication** sur la fenêtre de 3 barres (piste n°1). Faisable tout de suite,
   sans nouvelle donnée.
2. **Un export TradingView avec les triangles climax sur MES ou NQ**, volume affiché, pour
   valider les seuils hors de XYZ100.
3. **Un screen du panneau Climator** avec la pression acheteuse affichée sur une barre portant un
   triangle HIGH puis PREMIUM : ce serait la valeur numérique qui manque pour comprendre 70 vs 85.
4. Non testé : distance à un extrême récent (plus haut/bas sur N barres) ; composante horaire.
