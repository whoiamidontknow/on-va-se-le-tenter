# K.A.I.R.O.S

**K**ernel (le noyau, le cœur du système) · **A**pprentissage · **I**ntuition · **R**ésilience · **O**rientation ·
**S**ymbiose. En grec, *kairos* : le moment opportun, l'instant décisif qu'il faut saisir — savoir quand frapper.
(Ancien nom du projet : Strat-Botting, renommé le 24/10/2026. Données : `~/ERGON/KAIROS-data`.)

Recherche systématique d'une stratégie de trading automatisée sur futures (MNQ / MES), construite à partir
des confluences de l'indicateur maison `CompletV3.pine`, et calibrée pour les règles des propfirms
(Apex, Tradeify, Lucid — comptes 50k).

## Méthode
- **Données** : un indicateur d'export (`dataset/DATASET.pine`) sort toutes les confluences + les vrais
  prix sur l'historique TradingView le plus long possible.
- **Une équipe d'agents spécialisés**, chacun sur une famille de recettes (tendance, retournement,
  cassure, gestion SL/TP, timing, entrée multi-UT, contrôle machine learning), avec un même moteur de
  backtest et un même protocole.
- **Anti-surapprentissage** : 25 % des données les plus récentes sous scellé, walk-forward, référence
  « entrées au hasard », correction du biais de sélection, confirmation sur 3 ans au testeur TradingView.
- **Objectif propfirm, pas gain brut** : chaque recette est notée par sa probabilité de réussir l'éval et
  de survivre jusqu'au payout (Monte-Carlo sur les règles réelles de chaque propfirm).

## Organisation
| Dossier | Contenu |
|---|---|
| `dataset/` | Indicateur d'export et procédure |
| `moteur/` | Moteur de backtest commun |
| `propfirm/` | Règles des propfirms et simulateur Monte-Carlo |
| `recherche/` | Un dossier par agent de recherche |
| `registre/` | `registre_tests.csv` : tous les tests, un par ligne |
| `execution/` | Voie d'exécution du bot (alertes webhook) |
| `livrables/` | Stratégie finale et rapport |

Spécification complète : [`SPEC.md`](SPEC.md).

## État
- 16/10/2026 — vague 0 terminée :
  - moteur de backtest commun (23 tests, 374/374 trades identiques à l'ancien moteur) ;
  - simulateur Monte-Carlo propfirm (22 tests), règles de 17 comptes 50k ;
  - **Apex exclue** (automatisation interdite) ; propfirm recommandée : **Tradeify Select → Flex** ;
  - voie bot : TradingView → PickMyTrade → Tradovate ;
  - préréglage A (3 ans) : pas mieux que le hasard, et ses gains dépendent de trades gardés la nuit
    (interdit en propfirm) → toute la suite est testée **en intrajournée forcée** ;
  - `DATASET.pine` prêt (compile sans erreur) — en attente des exports.
