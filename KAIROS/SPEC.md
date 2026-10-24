# Strat-Botting — spécification (16/10/2026)

## Objectif
Trouver, parmi toutes les confluences de `CompletV3.pine`, **la recette d'entrée + stop + objectif la plus
convaincante pour un bot de futures en propfirm** (Apex 50k, Tradeify 50k ou Lucid 50k), sur MNQ1! et/ou
MES1!. Livrable final : `STRATEGIE_V7` (Pine, prête pour des alertes webhook) avec un préréglage
« Recette finale », ou un verdict honnête « rien de robuste » si aucune recette ne passe les critères.

Échéance visée : vendredi 23/10/2026.

## Ce qu'on sait déjà (ne pas refaire)
Voir `MEMOIRE_PROJET.md` §15 et `tools/strategie/` :
- Sur ~2 mois de données Python : aucune entrée robuste (corrélations, modèle multivarié, confluence).
- Testeur TradingView, 3 ans 15m : préréglage A (climax BUY + TREND 1H, stop 2 ATR, sortie Heishinator)
  NQ +0,16 R, PF 1,18, non distinguable de la dérive haussière ; ES non significatif.
- Les niveaux (pivots, Detector, sessions, Monday, ronds) ne retiennent pas le prix mieux qu'un placebo.
- Coûts : MES non tradable sous 15m ; Signator perd en séance de Londres.
- **Le verrou est la quantité de données, pas les idées.**

## Décisions
| Sujet | Décision |
|---|---|
| Propfirm | Indifférente : on évalue contre Apex 50k, Tradeify 50k, Lucid 50k et on recommande la plus compatible |
| Exécution | Non décidée : on livre une stratégie Pine pilotable par alertes webhook (voie la plus simple) |
| TradingView | Ultimate (export d'environ 40 000 bougies — à confirmer à l'export) |
| Marchés / UT | Au choix de l'équipe : MNQ1! et MES1!, signal 15m possible avec entrée affinée en 2m |

## Architecture
1. **`dataset/DATASET.pine`** — indicateur d'export, dérivé de `STRATEGIE_V1.pine` (modules déjà copiés
   de CompletV3, sans dessin) : chaque confluence en colonne (booléens empaquetés par bits si besoin, limite
   64 plots), plus les **vrais prix** OHLC (`ticker.new(..., backadjustment.inherit)`) et l'ATR des vrais
   prix. Graphique HA. Aucune donnée future (multi-UT en bougie clôturée). Contrôlé contre les exports
   existants de CompletV3 avant usage.
2. **`moteur/`** — moteur de backtest Python unique, partagé par tous les agents : signal à la clôture,
   entrée à l'ouverture vraie suivante, SL/TP sur vrais hauts/bas, si une bougie touche SL et TP → SL
   (prudent), commissions + 1 tick de glissement par côté, sortie forcée avant la clôture propfirm.
   Sortie : liste de trades (horodatage, sens, entrée, SL, TP, sortie, R, $, MAE, MFE).
3. **`propfirm/`** — règles actuelles des 3 propfirms (`regles.toml`) + simulateur Monte-Carlo : à partir
   d'une liste de trades → probabilité de réussir l'éval, délai médian, probabilité de survie jusqu'au
   1er payout, comparée à une référence « entrées au hasard, même gestion ».
4. **`recherche/<famille>/`** — un dossier par agent de recherche.
5. **`registre/registre_tests.csv`** — UNE ligne par test, écrite par chaque agent. Publié en page
   « Registre des tests ».
6. **`execution/`** — voie bot recommandée (webhook → Tradovate/Rithmic) et format des alertes.
7. **`livrables/`** — STRATEGIE_V7, rapport final.

## Protocole anti-surapprentissage (obligatoire pour tous les agents)
- Découpage chronologique : **75 % développement / 25 % les plus récents SOUS SCELLÉ**. Personne ne lit
  le scellé avant la vague 2 ; seul l'avocat du diable l'ouvre, une fois, pour les finalistes.
- Dans le développement : walk-forward, zone stable plutôt que maximum isolé, nombre de variantes testées
  déclaré dans le registre (correction Deflated Sharpe / White).
- Toute recette est comparée à des entrées au hasard avec la même gestion (référence).
- Coûts réalistes, exécution à l'ouverture suivante, aucune donnée future.

## Critère « probant » (fixé à l'avance)
Une recette est retenue seulement si :
1. ≥ 200 trades, PF ≥ 1,3 après coûts ;
2. positive sur le scellé ET sur 3 ans au testeur TradingView ;
3. tient sur MNQ et MES, ou au moins sur chaque moitié de la période ;
4. probabilité de réussite propfirm nettement supérieure à la référence au hasard.
Sinon le verdict est « non concluant » — dit clairement.

## Équipe et vagues
**Vague 0 (immédiate)** : inventaire des confluences + DATASET.pine · règles propfirms (dont autorisation
des bots) · simulateur propfirm (testé sur les trades « 1er jet », 3 ans) · moteur de backtest ·
exécution du bot.

**Vague 1 (dès réception du DATASET)** : Tendance (Signator, Heishinator, TREND multi-UT, Feu) ·
Retournement (Climax, Detector, ronds) · Cassure (trendlines, ORB, sessions, Monday) · SL/TP/gestion
optimisée propfirm (niveaux de protection vs ATR, partiels, break-even, suiveur) · Timing/régime ·
Entrée 15m → 2m · Contrôle machine learning (étalon).

**Vague 2** : Avocat du diable (audit + ouverture du scellé) · Intégrateur (STRATEGIE_V7, alertes,
linter + check_syntax) · confirmation au testeur 3 ans par Jeremy, concordance Python/testeur.

## Ce que fait Jeremy
1. Exporter le DATASET (6 exports : MNQ/MES × 15m/5m/2m, historique maximal) selon `dataset/EXPORT.md`.
2. En fin de parcours : testeur 3 ans sur la recette finale + export de la liste des trades.

## Règles du dépôt
Commit + push après chaque étape. Jamais de `.DS_Store`. Aucune mention du nom de l'indicateur d'origine
dans les fichiers Pine de ce dossier (dire « l'original »). Pine vérifié par `check_syntax` avant livraison.
