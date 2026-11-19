# Relevé complet — format et procédure

Stratégie de mesure `KAIROS/dataset/RELEVE_COMPLET.pine` (19/11/2026). Elle n'envoie aucun ordre réel et aucune alerte.
Elle couvre **toutes les bougies**, regroupées en trades fictifs d'1 contrat. Chaque trade correspond à un bloc de
bougies consécutives, et son **commentaire de sortie** contient une fiche par bougie.

## Origine du code (inventaire)

| Module | Version de référence | Dans le relevé |
|---|---|---|
| Heishinator | CompletV3 (formule exacte V4, 2600/2600 API), via Strat5669_PLUS | oui |
| Moyenator (EMA 50 / 60) | CompletV3 V5, via PLUS | oui |
| Signator V9 (Fort / Moyen, score, ADX) | CompletV3, via PLUS | oui |
| Trendlines V2 + cassures (Breakator) | CompletV3, via PLUS | oui |
| Detector (order blocks) | CompletV3, via PLUS | oui (blocage + distances) |
| Climax | CLIMATOR.pine V1, via PLUS | oui |
| Pivator V3 (annuel / mensuel / weekly) | CompletV3, via PLUS | oui (distance au pivot P) |
| Niveaux : sessions Asie / Londres / US, Monday high-low | CompletV3, via PLUS | oui (cassures) |
| TREND / Dashator 6 unités, Feu (10 voix), STRENGTH / MACD 10 min | CompletV3 (« 3 tableaux manquants + Feu »), via PLUS | oui |
| Biais fond / intraday (bi_F, bi_I) | PLUS | oui |
| Directionnor | DIRECTIONNOR.pine | oui, lecture des unités supérieures corrigée (voir plus bas) |
| Fibonator | FIBONACCI_AUTO.pine V3 | oui (détection du swing) |
| Rangeator | **introuvable** dans les .pine du dépôt | non |
| VIX / volumes du tableau | TABLEAU.pine, CompletV3 | **non** : lus en lookahead_on sans [1] (fuite) |
| LIN REGRESS du tableau | CompletV3 | non (seulement à travers bi_I) |

PORSCHEONARRIVE.pine (V8) contient Heishinator V4, Moyenator V5, Pivator V3, Trendlines V2 et le tableau : ce sont
les mêmes modules que CompletV3, qui est plus récent. Aucun fichier existant n'a été modifié.

## Sans fuite

- **Toutes les lectures multi-unités** (TREND, Dashator, Feu, STRENGTH, MACD, filtres de la stratégie) sont faites en
  « dernière bougie terminée ». Le réglage muClos est forcé dans le code : on lit [1], ou [0] seulement quand la
  bougie du graphique ferme la bougie supérieure.
- **`b1` / `b4`** : la bougie 1 h / 4 h en cours, reconstituée avec les bougies du graphique, comme en direct.
- **La lecture d'origine** (valeur finale de la bougie en cours) n'est jamais écrite dans le relevé.
- **Pivots** (Pivator : période précédente ; trendlines, Detector, Fibonator, Directionnor : pivots confirmés après
  N bougies). Chaque valeur est celle connue à la bougie, jamais une valeur redessinée ensuite.
- **MACD 10 min** (bit 31, et une voix du Feu) : 10 min ne divise pas 15 min. Aux bougies qui finissent à :15 et
  :45, la dernière bougie 10 min n'est pas finie : on lit la précédente. La Strat5669_PLUS lit la bougie non
  finie (fuite de 5 min), mais sans effet sur le 56, où le Feu n'est pas utilisé.
- **Unité inférieure qui ne divise pas le graphique** (règle générale depuis le 19/11, pour le 5 min) : TREND 3 min sur
  un graphique 5 min. Quand la bougie du graphique ne ferme pas sur une frontière de 3 min, on lit la bougie 3 min
  précédente. En 15 min et en 1 h, seules les unités qui divisent le graphique sont concernées (sauf le MACD 10 min
  en 15 min, déjà traité) : les relevés 15 min déjà exportés ne changent pas.
