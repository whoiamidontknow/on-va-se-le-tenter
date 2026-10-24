# Consignes communes — vague « taux de réussite » (17/10/2026)

Demande de Jeremy : des **préréglages où 60 à 75 % des trades sont gagnants**, en confluence avec les
indicateurs de CompletV3, et compatibles avec les règles de la propfirm. Lis aussi `recherche/CONSIGNES.md` :
toutes ses règles s'appliquent (intrajournée 15:59 Chicago, scellé de 25 %, registre, outils communs, Python
`~/venv-quant/bin/python`, pas de commit, n'écrire que dans ton dossier et le registre).

## Le piège à éviter absolument
Le taux de réussite dépend surtout de la **géométrie** stop / objectif, pas de l'entrée. Avec un objectif à
k × le risque, des entrées AU HASARD gagnent environ 1 / (1 + k) des trades, moins les coûts :
objectif 0,5R → ≈ 66 % de gagnants au hasard, et une stratégie qui perd. Un taux de 70 % ne prouve donc rien.

## Critère de réussite (les QUATRE à la fois)
1. **Taux de gagnants entre 60 et 75 %** hors échantillon (walk-forward), sur au moins 60 trades.
2. **Espérance positive après coûts** (R moyen > 0, profit factor > 1).
3. **Taux de gagnants nettement au-dessus du placebo** : mêmes stop, objectif, gestion, séances et nombre de
   trades, mais entrées au hasard (`moteur.reference_hasard`). Rapporte toujours les deux taux et l'écart en
   points, avec sa p-valeur (≥ 500 tirages).
4. **Propfirm** : `propfirm/simulateur.py` sur `tradeify_50k_select_flex` → P(réussite de l'éval),
   P(1er payout), valeur espérée, comparées à la référence au hasard ; respect de la règle de constance et du
   drawdown de 2 000 $ EOD (taille en micros via `optimise_taille`).
Correction du biais de sélection (bootstrap de White ou Deflated Sharpe) sur l'ensemble de ton balayage, et
`n_variantes_testees` honnête dans le registre. Si rien ne passe, **dis-le clairement** : c'est un résultat.

## Ce qu'on sait déjà (registre, à ne pas refaire)
- Aucune confluence seule n'a d'avantage net prouvé sur 2-4 mois ; le méta-modèle ML ne bat pas le hasard
  (AUC 0,48-0,55). Seul le bloc heure / séance porte de l'information (`recherche/meta_ml/RESULTATS.md`).
- Hypothèse FIXÉE À L'AVANCE à tester (pas à réoptimiser) : la nuit, 0 h-8 h heure de Paris, est meilleure.
- Stops sur niveau « le plus proche » : mauvais ; stop 2-3 ATR et sortie Heishinator meilleurs
  (`recherche/sorties/RESULTATS.md`).

## Données
Mêmes données que la vague 1 (cache ≈ 21/08 → 15/10 MES/NQ, MES1 avr.-juil.), DATASET pas encore exporté.
Accès aux données isolé dans UNE fonction, code relançable tel quel sur le DATASET.

## Livrable spécifique : des préréglages prêts pour TradingView
Pour tes (au plus) 3 meilleures recettes, écris dans `RESULTATS.md` :
- la recette en une phrase, ses chiffres (taux, taux placebo, écart, R moyen, PF, n, P(réussite) Tradeify) ;
- **la ligne de préréglage** pour `f_pr_def()` de `STRATEGIE_V1.pine` (format « clé=valeur;… », clés décrites
  en commentaire au-dessus de `f_pr_def`, ≈ lignes 290-320 ; s'inspirer des préréglages 20-24). Si la recette
  exige une option qui n'existe pas dans la stratégie Pine, décris-la précisément (pour que le coordinateur
  l'ajoute) au lieu de l'approcher en silence.
Ne modifie PAS `STRATEGIE_V1.pine` toi-même. Rapport final < 300 mots, en français, phrases simples.

## Usage
Un hook met tout en pause à 85 % d'utilisation du forfait. Travaille par étapes qui écrivent leurs résultats
sur disque (CSV, RESULTATS.md provisoire) pour qu'une reprise ne recommence pas de zéro.
