# Hypothèses — Relevé complet (écrites AVANT d'être testées)

Protocole commun : construction 2019-2022, contrôle 2023-2024, scellé 2025-2026 fermé. Moteur
`complet/moteur.py` (règles Strat5669, 2 contrats, 1,25 $ par côté, 1 tick de glissement, stop d'abord).
Hasard au même nombre de trades, mêmes heures (référence A : sens au hasard, même part de longs).
Chaque test va au registre avec le nombre d'essais cumulé ; correction de Bonferroni par famille.
Une hypothèse est retenue seulement si p < seuil corrigé en construction ET en contrôle.

**Critère ajouté le 19/11 (après le rejet de M1, décision DAEMON), pour tout ce qui suit :** P&L net
positif (coûts compris) en construction ET en contrôle, en plus de battre le hasard (réf. A) et la
référence « long seulement » (réf. L, dérive haussière) avec correction des tests multiples.

## C1 — Témoin « tout ou rien » (écrit le 19/11, avant le test)
- Cible : résultat en R (P&L par contrat, coûts compris, divisé par le risque 2 ATR × valeur du point)
  d'un trade décidé à la clôture de chaque bougie, dans chaque sens, géométrie FIXE : stop 2 ATR,
  objectif 1 R, sortie au temps 16 bougies, sorties `fin` comprises.
- Variables : les 25 champs numériques de la fiche (sauf dt et les prix bruts), les 35 bits, plus
  quelques dérivés sans prix bruts : (h − l) / ATR, (c − o) / ATR, rendements sur 4 et 16 bougies / ATR,
  heure de Paris, jour de la semaine.
- Modèle : gradient boosting (HistGradientBoostingRegressor, 300 itérations max, taux 0,05, 31 feuilles,
  200 exemples par feuille minimum, arrêt précoce sur les 20 % les plus récents de 2019-2022).
  Un modèle par instrument et par sens.
- Mesures sur 2023-2024 : corrélation de rang (Spearman) prédiction / résultat ; R moyen par décile
  de prédiction.
- Stratégie témoin : entrer quand la prédiction dépasse son 98e centile mesuré sur la tranche
  d'arrêt précoce (sens à la plus forte prédiction si les deux passent), une position à la fois.
  2 tests (MNQ, MES) : seuil corrigé 0,025.
- Lecture : si le témoin ne trouve aucun avantage hors échantillon, les familles faites à la main
  ont peu de chances (elles utilisent les mêmes champs).

**Résultat C1 (19/11)** : aucun avantage hors échantillon (contrôle MNQ p = 0,056, MES p = 0,47 ;
corrélations de rang expliquées par le coût fixe en R). Voir registre C1-01, C1-02.

## Familles faites à la main (écrites le 19/11, avant le test)
Signal décidé à la clôture de la bougie i (champs de la fiche i), entrée à l'ouverture suivante.
Long et short en miroir ; si les deux sont vrais sur la même bougie, pas de trade. Pas d'entrée sur une
bougie `fin` (moteur). 2 000 tirages au hasard (réf. A). Moins de 30 trades en construction = non testé.
Seuil = 0,05 / nombre de tests de la famille ; le contrôle utilise 0,05 / nombre d'hypothèses retenues.

### F1 Tendance — géométrie fixe : stop 2 ATR, objectif 1,5 R, 16 bougies — 3 × 2 instruments = 6 tests (seuil 0,0083)
- T1 : TREND 1 h et 4 h haussiers (bits tr1h, tr4h) ET Dashator 1 h / 4 h terminés haussiers (k1 > 0, k4 > 0)
  ET flip Heishinator haussier (hei_L) : fin de repli dans la tendance.
- T2 : T1 ET TREND 15 min haussier ET Directionnor 4 h long (dirH = 1).
- T3 : T1 ET 0 ≤ e1 ≤ 1 (clôture HA au-dessus de l'EMA 50, à 1 ATR au plus : repli près de la moyenne).

### F2 Retour à la moyenne — géométrie fixe : stop 1,5 ATR, objectif 1 R, 8 bougies — 5 × 2 = 10 tests (seuil 0,005)
- M1 : climax d'achat sur la bougie (clx_L) → long ; climax de vente → short.
- M2 : divergence (div_L / div_S).
- M3 : pW ≤ −2 (close à 2 ATR ou plus sous le pivot weekly) ET hei_L → long ; pW ≥ 2 ET hei_S → short.
- M4 : Fibonacci. Swing haussier (fib_bas = 0) ET 0,5 ≤ fib ≤ 0,786 (repli de 50 à 78,6 %) ET hei_L
  → long ; swing baissier (fib_bas = 1) ET 0,5 ≤ fib ≤ 0,786 ET hei_S → short.
- M5 : zone Detector proche : detD ≤ 0,5 ATR ET hei_L → long ; detU ≤ 0,5 ATR ET hei_S → short.

### F3 Cassure — géométrie fixe : stop 2 ATR, objectif 1,5 R, 16 bougies — 3 × 2 = 6 tests (seuil 0,0083)
- B1 : cassure de trendline (tl_L / tl_S).
- B2 : cassure de niveau de séance ou Monday (lvl_L / lvl_S).
- B3 : (B1 ou B2) ET Feu ≥ 60 ET STRENGTH ≥ 60 → long ; (B1 ou B2 baissiers) ET Feu ≤ 40 ET STRENGTH ≤ 40 → short.

### F4 Filtre de régime — sur chacune des 11 hypothèses, géométrie de sa famille — 11 × 2 × 2 = 44 tests (seuil 0,00114)
- R1 : vr ≥ 1,2 (volatilité au-dessus de sa moyenne 96 bougies).
- R2 : ADX ≥ 25.

**Résultat F1-F4 (19/11)** : 65 tests sur 66 ne passent pas la construction. MNQ M1 (climax) passe le
critère d'alors (construction p = 0,0035, contrôle p = 0,0495) mais perd de l'argent dans les deux
périodes (−3 314 $, −1 465 $) et ne bat pas « long seulement » en contrôle (p = 0,084) : REJETÉ,
scellé fermé. C'est ce cas qui a fait ajouter le critère de P&L positif.
