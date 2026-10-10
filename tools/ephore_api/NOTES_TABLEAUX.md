# Les 3 tableaux manquants — percée du 10/10/2026

Prospection des sources publiques du terminal web d'Ephore (24 requêtes, budget respecté).
Sources sur disque dans `web/`. **Tout ce qui suit est vérifié**, les citations sont verbatim.

## 1. LA TROUVAILLE : le Feu de Confluence décompose exactement nos tableaux

`web/trading_demo.html:36202-36208`, verbatim :

```js
const GROUPES_FEU = {
temps: "Colonne temps (6 voix)",
supertrader: "Bloc SuperTrader (10 voix)",
signal: "Colonne SIGNAL (7 voix)",
tendance: "Tendances multi-unites (6 voix)",
college: "Collège du feu"
};
```

6 + 10 + 7 + 6 = **29**, exactement les « 29 votes » de `d['feux']` dans l'API.

| groupe | voix | = notre tableau |
|---|---:|---|
| Colonne temps | 6 | **Dashator** (1m, 5m, 15m, 1H, 4H, 1D) |
| Bloc SuperTrader | 10 | tableau principal — **déjà validé** (source Midgar) |
| Colonne SIGNAL | 7 | **INDICATOR \| SIGNAL** |
| Tendances multi-unités | 6 | **TIMEFRAME \| TREND \| STRENGTH** |

**Conséquence méthodologique :** `feux.votes` de l'API devient une **cible numérique** pour nos
répliques. Pour une bougie donnée, nos 4 tableaux doivent produire le même décompte
long/short/neutre et la même part arrondie à 0,1 %. C'est une contrainte forte et gratuite.
Le détail voix par voix est volontairement masqué (`trading_demo.html:19430-19432`,
« réservé au cockpit de recherche »), mais les agrégats suffisent à valider.

## 2. Contenu des tableaux, lu sur capture

`web/screen_t437_chart.png` — MNQ1!, panneaux 15 min et 2 min côte à côte,
horodaté « Juin 06, 2026 01:50 **UTC+8** ».
`web/screen_t429_entree.jpeg` — MNQ1! 2 min, Replay « mar. 09 Juin '26 18:48 ».

### INDICATOR | SIGNAL — 7 lignes
| ligne | valeur 15m | valeur 2m | vocabulaire d'état déduit |
|---|---|---|---|
| SuperTrend | ● Bear | ● Bear | Bull / Bear |
| Moving Avg | ● Bear | ● Bear | Bull / Bear |
| VWAP | ● Bear | ● Bear | Bull / Bear |
| **Lin Regress** | ● **Bull** (bleu) | ● **Bear** (rouge) | Bull / Bear |
| CPR | ● Below BC | ● Below BC | Above TC / Inside / Below BC |
| ORB 15min | ● In Range (orange) | ● In Range | Above / In Range / Below |
| PDH/PDL | ● Below PDL | ● Below PDL | Above PDH / Inside / Below PDL |

> **CORRECTION IMPORTANTE.** Le rapport d'agent concluait « identique sur les deux unités de
> temps, donc calculé hors unité de temps du graphique ». **C'est faux** : `Lin Regress` vaut
> Bull en 15 min et Bear en 2 min sur la **même** capture. Les 6 autres lignes coïncident par
> hasard. Le tableau est donc bien **calculé sur l'unité de temps du graphique**, comme le
> tableau principal (dont le RSI passe de 12.47 en 15 min à 44.24 en 2 min, et le CCI de
> −119.59 à −23.98 sur cette même capture). **Il faut donc caler ce tableau par unité de temps.**

Vote : `+1 si Bull/Above`, `−1 si Bear/Below`, `0 si In Range/Inside` → 7 voix.
Les 7 lignes sont des indicateurs publics standards. Ordre de calage conseillé : d'abord les
3 **déterministes et sans paramètre libre** (CPR, ORB 15min, PDH/PDL), puis balayage des
périodes de SuperTrend / Moving Avg / Lin Regress.

### TIMEFRAME | TREND | STRENGTH — 6 lignes : 3, 5, 15, 60, 240, 1D
Identique sur les deux panneaux de la capture → **réellement multi-TF**, indépendant du graphique.

| unité | t437 (06/06) | t429 (09/06) |
|---|---|---|
| 3 | BEARISH 25 % | BEARISH **75 %** |
| 5 | BEARISH 25 % | BEARISH 50 % |
| 15 | BEARISH 0 % | BEARISH 0 % |
| 60 | BEARISH 0 % | BEARISH 0 % |
| 240 | BEARISH 0 % | BEARISH 50 % |
| 1D | **BULLISH** 50 % | **BULLISH** 50 % |

- Échelle de couleur du STRENGTH : 0 % et 25 % rouge, 50 % orange, 75 % **bleu**.
- **Paliers de 25 %** confirmés (0, 25, 50, 75 observés ; 100 cité sur le forum)
  → **hypothèse forte : 4 sous-tests booléens par unité de temps.**
- **TREND et STRENGTH sont indépendants** : 3 min BEARISH avec STRENGTH 75 % bleu.

Doctrine de l'auteur, forum sujet 429 post #18, verbatim :
> « la pression acheteuse montait en 3 minutes malgré un TREND bearish […] ne donne pas trop de
> pouvoir au pourcentage de STRENGTH. **Le Climator se lit avec les yeux, pas avec une
> calculatrice.** […] Le strenght % n'est pas un signal en soi »

Sujet 437 post #4 :
> « Quand tu es short et que **la colonne STRENGTH des acheteurs se met à monter et vire au bleu
> alors que le TREND est encore rouge**, c'est exactement ça : la jambe baissière s'essouffle »

