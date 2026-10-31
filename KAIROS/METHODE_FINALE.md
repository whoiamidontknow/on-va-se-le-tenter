# Méthode en test — Strat5669 (20/10/2026, périmètre mis à jour le 30/10)

> **Décision de Jeremy (20/10)** : on trade **tous les trades du 56** avec **`Strat5669.pine`**, qui marque chaque
> trade **GODLIKE** (règle du 69 respectée : corps HA du Dashator 1 h ET 4 h ≥ 0,025 × ATR de son unité) ou
> **« 56 seul »** (Dashator quasi neutre, trade fragile qui peut devenir « fantôme »). On ne change plus rien
> pendant 30 trades ; bilan : nombre et résultats (objectif / stop / temps) des GODLIKE contre les « 56 seul »,
> et réussite ou non de l'éval Tradeify. 3 ans : 56 = 630 trades, 83,5 %, PF 6,64, +100 558 $ ; dont GODLIKE
> = 546 trades, 84,6 %, PF 7,05, +91 411 $. (Ci-dessous : la recette, inchangée, et les règles.)

## La méthode
- Code : **`Strat5669.pine`** (« Strat5669 (alertes) »). Recette identique dans `STRATEGIE_V1.pine`,
  préréglage 56 ; marque GODLIKE = règle du préréglage 69.
- Marchés : **MNQ1!**, **MES1!** et **BTC CME**, **15 min**, bougies **Heikin Ashi**.
  *(La ligne disait « MNQ1! seul, pas MES, pas BTC ». Elle datait du 20/10 et n'avait pas suivi
  la décision du 24/10 — voir « Périmètre » ci-dessous.)*
- Entrée : n'importe quel signal (flèche Signator Fort ou Moyen, flip Heishinator, cassure de trendline,
  cassure de session / Monday, climax, divergence) **seulement si** le Dashator 1 h **et** 4 h (dernière
  bougie clôturée) vont dans le sens du trade **et** si la clôture HA est à **0,6 ATR au plus** de l'EMA50
  dans le sens du trade (on achète un repli, pas une envolée).
- Sortie : **stop 3 ATR**, **objectif 2 ATR**, sinon **sortie au marché après 16 bougies (4 h)**.
- Horaires : entrées de **00:20 à 22:15 Paris** ; à plat à 22:15 (et 15:59 Chicago).
- Comptes : **MNQ et MES** sur **Tradeify Select 50k, payouts Flex** (pas de perte journalière max)
  et sur un **challenge FTMO 100k** ; **BTC CME** sur **fonds propres**.

## Dimensionnement — décidé le 31/10

**450 $ de risque par DIRECTION, pas par instrument.** Le nombre de contrats flotte avec
l'ATR, puisque le stop est à 3 ATR : on vise un montant, pas une taille fixe.

| Situation | Quoi faire |
|---|---|
| Un seul signal | **450 $** dessus |
| MNQ et MES, **même sens** | **MNQ seul à 450 $** — ne pas doubler |
| MNQ et MES, sens opposés | 450 $ chacun (jamais observé à ce jour) |

**Pourquoi pas 450 $ chacun.** MES et MNQ sont corrélés à ~0,9, et la recette exige que le
Dashator 1 h et 4 h aillent dans le sens du trade — or le Dashator lit la direction du
marché, pas celle d'un contrat. Les deux partent donc presque toujours ensemble et dans le
même sens : 3 jours sur 5 depuis le 20/10, dont le 28/10 à 18:45 à la même minute.

Ce doublon a coûté deux fois : **900 $ d'exposition réelle** (45 % de la marge en une
barre), et la plus grosse journée du compte — celle qui porte la consistance à 81,73 %.
À MNQ seul, cette journée aurait pesé 42 % au lieu de 81,73 %.

**Le seuil de sécurité est entre 500 et 550 $**, pas entre 400 et 500 : à 550 $ on passe
de 5 pertes fatales à 4, et le risque de ruine quadruple. Calculé sur le taux de perte
**réel en direct (25 %)**, pas celui du backtest (17 %).

**Réserve** : ces calculs reposent sur 16 trades. Si le taux de perte réel se dégrade vers
35 %, 450 $ redevient trop.

## Le plafond qui peut bloquer l'éval

**Aucune journée ne doit dépasser 1 200 $** — la règle de consistance Tradeify impose
qu'aucun jour ne pèse plus de 40 % du profit net, et l'objectif est de 3 000 $.

Elle ne se corrige pas après coup. Point hebdomadaire : `propfirm/point_tradeify.py`.

## Périmètre — ce qui a réellement été décidé, et quand

Reconstitué à partir des transcriptions de session, pas de mémoire.

| Date | Décision, mot pour mot |
|---|---|
| **20/10 08:51** | « on reste comme ça et on voit ce que ça donne au bout de 30 trades si le compte passe ou pas » |
| **24/10 14:35** | « le btc c'est du fond propre, donc je prendrais les trades mes et mnq sur tradeify et un de mes ftmo 100k challenge » |
| **27/10 09:00** | « okay je retire btc index alors » |
| **29/10 20:55** | « faire btc avec mes fonds propres en cryptos pour voir ce que ça donne (je risque que dalle sur ça) » |
| **30/10** | « je pars du principe que maintenant je traite en BTC CME » |

**Le test porte sur 30 trades PAR INDICE**, pas 30 au total.

**Ce que ces 30 trades testent** : la fiabilité en direct et la validation du compte.
**Pas** GODLIKE contre « 56 seul » — mesuré, 30 trades ne peuvent pas séparer 84,6 % de
76,2 %, il en faudrait plusieurs centaines par groupe. Le verdict utile est binaire :
le compte passe ou non.

**BTC : le compteur repart de zéro.** Les 9 trades du 18 au 27 octobre sont tous sur
`INDEX:BTCUSD`, l'index retiré le 27/10. Ils restent dans l'historique mais ne comptent
pas pour les 30 — ils mesuraient un instrument qu'on ne trade plus.

**Échéance réelle** : Jeremy ne prend pas tous les signaux (pas d'automatisation avant le
payout). Au rythme observé, compter **12 à 14 semaines** plutôt que les 8 du calcul brut.

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
