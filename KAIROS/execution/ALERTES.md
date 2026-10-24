# Format des alertes — voie n° 1 : TradingView → PickMyTrade → Tradovate

*Agent « Exécution du bot », 16/10/2026. À destination de l'intégrateur de la V7.*
*Syntaxe Pine v6 vérifiée : signatures via `pine_reference` (strategy.entry / exit / close / close_all, alert) et module de test compilé sans erreur par le vérificateur de syntaxe TradingView (`mcp__pinescript-syntax-checker`).*

---

## 1. Principe : une seule alerte, deux sources de messages

| Événement | Mécanisme Pine | Message envoyé |
|---|---|---|
| Entrée (remplissage simulé à l'ouverture qui suit le signal) | `strategy.entry(..., alert_message = f_msg_entree(...))` | **ENTRÉE** : ordre au marché + bracket stop/objectif |
| Stop ou objectif atteint dans le testeur | `strategy.exit(..., alert_message = f_msg_flat())` | **FLAT** (`close`) : sans effet si Tradovate a déjà fermé (le bracket natif a agi), sinon remet le compte d'accord avec la stratégie |
| Objectif 1 d'une sortie partielle | `strategy.exit("XL1"…, disable_alert = true)` | rien (c'est Tradovate qui gère la jambe 1) |
| Stop déplacé à la clôture (break-even, suiveur) | `alert(f_msg_stop(...), alert.freq_once_per_bar_close)` | **DÉPLACEMENT DE STOP** (`update_sl`) |
| Fin de séance / Stop dépassé / Signal opposé | `strategy.close_all(...)` ou `strategy.close(...)` avec `alert_message = f_msg_flat()` | **FLAT** (`close`) : clôture + annulation des ordres restants |

**Règle impérative** (doc Pine, *Alerts*) : si **un seul** appel `strategy.*()` n'a pas d'`alert_message`, son remplissage enverra un message **vide** (« an empty string will replace the placeholder »). Donc **chaque** `strategy.entry / exit / close / close_all` de la V7 reçoit soit `alert_message=...`, soit `disable_alert=true`.

**Réglage de l'alerte dans TradingView (une seule) :**
- Condition : « Stratégie V7 » → **Order fills and alert() function calls**
- Message : `{{strategy.order.alert_message}}` (rien d'autre : c'est déjà du JSON complet)
- Notifications : cocher **Webhook URL** → URL fournie par PickMyTrade
- Les appels `alert()` envoient leur propre message ; le champ Message ne sert qu'aux remplissages d'ordres.

**Placeholders :** on n'utilise que `{{strategy.order.alert_message}}`. Toutes les valeurs (prix, quantité, heure) sont **calculées dans le Pine** avec `str.tostring` / `str.format_time`, parce que le message d'un `alert()` est une chaîne Pine ordinaire. Les autres placeholders existent mais ne servent pas ici : `{{strategy.order.action}}` (buy/sell), `{{strategy.order.contracts}}`, `{{strategy.market_position}}` (long/short/flat), `{{timenow}}`, `{{close}}`, `{{ticker}}`.

---

## 2. Les 4 messages JSON (exemple MNQ, long 2 contrats)

