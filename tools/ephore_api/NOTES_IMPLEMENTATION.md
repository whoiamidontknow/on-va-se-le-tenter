# Détails d'implémentation des indicateurs — FAMILLE FERMÉE (12/10/2026)

Recherche menée pour expliquer les 8 cas limites du Signator V8 (153/6/2).
**Verdict : rien n'y bat 153/6/2.** Les 8 écarts ne venaient pas d'un calcul inexact — ils
demandaient **une variable absente**, ce que la V9 a fourni (`range >= 0.5·ATR OU cpos >= 0.67`).

1 040 variantes exécutées, dont 530 dans cette famille. Scripts : `impl_lab_*.py`.

## DEUX DÉCOUVERTES POSITIVES, prouvées par la donnée

### 1. L'amorçage de `ta.ema` de Pine est une SMA — vérifié au centième

`MES 1D` démarre à la première bougie du contrat, donc la colonne `Moyenator 1` (l'EMA50
**exacte** de l'original) révèle son amorçage :

| | 1re valeur à l'index | attendu (`length − 1`) | valeur | SMA correspondante | écart |
|---|---:|---:|---|---|---:|
| EMA50 | 49 | 49 | 6953.1825 | SMA(close,50) = 6953.1825 | **0.000000** |
| EMA60 | 59 | 59 | 6947.5604 | SMA(close,60) = 6947.5604 | **0.000000** |

→ **`ta.ema(src, n)` renvoie `na` avant la barre `n−1`, puis s'amorce par `SMA(src, n)`.**
Ce n'est plus une supposition. À utiliser dans tout simulateur Python du projet.
Effet sur les flèches : **nul** (153/6/2 dans les 4 combinaisons d'amorçage), et l'état
Heishinator est identique sur 8599/8599 barres après 100 barres de chauffe.

### 2. Le volume nul de NQ 1D : la comparaison est bien large (`>=`)

`NQ 1D` a 644 barres sur 780 à volume nul. Sur ces barres `volume = 0` et `SMA20 = 0`, donc
`0 >= 0` est **vrai** : la clause volume passe toujours.

Ce n'est pas un artefact de notre code. Preuve : **NQ 1D 2025-05-01** a volume 0, SMA20 0,
`dBand = −0.072` — et **l'original y met une flèche**. Rendre le test strict, ou traiter le 0
comme `na`, supprime le faux positif de décembre **mais crée cette manquée de mai** : 8 erreurs
dans les deux cas. Ce faux positif **n'est pas corrigible** : il naît du mécanisme même qui
produit une vraie flèche.

## L'ARGUMENT QUI FERME LA PISTE ADX

Deux faux positifs ont un ADX de 18.37 et 18.69, à peine au-dessus du seuil 18. Il semblait
donc plausible que notre ADX soit légèrement surévalué. **C'est arithmétiquement impossible.**

```
ADX des 155 vraies flèches, les 4 plus faibles : 18.222 · 18.473 · 18.663 · 18.674
Faux positif à éliminer                        : 18.369
Marge disponible : 0.222 point    Besoin : 0.369 point
```

Pour tuer le faux positif il faudrait baisser l'ADX de 0.369 — on perdrait d'abord la vraie
flèche à 18.222. Vérifié par balayage : seuil 18.0 → 8 erreurs, 18.2 → 8, 18.4 → 8 (le faux part,
une vraie aussi), 18.5 → 9, 19.0 → 13.

Et aucune variante d'implémentation ne déplace l'ADX de plus de **0.05 point** après 100 barres
de chauffe : le RMA de Wilder amortit tout choix d'amorçage d'un facteur (13/14)ⁿ, soit 4·10⁻⁴
dès l'index 109. **Toute tentative future de corriger les cas limites par un recalage de l'ADX
est vouée à l'échec.**

## PISTES ÉPUISÉES — ne plus rechercher

| piste | variantes | résultat |
|---|---:|---|
| Amorçage ADX (SMA vs 1re valeur, `ta.tr` vs `ta.tr(true)`, DM na vs 0) | — | écart ≤ 0.05 pt, 20× trop peu |
| Longueurs DI × lissage ADX | 121 | **(14,14) optimum strict**, 2e à +5 erreurs |
| Lissage du DX : SMA, EMA au lieu de RMA | — | +36 et +29 erreurs. RMA de Wilder confirmé |
| Arrondis (ADX entier, dBand 0.1, prix au tick) | 20 | tous neutres ou pires |
| **ADX/ATR sur bougies RÉELLES** | 8 | **réfuté** : rappel 23/23 → 17/23 en 15m. C'est bien du HA |
| Amorçage des EMA | 6 | identifié (SMA) et sans aucun effet |
| ATR : RMA/SMA/EMA, 1re barre, périodes 7-28 | 12 | aucune n'aide, et les corrections nécessaires sont **contradictoires** (faux positifs : ×1.3 à ×2.6 ; manquées : ×0.65 à ×0.94) |
| Heishinator : source × périodes | 111 | `EMA(ohlc4,4) > EMA(ohlc4,32)` **optimum isolé**, voisins à +14 erreurs minimum. Ancienne formule SHA : 143/16/12 |
| Décalages d'une barre (ADX[1], dBand[1], SMA20[1]…) | — | tous neutres ou pires, jusqu'à 145/10/10 |
| Définition de la bande dans `dBand` (milieu, EMA60 seule) | 221 | semble gagner 1 sur le groupe 4, **mais échoue en validation croisée et sur l'API**. Assouplissements monotones : déplacement sur la courbe rappel/précision, pas une meilleure règle |
| Conviction **continue** `dBand + k·vol` | 510 | au mieux 154/12/1 = 13 erreurs contre 8. **Le OU booléen bat toute combinaison linéaire** |

## La leçon de méthode

Sur les 8 cas limites pris isolément, une conviction continue `dBand + 1.5·vol_ratio >= seuil`
les sépare **tous les huit**. Sur les 155 flèches, elle donne 13 erreurs contre 8. C'est la
démonstration en direct du surapprentissage : une règle qui explique parfaitement les cas
difficiles et se révèle pire sur l'ensemble.
