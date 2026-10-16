# Règles des propfirms — comptes futures 50k (Apex, Tradeify, Lucid)

Relevé du **16/10/2026**. Les données chiffrées pour le simulateur sont dans [`regles.toml`](regles.toml) (17 variantes).
Toutes les heures sont données en **heure de Chicago (CT)** ; l'heure de New York (ET) = CT + 1 h.

## Comment ça a été vérifié (lire avant d'utiliser)

| Propfirm | Accès aux sources officielles | Fiabilité |
|---|---|---|
| **Tradeify** | Help Center lu en entier (miroir `intercom.help/tradeify`), plus le *Funded Trader Agreement* (« Last modified: October 2026 ») lu en entier sur tradeify.co | Bonne. Tous les chiffres viennent du site officiel |
| **Lucid** | Help Center lu en entier (`support.lucidtrading.com`). Le site marchand renvoie une erreur 403 | Bonne pour les règles. **Prix non officiels** (sources secondaires) |
| **Apex** | Le site et le centre d'aide bloquent tout accès automatisé (Cloudflare 403). Lu à travers les **extraits que le moteur de recherche a indexés depuis les pages officielles**, recoupés avec des sources d'août-sept. 2026 | Moyenne. Règles cohérentes entre sources ; **prix contradictoires** |

Les points non confirmés par une source officielle sont marqués ⚠ ici, et notés dans la clé `incertitudes` du TOML.

---

## 1. Verdict sur les bots (point bloquant)

| Propfirm | Bots en éval | Bots en financé | Verdict |
|---|---|---|---|
| **Apex** | **Interdits** | **Interdits** (fermeture du compte, gains confisqués) | ❌ **éliminatoire** |
| **Tradeify** | Autorisés sous conditions | Autorisés sous conditions | ✅ **autorisé par écrit** dans le contrat d'octobre 2026 |
| **Lucid** | « Permis » (Help Center) | « Permis » (Help Center) | ⚠ **permis, mais le contrat exige un accord écrit préalable** |

