# Méthode finale — préréglage 69 (20/10/2026)

> 20/10 : la méthode devient le **69** = le 56 + Dashator 1 h / 4 h compté seulement si le corps de sa bougie
> HA ≥ **0,025** × ATR de son unité. C'est le plus petit seuil qui supprime le « trade fantôme » du 20/10 05:00
> (alerte en direct, trade absent de l'historique : Dashator 4 h quasi neutre ; testé en replay par Jeremy :
> présent à 0,01 et 0,02, absent à 0,025). 3 ans : 546 trades (~15/mois), 84,6 % gagnants, PF 7,05,
> +91 411 $, baisse max 783 $. Code : **`STRATEGIE_69.pine`**. Règles et garde-fous ci-dessous inchangés.

## La méthode
- Code : **`STRATEGIE_69.pine`** (« Stratégie 69 (alertes) »). Recette identique dans `STRATEGIE_V1.pine`,
  préréglage 69 (= 56 + Dashator corps ≥ 0,025 ATR).
- Marché : **MNQ1!**, **15 min**, bougies **Heikin Ashi**. Pas MES, pas BTC.
- Entrée : n'importe quel signal (flèche Signator Fort ou Moyen, flip Heishinator, cassure de trendline,
  cassure de session / Monday, climax, divergence) **seulement si** le Dashator 1 h **et** 4 h (dernière
  bougie clôturée) vont dans le sens du trade **et** si la clôture HA est à **0,6 ATR au plus** de l'EMA50
  dans le sens du trade (on achète un repli, pas une envolée).
- Sortie : **stop 3 ATR**, **objectif 2 ATR**, sinon **sortie au marché après 16 bougies (4 h)**.
- Horaires : entrées de **00:20 à 22:15 Paris** ; à plat à 22:15 (et 15:59 Chicago).
- Compte : **Tradeify Select 50k, payouts Flex** (pas de perte journalière max). **2 micros fixes.**

## Comment on y est arrivé (MNQ1! 15 min, 25/10/2023 → 16/10/2026, 2 micros)
| | 45 | 48 | **56** |
|---|---|---|---|
| Stop / objectif / sortie au temps | 2 / 2 ATR / 2 h | 3 / 2 ATR / 2 h | **3 / 2 ATR / 4 h** |
| Trades | 656 | 651 | 628 |
| Gagnants | 75,5 % | 78,5 % | **83,4 %** |
| Profit factor | 4,51 | 5,54 | **6,61** |
| Net | +78 439 $ | +84 437 $ | **+99 931 $** |
| Baisse max | 1 162 $ | 1 157 $ | **783 $** |
| Pire journée | −749 $ | −932 $ | −783 $ |
| Trimestres positifs | 13/13 | 13/13 | 13/13 (pire +2 307 $) |
| Depuis juillet 2026 | 64 % / PF 2,4 | 66 % / PF 2,8 | **80 % / PF 5,2** |
| Tradeify Select, P(réussite) 2 / 3 / 4 micros | 99,8 / 98,6 / 95,7 % | 100 / 99,0 / 96,5 % | **100 / 99,9 / 99,0 %** |
| Jours pour valider l'éval (2 / 3 micros) | 33 / 23 | 30 / 22 | **26 / 18** |

- 45 → 48 : 53 % des stops du 45 étaient suivis de l'objectif dans les 2 h ; stop élargi à 3 ATR (avocat du
  diable : +6 094 $, p < 0,0002, régulier par année et par sens).
- 48 → 56 : la sortie au temps passe de 8 à 16 bougies ; mieux chaque année ; supprimer la sortie au temps
  (57) dégrade (PF 4,54, baisse max 1 617 $).
- Écartés : 49 (RR 1, moins sûr à 4 micros), 50 (stop 3,5 ATR, non significatif), famille 46 / 52 (baisse
  max 2 748 $ en 2 micros > drawdown Tradeify).
- Réserve : stop et sortie choisis sur ces 3 ans → attendre en réel ≈ 75-80 % de gagnants et PF 4-5.

## Garde-fous (arrêter et réexaminer)
- ≤ 20 gagnants sur 30 trades, ≤ 35 sur 50, ≤ 72 sur 100.
- Perte du jour ≥ 700 $ ; 4 perdants d'affilée ; baisse > 1 000 $ depuis le plus haut.
- Glissement moyen > 8 ticks ; > 20 % d'alertes ratées.

## Règles d'exécution
1. Entrer dès l'alerte. En retard : n'entrer que si le prix est encore à moins d'¼ de la distance du stop
   du prix de l'alerte ; sinon laisser passer.
2. Stop et objectif aux **prix exacts** de l'alerte. Ne jamais déplacer le stop.
3. Fermer à l'heure limite de l'alerte (16 bougies = 4 h), même près de l'objectif.
4. Prendre **toutes** les alertes (pas de tri à l'instinct). Une seule alerte active : « Stratégie 56 ».
5. Journal : date, sens, prix alerte, prix d'entrée, sortie, raison — envoyé tous les 10 trades.
6. On ne change plus rien pendant au moins 30 trades.

## Plan
Évaluation Tradeify Select 50k Flex en cours (solde 49 900 $ après un 1er trade en 45, seuil 48 000 $),
2 micros fixes ; 3 micros seulement après 30 trades conformes et un solde > 51 000 $.
