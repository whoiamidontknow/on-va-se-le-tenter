# TRENDLINES — diagnostic et correctif

Analyse du 2026-09-29. Objet : les trendlines de `PORSCHEONARRIVE` sont justes par
intermittence (« parfois oui, parfois non »).

## 0. Préalable : deux versions divergentes

| Où | Logique de la résistance |
|---|---|
| `PORSCHEONARRIVE.pine:1310-1378` (git, commit `9f882a7`, seul commit sur ce fichier) | double boucle « closest above price, min 2 touches » — copie de `TRENDLINES.pine` |
| Version en cours dans TradingView (collée le 2026-09-29) | ancrage sur le pivot le plus haut + pente maximale, `best_tc := 2` en dur |

`git status` est propre : **la version live n'est pas versionnée**. Le support
ascendant, lui, est identique dans les deux. Le diagnostic ci-dessous porte sur la
version live, en signalant ce qui vaut aussi pour le disque.

## 1. Causes, par ordre d'impact

### 1.1 La résistance disparaît quand le plus haut pivot est le plus récent

*Version live uniquement.* C'est la cause principale.

L'ancrage retient le pivot haut le plus élevé de la fenêtre, puis cherche la pente
parmi les pivots **strictement postérieurs** :

```pine
for i = 0 to n_ph - 1
    int bb = array.get(ph_bar, i)
    if bb > a_bar                      // aucun pivot après l'ancrage → jamais vrai
        ...
        s_max := sl
```

Si le plus haut pivot est le plus récent (`a_idx == 0`), aucun `i` ne satisfait
`bb > a_bar`, donc `s_max` reste `na`, donc `best_x1 := na` → **aucune ligne**.

Ce cas correspond exactement à une jambe haussière qui fait des plus hauts. La
résistance s'évapore alors pendant au minimum `2 × tl_piv_len` = **20 barres** :
10 pour former le pivot suivant, 10 pour le confirmer.

### 1.2 Le filtre de touches est mathématiquement vide

*Les deux versions, côté support ; version disque, côté résistance aussi.*

`f_count_touches(x1_v, y1_v, slope, …)` compte les pivots situés dans le buffer de
la droite. Or les deux pivots qui **construisent** la droite sont dessus par
définition, et passent tous deux les gardes (`px >= x1`, fenêtre) :

- pivot `j` en `x1_v` : `tl_y == y1_v`, écart nul → compté
- pivot `i` en `x2_v` : `tl_y == y2_v`, écart nul → compté

Le compte vaut donc **toujours ≥ 2**, et `if touches >= 2` ne rejette jamais rien.
Conséquence : **n'importe quelle paire de pivots constitue une « trendline
valide »**. L'input `tl_min_touches` (défaut 3) n'est jamais lu — le tooltip
l'admet déjà (« inactif »).

### 1.3 La passe de repli trace une ligne du mauvais côté du prix

*Les deux versions.*

Support, première passe : exige `tl_now < close`. Si rien n'est trouvé, la seconde
passe **retire cette condition** :

```pine
if not found2
    ...
    if dist < bot_dist            // plus aucun test de côté
```

→ un « support » tracé **au-dessus** du prix. Même schéma pour la résistance sur
disque (`:1350`) → résistance **sous** le prix.

Combiné à 1.2, le repli trouve toujours quelque chose : une ligne est
quasi systématiquement tracée, **même en l'absence totale de structure**.

### 1.4 `best_tc := 2` codé en dur

*Version live.* Le garde-fou `best_tc >= 2` de `tl_val` est donc toujours vrai, et
`f_count_touches` n'est plus appelée que par le support — code mort côté résistance.

### 1.5 Les ronds de cassure ne peuvent pas coller à la ligne dessinée

*Les deux versions.* `breakout_signal` est évalué à chaque barre avec la trendline
telle qu'elle existait *à ce moment*, alors que seule la ligne finale est dessinée
à `barstate.islast`. Les ○ historiques ne sont donc pas sur la droite visible. Ça
se lit comme « la trendline est fausse » alors que c'est un décalage d'affichage.

### 1.6 Détails qui trompent

- `tl_extend` annonce « à l'infini » mais trace `bar_index + 50`, et `extend.right`
  n'est pas utilisé.
- `tl_lb_bull_lo` et `tl_lb_bull_hi` valent tous deux `100` → le switch par unité
  de temps est un no-op pour le support.