### Dashator — colonne verticale, 6 cases
Icône horloge en tête, cases `1m / 5m / 15m / 1H / 4H / 1D`, chacune bleue ou rouge, éclair en pied.
- t437 : **les 6 rouges**, alors que TIMEFRAME donne 1D = BULLISH.
- t429 : 5m **bleue**, 15m/1H/4H/1D rouges, alors que TIMEFRAME donne 5 = BEARISH.

→ **Preuve chiffrée que le Dashator suit une logique différente du tableau TIMEFRAME.**
La contrainte « 1D rouge pendant que TREND 1D = bullish » élimine toute règle de tendance longue
classique : c'est probablement un état court terme (clôture vs EMA rapide, ou l'état Heishinator
de l'unité).

## 3. Ce qui est DÉFINITIVEMENT hors d'atteinte côté web

`trading_demo.html:17514`, verbatim :
> « **Les couches sont calculées sur le serveur et dessinées sur le graphique.** »

Le cockpit est un pur moteur de rendu (lightweight-charts). Il ne contient **aucune formule** :
pas une EMA, pas un ATR, pas un ADX. Les 3 modules JS (`demo_membres.js`, `flux_service.js`,
`i18n_cockpit.js`) sont de la plomberie — simulateur d'ordres, WebSocket, libellés.

Routes fermées (ne pas réessayer, réponses conservées dans `web/`) :
`/api/vitrine/checklist` **401**, `/api/cours/<slug>` **401** (y compris glossaire et annexe-1),
`/api/feu` **404**, `/api/strategies` **404**. Le flux WebSocket ne transporte que des objets
déjà dessinés : même pauvreté que `/api/vitrine/instantane`.

## 4. TBT : la piste est morte côté web — et c'est une information

**0 occurrence** de « TBT » dans les 2,4 Mo de sources, dans les 3 modules JS, dans l'API locale,
et **0 post** sur le forum public. « Seuil de Force » est également introuvable. Le terme
n'existe que dans **nos propres fichiers**.

→ Soit c'est un libellé interne du script TradingView jamais commenté publiquement, soit il a
été mal lu sur le screen d'origine. **Ne plus investir côté web.** La seule voie reste un screen
du tableau Signator de l'original — que le mur des victoires peut probablement fournir (§5).

## 5. Vocabulaire Ephore remis d'aplomb

- **Climator** = le nom du **module d'affichage**, pas seulement des tables.
  `trading_demo.html:26529` → `"Ephore Market Climator v10"`. Glossaire du cockpit (`:17524`) :
  « **Le Climator : la couleur des bougies.** Il donne le climat de la période, le biais dans
  lequel se lit le reste. » Et `:42665` → `p08: ["tables du Climator", …]`.
  → **Les 3 tableaux manquants appartiennent au Climator, pas au Signator.**
- **Detector** : `det_bull_#` / `det_bear_#`, 5 boîtes par unité, clé **`grise`** dans le JSON.
  FAQ `racine.html:6004` : « Mon Detector est passé en gris : je peux encore viser cette zone ? »
  → zone consommée = grisée. Cohérent avec les « zones atténuées » d'EPHORE_METHODE.md.
- **Rangeator** : `rng_boite_#`, clés `ligne`, `ligne_pointille`, `ligne_t1`. Trois états :
  haussier / baissier / **gris**. Elio, sujet 437 : « le Rangeator gris sur le 2 minutes […] le
  gris te disait : à cette échelle, le marché digérait […] Dans une vraie jambe baissière saine
  tu veux voir **l'escalier rouge qui descend marche après marche**, pas une boîte grise ».
- **Fibonator** = `fib_75` / `fib_zone` (le niveau retenu par la méthode est **75 %**).
  **Rondator** = `rnl_#` / `rnq_#` (niveaux ronds). **Pivator** = `piv_setN_*`.
- **Breakator** : **0 occurrence** partout, web et forum. Ce nom n'existe probablement pas chez
  Ephore — à retirer de nos listes de modules.

## 6. LA SOURCE DE DONNÉES QUI MANQUAIT DEPUIS LE DÉBUT

`MEMOIRE_PROJET.md` §4.3 dit : « les tableaux ne s'exportent pas, il faut des screens horodatés ».
Il n'y avait **aucune capture sur le disque**. Le forum public en contient des centaines.

- Catégorie `le-mur-des-victoires` (id 13), annoncée à ~490 sujets, **publique, sans compte**.
- Liste : `https://forum.ephore-market.com/c/le-mur-des-victoires/13.json?page=N`
- Sujet : `https://forum.ephore-market.com/t/<id>.json` → le champ `cooked` contient les URL
  `https://app.ephore-market.com/fichiers-forum/original/1X/<sha1>.<ext>`
  (vérifié : **200 sans cookie**, 2 images déjà récupérées).
- **Bonus décisif** : beaucoup de posts sont publiés automatiquement depuis la check-list du
  cockpit et contiennent un texte structuré du type « En 15 min : … climator bleu et **feu à
  82 % long** / En 2 min : … ». C'est **la valeur du Feu de Confluence à un instant daté** —
  donc une cible numérique directe pour calibrer les 29 voix (cf. §1).

→ Avec ~30 captures lisibles, on obtient une table de calibration TREND / STRENGTH / Dashator /
SIGNAL sur plusieurs dates et deux instruments, **sans demander un seul screen à Jeremy**.
L'agent `tableau-screen-reader` devient immédiatement utilisable avec cette source.

**Piège à ne pas rater** : la capture t437 est horodatée en **UTC+8**, pas en heure de Paris.
Chaque screen du forum peut avoir son propre fuseau selon l'auteur. Relever le fuseau affiché
avant toute jointure avec un CSV (qui, lui, est en heure de Paris — §8).
