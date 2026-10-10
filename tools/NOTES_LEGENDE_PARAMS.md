# Décodage de la légende TradingView — quels inputs d'Ephore nous manquent

Source : `images/4.png` (2000 × 201 px), légende TradingView de 5 indicateurs.
Méthode : découpe ligne par ligne (profil de pixels sombres → 5 lignes de texte aux
y = 5-16 / 38-47 / 85-96 / 117-129 / 150-160), puis relecture de chaque ligne en tranches
de 150-300 px agrandies ×7 puis ×13 (Pillow/LANCZOS). Chaque passage douteux a été relu
au zoom ×13. Les caractères que je n'ai pas pu identifier sont marqués `?`.

---

## 0. Un point méthodologique décisif (validé par le Fibonator)

La ligne 2 de la légende est : **« Ephore Market Fibonator v4 10 1 small »**.

Notre `FIBONACCI_AUTO.pine` a exactement 3 inputs non-booléens / non-couleur :
`piv_len = 10`, `ln_width = 1`, `lbl_size = "small"`. **Les trois valeurs, dans l'ordre.**

Donc :
1. la légende TradingView **n'affiche que les inputs `int`, `float`, `string`, `source`,
   `timeframe`, `symbol`** — les `input.bool` et les `input.color` n'y figurent pas ;
2. notre Fibonator est une réplique structurellement exacte du Fibonator d'Ephore ;
3. la méthode « légende = empreinte de la liste d'inputs » est **confirmée empiriquement**.

Conséquence importante pour la suite : **tout ce qui est case à cocher est invisible ici**
(« Activer Filtre », « Afficher X »…). Les écarts de longueur entre versions correspondent
donc uniquement à des inputs numériques/texte ajoutés ou retirés.

---

## 1. Transcription brute, valeur par valeur

### Ligne 1 — « Ephore Market Ultimate v30 » (67 valeurs)

```
 1 🏆 Classique Ultime      2 Classique (Original)   3 Classique (Original)
 4 Subtle                   5 75                     6 5
 7 3                        8 3                      9 ——— (style de ligne)
10 1                       11 Wick                  12 Top Right
13 18                      14 Normal                15 0,5
16 0,33                    17 0,35                  18 14
19 0,5                     20 20                    21 1
22 ATR                     23 0,3                   24 0,5
25 50                      26 25                    27 25
28 25                      29 25                    30 10
31 0,1                     32 3                     33 2
34 100                     35 1                     36 100
37 10                      38 1                     39 Solide
40 Gauche                  41 150                   42 normal  (minuscule)
43 Bottom Center           44 Normal                45 1
46 5                       47 15                    48 60
49 240                     50 1D                    51 1W
52 Middle Right            53 Large                 54 Traditional
55 1                       56 Right                 57 2
58 Yearly                  59 Monthly               60 close
61 2                       62 close                 63 1
64 0                       65 Bottom Left           66 Bottom Right
67 Normal
```

### Ligne 2 — « Ephore Market Fibonator v4 » (3 valeurs)

```
1 10      2 1      3 small
```

### Ligne 3 — « Ephore Market Ultim… » / preset **Scalping Nasdaq (1-5m)** (84 valeurs)

```
 1 🏆 Classique Ultime      2 Classique (Original)   3 Classique (Original)
 4 Subtle                   5 75                     6 5
 7 3                        8 3                      9 ———
10 1                       11 Wick                  12 Griser
13 1,5 % fixe              14 0,1                   15 Top Right
16 18                      17 Normal                18 0,5
19 0,33                    20 0,35                  21 14
22 0,5                     23 20                    24 1
25 ATR                     26 0,3                   27 0,5
28 50                      29 25                    30 25
31 25                      32 25                    33 10
34 0,1                     35 3                     36 2
37 100                     38 1                     39 100
40 10                      41 1                     42 Solide
43 Gauche                  44 150                   45 small
46 Top Right               47 Small                 48 1
49 5                       50 15                    51 60
52 240                     53 1D                    54 1W
55 Top Right               56 Small                 57 Traditional
58 1                       59 Right                 60 1
61 Yearly                  62 Monthly               63 Weekly
64 close                   65 1                     66 close
67 1                       68 0                     69 Bottom Left
70 Bottom Right            71 Small                 72 100
73 Scalping Nasdaq (1-5m)  74 22                    75 0,34
76 3                       77 8                     78 1
79 1                       80 0,45                  81 0,12
82 20                      83 61,8                  84 0,3
```

### Ligne 4 — « Ephore Market Ultimat… » / preset **Intraday (15m-1h)** (90 valeurs)

