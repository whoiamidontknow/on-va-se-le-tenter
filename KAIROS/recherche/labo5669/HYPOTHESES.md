# Hypothèses — Relevé complet (écrites AVANT d'être testées)

Protocole commun : construction 2019-2022, contrôle 2023-2024, scellé 2025-2026 fermé. Moteur
`complet/moteur.py` (règles Strat5669, 2 contrats, 1,25 $ par côté, 1 tick de glissement, stop d'abord).
Hasard au même nombre de trades, mêmes heures (référence A : sens au hasard, même part de longs).
Chaque test va au registre avec le nombre d'essais cumulé ; correction de Bonferroni par famille.
Une hypothèse est retenue seulement si p < seuil corrigé en construction ET en contrôle.

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