### Apex — interdit
Sources : [Prohibited Activities](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/) ·
[support : Prohibited Activities](https://support.apextraderfunding.com/hc/en-us/articles/40463668243099-Prohibited-Activities) ·
[PA and Compliance](https://support.apextraderfunding.com/hc/en-us/articles/31519788944411-Performance-Account-PA-and-Compliance) — consultées le 16/10/2026 (texte lu via l'index de recherche, pages bloquées en 403).

> « Apex Trader Funding strictly prohibits the use of automation on all account types, including any form of AI (Artificial Intelligence), Autobots, algorithms, fully automated trading systems, and high-frequency trading (HFTs). »

> « The use of any method, tool, script, macro, or system that pre-programs, batch-submits, pre-loads, auto-executes, modifies, or otherwise automates orders entry or order modification is strictly prohibited. »

> « Any type of hands-off, set-and-forget, set-and-walk-away trading, including systems that run continuously 24 hours a day, is strictly prohibited. »

> « Rewards are intended to recognize human traders actively participating in the learning process, not to reward automated systems executing preprogrammed logic. »

> « [PA and Live Prop Accounts] cannot be managed or influenced by any other party, person, system, automated trading bot, copy trading service, or trade mirroring software. »

Sanction : fermeture immédiate du PA ou du compte Live et confiscation de tous les gains. Seul cas toléré : la gestion semi-automatique d'une position **ouverte à la main** (ATM NinjaTrader, brackets, stop suiveur). Le copieur de groupe Tradovate entre ses propres comptes existe. Un bot qui ouvre lui-même ses positions, y compris via une alerte TradingView envoyée par webhook, est donc **interdit**.

### Tradeify — autorisé sous conditions
Source principale : [Funded Trader Agreement](https://tradeify.co/funded-trader-agreement), §6.6, « Last modified: October 2026 », consulté le 16/10/2026 :

> « **6.6 Automated Bots:** The use of automated trading bots or algorithms ("bots/algos") is permitted only under the following conditions:
> **Ownership:** The Trader must be able to prove that the Trader is the sole owner of the bot or strategy and that no one else has access to or is using it. […]
> **Exclusive Use:** While the Trader may use the bot on the Trader's personal accounts, using it across multiple firms is against Tradeify's policy. The bot must be solely for the Trader's own use within Tradeify.
> **No High-Frequency Trading (HFT) Bots:** Personal bots are allowed as long as they are not high-frequency trading (HFT) bots. […]
> **Compliance & Verification:** Tradeify reserves the right to request information or documentation if our risk measures flag the Trader's account […]. »

Le [Help Center, *Guidelines for Traders*](https://help.tradeify.co/en/articles/10468318-guidelines-for-traders) (consulté le 16/10/2026) ajoute :
> « We scan to ensure there are no similar orders on other accounts. We will also require a live video of you enabling the code on your own PC. »

Autres conditions :
- La [FAQ Risk & Compliance](https://help.tradeify.co/en/articles/17069653-risk-compliance-guidelines-faq) dit : « Automated trading is permitted only as expressly allowed […] No trading technology exempts a trader from any Tradeify rule. »
- Copier ses propres comptes est permis (5 comptes financés au maximum). Copier les trades d'une autre personne est interdit (§6.7(b)).
- **Microscalping** (comptes financés seulement) : plus de 50 % des trades **et** plus de 50 % du profit doivent venir de trades tenus plus de 10 s. Sinon le payout est refusé ; le compte n'est pas perdu.
- §6.5 du contrat : il faut « un plan de trading constant (taille, stops, objectifs) ». Le DCA est permis s'il est structuré.

Conséquence pour nous : **un bot MNQ/MES en 15 min, codé par nous, est conforme.** En revanche, la clause « Exclusive Use » **interdit de faire tourner le même bot en même temps chez Lucid ou ailleurs**. Il faut choisir une seule firme pour ce bot.

### Lucid — permis, avec un accord écrit à obtenir
[Help Center, *Other Trading Activities*](https://support.lucidtrading.com/en/articles/11404728-other-trading-activities), consulté le 16/10/2026 :
> « **Automated Strategies** — Automated trading systems and trade copiers are permitted. All automated activity must comply with Lucid Trading rules. Traders are fully responsible for any software errors, malfunctions, or unintended outcomes. »

Restrictions :
- **HFT** interdit ([page HFT](https://support.lucidtrading.com/en/articles/11404736-prohibited-high-frequency-trading)) : avertissement écrit la première fois, puis profits retirés, comptes fermés et exclusion.
- **Microscalping** ([page](https://support.lucidtrading.com/en/articles/11404742-prohibited-microscalping)) : le compte est signalé si plus de 50 % du profit vient de trades tenus 5 s ou moins.

**Contradiction** : le [LucidDirect Account Agreement](https://lucidtrading.com/wp-content/uploads/2025/05/LucidDirect-Account-Agreement-5-19.pdf) (« Last modified: May 19, 2025 ») dit autre chose. Le PDF est bloqué en 403 ; le texte a été lu via l'index de recherche :
> « you must immediately notify Lucid Trading in writing and obtain written approval […] prior to using any Automated Trading Software […] Lucid Trading prohibits the use of any Automated Trading Software owned or developed by any third party other than you. »

Ce contrat est peut-être ancien. Le texte des contrats Flex/Pro actuels n'a pas été trouvé. **Avant tout usage, il faut demander une validation écrite au support Lucid.** Il faut aussi faire préciser si une passerelle webhook tierce (TradersPost, PickMyTrade…) compte comme « third-party software ».

---

## 2. Tableau comparatif (variantes 50k)

DD = drawdown max. EOD = suivi à la clôture, mais **appliqué en temps réel** partout. DLL = perte journalière max (« soft » = journée arrêtée, compte conservé). « Plancher figé » = niveau où le trailing s'arrête en financé.

| Variante | Éval (catalogue) | Activation | Objectif | DD / type | Plancher figé | DLL éval → financé | Contrats éval / financé | Jours min éval | Constance éval / financé | Payout (conditions, plafond) | Partage | Fermeture CT | Bots |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Apex EOD | 490 $ ⚠ (ou 590) | 139 $ ⚠ (ou 129) | 3 000 | 2 000 EOD | 50 100 (à 52 100) | 1 000 → paliers 1 000/1 000/2 000 | 6 / 2→3→4 | 1 (**30 j max**) | 0 / **50 %** | 5 j ≥ 250 $, solde ≥ 52 600, min 500, plafonds 1,5k-1,5k-2k-2,5k-2,5k-3k, **6 payouts max** | 100 % | 15:59 | ❌ |
| Apex EOD sans activation | 1 190 $ (119 $ avec code) | 0 | idem | idem | idem | idem | idem | idem | idem | idem | 100 % | 15:59 | ❌ |
| Apex Intraday | 249 $ ⚠ | 59 $ ⚠ (ou 79) | 3 000 | 2 000 **intraday** | 50 100 | aucune → paliers ⚠ | 6 / 2→3→4 ⚠ | 1 (**30 j max**) | 0 / 50 % | 5 j ≥ 200 $, plafonds 1,5k-2k-2,5k-2,5k-3k-3k ⚠ | 100 % | 15:59 | ❌ |
| Apex Intraday sans activation | introuvable | 0 | idem | idem | idem | idem | idem | idem | idem | idem | 100 % | 15:59 | ❌ |
| **Tradeify Growth** | 145 $ | 0 | 3 000 | 2 000 EOD | 50 100 (à 52 100 ou à la demande de payout) | 1 250 → 1 250 (2 000 dès 53 000) | 4 / 4 | 1 | 0 / **35 %** | 5 j ≥ 150 $, solde ≥ 53 000, min 500, plafonds 1,5k-2k-2,5k-3k | 90 % | 15:45 | ✅ cond. |
| **Tradeify Select → Flex** | 165 $ (205 $ option 50 %) | 0 | 3 000 | 2 000 EOD | 50 100 | **aucune → aucune** | 4 / 2→3→4 | 3 (2 avec option) | **40 %** (50 % option) / **0** | 5 j gagnants ≥ 150 $, profit du cycle > 0, **50 % du profit**, plafond **2 500**, min 250, pas de solde min | 90 % | 15:45 | ✅ cond. |
| **Tradeify Select → Daily** | 165 $ (205 $) | 0 | 3 000 | 2 000 EOD | 50 100 | aucune → **1 000** | 4 / 2→3→4 | 3 (2) | 40 % (50 %) / 0 | chaque jour, au-dessus du tampon 52 100, ≤ 2 × profit du cycle, plafond **1 250**, min 250 | 90 % | 15:45 | ✅ cond. |
| Tradeify Lightning (direct) | 492 $ (achat) | 0 | — | 2 000 EOD | 50 100 | 1 250 (2 000 dès 53 000) | 4 | — | — / 20→25→30 % | profit de cycle 3 000 puis 2 000, min **1 000**, plafonds 2k-2k-2k-2,5k | 90 % | 15:45 | ✅ cond. |
| **LucidFlex DLL** | 146 $ ⚠ | 0 | 3 000 | 2 000 EOD | 50 100 (éval **et** financé) | 1 200 ⚠ → 1 200 | 4 / 2→3→4 | 2 | **50 %** / **0** | 5 j ≥ 150 $, profit du cycle > 0, 50 % du profit, plafond **2 000** (fixe), min 500, **5 payouts** puis examen Live | 90 % | 15:45 | ⚠ cond. |
| LucidFlex sans DLL | introuvable (plus cher) | 0 | 3 000 | 2 000 EOD | 50 100 | aucune | 4 / 2→3→4 | 2 | 50 % / 0 | idem | 90 % | 15:45 | ⚠ cond. |
| **LucidPro DLL** | 192 $ ⚠ (ou 185) | 0 | 3 000 | 2 000 EOD | 50 100 | 1 200 → 1 200 puis 60 % du pic | 4 / 4 | 1 | 0 / **40 %** | profit du cycle ≥ 500, tampon 52 100, plafonds 2k puis 2,5k, min 500, 5 payouts | 90 % | 15:45 | ⚠ cond. |
| LucidPro sans DLL | introuvable | 0 | 3 000 | 2 000 EOD | 50 100 | aucune | 4 / 4 | 1 | 0 / 40 % | idem | 90 % | 15:45 | ⚠ cond. |
| LucidDaily (4 configs) | dès 156 $ ⚠ | 0 | 3 000 | 2 000 EOD ou intraday en éval, **intraday en financé** | 50 100 | 1 200 ou aucune (les deux phases) | 4 / 4 | 2 | 50 % / 0 | chaque jour, tout le profit au-dessus de 52 100, min 500 ; jour à 8 000 $ → Live | 90 % | 15:45 | ⚠ cond. — **news interdites** |
| LucidDirect (direct) | 515 $ ⚠ (achat) | 0 | — | 2 000 EOD | 50 100 | 1 200 puis 60 % du pic | 4 | — | — / **20 %** | profit de cycle 3 000 puis 2 500, plafonds 2k×3 puis 2,5k×2, min 500 | 90 % | 15:45 | ⚠ cond. (contrat : accord écrit) |

Points communs aux trois firmes :
- Il est interdit de garder une position la nuit ou le week-end.
- Pas de frais mensuels.
- Le **hedging** est interdit : positions opposées sur le même produit ou sur des produits corrélés, dans un compte ou entre plusieurs comptes, et même entre firmes chez Tradeify et Lucid.
- Pour les micros, 10 micros = 1 mini.

---

## 3. Détail par propfirm

### 3.1 Apex Trader Funding (règles « 4.0 », comptes achetés depuis le 01/03/2026)

Sources, toutes consultées le 16/10/2026 :
- [EOD Evaluations](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-evaluations/)
- [EOD Drawdown Explained](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/)
- [EOD Performance Accounts](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-performance-accounts-pa/)
- [EOD Payouts](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/)
- [Intraday Evaluations](https://apextraderfunding.com/help-center/evaluation-accounts-ea/intraday-trailing-drawdown-evaluations/)
- [Intraday Explained](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/)
- [Intraday PA](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-performance-accounts-pa/)
- [Intraday Payouts](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-payouts/)
- [Daily Loss Limit Explained](https://apextraderfunding.com/help-center/additional-helpful-items/daily-loss-limit-explained/)
- [No Activation Fee Evaluations](https://apextraderfunding.com/help-center/uncategorized/no-activation-fee-evaluations/)
- [Futures Trading Times](https://apextraderfunding.com/help-center/getting-started/futures-trading-times/)

Sources secondaires :
- [proptradingvibes (10/08/2026)](https://proptradingvibes.com/blog/apex-trader-funding-rules-overview)
- [prop50k (25/09/2026)](https://www.prop50k.com/review/apex-trader-funding/)
- [fundedfuturesfamily (04/09/2026)](https://www.fundedfuturesfamily.com/apex-activation-fee/)
- [traderssecondbrain (22/09/2026)](https://traderssecondbrain.com/guides/apex-payout-rules-explained)

**Variantes :** deux types de drawdown (EOD Trail et Intraday Trail), chacun avec deux formules de frais (avec frais d'activation, ou « No Activation Fee »). Les règles sont les mêmes ; seuls les frais changent.

**Éval (30 jours calendaires au maximum, sans reset) :**
- Objectif : 3 000 $.
- DD : 2 000 $.
  - EOD : recalculé à 16:59 ET (15:59 CT) sur le solde de clôture, mais un contact intraday liquide le compte et fait échouer l'éval.
  - Intraday : suit le pic de solde réalisé ou latent.
- Le trailing s'arrête à 53 000 $ en éval. C'est sans effet pratique, car l'éval est réussie dès 53 000 $.
- DLL de 1 000 $ sur l'**EOD** seulement : c'est une soft breach (« Hitting the Daily Loss Limit does not fail your account. It simply pauses trading for the remainder of the day »). L'Intraday n'a pas de DLL en éval.
- 6 minis / 60 micros.
- Pas de minimum de jours (1 jour suffit).
- Pas de constance en éval.
- 7 jours pour activer le PA après la réussite.

**Compte financé (PA) :**
- DD de 2 000 $, du même type qu'en éval. Le plancher se fige à **50 100 $** dès que le solde atteint 52 100 $ (« Threshold Stop Level = $50,100 »).
- Paliers de contrats et de DLL, d'après la page du PA EOD :

  | Profit du PA | Contrats max | DLL |
  |---|---|---|
  | 0 à 1 499 $ | 2 | 1 000 $ |
  | 1 500 à 2 999 $ | 3 | 1 000 $ |
  | 3 000 à 5 999 $ | 4 | 2 000 $ |

  ⚠ Pour le PA Intraday, la page dit « tier-based » sans que les montants aient été vus.
- « Safety net » : 52 100 $, à conserver toute la vie du compte.

**Payouts :**
- 5 jours qualifiants, pas forcément consécutifs, avec un gain minimal de 250 $ (EOD) ou 200 $ (Intraday).
- Solde minimal de 52 600 $ ; demande minimale de 500 $.
- **Constance 50 %** : « No single profitable trading day may account for 50% or more of total profit earned since your last approved payout ».
- Partage à 100 % ; **6 payouts maximum**, puis le PA est clos.
- Plafonds par demande :
  - EOD : 1 500 / 1 500 (source officielle), puis 2 000 / 2 500 / 2 500 / 3 000 ⚠ (source secondaire).
  - Intraday : 1 500 / 2 000 / 2 500 / 2 500 / 3 000 / 3 000 ⚠.
- Les règles « 30 % negative P&L » et « 5:1 risk-reward » ont été supprimées pour les comptes 4.0.

**Clôture :** « all positions must be closed by 4:59:00 PM ET » (15:59 CT). Une position encore ouverte à 17:00 ET peut faire échouer le compte. Le filet de sécurité automatique à 16:59 ET n'est qu'un dernier recours.

**News :** le trading pendant les annonces est permis (« You can trade on holidays and during news »). Prendre des positions opposées pour jouer les deux côtés est interdit.

**Plateformes :** Rithmic, Tradovate, WealthCharts ; NinjaTrader ; TradingView via Tradovate.

**Prix ⚠ contradictoires :**
- EOD standard : 490 $ ou 590 $ au catalogue, plus 129 $ ou 139 $ d'activation.
- EOD sans activation : 1 190 $ au catalogue (119 $ avec code), d'après l'extrait du sélecteur officiel.
- Intraday : 249 $, plus 59 $ ou 79 $ d'activation.
- Les remises de 80 à 92 % sont quasi permanentes.
- Depuis le 01/10/2026, Apex n'affiche plus le montant de l'activation.

### 3.2 Tradeify

Sources officielles, toutes consultées le 16/10/2026 :
- [Funded Trader Agreement (oct. 2026)](https://tradeify.co/funded-trader-agreement)
- [Growth Evaluation](https://help.tradeify.co/en/articles/10495915-growth-evaluation-accounts)
- [Growth Funded Payout](https://help.tradeify.co/en/articles/11083796-growth-funded-account-payout-policy)
- [Select Evaluation](https://help.tradeify.co/en/articles/12853921-select-evaluation-accounts)
- [Select Flex & Daily](https://help.tradeify.co/en/articles/12853966-select-flex-and-select-daily-payout-policies)
- [Lightning Funded](https://help.tradeify.co/en/articles/10495938-lightning-funded-accounts)
- [Lightning Payout](https://help.tradeify.co/en/articles/10495932-lightning-funded-account-payout-policy)
- [Trailing Max Drawdowns](https://help.tradeify.co/en/articles/10495897-rules-trailing-max-drawdowns)
- [Daily Loss Limit](https://help.tradeify.co/en/articles/10468321-rules-daily-loss-limit)
- [Consistency Rule](https://help.tradeify.co/en/articles/10468320-rules-consistency-rule)
- [Permitted Times](https://help.tradeify.co/en/articles/10495876-rules-permitted-times-to-trade)
- [News Trading](https://help.tradeify.co/en/articles/10495874-rules-news-trading)
- [Pricing Reference](https://help.tradeify.co/en/articles/14369021-tradeify-pricing-reference)
- [Supported Platforms](https://help.tradeify.co/en/articles/10468221-supported-platforms)
- [Essential Trading Rules](https://help.tradeify.co/en/articles/12268167-essential-trading-rules-overview)

**Règles communes :**
- **Drawdown** : tous les comptes sont en **EOD trailing**, appliqué en temps réel sur la valeur nette liquidative, positions latentes comprises (« Hitting this limit FAILS your account permanently »).
- **Blocage du plancher** : en financé seulement, il se fige à 50 100 $ quand la clôture atteint 52 100 $ ou dès la première demande de payout. Il n'y a **pas de blocage en éval**.
- **DLL** : toujours soft (« pauses trading for the day but does NOT fail your account »).
- **Clôture** : à **16:45 ET (15:45 CT)**. Les positions oubliées sont fermées d'office, sans échec du compte.
- **News** : libres (« We do not have any rules against or guidelines around trading news events »).
- **Activité** : au moins 1 trade par semaine et par compte.
- **Pas de limite de temps** pour l'éval.
- **Comptes** : 5 comptes financés au maximum par foyer.
- **Commissions** : 1,82 $ aller-retour sur MNQ et MES.
- **Plateformes** : il y a trois brokers au choix à l'achat. Ce choix est définitif.
  - **Tradovate** donne accès à Tradovate, NinjaTrader et **TradingView** (« TradingView connects through Tradovate only »).
  - **Rithmic** donne accès à Tradesea, Quantower, Sierra Chart et R|Trader.
  - **WealthCharts** ne donne accès qu'à WealthCharts.
- **Éval** : il n'y a pas d'éval Advanced dans le Help Center actuel. Le contrat la cite encore.

**Growth 50k (145 $, reset 95 $) :**
- Éval :
  - Objectif 3 000 $ ; DLL 1 250 $ soft ; DD 2 000 $ EOD ; 4 minis / 40 micros.
  - **Pas de constance**, réussite possible en 1 jour.
- Financé :
  - DLL de 1 250 $, portée à 2 000 $ quand le solde atteint 53 000 $.
  - 4 / 40, sans palier.
  - **Constance 35 %** pour chaque payout.
- Payout :
  - 5 jours avec un gain supérieur à 150 $.
  - Solde minimal de 53 000 $ ; demande minimale de 500 $.
  - Plafonds de 1 500 / 2 000 / 2 500 / 3 000 $ (payouts 1, 2, 3 et 4 et suivants).
  - Partage 90/10.
- Contradiction relevée : la page *Pricing Reference* écrit « Growth… 35% consistency rule » sans préciser la phase, alors que la page Growth dit explicitement « pas de constance en éval ». On retient : 35 % en financé seulement.

**Select 50k (165 $ ; 205 $ avec l'option constance 50 % ; reset 109 / 135 $) :**
- Éval :
  - Objectif 3 000 $ ; DD 2 000 $ EOD ; **pas de DLL** ; 4 / 40.
  - **Constance 40 %**, donc 3 jours au minimum (2 jours avec l'option 50 %).
  - Le choix Flex ou Daily se fait à l'activation et il est définitif.
- **Select Flex** :
  - Pas de DLL et pas de constance.
  - Contrats : 2 au départ, 3 dès 1 500 $ de profit en clôture, 4 dès 2 000 $.
  - Payout tous les 5 jours gagnants (≥ 150 $), avec un profit net du cycle positif.
  - Montant retirable : 50 % du profit total, plafonné à **2 500 $** par demande pour un achat après le 01/09/2026 (3 000 $ avant). Demande minimale de 250 $ ; pas de solde minimal.
- **Select Daily** :
  - DLL de 1 000 $ ; mêmes paliers de contrats.
  - Tampon à 52 100 $ ; payout éligible chaque jour.
  - Montant : au plus 2 × le profit du cycle, plafonné à **1 250 $** (1 000 $ avant le 01/09/2026). Demande minimale de 250 $.

**Lightning 50k (financé direct, 492 $, sans reset) :**
- DLL de 1 250 $ (portée à 2 000 $ à 53 000 $) ; DD 2 000 $ EOD ; 4 / 40.
- Constance progressive : 20 % au payout 1, 25 % au payout 2, puis 30 %.
- Objectif de profit du cycle : 3 000 $ puis 2 000 $ ; pas de minimum de jours.
- Demande minimale de 1 000 $ ; plafonds de 2 000 / 2 000 / 2 000 / 2 500 $.

**Autres interdictions :**
- Hedging (§6.7, groupes de produits : NQ et ES sont dans le même groupe « Equity Index »), sanctionné même sans intention.
- Exploiter des erreurs de la plateforme.
- Utiliser un flux de données externe ou retardé (§6.3).
- Trader des contrats expirés ou hors contrat actif (§6.11).

### 3.3 Lucid Trading

Sources officielles, toutes consultées le 16/10/2026 :
- LucidFlex : [Evaluation](https://support.lucidtrading.com/en/articles/12945790-lucidflex-evaluation-account), [Funded](https://support.lucidtrading.com/en/articles/12945795-lucidflex-funded-account), [Payouts](https://support.lucidtrading.com/en/articles/12945796-lucidflex-payouts), [Consistency](https://support.lucidtrading.com/en/articles/12945805-lucidflex-consistency-percentage), [Scaling](https://support.lucidtrading.com/en/articles/12945808-lucidflex-scaling-plan), [Drawdown](https://support.lucidtrading.com/en/articles/12945815-lucidflex-drawdown), [Customization](https://support.lucidtrading.com/en/articles/16226050-lucidflex-customization)
- LucidPro : [Evaluation](https://support.lucidtrading.com/en/articles/12890029-lucidpro-evaluation-account), [Funded](https://support.lucidtrading.com/en/articles/12890069-lucidpro-funded-account), [Payouts](https://support.lucidtrading.com/en/articles/12890092-lucidpro-payouts), [DLL](https://support.lucidtrading.com/en/articles/12890122-lucidpro-daily-loss-limit), [Drawdown](https://support.lucidtrading.com/en/articles/12890136-lucidpro-drawdown)
- LucidDaily : [Evaluation](https://support.lucidtrading.com/en/articles/15996664-luciddaily-evaluation), [Funded](https://support.lucidtrading.com/en/articles/15997244-luciddaily-funded-account), [Payouts](https://support.lucidtrading.com/en/articles/15997266-luciddaily-payouts), [Customization](https://support.lucidtrading.com/en/articles/16033858-luciddaily-customization)
- LucidDirect : [Funded](https://support.lucidtrading.com/en/articles/12890148-luciddirect-funded-account), [Payouts](https://support.lucidtrading.com/en/articles/12890164-luciddirect-payout-objectives)
- Règles générales : [Allowed Trading Times](https://support.lucidtrading.com/en/articles/11404729-allowed-trading-times), [Hedging](https://support.lucidtrading.com/en/articles/11404734-prohibited-hedging), [Platforms](https://support.lucidtrading.com/en/articles/11404614-lucid-trading-supported-platforms), [Account limits](https://support.lucidtrading.com/en/articles/11404617-maximum-number-of-accounts), [Inactivity](https://support.lucidtrading.com/en/articles/11404632-inactivity-policy)

**Règles communes :**
- **Drawdown (MLL)** : EOD trailing, qui se fige à **50 100 $** dès que le solde de clôture dépasse 52 100 $. Ce blocage vaut aussi **en éval**, ce qui est propre à Lucid.
- **DLL** : toutes sont soft (« you do not lose your account for hitting DLL »). Chez Flex, Pro et Daily, la DLL est une **option choisie à l'achat** : elle est soit active dans les deux phases, soit absente des deux. La version avec DLL est moins chère.
- **Clôture** : à **16:45 ET (15:45 CT)**. Les positions sont fermées d'office, sans échec du compte.
- **News** : permises sur Flex, Pro et Direct. **Interdites sur LucidDaily** (« Trading red folder news on the LucidDaily is a hard breach » : il faut être à plat de 1 min avant à 1 min après chaque annonce USD à fort impact).
- **Activité** : un compte sans trade pendant 30 jours est supprimé.
- **Comptes** : 5 comptes financés et 10 comptes au total par foyer.
- **Partage** : 90/10.
- **Pas d'activation** ni de limite de temps pour l'éval.
- **Plateformes** :
  - **CQG** : NinjaTrader, Tradovate, **TradingView**.
  - **Rithmic** : Quantower, Tradesea, MotiveWave, Sierra Chart, Jigsaw, Bookmap, ATAS, R|Trader Pro, MultiCharts.

**LucidFlex 50k :**
- Éval :
  - Objectif 3 000 $ ; MLL 2 000 $ ; 4 / 40.
  - **Constance 50 %**, avec une petite marge : réussite possible en 2 jours.
  - DLL optionnelle. Son montant n'est pas affiché sur les pages officielles ; 1 200 $ d'après une source secondaire ⚠.
- Financé :
  - Pas de constance et pas de tampon.
  - Contrats : 2, puis 3 dès 1 000 $ de profit, puis 4 dès 2 000 $ (mis à jour à la clôture, en baisse aussi après un payout).
- Payout :
  - 5 jours au-dessus de 150 $, avec un profit net du cycle positif.
  - Montant : 50 % du profit, plafonné à **2 000 $**. Ce plafond ne monte pas avec les payouts. Demande minimale de 500 $.
  - **5 payouts**, puis examen pour passer en Live.

**LucidPro 50k :**
- Éval :
  - Objectif 3 000 $ ; MLL 2 000 $ ; DLL 1 200 $ si l'option est prise ; 4 / 40.
  - **Pas de constance**, réussite possible en 1 jour.
- Financé :
  - DLL de 1 200 $, puis « LucidScale » (60 % du plus haut profit de clôture) après une clôture au-dessus de 52 100 $.
  - 4 / 40 sans palier.
  - **Constance 40 %** par cycle.
- Payout :
  - Profit du cycle d'au moins 500 $ ; tampon de 52 100 $.
  - Plafonds de 2 000 $ au payout 1, puis 2 500 $. Demande minimale de 500 $ ; 5 payouts.

**LucidDaily 50k :**
- Quatre configurations possibles (DLL oui ou non × drawdown d'éval EOD ou intraday).
- Éval :
  - Objectif 3 000 $ ; constance 50 %.
- Financé :
  - **Toujours en drawdown intraday**, figé à 50 100 $.
  - DLL de 1 200 $ si l'option est prise ; pas de constance.
- Payout :
  - Chaque jour, pour tout le profit au-dessus de 52 100 $. Demande minimale de 500 $.
  - Un jour à 8 000 $ de gain fait passer le compte en Live.
- **News USD à fort impact interdites** (hard breach).

**LucidDirect 50k (financé direct, environ 515 $ ⚠) :**
- MLL 2 000 $ EOD ; DLL de 1 200 $ puis 60 % du pic ; 4 / 40.
- **Constance 20 %**.
- Objectif de profit du cycle : 3 000 $ puis 2 500 $.
- Plafonds de 2 000 $ (payouts 1 à 3), puis 2 500 $ (payouts 4 et 5).

**LucidMaxx :** sur invitation seulement. Non inclus.

**Prix ⚠ :** le site marchand est en 403.
- Sources secondaires (sept.-oct. 2026) : Flex 146 $, Pro 192 $ (ou 185 $), Daily « dès 156 $ », Direct 515 $ (ou 520 $).
- La configuration correspondant à ces prix n'est pas précisée.

---

## 4. Compatibilité bot — recommandation

**Apex est éliminé.** Le texte interdit explicitement tout ce que nous voulons faire : algorithmes, ordres auto-exécutés, webhook, « set-and-forget ». La sanction est la confiscation des gains. Aucune variante Apex ne doit être retenue, quel que soit le résultat du Monte-Carlo. Les tables Apex restent dans le TOML pour comparaison seulement.

**Recommandation : Tradeify Select 50k → Select Flex** (165 $, sans activation).

Pourquoi :
1. **C'est la seule autorisation écrite et contractuelle de bots**, dans un contrat daté d'octobre 2026, avec des conditions que nous remplissons naturellement : bot à nous, pas de HFT, trades MNQ/MES de plusieurs minutes, donc bien au-delà de la règle des 10 s.
2. **Pas de DLL**, ni en éval ni en Flex. Pour un bot, une DLL « soft » mal synchronisée peut couper un trade au pire moment. Il ne reste qu'une seule limite à coder : le plancher EOD.
3. **Pas de constance en financé** et pas de solde minimal pour demander un payout. Il suffit de 5 jours gagnants de 150 $ ou plus.
4. Drawdown EOD (et non intraday) : les gains latents d'un trade ne relèvent pas le plancher.
5. TradingView est branché via un compte Tradovate. Il faut donc **choisir Tradovate à l'achat**.

Ce qui coûte :
- En éval, la constance de 40 % impose au moins 3 jours et pénalise un gros jour isolé. L'option à 50 % (205 $) ramène le minimum à 2 jours.
- Le financé démarre à 2 contrats et monte à 4 à partir de 2 000 $ de profit.
- Le plafond est de 2 500 $ par payout, et limité à 50 % du profit.

**Alternative à simuler : Tradeify Growth 50k** (145 $). L'éval est réussie dès le 1er jour, sans constance. Mais il y a une DLL soft de 1 250 $ et une constance de 35 % en financé. Le Monte-Carlo doit trancher entre Growth et Select Flex.

**Plan B : LucidFlex ou LucidPro**, si et seulement si Lucid confirme **par écrit** que notre bot et la passerelle webhook sont acceptés.
- LucidPro : éval sans constance, mais constance de 40 % en financé.
- LucidFlex : constance de 50 % en éval, aucune en financé, plafond de 2 000 $.
- Avantage commun : le plancher est figé à 50 100 $ dès l'éval.
- À éviter pour un bot : **LucidDaily**. Le financé est en drawdown intraday et une seule annonce USD tenue en position fait perdre le compte.

**Contraintes à transmettre au simulateur et à l'agent exécution :**
- **Un seul hébergeur pour le bot.** La clause d'exclusivité de Tradeify interdit de faire tourner le même bot chez Lucid en parallèle.
- **Clôture forcée** avant 15:45 CT, avec une marge. Apex demanderait 15:59 CT, mais Apex est exclu.
- Plancher appliqué en temps réel sur la valeur liquidative, positions latentes comprises.
- Garder le journal de propriété du code (dépôt git) pour la preuve demandée par Tradeify, et être prêt à filmer le lancement du bot sur notre PC.
- TradingView n'exécute pas seul des alertes vers Tradovate : il faut une passerelle webhook. Tradeify exige que « le bot ou la stratégie » nous appartienne ; une passerelle qui transmet nos propres signaux semble conforme, mais **une confirmation par ticket au support est conseillée**. Chez Lucid, la clause « third party software » rend cette confirmation indispensable.