```
 1 Middle Left              2 Large                  3 8
 4 60                       5 📅? Normal             6 🔵 Bleu à gauche
 7 🏆 Classique Ultime      8 5                      9 3
10 3                       11 ———                   12 1
13 Wick                    14 Griser                15 1,5 % fixe
16 0,1                     17 Flèches (défaut)      18 Normale
19 250                     20 18                    21 Normal
22 0,5                     23 0,33                  24 0,35
25 14                      26 0,5                   27 20
28 1                       29 ATR                   30 0,3
31 0,5                     32 50                    33 25
34 25                      35 25                    36 25
37 10                      38 0,1                   39 3
40 2                       41 100                   42 1
43 100                     44 10                    45 1
46 Solide                  47 Gauche                48 150
49 small                   50 1                     51 5
52 15                      53 60                    54 240
55 1D                      56 1W                    57 Traditional
58 1                       59 Right                 60 1
61 Yearly                  62 Monthly               63 Weekly
64 close                   65 1                     66 close
67 1                       68 0                     69 3
70 3                       71 90                    72 America/New_York
73 Europe/Paris            74 9                     75 0
76 9                       77 30                    78 Tous
79 14                      80 30                    81 Tous
82 20                      83 0                     84 100
85 Intraday (15m-1h)       86 22                    87 0,34
88 3                       89 8                     90 1
```

### Ligne 5 — « Ephore Market Ultimate Old » (19 valeurs)

```
 1 Traditional   2 1    3 Right   4 1    5 Yearly   6 Monthly
 7 close         8 2    9 close  10 2   11 70
12 5            13 3   14 3      15 ———  16 1      17 Wick
18 Top Left     19 0,5
```

**Lectures incertaines (les seules) :**
- L4 pos 5 : l'émoji avant « Normal » est un petit rectangle jaune pâle avec des
  marques colorées en haut — **probablement 📅 (calendrier)**, je ne peux pas trancher
  entre 📅 / 🗓 / 🧮. Le libellé texte « Normal » est net.