- `max_i = 19` / `max_j = 29` : caps asymétriques et silencieux sur les paires
  examinées (rien n'est loggé).
- `tl_max_lines` est inactif : une seule ligne par côté.

## 2. Principe du correctif

Celui de la méthode Ephore elle-même — *pas de confluence, pas de trade* :

> **Pas de structure, pas de ligne.**
> Une trendline absente est une information. Une trendline inventée est un piège.

Sept changements :

1. **Supprimer les deux passes de repli.** Rien de valide → rien de dessiné.
2. **Compte de touches réel** : les 2 ancrages comptent, mais il faut atteindre
   `tl_min_touches` au total → au moins 1 confirmation indépendante.
3. **Test de non-violation (hull)** : rejeter la droite si un pivot postérieur à
   l'ancrage la dépasse de plus que le buffer. Une résistance déjà transpercée
   n'est plus une résistance. C'est ce test qui fait qu'une ligne « a l'air juste ».
4. **Écart minimum entre ancrages** (`tl_min_span × tl_piv_len`, défaut 20 barres)
   pour ne pas tracer sur deux vaguelettes voisines.
5. **Classement des candidates** : touches ↓, puis longueur ↓, puis proximité ↑ —
   plus seulement la proximité.
6. **Persistance** : la ligne est créée comme objet `line` dès qu'elle est validée,
   prolongée à chaque barre, puis **figée** à sa cassure. Corrige 1.5 et donne
   l'historique visuel des trendlines cassées.
7. **Coût d'exécution** : la recherche ne tourne que sur confirmation d'un nouveau
   pivot ou juste après une cassure — pas à chaque barre.

Le point 1 seul devrait supprimer la majorité de l'intermittence. 2 et 3 font le reste.

## 3. Bloc de remplacement

Remplace **toute** la section `=== EPHORE TRENDLINES V1 ===` **et** le groupe
`=== TREND HAUSSIÈRE (Support Ascendant) ===`, depuis `grp_tl = …` jusqu'à la fin
des blocs de dessin `asc_lines` — c'est-à-dire juste avant
`// EPHORE ROUND LEVELS V1`.

Conserve les blocs `tl_ph` / `tl_pl` et les tableaux `ph_price`/`ph_bar`,
`pl_price`/`pl_bar` : ils sont réutilisés tels quels. Les noms `breakout_signal` et
`breakdown_signal` sont préservés — ils sont consommés par les `alertcondition` en
fin de fichier.

```pine
// ══════════════════════════════════════════════════════════════
// EPHORE TRENDLINES V2 — Résistance descendante + Support ascendant
// ══════════════════════════════════════════════════════════════
// Règle : pas de structure valide → aucune ligne tracée.
// Une droite n'est retenue que si :
//   (a) ses 2 ancrages sont séparés d'au moins tl_min_span × tl_piv_len barres
//   (b) elle est du bon côté du prix (résistance au-dessus, support en dessous)
//   (c) aucun pivot postérieur à l'ancrage ne la dépasse (test de hull)
//   (d) elle totalise au moins tl_min_touches pivots dans son buffer
// La ligne validée est figée à sa cassure → l'historique reste visible et les
// marqueurs de cassure tombent sur la droite réellement dessinée.
grp_tl = "=== EPHORE TRENDLINES V2 ==="

tl_enable      = input.bool(true, "Activer Trendlines", group=grp_tl)
tl_piv_len     = input.int(10, "Force des pivots (barres de chaque côté)",
     group=grp_tl, minval=2, maxval=50,
     tooltip="Barres de chaque côté d'un sommet/creux pour le valider comme pivot.")
tl_buffer      = input.float(0.1, "Tolérance de touche (% du prix)",
     group=grp_tl, minval=0.01, maxval=5.0, step=0.05)
tl_min_touches = input.int(3, "Touches minimum (ancrages inclus)",
     group=grp_tl, minval=2, maxval=10,
     tooltip="3 = les 2 ancrages + 1 confirmation indépendante. 2 = permissif.")
tl_min_span    = input.int(2, "Écart minimum entre ancrages (× force des pivots)",
     group=grp_tl, minval=1, maxval=10)
tl_hold        = input.bool(true, "Garder la ligne jusqu'à sa cassure", group=grp_tl)
tl_ext_right   = input.int(30, "Prolongation à droite (barres)",
     group=grp_tl, minval=0, maxval=200)

tl_color       = input.color(#000000, "Couleur résistance descendante", group=grp_tl, inline="tlcol")
tl_width       = input.int(2, "Épaisseur", group=grp_tl, minval=1, maxval=5, inline="tlcol")
tl_lb_bear_lo  = input.int(250, "Résistance : fenêtre de recherche, TF < 30 min", group=grp_tl, minval=10, maxval=2000)
tl_lb_bear_hi  = input.int(150, "Résistance : fenêtre de recherche, TF ≥ 30 min", group=grp_tl, minval=10, maxval=2000)
tl_show_break  = input.bool(true, "Cassures haussières (prix casse la résistance)", group=grp_tl, inline="brk")
tl_break_col   = input.color(#90EE90, "Couleur", group=grp_tl, inline="brk")

grp_bl = "=== TREND HAUSSIÈRE (Support Ascendant) ==="
bl_enable      = input.bool(true, "Activer trend haussière", group=grp_bl)
bl_color       = input.color(#FFFFFF, "Couleur support ascendant", group=grp_bl, inline="blcol")
bl_width       = input.int(2, "Épaisseur", group=grp_bl, minval=1, maxval=5, inline="blcol")
tl_lb_bull_lo  = input.int(150, "Support : fenêtre de recherche, TF < 30 min", group=grp_bl, minval=10, maxval=2000)
tl_lb_bull_hi  = input.int(100, "Support : fenêtre de recherche, TF ≥ 30 min", group=grp_bl, minval=10, maxval=2000)
bl_show_break  = input.bool(true, "Cassures baissières (prix casse le support)", group=grp_bl, inline="blbrk")
bl_break_col   = input.color(#EF5350, "Couleur", group=grp_bl, inline="blbrk")

tl_is_low_tf  = timeframe.in_seconds(timeframe.period) < 30 * 60
tl_lookback   = tl_is_low_tf ? tl_lb_bull_lo : tl_lb_bull_hi   // support
tl_macro_look = tl_is_low_tf ? tl_lb_bear_lo : tl_lb_bear_hi   // résistance
tl_min_sep    = tl_min_span * tl_piv_len

// ── Pivots (inchangé) ──────────────────────────────────────────
tl_ph = ta.pivothigh(high, tl_piv_len, tl_piv_len)

var float[] ph_price = array.new_float(0)
var int[]   ph_bar   = array.new_int(0)

if not na(tl_ph)
    array.unshift(ph_price, tl_ph)
    array.unshift(ph_bar,   bar_index - tl_piv_len)
    if array.size(ph_price) > 50
        array.pop(ph_price)
        array.pop(ph_bar)

tl_pl = ta.pivotlow(low, tl_piv_len, tl_piv_len)

var float[] pl_price = array.new_float(0)
var int[]   pl_bar   = array.new_int(0)

if not na(tl_pl)
    array.unshift(pl_price, tl_pl)
    array.unshift(pl_bar,   bar_index - tl_piv_len)
    if array.size(pl_price) > 50
        array.pop(pl_price)
        array.pop(pl_bar)

// ── Géométrie ──────────────────────────────────────────────────
f_tl_value(x1, y1, slope, x) =>
    y1 + slope * (x - x1)

// Recherche de la meilleure droite valide.
// `run` court-circuite le calcul : la fonction ne coûte rien quand on n'en a pas
// besoin (aucun ta.* ni var à l'intérieur → appel conditionnel sans effet de bord).
// is_res = true  → résistance sur pivots hauts (pente ≤ 0, au-dessus du prix)
// is_res = false → support    sur pivots bas  (pente ≥ 0, en dessous du prix)
f_best_line(run, pp, pb, is_res, lb, buf_pct, min_sep, min_touch, px_ref) =>
    float b_x1   = na
    float b_y1   = na
    float b_sl   = na
    int   b_tc   = 0
    int   b_span = 0
    float b_dist = 999999.0
    int   sz     = array.size(pp)

    if run and sz >= 2
        int cap = math.min(sz - 1, 11)          // paires : 12 pivots les plus récents
        int hull_cap = math.min(sz - 1, 29)     // hull/touches : 30 pivots
        for i = 0 to cap - 1
            for j = i + 1 to cap
                int   xa = array.get(pb, i)     // le plus récent
                float ya = array.get(pp, i)
                int   xb = array.get(pb, j)     // le plus ancien = ancrage
                float yb = array.get(pp, j)

                if xa > xb and (xa - xb) >= min_sep and (bar_index - xb) <= lb
                    float sl = (ya - yb) / (xa - xb)
                    if (is_res and sl <= 0) or (not is_res and sl >= 0)
                        float now_y = f_tl_value(xb, yb, sl, bar_index)
                        bool side_ok = is_res ? now_y > px_ref : now_y < px_ref
                        if side_ok
                            bool viol = false
                            int  tc   = 0
                            for k = 0 to hull_cap
                                int   xk = array.get(pb, k)
                                float yk = array.get(pp, k)
                                if xk >= xb and (bar_index - xk) <= lb
                                    float ly = f_tl_value(xb, yb, sl, xk)
                                    float bf = math.abs(ly) * buf_pct / 100.0
                                    if is_res and yk > ly + bf
                                        viol := true
                                    if (not is_res) and yk < ly - bf
                                        viol := true
                                    if math.abs(yk - ly) <= bf
                                        tc += 1
                            if not viol and tc >= min_touch
                                int   span = xa - xb
                                float dist = math.abs(px_ref - now_y) / px_ref * 100.0
                                bool better = tc > b_tc
                                if tc == b_tc and span > b_span
                                    better := true
                                if tc == b_tc and span == b_span and dist < b_dist
                                    better := true
                                if better
                                    b_x1   := float(xb)
                                    b_y1   := yb
                                    b_sl   := sl
                                    b_tc   := tc
                                    b_span := span
                                    b_dist := dist
    [b_x1, b_y1, b_sl, b_tc]

// ══════════════════════════════════════════════════════════════
// RÉSISTANCE DESCENDANTE — état persistant
// ══════════════════════════════════════════════════════════════
var float res_x1 = na
var float res_y1 = na
var float res_sl = na
var int   res_tc = 0
var line  res_ln = na
var bool  res_on = false

float res_now = res_on ? f_tl_value(res_x1, res_y1, res_sl, bar_index) : na
float res_buf = res_on ? math.abs(res_now) * tl_buffer / 100.0 : na

// Cassure = clôture franche au-delà de la droite (règle Ephore : pas juste une mèche)
breakout_signal = tl_enable and tl_show_break and res_on and close > res_now + res_buf

if breakout_signal
    if not na(res_ln)
        line.set_xy2(res_ln, bar_index, res_now)   // on fige la ligne sur la cassure
    res_ln := na
    res_on := false

bool res_run = tl_enable and (not res_on or not tl_hold) and (not na(tl_ph) or breakout_signal)
[rc_x1, rc_y1, rc_sl, rc_tc] = f_best_line(res_run, ph_price, ph_bar, true,
     tl_macro_look, tl_buffer, tl_min_sep, tl_min_touches, close)

if not na(rc_x1)
    if res_on and not na(res_ln)
        line.delete(res_ln)                        // remplacement (tl_hold = off)
    res_x1 := rc_x1
    res_y1 := rc_y1
    res_sl := rc_sl
    res_tc := rc_tc
    res_on := true
    res_ln := line.new(int(rc_x1), rc_y1, bar_index,
         f_tl_value(rc_x1, rc_y1, rc_sl, bar_index),
         xloc=xloc.bar_index, color=tl_color, width=tl_width, style=line.style_solid)

if res_on and not na(res_ln)
    int rx = bar_index + tl_ext_right
    line.set_xy2(res_ln, rx, f_tl_value(res_x1, res_y1, res_sl, rx))

plotshape(breakout_signal, title="TL Breakout", style=shape.circle,
     location=location.belowbar, color=tl_break_col, size=size.tiny)

// ══════════════════════════════════════════════════════════════
// SUPPORT ASCENDANT — état persistant
// ══════════════════════════════════════════════════════════════
var float sup_x1 = na
var float sup_y1 = na
var float sup_sl = na
var int   sup_tc = 0
var line  sup_ln = na
var bool  sup_on = false

float sup_now = sup_on ? f_tl_value(sup_x1, sup_y1, sup_sl, bar_index) : na
float sup_buf = sup_on ? math.abs(sup_now) * tl_buffer / 100.0 : na

breakdown_signal = bl_enable and bl_show_break and sup_on and close < sup_now - sup_buf

if breakdown_signal
    if not na(sup_ln)
        line.set_xy2(sup_ln, bar_index, sup_now)
    sup_ln := na
    sup_on := false

bool sup_run = bl_enable and (not sup_on or not tl_hold) and (not na(tl_pl) or breakdown_signal)
[sc_x1, sc_y1, sc_sl, sc_tc] = f_best_line(sup_run, pl_price, pl_bar, false,
     tl_lookback, tl_buffer, tl_min_sep, tl_min_touches, close)

if not na(sc_x1)
    if sup_on and not na(sup_ln)
        line.delete(sup_ln)
    sup_x1 := sc_x1
    sup_y1 := sc_y1
    sup_sl := sc_sl
    sup_tc := sc_tc
    sup_on := true
    sup_ln := line.new(int(sc_x1), sc_y1, bar_index,
         f_tl_value(sc_x1, sc_y1, sc_sl, bar_index),
         xloc=xloc.bar_index, color=bl_color, width=bl_width, style=line.style_solid)

if sup_on and not na(sup_ln)
    int sx = bar_index + tl_ext_right
    line.set_xy2(sup_ln, sx, f_tl_value(sup_x1, sup_y1, sup_sl, sx))

plotshape(breakdown_signal, title="TL Breakdown", style=shape.circle,
     location=location.abovebar, color=bl_break_col, size=size.tiny)
```

## 4. Ce qui change à l'écran

| Avant | Après |
|---|---|
| Une ligne presque toujours affichée, parfois du mauvais côté du prix | Ligne affichée seulement si la structure existe — périodes sans ligne, c'est normal et voulu |
| Ligne recalculée à chaque barre, saute d'une paire de pivots à l'autre | Ligne stable, adoptée une fois, figée à sa cassure |
| ○ de cassure éparpillés hors de la droite visible | ○ sur l'extrémité de la droite figée |
| `tl_min_touches` ignoré | Actif : 3 = 2 ancrages + 1 confirmation |
| Droite pouvant traverser des sommets postérieurs | Test de hull : aucun pivot ne la dépasse |

## 5. À vérifier après collage

Non vérifié de mon côté : **je n'ai pas pu compiler ni exécuter ce code** — pas
d'accès TradingView. La logique est raisonnée, pas observée. À contrôler dans cet
ordre :

1. **Compilation.** Points de risque : la déstructuration de tuple
   (`[rc_x1, …] = f_best_line(…)`) est au scope global, c'est voulu — ne pas la
   déplacer dans un `if`. Vérifier aussi qu'aucun nom n'entre en collision avec le
   reste du fichier (`tl_*`, `res_*`, `sup_*` ont été choisis pour l'éviter ;
   `bs_x1`, `best_x1`, `best_tc`, `desc_lines`, `asc_lines` disparaissent).
2. **Temps d'exécution.** La triple boucle est bornée à 12×12/2 paires × 30 pivots
   ≈ 2 000 itérations, et ne tourne que sur confirmation de pivot. Si TradingView
   râle quand même, baisser `cap` de 11 à 7.
3. **Densité de lignes.** Sur MES 15 min, comparer visuellement au Breakator
   original. Si trop peu de lignes : `tl_min_touches` à 2. Si trop : `tl_min_span`
   à 3.
4. **Calibration chiffrée.** Même protocole que le Signator : exporter un CSV avec
   `breakout_signal` + la colonne Breakator de l'original sur les ~4 500 barres MES
   15 min déjà disponibles, puis mesurer couverture/précision. C'est le seul moyen
   de savoir si le correctif réplique vraiment l'original, plutôt que d'avoir l'air
   juste.

## 6. Reste ouvert (hors trendlines)

- `tl_max_lines` reste inactif : 1 ligne par côté. Plusieurs trendlines simultanées
  demanderaient un tableau d'états persistants, pas juste un jeu de `var`.
- Validation de cassure incomplète vs `document-de-reference` §4 : il manque
  encore « prix reste du bon côté après cassure », alignement Moyenator, signal
  Heishinator dans le sens, et le blocage news 3★. Ces conditions existent ailleurs
  dans le fichier mais ne sont pas câblées sur `breakout_signal`.
- La version live devrait être commitée avant toute modification, sinon il n'y a
  aucun point de retour.
