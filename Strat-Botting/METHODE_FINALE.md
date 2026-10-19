# Méthode finale — préréglage 48 (19/10/2026)

## La méthode
- Code : `STRATEGIE_45_46.pine`, **Modèle 48** (par défaut). Recette identique dans `STRATEGIE_V1.pine`, préréglage 48.
- Marché : **MNQ1!**, **15 min**, bougies **Heikin Ashi**. Pas MES, pas BTC.
- Entrée : n'importe quel signal (flèche Signator Fort ou Moyen, flip Heishinator, cassure de trendline,
  cassure de session / Monday, climax, divergence) **seulement si** le Dashator 1 h **et** 4 h (dernière
  bougie clôturée) vont dans le sens du trade **et** si la clôture HA est à **0,6 ATR au plus** de l'EMA50
  dans le sens du trade (on achète un repli, pas une envolée).
- Sortie : **stop 3 ATR**, **objectif 2 ATR**, sinon **sortie au marché après 8 bougies (2 h)**.
- Horaires : entrées de **00:20 à 22:15 Paris** ; à plat à 22:15 (et 15:59 Chicago).
- Compte : **Tradeify Select 50k, payouts Flex** (pas de perte journalière max). **2 micros fixes.**

## Différences avec le 45
Une seule : le stop passe de 2 ATR à 3 ATR, l'objectif reste à 2 ATR de l'entrée (mêmes trades, mêmes heures).

| MNQ1! 15 min, 25/10/2023 → 16/10/2026, 2 micros | 45 | **48** |
|---|---|---|
| Trades | 656 | 651 |
| Gagnants | 75,5 % | **78,5 %** |
| Profit factor | 4,51 | **5,54** |
| Net | +78 439 $ | **+84 437 $** |
| Baisse max | 1 162 $ | 1 157 $ |
| Stops touchés | 66 | **22** (≈ 330 $ chacun) |
| Gagnants par année | 77 / 77 / 73 % | **80 / 80 / 75 %** |
| Tradeify Select, P(réussite) 2 / 3 micros | 99,8 / 98,6 % | **100 / 99,0 %** |

Avocat du diable (recherche/avocat48) : 48 > 45 significatif (+6 094 $, p < 0,0002, régulier par année
et par sens). Attendre en réel ≈ 72 % de gagnants et PF 3,5-4,5 (depuis juillet 2026 : 66 % / PF 2,8).

## Pourquoi pas les autres
- **49** (stop 3 / objectif 3 ATR, RR 1) : plus de profit (+87,9 k$) mais 75,4 % de gagnants ; moins sûr à 4 micros.
- **50** (stop 3,5 ATR) : à peine mieux que le 48, non significatif, stop plus coûteux, dernière année moins bonne.
- **Famille 46** (≈ 44 trades/mois) : meilleur = **52** (46 + stop 3 ATR) : 69,7 % / PF 2,79 / +139 k$, mais
  **baisse max 2 748 $ en 2 micros (> drawdown Tradeify 2 000 $)**, pire jour −1 243 $, dernier trimestre
  62 % / PF 1,80 → 1 micro seulement sur un 50k. Option « volume » pour plus tard, pas pour le test.

## Garde-fous (arrêter et réexaminer)
- ≤ 18 gagnants sur 30 trades, ≤ 32 sur 50, ≤ 69 sur 100.
- Perte du jour ≥ 700 $ ; 4 perdants d'affilée ; baisse > 1 200 $ depuis le plus haut.
- Glissement moyen > 8 ticks ; > 20 % d'alertes ratées.

## Règles d'exécution
1. Entrer dès l'alerte. En retard : n'entrer que si le prix est encore à moins d'¼ de la distance du stop
   du prix de l'alerte ; sinon laisser passer.
2. Stop et objectif aux **prix exacts** de l'alerte. Ne jamais déplacer le stop.
3. Fermer à l'heure limite de l'alerte (8 bougies), même près de l'objectif.
4. Prendre **toutes** les alertes (pas de tri à l'instinct).
5. Journal : date, sens, prix alerte, prix d'entrée, sortie, raison — envoyé tous les 10 trades.

## Plan
1. 30 trades en simulation (≈ 7 semaines), 2 micros.
2. Si les garde-fous tiennent : évaluation Tradeify Select 50k Flex, 2 micros fixes.