- Je ne peux pas savoir si « 🏆 Classique Ultime » est **une seule** valeur de liste
  déroulante (émoji inclus dans l'option) ou **deux** inputs successifs. Même remarque
  pour « 🔵 Bleu à gauche » et « 📅 Normal ». J'ai compté 1 valeur à chaque fois, par
  analogie avec les listes à émoji usuelles. Si c'est faux, la numérotation de L4 décale
  de 3 et celle de L1/L3 de 1.
- Tout le reste est lu sans ambiguïté au zoom ×13.

---

## 2. Alignement avec ce que nous avons déjà

L'alignement proposé dans la mission est **confirmé**, et je le prolonge nettement.
Trois ancrages indiscutables (séquence exacte d'un script public connu) :

### Ancrage A — Detector (order blocks LuxAlgo) : `5 3 3 ——— 1 Wick`
`PORSCHEONARRIVE.pine` l. 984-1019 : `length=5` (Volume Pivot Length), `bull_ext_last=3`,
`bear_ext_last=3`, `line_style='⎯⎯⎯'`, `line_width=1`, `mitigation='Wick'`.
→ **6 valeurs, même ordre, mêmes valeurs.** Présent dans les 4 versions (L1 6-11,
L3 6-11, L4 8-13, L5 12-17). **Nous l'avons.**

### Ancrage B — Trendlines (Amphibiantrading) : `10 0,1 3 2 100 1`
`tools/amphibiantrading_trendlines_source.pine` — inputs visibles dans l'ordre :
`bars`, `buffer`, `numTouches`, `tlWidth`, `newH`, `showNum`.
Valeurs d'Ephore lues : **10 / 0,1 / 3 / 2 / 100 / 1** = exactement les réglages validés
en §5 de MEMOIRE_PROJET (pivots 10, tampon 0,1 %, 3 touches, nouvelle ancre 100 barres,
1 ligne par côté). **Nous l'avons.**
Les 3 valeurs suivantes `100 10 1` sont très probablement **le jeu symétrique côté
support** (newL 100, pivot-low bars 10, nombre de lignes 1) — Ephore a dupliqué le bloc
pour le « support ascendant en miroir » (§5). Fonctionnellement équivalent chez nous
(`tl_bars`, `tl_newH` partagés). **Confiance moyenne-haute, impact nul.**

### Ancrage C — Fibonator : `10 1 small` (cf. §0). **Nous l'avons.**

### Bloc Signator / Candle Quality Filter — `18 Normal 0,5 0,33 0,35 14 0,5 20 1 ATR 0,3 0,5 50`
Alignement confirmé, 13 valeurs, **identique dans les 4 versions Ultimate** :

| # | valeur | réglage | chez nous ? |
|---|---|---|---|
| 1 | 18 | Seuil de Force (ADX 14) | ✅ `sg_force = 18` |
| 2 | Normal | **Mode de Lag** | ❌ aucun input |
| 3 | 0,5 | Ratio Corps/Range | ✅ `/0.5` en dur |
| 4 | **0,33** | Position Close | ⚠️ **nous divisons par 0,67** |
| 5 | 0,35 | Mèche Adverse Max | ✅ `/0.35` |
| 6 | 14 | Période ATR | ✅ `ta.atr(14)` |
| 7 | 0,5 | Range Min (× ATR) | ✅ `0.5*atr` |
| 8 | 20 | Période SMA Volume | ✅ `sma(volume,20)` |
| 9 | 1 | Ratio Volume Min | ✅ |
| 10 | ATR | Type de gap | ✅ (mode unique) |
| 11 | 0,3 | Gap Min ATR | ✅ `0.3*atr` |
| 12 | 0,5 | Gap Min % | ❌ mode % absent |
| 13 | 50 | Score Minimum | ✅ `sg_scoreMin = 50` |

### Bloc Pivator — `Traditional 1 Right <largeur> Yearly Monthly [Weekly]`
= type, nombre de pivots en arrière, position des étiquettes, largeur de ligne, puis
1 input `string` par Set. **Nous l'avons** (`piv_type`, `piv_lookback`, `piv_line_w`,
`piv_s1/s2/s3_tf`). Détail : L1 et L5 n'affichent que **2** sets (Yearly, Monthly),
L3 et L4 en affichent **3** (+ Weekly) → le Set 3 hebdomadaire est une **addition** des
versions récentes, exactement comme chez nous (V5 → V8).

### Bloc Moyenator — `close <w1> close <w2> <opacité>`
L1 : `close 2 close 1 0` = nos valeurs par défaut exactes (`moy_w1=2`, `moy_w2=1`,
`moy_fill_opa=0`). L3/L4 : `close 1 close 1 0`. L5 : `close 2 close 2 70`.
**Nous l'avons.** (Les deux `close` sont des `input.source`.)

---

## 3. LIVRABLE — ce que nous n'avons PAS

Classé par valeur opérationnelle décroissante.

### 🔴 P1 — `22 0,34 3 8 1` (L3 74-78, L4 86-90) — **structurel, 2 versions sur 4**

Toujours **juste après** le nom du preset, dans les deux versions récentes. C'est donc le
bloc de réglages du **moteur de signaux de la nouvelle génération**.

Hypothèse la plus probable (**confiance moyenne-haute**) : ce sont les **mêmes grandeurs
que notre Signator, mais re-réglées par le preset** —

| pos | valeur | hypothèse | à recouper avec |
|---|---|---|---|
| 1 | **22** | Seuil de Force (ADX) propre au preset | notre `sg_force = 18` (valeur globale, toujours 18 plus haut dans la ligne) |
| 2 | **0,34** | Seuil de conviction `dBand` (× ATR) | notre `sg_conv : sg_dBand >= 0.3` |
| 3 | 3 | nb de barres de confirmation / fenêtre | notre `sg_run == 2` |
| 4 | 8 | période courte (EMA ou lissage) | Heishinator EMA(ohlc4,4) ? |
| 5 | 1 | ratio volume min / multiplicateur | `volume >= sg_volMa` |

**Pourquoi c'est la piste n°1 :** MEMOIRE §5 dit que nos faux positifs résiduels se
concentrent dans la zone `dBand` **0,3–0,5 portés sans volume**, et qu'aucun seuil ne les
sépare. Or la légende donne **0,34** là où nous avons 0,30, et **22** là où nous avons 18.
C'est précisément le genre de micro-ajustement qui n'était pas devinable, et il est
**testable immédiatement** avec `tools/signator_sim.py` (passer `dBand ≥ 0.34` et
`ADX ≥ 22`, mesurer rappel/précision sur Singal et Filtres).
Attention : ces valeurs sont **liées au preset** — « Scalping Nasdaq (1-5m) » et
« Intraday (15m-1h) » portent les **mêmes** 5 valeurs ici, donc soit le preset ne les
change pas, soit ce bloc est indépendant du preset.

### 🔴 P2 — Le bloc annonces, **configurable** (L4 69-83) — 15 inputs, 0 chez nous

```
3  3  90  America/New_York  Europe/Paris  9 0  9 30 Tous  14 30 Tous  20 0
```

Notre V8 code en dur « 14:30 et 16:00 Paris ». L'original a un **vrai module paramétrable**.

Découpage proposé (**confiance moyenne** sur le découpage, **haute** sur le fait que
c'est bien le filtre d'annonces — les deux fuseaux et les « Tous » ne laissent pas de
doute) :

| pos | valeur | hypothèse | conf. |
|---|---|---|---|
| 69 | 3 | marge **avant** l'annonce, en minutes | moyenne |
| 70 | 3 | marge **après** l'annonce, en minutes | moyenne |
| 71 | 90 | transparence / opacité de la bande rouge | moyenne |
| 72 | America/New_York | fuseau n°1 | haute |
| 73 | Europe/Paris | fuseau n°2 | haute |
| 74-75 | 9 / 0 | **début** de plage horaire = 09:00 | moyenne |
| 76-78 | 9 / 30 / Tous | **annonce n°1 : 09:30**, jours = Tous | haute |
| 79-81 | 14 / 30 / Tous | **annonce n°2 : 14:30**, jours = Tous | haute |
| 82-83 | 20 / 0 | **fin** de plage horaire = 20:00 | moyenne |

Deux lectures possibles des fuseaux, les deux cohérentes avec MEMOIRE §9 :
- **(a)** fuseau n°1 = celui de l'annonce n°1, fuseau n°2 = celui de l'annonce n°2 →
  09:30 New York = **15:30 Paris** ✔ et **14:30 Paris** ✔. Deux des quatre bandes
  rouges mesurées sur le terminal web (09:00, 14:30, 15:30, 16:00), les deux autres
  (09:00 et 16:00) venant alors de la plage horaire et/ou d'un 3ᵉ créneau non exposé ici.
- **(b)** fuseau n°1 = fuseau des annonces, fuseau n°2 = fuseau d'affichage → annonces
  09:30 et 14:30 **New York** = 15:30 et 20:30 Paris. Moins cohérent avec les mesures.

Je penche pour **(a)**.

**Recoupement avec le fait mesuré 176 vs 161 flèches :** la version à 161 flèches
(sous-ensemble strict, 11 des 15 retraits sur une heure d'annonce) est forcément celle
qui exécute ce filtre. C'est **cette ligne 4** (la seule des quatre qui porte le bloc
annonces). Les 4 retraits restants ne tombant pas sur une annonce s'expliqueraient par la
**marge ±3 minutes** (pos 69-70) ou par la **plage 09:00-20:00** (pos 74-75 / 82-83), qui
coupe tout signal hors séance — deux mécanismes que nous n'avons pas du tout.

**À coder :** créneaux multiples (au moins 2), chacun avec heure + minute + sélecteur de
jours (« Tous » = toute la semaine ; les autres options sont probablement les jours, ce
qui permettrait de ne bloquer le NFP que le vendredi), un fuseau par créneau, une marge
avant/après en minutes, et une plage horaire de séance.

### 🟠 P3 — `25 25 25 25` (L1 26-29, L3 29-32, L4 33-36) — structurel, 3 versions sur 4

Position : **immédiatement après « Score Minimum = 50 »** et immédiatement avant le bloc
Trendlines (`10 0,1 3 …`). Quatre fois la même valeur, somme = 100.

- **Hypothèse 1 (confiance moyenne, haute valeur) : les pondérations des 4 composantes
  du score** (structure, momentum, volume, gap), 25 % chacune. Notre score fait
  `(structure + momentum + volume + gap + engulfing) / 5 × 100`, c.-à-d. 5 poids de 20 %
  **avec l'engulfing qui vaut toujours 0 en Heiken Ashi** → notre score plafonne à 80.
  Si l'original pondère 4 composantes à 25 %, son score = le nôtre **× 1,25**, et le
  seuil « Fort ≥ 50 » équivaut chez nous à **≥ 40**.
  ⚠️ **Conséquence à tester, pas à appliquer les yeux fermés** : abaisser notre seuil
  effectif produirait **plus** de flèches, alors que nous en avons déjà 5 en trop. Mais
  combiné à P1 (ADX 22, dBand 0,34, qui en retirent), le couple pourrait converger.
  C'est la première hypothèse de la liste à passer au simulateur.
- **Hypothèse 2 (confiance faible-moyenne) : les pondérations des 4 groupes du Feu de
  Confluence.** MEMOIRE §6.3 : `GROUPES_FEU` = 4 groupes (Colonne temps 6 voix, Bloc
  SuperTrader 10, Colonne SIGNAL 7, Tendances multi-unités 6) = 29 votes. Quatre groupes,
  quatre poids de 25 %. Le problème : la position dans la séquence (collée au Signator)
  plaide plutôt pour l'hypothèse 1.
- **Hypothèse 3 (faible) :** 4 transparences de remplissage de zones, à 25 %.

### 🟠 P4 — `Griser` / `1,5 % fixe` / `0,1` (L3 12-14, L4 14-16) — absent de v30

Trois inputs ajoutés **entre le Detector et le Signator** dans les deux versions récentes.
« Griser » est une option de liste (griser / masquer / colorer ?), « 1,5 % fixe » est une
valeur de liste **texte** (donc un mode : « 1,5 % fixe » vs « × ATR » vs « auto »),
« 0,1 » un float.
**Hypothèse (confiance moyenne) :** réglage d'une **zone de mitigation / d'invalidation**
appliquée aux order blocks du Detector — on *grise* le bloc quand le prix s'en écarte de
1,5 % (mode fixe) avec une tolérance de 0,1. Alternative : réglage d'atténuation visuelle
des bougies hors-tendance.
**Nous n'avons rien de tel.** Impact probablement cosmétique (donc P4 et pas P1), mais à
vérifier : si « Griser » touche la *validité* d'un order block, ça change le Detector.

### 🟠 P5 — `Flèches (défaut)` / `Normale` / `250` (L4 17-19) — L4 uniquement

**Hypothèse (confiance moyenne-haute, c'est de l'affichage) :** forme des marqueurs
(options « Flèches (défaut) », triangles, points…), taille (« Normale »), et **nombre
maximum d'objets dessinés = 250**. Le 250 est typiquement un garde-fou `max_labels_count`.
Chez nous : forme et taille sont en dur (`shape.arrowup`, `size.normal` / `size.small`).
**Impact : nul sur les signaux, mais explique une différence d'affichage.**

### 🟡 P6 — `Solide` / `Gauche` / `150` + une taille (L1 39-42, L3 42-45, L4 46-49)

Structurel (les 3 versions Ultimate), valeurs identiques partout (seule la taille varie :
`normal` en L1, `small` en L3 et L4 — noter la **minuscule**, comme les options du
Fibonator, donc une liste `["tiny","small","normal","large"]`).

**Hypothèses :**
- (a) **confiance moyenne** : module de **niveaux horizontaux** (PDH/PDL, ORB, VWAP…) —
  style de ligne « Solide », étiquettes à « Gauche », longueur/extension 150 barres,
  taille d'étiquette. Le tableau `INDICATOR | SIGNAL` de l'original contient bien
  « CPR, ORB 15min, PDH/PDL » (MEMOIRE §6.3), qui doivent être tracés quelque part.
- (b) **confiance faible** : réglages visuels du Rangeator.

Nous n'avons **aucun** de ces trois modules (Rangeator et Breakator jamais traités, §6.4).

### 🟡 P7 — La liste des 7 unités de temps `1 5 15 60 240 1D 1W`

Identique dans les 3 versions Ultimate (L1 45-51, L3 48-54, L4 50-56). Ce sont **7 inputs
`timeframe`**, alors que le Dashator n'affiche que **6 cases**.

**Explication la plus simple (confiance haute) :** il y a 7 champs de TF **et 7 cases à
cocher « afficher »**, dont une est décochée — et les booléens **ne figurent pas dans la
légende** (cf. §0). La 7ᵉ unité (`1W`) est donc présente dans le code mais masquée par
défaut. Recoupement : MEMOIRE §6.3 note que le groupe « Tendances multi-unités » du Feu
de Confluence pèse **6 voix** → 6 unités actives. Cohérent.
**À faire chez nous : prévoir 7 champs TF, pas 6.**

### 🟡 P8 — Positions et tailles de 3 tableaux que nous n'avons pas

| ligne | positions lues | ce que nous avons |
|---|---|---|
| L1 | Top Right / Bottom Center+Normal / Middle Right+Large / Bottom Left / Bottom Right+Normal | 2 tableaux (`main_pos`, `sg_pos`) |
| L3 | Top Right / Top Right+Small / Top Right+Small / Bottom Left / Bottom Right+Small | idem |
| L4 | Middle Left+Large (en tête) uniquement | idem |

→ L'original pilote **au moins 5 emplacements de tableaux/panneaux** (Top Right,
Bottom Center, Middle Right, Bottom Left, Bottom Right). Nous en avons 2. Cela confirme
qu'il manque **3 panneaux** : très probablement `INDICATOR | SIGNAL`,
`TIMEFRAME | TREND | STRENGTH` et le **Dashator** (ou le Feu de Confluence).
Confiance haute sur le comptage, moyenne sur l'attribution.