- **Directionnor.** L'original lit le 4 h et le 1 h en lookahead_off. C'est juste en historique, mais en direct il
  voit la bougie en formation. Ici, la lecture suit la même règle que muClos.

## Format du commentaire de sortie

`t=<ouverture de la 1re bougie, secondes Unix>|r=<prix de référence>|<fiche>;<fiche>;…|n=<nombre de bougies>`

- `r` = vraie ouverture de la 1re bougie du bloc.
- Les fiches sont séparées par `;` et leurs champs par `,`.
- Un champ vide = valeur inconnue (na).
- Les ratios ont 5 décimales au plus (format `#.#####`).
- Un `|n=` absent en fin de commentaire signifie que le commentaire a été coupé par TradingView.

Quand « Fin » est réglée, le bloc en cours est fermé à la première bougie hors période : rien ne manque entre deux
périodes contiguës (Fin de l'une = Début de la suivante). Sans « Fin », le dernier bloc de l'historique reste ouvert et n'a pas de commentaire de sortie : ses bougies manquent.

Le commentaire d'entrée contient seulement `t=…` (le même horodatage que la 1re bougie).

### Champs d'une fiche (31)

| # | Champ | Sens |
|---|---|---|
| 1 | dt | écart en bougies avec la bougie précédente (1 en continu, plus après une pause de séance ou un week-end) |
| 2-5 | o, h, l, c | vrais prix OHLC, en ticks entiers par rapport à `r` |
| 6 | bits | 35 caractères 0/1, détail ci-dessous |
| 7 | clx | dernier climax : 1 achat, −1 vente, 0 aucun |
| 8 | adx | ADX 14 (Signator) |
| 9 | di | DI+ − DI− |
| 10 | sgs | score Signator (0-100) |
| 11 | feu | Feu : part des voix long (%) |
| 12 | str | STRENGTH : part haussière (%) |
| 13-15 | dirC, dirM, dirH | Directionnor graphique / 1 h / 4 h : 1 long, −1 short, 0 range |
| 16 | atr | ATR des vrais prix, en points |
| 17 | e1 | (close HA − EMA50) / ATR HA |
| 18 | e2 | (close HA − EMA60) / ATR HA |
| 19-20 | k1, k4 | Dashator 1 h / 4 h, dernière bougie terminée : corps HA / ATR (> 0 haussier) |
| 21-22 | b1, b4 | idem, bougie en cours reconstituée (comme en direct) |
| 23-24 | biF, biI | biais fond / intraday (−1 à +1) |
| 25-27 | pW, pM, pA | (vrai close − pivot P weekly / mensuel / annuel) / ATR |
| 28 | fib | position du close HA dans le dernier swing : 0 = swing récent, 1 = swing ancien |
| 29 | detU | distance à la zone d'offre (Detector) la plus proche au-dessus, en ATR HA (vide = aucune) |
| 30 | detD | distance à la zone de demande la plus proche au-dessous, en ATR HA |
| 31 | vr | ATR / moyenne 96 bougies |

### Les 35 bits (champ 6), dans l'ordre

| Bit | Sens |
|---|---|
| 1 | bougie HA haussière (Heishinator) |
| 2, 3 | flip Heishinator haussier / baissier |
| 4, 5 | Signator Fort long / short |
| 6, 7 | Signator Moyen long / short |
| 8, 9 | cassure de trendline haussière / baissière |
| 10, 11 | cassure de niveau haussière / baissière |
| 12, 13 | climax achat / vente |
| 14, 15 | divergence long / short |
| 16, 17 | Detector bloque un long / un short |
| 18 | bougie de blackout news |
| 19-24 | TREND unités 3 min, 5 min, 15 min, 1 h, 4 h, 1 jour (1 = haussier) |
| 25-30 | Dashator unités 1 min, 5 min, 15 min, 1 h, 4 h, 1 jour (1 = bougie HA haussière) |
| 31 | MACD 10 min haussier |
| 32 | sortie forcée (fenêtre 00:20-22:15 Paris, à plat 15:59 Chicago) |
| 33, 34 | la stratégie 56 aurait décidé un long / un short (en lecture sans fuite muClos, avant « une position à la fois ») |
| 35 | Fibonator : dernier swing baissier (le bas est plus récent que le haut) |

## Procédure pour Jeremy

**Étape 0 : test de longueur (une seule fois, 2 minutes).**
1. Colle `KAIROS/dataset/RELEVE_COMPLET.pine` comme nouvelle stratégie. Ajoute-la seule sur MNQ1! 15 min Heikin
   Ashi.
2. Dans le groupe « RELEVÉ COMPLET », mets **Mode = Test de longueur**. Pas besoin d'historique profond.
3. Exporte la liste des trades (8 trades) et dépose le fichier dans `~/ERGON/KAIROS-data/releve_complet/`.

TALOS lit où TradingView coupe les commentaires, puis te donne la valeur à mettre dans « Longueur max d'un
commentaire ».

**Étape 1 : les relevés.**
1. **Mode = Relevé**, longueur max = la valeur donnée par TALOS.
2. Testeur : historique profond depuis le **01/01/2019** (MNQ et MES commencent en mai 2019).
3. Exporte la liste des trades. Refais pareil sur **MES1!**.
4. Dépose les fichiers dans `~/ERGON/KAIROS-data/releve_complet/` sans les renommer.

**Volume attendu.** Une fiche fait environ 220 caractères, et il y a environ 175 000 bougies par instrument depuis
2019. Le nombre de trades par instrument dépend donc de la longueur max :
- à 4 000 caractères, environ 10 000 trades, soit **1 export par instrument** (le Relevé 5669 en a passé 13 018) ;
- à 2 000 caractères, environ 20 000 trades. Si le testeur refuse, on découpe avec « Début » / « Fin » en deux
  périodes, soit 2 exports par instrument.

Au total : 1 test + 2 à 4 relevés, soit 3 à 5 exports.

## Relevés 5 min et 1 h (plan du 19/11)

Mesures sur les relevés 15 min exportés (MNQ, MES) : le test de longueur passe **4 000 caractères intacts**, une fiche
fait **205 caractères** en moyenne, et un bloc en contient **18,6**. Le 15 min a donné **9 566 trades** par instrument,
en un seul export.

| Unité | Bougies par instrument | Trades à 4 000 car. | Exports par instrument |
|---|---|---|---|
| 1 h | ≈ 44 000 | ≈ 2 400 | 1 |
| 5 min | ≈ 530 000 | ≈ 28 500 | 3 périodes de ≈ 9 500 trades (la taille déjà passée en 15 min) |

Les mêmes réglages pour tous les exports : Mode = Relevé, longueur max = **4 000**. Testeur : historique profond
du **01/01/2019** à aujourd'hui, toujours le même, même quand « Début » / « Fin » découpent. Seuls les deux
réglages du script changent :

| # | Graphique (Heikin Ashi) | Début | Fin |
|---|---|---|---|
| 1 | MNQ1! 1 h | 01/01/2019 | (défaut, 2099) |
| 2 | MES1! 1 h | 01/01/2019 | (défaut) |
| 3 | MNQ1! 5 min | 01/01/2019 | 01/11/2021 |
| 4 | MNQ1! 5 min | 01/11/2021 | 01/05/2024 |
| 5 | MNQ1! 5 min | 01/05/2024 | (défaut) |
| 6-8 | MES1! 5 min | idem 3-5 | |

Contrôles :
- La 1re date de chaque export doit être ≈ « Début ». Sinon, TradingView a tronqué la liste : prévenir TALOS, qui
  passera à 4 périodes.
- Si le calcul échoue (délai dépassé) en 5 min : régler le testeur pour qu'il commence 1 an avant « Début » au lieu
  de 2019. L'année en plus sert de chauffe aux moyennes longues (SMA 200 jour, EMA 50 4 h).
- Déposer les fichiers dans `~/ERGON/KAIROS-data/releve_complet/5min/` et `.../1h/` sans les renommer.
