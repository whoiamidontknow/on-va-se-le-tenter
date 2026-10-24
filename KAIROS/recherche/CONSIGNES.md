# Consignes communes — vague 1 « réglage ultime »

Objectif fixé par Jeremy : trouver **le réglage ultime** sur Tradeify, avec TOUT ce que CompletV3 met à
disposition (tous les modules, toutes les confluences, toutes les unités de temps). Ce réglage peut **varier
selon la situation** du marché : il n'y a pas d'obligation d'avoir une recette unique.

## Cible propfirm
- Variante principale : `tradeify_50k_select_flex` (`propfirm/regles.toml`). Secondaire : `tradeify_50k_growth`.
- **Intrajournée obligatoire** : le moteur ferme tout à 15:59 heure de Chicago (`heure_sortie`, défaut). Ne
  jamais le désactiver : garder une position la nuit est interdit chez Tradeify.
- Note d'une recette = sortie de `propfirm/simulateur.py` (`monte_carlo`, `optimise_taille`) sur ses trades :
  P(réussite de l'éval), P(1er payout), valeur espérée par tentative ; **comparée à la référence au hasard**
  (`moteur.reference_hasard` avec la même gestion, puis le même simulateur).

## Outils communs (ne pas les modifier ; signaler un bug au coordinateur dans le rapport)
- Moteur : `KAIROS/moteur/` (lire README.md). `backtest`, `metriques`, `reference_hasard`,
  `decoupage`, `walk_forward`, `registre.ajouter_test`.
- Simulateur propfirm : `KAIROS/propfirm/simulateur.py`.
- Python : `~/venv-quant/bin/python` (numpy, pandas, scipy, statsmodels, scikit-learn). N'installe rien.

## Données
- **Maintenant** : les séries déjà calculées de `tools/strategie/cache_series.pkl` (tous les modules de
  CompletV3 recalculés en Python sur les exports HA + vrais prix reconstitués ; ≈ 21/08 → 15/10/2026, MES et
  NQ, 1 min → 1D ; MES1 avr.-juil. en 15m). Voir `moteur/verif_concordance.py` (`charger`, `vers_df`) et
  `tools/strategie/features.py` pour le contenu.
- **Bientôt** : les exports `DATASET.pine` (≈ 1,7 an en 15m), lus par `dataset/charger.py` (colonnes décrites
  dans `dataset/INVENTAIRE.md`). **Isole tout l'accès aux données dans UNE fonction** de ton code, pour que
  le passage au DATASET soit un changement d'une ligne, puis tout relancer.
- Avec 2 mois de données, tout résultat est fragile : c'est normal. Le but immédiat est d'avoir une machine de
  recherche complète, correcte et déjà classée, prête à tourner sur le gros historique.

## Protocole anti-surapprentissage (obligatoire)
- Les 25 % les plus récents sont SOUS SCELLÉ : n'utilise que `moteur.charger_recherche` / `decoupage` sans
  `ouvrir_scelle`. Seul l'avocat du diable ouvrira le scellé.
- Walk-forward dans le développement ; préférer une zone stable de réglages à un maximum isolé.
- Déclarer honnêtement le nombre de variantes essayées (`n_variantes_testees`) ; correction du biais de
  sélection (Deflated Sharpe ou bootstrap de White) pour tout « gagnant ».
- Exécution à l'ouverture suivante, coûts réalistes, aucune donnée future (attention aux colonnes multi-UT et
  aux pivots).

## Registre et livrables
- Chaque test notable → `registre.ajouter_test({...})` avec ton préfixe d'agent, `echantillon` =
  `"dev_cache"` (ou `"dev_dataset"` plus tard), `p_tradeify` = P(réussite) Select Flex, `p_ref_hasard`,
  verdict court et clair. Une ligne par recette retenue, pas une par variante du balayage (le balayage complet
  va dans un CSV de ton dossier).
- Dans ton dossier `recherche/<nom>/` : ton code, `RESULTATS.md` (classement, ce qui marche, ce qui ne marche
  pas, limites), et pour tes 3 meilleures recettes la liste des trades (entrée, SL, TP, sortie, niveau utilisé)
  écrite par `ajouter_test`.
- Pas de commit git (le coordinateur commite). N'écris que dans ton dossier et dans le registre.
- Écris en français, phrases simples. Rapport final < 300 mots.