### 🟡 P9 — `1 0,45 0,12 20 61,8 0,3` (L3 79-84) — version Scalping uniquement

Six valeurs, en toute fin de ligne, après le bloc `22 0,34 3 8 1`.
**61,8 est un ratio de Fibonacci**, et l'API d'Ephore expose un objet `fib_75`
(MEMOIRE §9) : il y a donc bien un module d'entrée sur retracement.

**Hypothèse (confiance moyenne) : un module « entrée sur repli » / CONTINUATION.**

| pos | valeur | hypothèse |
|---|---|---|
| 79 | 1 | nombre de replis autorisés / multiplicateur |
| 80 | 0,45 | ratio corps/range minimal de la bougie de repli |
| 81 | 0,12 | tolérance autour du niveau (× ATR ou %) |
| 82 | 20 | fenêtre de recherche du swing (barres) |
| 83 | **61,8** | niveau de retracement visé (%) |
| 84 | 0,3 | marge / multiplicateur ATR d'invalidation |

Recoupement fort : l'API de la **nouvelle** version émet `v7c:CONTINUATION` (3 occurrences
en 15 m) en plus des flèches (MEMOIRE §9). Ce bloc en est très probablement le réglage.

### 🟡 P10 — Le système de **presets** et le `100` qui le précède

