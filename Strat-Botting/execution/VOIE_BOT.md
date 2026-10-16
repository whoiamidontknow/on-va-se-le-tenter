# Voie d'exécution du bot — STRATÉGIE V1 → V7

*Agent « Exécution du bot », 16/10/2026. Sources en fin de document. Quand une info n'a pas été trouvée, c'est écrit « non trouvé ».*

## 0. En une phrase

**TradingView (alerte webhook) → PickMyTrade → Tradovate, sur un compte Lucid Trading (Flex ou Pro) avec Tradovate choisi à l'achat.**
Plan B : même chaîne mais **CrossTrade** en route « Tradovate direct » (dans le cloud, sans NinjaTrader) à la place de PickMyTrade.
**Apex : à exclure pour un bot** (automatisation interdite). **Tradeify : possible** sous conditions (voir §2).

---

## 1. Ce que la stratégie demande au courtier

Lu dans `STRATEGIE_V1.pine` (l. 152-160 et 1700-1822) :

| Comportement Pine | Ce qu'il faut côté courtier |
|---|---|
| Calcul **à la clôture** de bougie, entrée **au marché à l'ouverture suivante** (`process_orders_on_close=false`, `calc_on_every_tick=false`) | ordre au marché envoyé à la clôture → rempli ≈ à l'ouverture suivante |
| `strategy.exit` = **bracket stop + objectif** posé dès le remplissage (distance en ticks, ou prix d'un niveau) | **bracket natif chez le courtier** (OCO) attaché à l'entrée, pour qu'un stop existe même si les alertes tombent ensuite |
| Le stop bouge **à chaque clôture** (break-even, stop suiveur ATR / swing — l. 1700-1708) | **modifier le prix du stop** d'une position ouverte, à un prix exact |
| Sortie partielle possible (2 brackets XL1/XL2, objectif 1 et objectif 2) | plusieurs objectifs avec quantités différentes — à tester, voir §6 |
| `strategy.close_all` « Fin de séance », « Stop dépassé », `strategy.close` « Signal opposé » | **clôturer au marché ET annuler les ordres restants** |

Conséquence : la solution doit savoir (a) bracket attaché, (b) **déplacer le stop à un prix donné**, (c) « clôturer + annuler tout ». C'est le point (b) qui départage les outils.

---

## 2. Les propfirms : plateforme fournie et autorisation du bot

| | Plateformes / flux fournis | Le bot est-il autorisé ? (texte exact) |
|---|---|---|
| **Lucid Trading** | Flux **CQG** : NinjaTrader, **Tradovate**, **TradingView**. Flux **Rithmic** : Quantower, Tradesea, MotiveWave, Sierra Chart, Jigsaw, Bookmap, ATAS, R\|Trader Pro, MultiCharts. « All listed platforms work with all Lucid account types. » (page officielle *Supported Platforms*) | **OUI.** Page officielle *Other Trading Activities* (MAJ 26/08/2026) : « **Automated trading systems and trade copiers are permitted** » et « All automated activity must comply with Lucid Trading rules. » Le trader porte la responsabilité des erreurs logicielles. Interdits à côté : HFT (« submitting and executing a high volume of trades within extremely short time frames, often measured in seconds or even milliseconds »), microscalping. Annonces : **interdites sur LucidDaily** (red folder = perte du compte), autorisées sur Flex / Pro / Direct. |
| **Tradeify** | 3 courtiers au choix à l'achat : **Tradovate** (Tradovate, NinjaTrader, TradingView), **Rithmic** (Tradesea, Quantower, Sierra Chart, R\|Trader), **WealthCharts**. « **TradingView connects through Tradovate only.** » (page officielle, MAJ 05/08/2026). Pas de ProjectX listé. | **OUI, sous conditions.** Page officielle *Guidelines for Traders* (MAJ 12/08/2026) : « At Tradeify, we allow the use of bots and algorithms under certain conditions » ; « You must be able to prove that you are the sole owner of the bot or strategy, and that no one else has access to or is using it » ; contrôle possible par « a live video of you enabling the code on your own PC » ; « **While you may use the bot on your personal accounts, using it across multiple firms is against Tradeify's policy.** » ; « Personal bots are allowed as long as they are not high-frequency trading (HFT) bots ». Comptes financés : « Over 50% of your trades are longer than 10 seconds » et « Over 50% of your profit must come from trades held longer than 10 seconds ». Annonces : « We do not have any rules against or guidelines around trading news events ». |
| **Apex Trader Funding** | Rithmic, Tradovate, WealthCharts (plateforme figée à l'achat). | **NON.** Page officielle *Prohibited Activities* : **« No Automation or Algorithm Usage allowed »**, motif : récompenser « human traders actively participating in the learning process, not to reward automated systems » (citation relevée par QuantVPS le 10/10/2026 ; la page officielle renvoie un 403 aux robots, **je n'ai pas pu la lire moi-même**). Selon la même source, l'interdiction couvre explicitement les services webhook « alerte → ordre ». Risque : fermeture du compte PA/Live et perte des gains. **À ne pas utiliser pour ce projet.** |

Points clés pour l'exécution :
- **Lucid et Tradeify fournissent tous deux Tradovate** → une seule chaîne technique marche pour les deux.
- Règle Tradeify « pas le même bot dans plusieurs propfirms » : **choisir UNE propfirm pour le bot** (ne pas faire tourner la même stratégie chez Lucid et Tradeify en même temps).
- Heure de clôture forcée : **Lucid 16 h 45 ET** (liquidation automatique sur Flex/Pro/Direct, ce n'est pas une perte du compte — source secondaire) ; **Tradeify 16 h 59 ET** (source secondaire TradersPost). L'agent « règles » doit confirmer.
- L'API Tradovate « maison » est **hors jeu** pour un compte propfirm (voir §3).

---

## 3. Comparatif des voies d'exécution

| Voie | Propfirms (via) | Bracket attaché côté courtier | Déplacer le stop à un prix | Prix / mois | Latence | Fiabilité / remarques | Multi-comptes |
|---|---|---|---|---|---|---|---|
| **PickMyTrade** (cloud) | Lucid, Tradeify (Tradovate) ; aussi Rithmic, ProjectX | **Oui** : `dollar_sl` / `dollar_tp` (distance en points), multi-objectifs `advance_tp_sl` (3 blocs max) | **Oui** : `update_sl:true` + `sl` = **prix exact** (« cancels the existing stop … and replaces it with a new order at the price you sent ») ; break-even et stop suiveur natif Tradovate aussi | **50 $/mois** ou 500 $/an, essai 7 j (page officielle) — une autre page dit « 50 $ par connexion courtier » | « under 200ms on our side » (dire du vendeur) ; latence TradingView : non trouvé | `close` = « squares off the current position and cancels open orders » ; `same_direction_ignore` évite les doublons. Doc JSON officielle incomplète → **tester en démo** | `multiple_accounts` (tableau de comptes, multiplicateur de quantité) |
| **CrossTrade** — route Tradovate direct (cloud, GA 22/07/2026) | Tradovate (donc Lucid, Tradeify) ; « No VPS requirement » | **Oui** : brackets natifs, multibrackets, ATM Tradovate | **Oui** : « Change quantity or applicable prices on working orders » | **Standard 29 $**, Pro 49 $ (copieur), Elite 99 $ ; essai 7 j | non trouvé | Cancel, flatten, close partiel, reverse documentés ; syntaxe `key=value;` | Pro : copieur illimité |
| **CrossTrade** — via NinjaTrader 8 | NinjaTrader de Lucid/Tradeify (flux Tradovate/CQG) | Oui (ATM NinjaTrader) | Oui (commande CHANGE) | 29 $ + NinjaTrader | dépend du PC | **NinjaTrader doit tourner en continu** (PC ou VPS) → un point de panne de plus | Pro |
| **TradersPost** | Lucid, Tradeify, Apex… (Tradovate, OAuth) | **Oui**, Tradovate est un des rares courtiers avec bracket attaché (`stopLoss.stopPrice`, `takeProfit.limitPrice`) | **Seulement break-even** (`action:"breakeven"`). Déplacement à un prix quelconque : **non documenté** (vérifié dans la doc) | Starter 41,65 $/mois en annuel (1 compte réel, prop firm comptée comme compte réel) ; mensuel ≈ 49 $ (déduit : « save 15 % ») | non trouvé | Déconseille les symboles continus `1!` ; `resize` à la baisse **annule les brackets** ; un seul objectif | selon formule (1 à 6 comptes réels) |
| **TradingView ↔ Tradovate natif** (panneau de trading) | Lucid, Tradeify | — | — | inclus | — | **Impossible pour un bot** : « Automated strategy trading with a brokerage account is not available on TradingView yet. » (aide officielle TradingView) | — |
| **API / webhook Tradovate maison** | — | (oui techniquement) | (oui) | 25 $/mois d'add-on API + compte réel ≥ 1 000 $ | — | **Comptes propfirm non éligibles** (forum Tradovate + blog PickMyTrade) ; il faudrait aussi héberger un serveur | — |
| **Rithmic** (NinjaTrader, Quantower…) | Tradeify-Rithmic, Lucid-Rithmic, Apex | via PickMyTrade (connecteur Rithmic) | via PickMyTrade | 50 $ + frais Rithmic (non trouvé) | non trouvé | Pas de TradingView sur Rithmic chez Tradeify ; NinjaTrader n'est pas listé côté Rithmic chez Lucid → aucun intérêt ici | — |
| **ProjectX / TopstepX** | **aucune des trois** ne le liste | TradersPost : « ProjectX does not yet support brackets » | — | — | — | hors sujet | — |

---

## 4. Recommandation

### N° 1 — TradingView → PickMyTrade → Tradovate, compte **Lucid Flex ou Pro**
- **Lucid** : seul des trois à écrire noir sur blanc que les systèmes automatiques sont permis, sans validation préalable ni condition de propriété ; Tradovate + TradingView fournis.
  Prendre **Flex ou Pro**, **pas Daily** (annonces = perte du compte sur Daily).
- **PickMyTrade** : c'est le seul des outils « simples » dont la doc montre à la fois le bracket attaché, le **déplacement du stop à un prix exact** (indispensable au stop suiveur de la stratégie) et la clôture qui annule les ordres restants. Cloud, rien à faire tourner chez soi.
- Tradeify reste possible avec la même chaîne si l'agent « règles » le préfère (conditions de propriété, pas multi-firmes, durée > 10 s — facile pour une stratégie en bougies).

### Plan B — CrossTrade, route « Tradovate direct » (29 $/mois)
Même architecture, mêmes capacités (bracket natif, modification d'ordre, flatten). À prendre si PickMyTrade déçoit en démo (doc JSON incomplète, comportement de `update_sl` avec plusieurs objectifs). Le format d'alerte change (syntaxe `key=value;`), la logique Pine reste la même.

### Plan C (dégradé) — TradersPost
Seulement si on renonce au stop suiveur (break-even seul).

---

## 5. Coûts mensuels (hors propfirm)

| Poste | Prix | Statut |
|---|---|---|
| TradingView Ultimate | déjà payé | webhooks inclus dans les formules payantes |
| **Données CME temps réel dans TradingView** (sinon les alertes partent sur des cours différés) | **non trouvé** | à vérifier dans le compte TradingView de Jeremy |
| PickMyTrade | 50 $/mois (ou 500 $/an) | page officielle |
| CrossTrade (plan B) | 29 $/mois | page officielle |
| Tradovate (fourni par la propfirm) | 0 $ | compte inclus dans l'éval |
| **Total voie n° 1** | **≈ 50 $/mois** + données CME éventuelles | |

---

## 6. Mise en place pour Jeremy (dans l'ordre)

1. **Acheter l'éval Lucid 50k Flex (ou Pro)** en choisissant **Tradovate / CQG** comme plateforme. *(Attendre le verdict de l'agent « règles » si besoin.)*
2. Vérifier dans TradingView que **MNQ/MES sont en temps réel** (pas de mention « D » = différé sur le graphique).
3. Créer un compte **PickMyTrade** (essai gratuit 7 jours), y **connecter Tradovate** avec les identifiants Lucid, et noter le **token** et l'**ID de compte**.
4. **D'abord en démo / compte simulé** : brancher PickMyTrade sur un compte d'essai Tradovate, pas sur l'éval.
5. Dans TradingView, ouvrir la **V7** (avec le module d'alertes de `ALERTES.md`), réglages : cocher « Envoyer les ordres au courtier », coller token, ID de compte, symbole.
6. Créer **une seule alerte** : Condition = la stratégie V7 → « **Order fills and alert() function calls** » ; Message = `{{strategy.order.alert_message}}` ; cocher **Webhook URL** = l'URL donnée par PickMyTrade ; expiration = la plus lointaine possible.
7. **Test à blanc** pendant au moins 3 séances : à chaque entrée, vérifier dans Tradovate que le **stop et l'objectif apparaissent tout de suite** ; à chaque clôture de bougie, que le stop **se déplace** ; à 16 h 40 ET, que tout est **à plat sans ordre restant**.
8. Tester exprès les cas tordus : couper l'alerte en pleine position (le stop doit rester chez Tradovate) ; envoyer deux fois la même entrée (pas de double position) ; sortie partielle si utilisée.
9. Seulement ensuite, basculer le token/compte sur **l'éval Lucid**, **1 micro**.
10. Chaque matin : regarder dans TradingView que l'alerte est **active** (pas « arrêtée »), et dans PickMyTrade que la connexion Tradovate est **verte**.
11. **Toute modification du Pine = supprimer et recréer l'alerte** (une alerte garde la version du script au moment où elle a été créée).

---

## 7. Risques et parades

| Risque | Ce qui se passe | Parade |
|---|---|---|
| **Webhook / PickMyTrade / TradingView en panne** pendant une position | plus de mise à jour du stop | Le **stop et l'objectif sont chez Tradovate** dès l'entrée (bracket natif) : la perte maximale reste celle du stop initial. Le stop reste au dernier niveau envoyé. |
| Panne **pendant l'entrée** | position sans protection ? | PickMyTrade envoie entrée + bracket dans la même alerte ; contrôle visuel lors des tests (étape 7). En cas de doute : stop manuel dans Tradovate. |
| **Double ordre** (TradingView renvoie le webhook jusqu'à 3 fois si le serveur répond une erreur 5xx, toutes les 5 s) | deux entrées | `same_direction_ignore:true` + `pyramid:false` dans le JSON ; la stratégie a `pyramiding=0` ; `close` ne peut jamais ouvrir de position. |
| **Alerte manquée** (alerte arrêtée, expirée, limite TradingView : « more than 15 alerts … within three minutes » → arrêt automatique ; serveur > 3 s → requête annulée) | position non ouverte ou non fermée | 1 message de stop par bougie au plus (pas d'envoi si le stop ne bouge pas) ; vérification quotidienne (étape 10) ; la propfirm liquide de toute façon à l'heure limite. |
| **Désynchronisation** (le stop a sauté chez Tradovate mais pas dans le testeur, ou l'inverse) | stratégie et compte ne sont plus d'accord | Chaque sortie de bracket du testeur envoie un `close` (sans effet si déjà à plat) ; `update_sl` ne fait rien si aucune position. |
| **Heure de clôture** (Lucid 16 h 45 ET, Tradeify 16 h 59 ET) | liquidation forcée par la propfirm | Régler la sortie « Fin de séance » de la V7 **avant 16 h 40 ET** (marge de 5 min) + pas de nouvelle entrée après ~16 h 15 ET. |
| **Annonces** | slippage ; perte du compte sur LucidDaily | Compte **Flex/Pro**, pas Daily ; garder le blackout d'annonces du Signator dans la V7. |
| Roll de contrat (MNQ1! → nouveau contrat) | ordre sur le mauvais contrat | Vérifier comment PickMyTrade résout `MNQ1!` lors du premier roll ; sinon mettre le contrat exact (ex. `MNQZ2026`) dans le réglage symbole. |
| Règles de la propfirm qui changent | compte fermé | Relire les pages citées avant chaque achat de compte. |

---

## Sources
- Lucid — automatisation : https://support.lucidtrading.com/en/articles/11404728-other-trading-activities
- Lucid — plateformes : https://support.lucidtrading.com/en/articles/11404614-lucid-trading-supported-platforms
- Lucid — HFT : https://support.lucidtrading.com/en/articles/11404736-prohibited-high-frequency-trading
- Lucid — clôture 16 h 45 ET (secondaire) : https://proptradingvibes.com/blog/lucid-trading-allowed-trading-times
- Tradeify — règles bots : https://intercom.help/tradeify/en/articles/10468318-guidelines-for-traders
- Tradeify — plateformes : https://intercom.help/tradeify/en/articles/10468221-supported-platforms
- Tradeify — clôture 16 h 59 ET (secondaire) : https://blog.traderspost.io/article/automate-tradeify-with-traderspost
- Apex — page officielle (403 pour moi) : https://apextraderfunding.com/help-center/getting-started/prohibited-activities/ ; citation relevée par : https://www.quantvps.com/blog/apex-trader-funding-automated-trading-bots
- TradingView — pas d'auto-trading natif : https://www.tradingview.com/support/solutions/43000481026-how-to-autotrade-using-pine-script-strategies/
- TradingView — renvoi des webhooks : https://www.tradingview.com/support/solutions/43000735201-webhook-resubmission/
- TradingView — webhooks (3 s, IP) : https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/
- TradingView — limite 15 alertes / 3 min : https://www.tradingview.com/pine-script-docs/faq/alerts/
- PickMyTrade — prix : https://pickmytrade.io/faq/pricing-costs
- PickMyTrade — update_sl/update_tp : https://blog.pickmytrade.trade/change-stop-loss-take-profit-live-tradovate-trade/
- PickMyTrade — vocabulaire `data` : https://blog.pickmytrade.trade/strategy-market_position-vs-market_position_size-in-alerts/
- PickMyTrade — stop suiveur : https://blog.pickmytrade.trade/auto-trail-stop-futures-math-trigger-distance-frequency/
- PickMyTrade — multi-objectifs : https://blog.pickmytrade.trade/multiple-take-profit-levels-tradingview-alert/
- PickMyTrade — close annule les ordres : https://blog.pickmytrade.trade/automating-trade-management-closing-orders-positions-tradovate-tradingview/
- PickMyTrade — Lucid : https://pickmytrade.io/copier/tradingview-to-lucid-trading-copier
- CrossTrade — prix : https://crosstrade.io/pricing
- CrossTrade — Tradovate direct : https://crosstrade.io/blog/tradovate-webhook-trading-generally-available
- TradersPost — champs webhook : https://docs.traderspost.io/docs/core-concepts/webhooks
- TradersPost — futures (brackets, symboles) : https://docs.traderspost.io/docs/assets/futures-trading
- TradersPost — prix : https://traderspost.io/pricing
- API Tradovate & comptes prop : https://community.tradovate.com/t/api-access-for-propfirm-accounts/10348 ; https://blog.pickmytrade.trade/tradovate-api-access-without-1000-minimum-2026-options/