Champs PickMyTrade utilisés (d'après les articles PickMyTrade cités dans `VOIE_BOT.md` — la doc officielle complète du schéma n'est **pas publiée**, PickMyTrade conseille de générer le JSON depuis son interface : **comparer avec le JSON généré par l'interface PickMyTrade avant la mise en service**) :
- `data` : `buy` / `sell` (ordre), `close` (« never opens a position », clôture et annule les ordres ouverts).
- `dollar_sl`, `dollar_tp` : **distance en points de prix** depuis le remplissage, pas des dollars (« "dollar" fields measure price distance, not currency »).
- `update_sl` / `update_tp` : `true` → pas de nouvel ordre ; remplace le stop / l'objectif de la position ouverte par le **prix exact** de `sl` / `tp` (« Only sl and tp count, and both take literal price levels »).
- `same_direction_ignore: true` + `pyramid: false` : ignore une 2e entrée dans le même sens (anti-doublon).
- `reverse_order_close: false` : un signal opposé ne retourne pas la position (la stratégie ferme d'abord, puis rentre plus tard).

### 2.1 ENTRÉE avec stop et objectif attachés
```json
{"symbol":"MNQ1!","date":"2026-10-16T14:35:00Z","data":"buy","quantity":2,"price":20125.25,"order_type":"MKT",
 "risk_percentage":0,"dollar_sl":18.5,"dollar_tp":37,"percentage_sl":0,"percentage_tp":0,"sl":0,"tp":0,
 "trail":0,"update_sl":false,"update_tp":false,"pyramid":false,"same_direction_ignore":true,"reverse_order_close":false,
 "token":"VOTRE_TOKEN","account_id":"VOTRE_COMPTE"}
```
- Short : `"data":"sell"`.
- Le champ `sl` à l'entrée n'est pas utilisé : les sources PickMyTrade se contredisent sur son unité (prix ou ticks). La distance `dollar_sl` est sans ambiguïté ; le stop exact est reposé en prix absolu à la clôture suivante (2.2).

### 2.2 DÉPLACEMENT DE STOP (et d'objectif) — break-even, stop suiveur
```json
{"symbol":"MNQ1!","date":"2026-10-16T14:40:00Z","data":"buy","quantity":2,"price":20140.00,"order_type":"MKT",
 "risk_percentage":0,"dollar_sl":0,"dollar_tp":0,"percentage_sl":0,"percentage_tp":0,
 "sl":20118.75,"tp":20162.25,"update_sl":true,"update_tp":true,
 "token":"VOTRE_TOKEN","account_id":"VOTRE_COMPTE"}
```
- `data` = sens de la position (`buy` si long, `sell` si short). Avec `update_sl:true`, aucun nouvel ordre n'est passé.
- Sans objectif : `"tp":0,"update_tp":false`.
- Attention (PickMyTrade) : la mise à jour vaut pour **toutes** les positions du symbole sur ce compte, et **supprime un stop suiveur natif** s'il y en avait un. On n'utilise donc pas le `trail` natif : c'est le Pine qui calcule le suiveur.

### 2.3 SORTIE (signal opposé, stop dépassé, synchro après bracket)
```json
{"symbol":"MNQ1!","date":"2026-10-16T15:05:00Z","data":"close","quantity":0,"price":20151.50,"order_type":"MKT",
 "token":"VOTRE_TOKEN","account_id":"VOTRE_COMPTE"}
```

### 2.4 FLAT DE FIN DE JOURNÉE
Même message que 2.3 (`"data":"close"`), envoyé par le `strategy.close_all(comment="Fin de séance", ...)`.
Régler l'heure « Fin de séance » de la V7 **avant 16 h 40 ET** (Lucid liquide à 16 h 45 ET ; Tradeify 16 h 59 ET).
⚠️ Dans la V1, cette heure est saisie **en heure de Paris** (`fin_apres` utilise `f_minParis`, l. 1415) et l'option est **désactivée par défaut** (`x_finOn` = false, l. 414) : la **cocher** en V7. 16 h 40 ET = 22 h 40 Paris la plupart de l'année, mais **21 h 40 Paris** pendant les semaines où l'Europe et les États-Unis n'ont pas encore changé d'heure en même temps (fin mars ; du 25/10 au 01/11/2026). Le plus sûr : passer ce réglage en heure de New York en V7.

### 2.5 Sortie partielle (2 objectifs) — À VALIDER EN DÉMO AVANT USAGE
PickMyTrade documente un tableau `advance_tp_sl` (jusqu'à 3 blocs, chacun avec `quantity`, `dollar_tp`, `dollar_sl`, `breakeven`, `trail`). Comportement de `update_sl` avec plusieurs blocs : **non trouvé**. **Recommandation : V7 en direct sans sortie partielle (`x_part = false`)** tant que ce cas n'a pas été testé sur compte démo.

---

## 3. Code Pine v6 à intégrer en V7

### 3.1 Réglages et constructeurs de messages (en haut du script, après les inputs)
```pine
// ── Webhook PickMyTrade ──
string grpW  = "Webhook PickMyTrade"
bool   w_on  = input.bool(false, "Envoyer les ordres au courtier", group=grpW)
string w_sym = input.string("MNQ1!", "Symbole PickMyTrade", group=grpW)
string w_tok = input.string("", "Token PickMyTrade", group=grpW)
string w_acc = input.string("", "ID de compte", group=grpW)

f_px(float p) => str.tostring(p, format.mintick)
f_head(string data, int q) =>
    '{"symbol":"' + w_sym + '","date":"' + str.format_time(timenow, "yyyy-MM-dd'T'HH:mm:ss'Z'", "UTC") + '","data":"' + data + '","quantity":' + str.tostring(q) + ',"price":' + f_px(close) + ',"order_type":"MKT"'
f_tail() =>
    ',"token":"' + w_tok + '","account_id":"' + w_acc + '"}'
f_msg_entree(int d, int q, float distSL, float distTP) =>
    f_head(d > 0 ? "buy" : "sell", q) + ',"risk_percentage":0,"dollar_sl":' + f_px(distSL) + ',"dollar_tp":' + (na(distTP) ? "0" : f_px(distTP)) + ',"percentage_sl":0,"percentage_tp":0,"sl":0,"tp":0,"trail":0,"update_sl":false,"update_tp":false,"pyramid":false,"same_direction_ignore":true,"reverse_order_close":false' + f_tail()
f_msg_stop(int d, int q, float sl, float tp) =>
    f_head(d > 0 ? "buy" : "sell", q) + ',"risk_percentage":0,"dollar_sl":0,"dollar_tp":0,"percentage_sl":0,"percentage_tp":0,"sl":' + f_px(sl) + ',"tp":' + (na(tp) ? "0" : f_px(tp)) + ',"update_sl":true,"update_tp":' + (na(tp) ? "false" : "true") + f_tail()
f_msg_flat() =>
    f_head("close", 0) + f_tail()

var float w_slEnv = na   // dernier stop envoyé au courtier
var float w_tpEnv = na   // dernier objectif envoyé
```
Note : `close` dans `f_head` est le cours de la bougie du **graphique** (Heiken Ashi) ; il n'est qu'informatif pour PickMyTrade (ordre au marché). Pour un prix réel, passer `r_c` à la place.

### 3.2 Branchement sur le code de `STRATEGIE_V1.pine`

**Sorties au marché (l. 1712-1723)** — ajouter à chaque appel :
```pine
strategy.close_all(comment="Stop dépassé", alert_message=f_msg_flat(), disable_alert=not w_on)
strategy.close_all(comment="Fin de séance", alert_message=f_msg_flat(), disable_alert=not w_on)
strategy.close("L", comment="Signal opposé", alert_message=f_msg_flat(), disable_alert=not w_on)
strategy.close("S", comment="Signal opposé", alert_message=f_msg_flat(), disable_alert=not w_on)
```

**Entrées (l. 1796-1799)** — `dist` et `tp0` sont déjà calculés juste au-dessus :
```pine
float w_dTP = na(tp0) ? na : math.abs(tp0 - e0)
if d > 0
    strategy.entry("L", strategy.long, qty=q, comment="L " + str.tostring(q), alert_message=f_msg_entree(1, q, dist, w_dTP), disable_alert=not w_on)
else
    strategy.entry("S", strategy.short, qty=q, comment="S " + str.tostring(q), alert_message=f_msg_entree(-1, q, dist, w_dTP), disable_alert=not w_on)
w_slEnv := na
w_tpEnv := na
```

**Brackets (l. 1817-1821)** :
```pine
if tr_part
    if not tr_p1
        strategy.exit(lg ? "XL1" : "XS1", fe, qty=tr_q1, stop=ex_stop, loss=ex_loss, limit=ex_tp1, profit=ex_prof, comment_loss=cl, comment_profit=cp + "1", disable_alert=true)
    strategy.exit(lg ? "XL2" : "XS2", fe, qty=tr_q - tr_q1, stop=ex_stop, loss=ex_loss, limit=tr_tp2, comment_loss=cl, comment_profit=cp + "2", alert_message=f_msg_flat(), disable_alert=not w_on)
else
    strategy.exit(lg ? "XL" : "XS", fe, stop=ex_stop, loss=ex_loss, limit=ex_tp1, profit=ex_prof, comment_loss=cl, comment_profit=cp, alert_message=f_msg_flat(), disable_alert=not w_on)
```
⚠️ Avec `XL1` muet, si le **stop** de la jambe 1 est touché, c'est la jambe 2 (même stop) qui enverra le `close` : cohérent. À valider en démo (cf. 2.5).

**Déplacement du stop (juste après le bloc ci-dessus, section 5)** :
```pine
if w_on and strategy.position_size != 0 and tr_dir != 0 and not sortie_marq
    float w_sl = math.round_to_mintick(tr_stop)
    float w_tp = na(tr_tp) ? na : math.round_to_mintick(tr_tp)
    if na(w_slEnv) or w_sl != w_slEnv or (not na(w_tp) and w_tp != w_tpEnv)
        alert(f_msg_stop(tr_dir, int(math.abs(strategy.position_size)), w_sl, w_tp), alert.freq_once_per_bar_close)
        w_slEnv := w_sl
        w_tpEnv := w_tp
```
- 1re clôture en position : `w_slEnv` est `na` → envoi du stop et de l'objectif **en prix absolus** (remplace le bracket « en distance » posé à l'entrée, exactement comme le fait déjà le Pine : ticks sur la bougie de remplissage, prix absolus ensuite).
- Ensuite : un message **seulement si le stop (ou l'objectif) a bougé** → 1 message par bougie au maximum, loin de la limite TradingView de 15 alertes / 3 min.
- `sortie_marq` (l. 1714-1723) évite de déplacer un stop sur une bougie où la sortie au marché est déjà demandée.
- Vérifier le nom réel de la variable de sortie partielle en V7 : après TP1, `strategy.position_size` = reste ; la quantité du message est informative (PickMyTrade met à jour par symbole/compte).

### 3.3 Points à vérifier par l'intégrateur
1. **Aucun** appel `strategy.*()` sans `alert_message` ou `disable_alert` (sinon message vide).
2. `w_on = false` par défaut → le backtest et les tests visuels n'envoient rien.
3. Le token est dans les réglages du script : **ne jamais publier** la V7 avec un token saisi.
4. Passer le Pine final au vérificateur de syntaxe et à `pine-v6-linter`.
5. Après toute modification du script : **supprimer et recréer l'alerte**.

---

## 4. Plan B (CrossTrade, Tradovate direct) — pour mémoire
Même architecture Pine ; seul le texte des messages change (format `clé=valeur;`, ex. `command=PLACE; action=...; qty=...;`, brackets via modèles ATM Tradovate, modification d'ordre et `flatten` disponibles). Syntaxe exacte des commandes CHANGE / FLATTEN : **non vérifiée en détail** — à reprendre dans https://crosstrade.io/docs si on bascule.