`… 100 | Scalping Nasdaq (1-5m) | …` (L3 72-73) et `… 100 | Intraday (15m-1h) | …`
(L4 84-85). Absent de v30 et de « Old ».

- Le preset est une **liste déroulante** avec au moins deux options nommées par style de
  trading et par plage d'unités de temps. Cohérent avec la formation (MEMOIRE §7 :
  « 15 m + 2 m, scalping Nasdaq, MNQ1! »). **Confiance haute** sur l'existence, nulle sur
  la liste complète des options.
- Le `100` juste avant : **confiance faible**. Candidats : nombre max de barres
  historiques traitées, transparence globale, ou seuil 0-100 d'un module. Ce n'est pas la
  fin du groupe annonces (L3 l'a sans le groupe annonces).

### 🟢 P11 — Le thème visuel : `🏆 Classique Ultime` + `Classique (Original)` ×2 + `Subtle` + `75`

L1 1-5 et L3 1-5 ; L4 n'a que `🏆 Classique Ultime` (pos 7) ; L5 n'a rien.
**Confiance haute** que c'est purement cosmétique : un préréglage de thème, deux palettes
(bougies / lignes ?), une intensité (« Subtle »), et une transparence 75.
**Aucun impact sur les signaux. À ignorer pour la rétro-ingénierie.**

### 🟢 P12 — L'en-tête propre à L4 : `Middle Left Large 8 60 📅? Normal 🔵 Bleu à gauche`

Six valeurs en tête de la ligne 4, inexistantes ailleurs.
- `Middle Left` + `Large` = position + taille d'un tableau remontée en tête du script
  (ce qui explique que L4 n'ait plus de couple position/taille au milieu de sa séquence).
  **Confiance moyenne-haute.**
- `8` et `60` : **confiance faible**. Deux périodes (EMA 8 et 60 ?) ou largeur/hauteur
  d'un panneau. À noter : notre Moyenator est EMA50/EMA60 — le **60** colle, le **8** non.
- `📅? Normal` et `🔵 Bleu à gauche` : deux listes déroulantes à émoji. « Bleu à gauche »
  évoque fortement l'**orientation d'une jauge** (bleu = haussier à gauche, rouge à
  droite) → le **Dashator** ou le **Feu de Confluence**. **Confiance faible-moyenne.**

### 🟢 P13 — Divers, impact nul ou faible

- **`Normal` juste après le Seuil de Force 18** (« Mode de Lag » selon la mission) :
  liste à 2-3 options, pas d'équivalent chez nous. Pourrait décaler le calcul d'une barre
  — à surveiller, mais la valeur est « Normal » partout donc sans effet sur nos comparatifs.
- **`0,5` « Gap Min % »** : nous n'implémentons que le mode ATR ; comme le type de gap vaut
  « ATR » dans les 4 versions, cet input est inactif. **Aucun impact.**
- **`100 10 1`** après le bloc Trendlines : jeu symétrique côté support (cf. ancrage B).
  Fonctionnellement couvert.
- **L5 `Top Left 0,5`** : position d'un panneau + un float 0,5 inconnu, dans la version
  « Old » uniquement. Sans intérêt (version obsolète).
- **`0,33` vs notre `0,67`** : voir §4 ci-dessous, c'est une vraie question ouverte.

---

## 4. Un écart interne à vérifier : Position Close 0,33 vs notre 0,67

La légende donne **0,33** à la position du « Position Close » dans les 4 versions.
`TABLEAU.pine` l. 344 calcule `math.min(sg_cpos / 0.67, 1.0)` (et l'en-tête V7 dit
« position du close ≥ 0.33 »). Les deux sont des lectures possibles du même réglage
(0,33 = seuil, 0,67 = 1 − seuil), mais si l'original divise bien par **0,33**, notre
composante « structure » est **sous-évaluée d'un facteur 2** sur ce tiers-là, donc notre
score global est trop bas.
**Combiné à P3 (poids 25 %), cela se teste en une passe du simulateur.** C'est, avec P1,
le deuxième levier purement numérique disponible sans nouvelle donnée.

---

## 5. Comparaison des 4 versions

| élément | L1 « v30 » | L3 « Scalping » | L4 « Intraday » | L5 « Old » |
|---|---|---|---|---|
| nb de valeurs | 67 | 84 | 90 | 19 |
| thème (5 inputs) | ✔ | ✔ | **1 seul** | ✘ |
| en-tête `Middle Left Large 8 60 📅 🔵` | ✘ | ✘ | **✔** | ✘ |
| Detector `5 3 3 ——— 1 Wick` | ✔ | ✔ | ✔ | ✔ |
| `Griser 1,5 % fixe 0,1` | ✘ | **✔** | **✔** | ✘ |
| `Flèches (défaut) Normale 250` | ✘ | ✘ | **✔** | ✘ |
| bloc Signator 13 valeurs | ✔ | ✔ | ✔ | ✘ |
| `25 25 25 25` | ✔ | ✔ | ✔ | ✘ |
| Trendlines `10 0,1 3 2 100 1 (100 10 1)` | ✔ | ✔ | ✔ | ✘ |
| `Solide Gauche 150` + taille | normal | small | small | ✘ |
| 7 TF `1 5 15 60 240 1D 1W` | ✔ | ✔ | ✔ | ✘ |
| emplacements de tableaux | 5 | 5 | **1** | 1 |
| largeur de ligne Pivator | **2** | 1 | 1 | 1 |
| sets de pivots | Yearly, Monthly | **+ Weekly** | **+ Weekly** | Yearly, Monthly |
| Moyenator | close 2 / close 1 / 0 | close 1 / close 1 / 0 | close 1 / close 1 / 0 | close 2 / close 2 / **70** |
| bloc annonces (15 inputs) | ✘ | ✘ | **✔** | ✘ |
| `100` + preset nommé | ✘ | **✔** | **✔** | ✘ |
| `22 0,34 3 8 1` | ✘ | **✔** | **✔** | ✘ |
| `1 0,45 0,12 20 61,8 0,3` | ✘ | **✔** | ✘ | ✘ |

**Lecture.**
1. **L5 « Old » est un squelette** : Pivator + Moyenator + Detector seulement. Pas de
   Signator, pas de trendlines, pas de tableaux. Rien à en tirer.
2. **L1 « v30 » est le tronc commun complet** : Signator, trendlines, 5 tableaux, 7 TF.
   Pas de preset, pas d'annonces, pas de `Griser`.
3. **L3 et L4 ne sont PAS dans une même lignée.** Les deux ajoutent `Griser 1,5 % fixe 0,1`
   et le système de presets par rapport à v30, mais ensuite elles divergent :
   - L3 garde les 5 tableaux + le thème complet, ajoute `1 0,45 0,12 20 61,8 0,3`, et
     **n'a pas** le bloc annonces ;
   - L4 supprime 4 des 5 emplacements de tableaux et 4 des 5 inputs de thème, ajoute
     `Flèches (défaut) Normale 250` et **tout le bloc annonces**.
   Ce sont donc **deux branches distinctes** (ou deux builds très éloignés dans le temps),
   pas deux étapes d'une même progression. Elles partagent un **noyau récent commun** :
   `Griser…` + `100` + preset + `22 0,34 3 8 1`.
4. **Lien direct avec le fait mesuré 176 / 161 flèches.** La version à 161 est un
   sous-ensemble strict, et 11 des 15 flèches retirées tombent sur une heure d'annonce :
   c'est la signature de **L4**, la seule à embarquer le filtre d'annonces. Les 4 retraits
   non expliqués par une heure ronde le sont très probablement par la **marge ±3 min** et
   la **plage 09:00-20:00** du même bloc. Ce recoupement vaut confirmation croisée :
   le bloc `3 3 90 … 9 0 9 30 Tous 14 30 Tous 20 0` **est** le filtre d'annonces.

---

## 6. Ce que je recommande de faire ensuite (ordre de rentabilité)

1. **Passer `tools/signator_sim.py` avec ADX ≥ 22 et dBand ≥ 0,34** (P1) sur `Singal` et
   `Filtres`. Zéro donnée nouvelle nécessaire, résultat en une minute. Si précision ↑ sans
   perte de rappel, c'est l'« ingrédient manquant » que §5 de MEMOIRE cherchait.
2. **Tester le score à 4 composantes pondérées 25 %** (P3) et **`cpos / 0,33`** au lieu de
   `/ 0,67` (§4), en gardant le seuil Fort ≥ 50. Même simulateur, mêmes fichiers.
3. **Rendre le filtre d'annonces configurable** (P2) : N créneaux (heure, minute, jours,
   fuseau), marge avant/après en minutes, plage de séance. Même si Jeremy garde 14:30 /
   16:00, la marge ±3 min est une nouveauté testable sur les 15 flèches retirées.
4. **Prévoir 7 champs TF** pour le Dashator (P7), pas 6.
5. Laisser de côté P11 (thème), P5 (forme des flèches), P13 : aucun effet sur les chiffres.

---

## 7. Fichiers produits

Rien n'a été écrit dans le dépôt, aucun `.pine` n'a été modifié.
Les découpes d'image servant à la relecture sont dans
`…/scratchpad/crops/` (jetables), l'original copié dans `…/scratchpad/src.png`,
et un venv Pillow dans `…/scratchpad/venv/`.

---

# VÉRIFICATION PAR SIMULATION (ajoutée le 10/10 par la session principale)

Les trois hypothèses testables de ce rapport ont été confrontées aux données
(groupe 4 des 14 exports « Ajustements », warmup 100, niveau Fort).
Script : `tools/ephore_api/test_hypotheses_legende.py`.

| hypothèse | exactes | trop | manq | erreurs | verdict |
|---|---:|---:|---:|---:|---|
| **V8 actuelle** (ADX 18, dBand 0.30, cpos/0.67, 5 comp.) | 140 | 3 | 10 | **13** | référence |
| P1 : ADX 22 + dBand 0.34 | 95 | 3 | 55 | 58 | **RÉFUTÉ** |
| P1 partiel : dBand 0.34 seul | 138 | 3 | 12 | 15 | pire |
| P1 partiel : ADX 22 seul | 97 | 3 | 53 | 56 | **RÉFUTÉ** |
| P3 : score 4 composantes à 25 % | 143 | 9 | 7 | 16 | pire |
| §4 : `cpos / 0.33` | 141 | 4 | 9 | 13 | **neutre** |

**Conclusions.**
1. **`22` n'est PAS le Seuil de Force.** À ADX 22 on perd 55 flèches. Cela recoupe le
   balayage indépendant du même jour : ADX 19 → 9 manquées, ADX 20 → 29. Le 18 est un
   optimum net et non négociable.
2. **`0,34` n'est pas notre `dBand`** : légèrement pire que 0.30.
3. **La pondération 4 × 25 % dégrade** (9 faux positifs au lieu de 3). Notre division par 5
   avec un engulfing nul en HA reste meilleure.
4. **`cpos / 0.33` est équivalent** à `/0.67` au total (13 erreurs), avec une répartition
   légèrement différente. Aucune raison de changer.

**Donc `22 0,34 3 8 1` appartient à un autre module.** Il suit immédiatement le nom du preset
et porte les **mêmes valeurs dans les deux versions récentes**. L'hypothèse la plus cohérente
avec le reste des preuves : ce sont les réglages des signaux **ALLUMAGE** (`v7a`) et
**CONTINUATION** (`v7c`) que l'API du terminal web expose (MEMOIRE §9) et que nous n'avons
pas du tout implémentés. Même chose pour `1 0,45 0,12 20 61,8 0,3`, propre à la version
Scalping, où le 61,8 est un retracement de Fibonacci.

**Ce qui reste solide dans ce rapport**, et qui est précieux :
- la méthode est **validée empiriquement** par le Fibonator (`10 1 small` = nos 3 inputs exacts) ;
- la légende **n'affiche ni les booléens ni les couleurs** — toute case à cocher est invisible ;
- elle **confirme** notre Detector, nos Trendlines, notre Pivator, notre Moyenator et les
  13 valeurs du bloc Signator ;
- le **bloc annonces de 15 inputs** (L4 uniquement) est la vraie trouvaille : marge avant/après,
  deux fuseaux, plusieurs créneaux avec sélecteur de jours, plage de séance. C'est la signature
  de la version qui émet 161 flèches au lieu de 176.
