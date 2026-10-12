# Pierre de Rosette des réglages d'Ephore — « Réglage NN » → vrais noms

> **Objet.** Le créateur d'Ephore a remplacé les libellés de ses paramètres par des numéros
> anonymes (`Réglage 1` … `Réglage 82`) dans la dernière version. Jeremy a fourni le panneau de
> réglages d'une **version ancienne**, où les mêmes paramètres portent encore **leurs vrais noms**,
> dans le **même ordre de déclaration**. Ce document aligne les deux et donne la table complète.
>
> Source : captures `11.png`–`17.png` (ancienne version, noms réels) et `18.png`–`31.png`
> (dernière version, numéros), du dossier d'images de la session du 2026-10-12.
> Méthode : lecture de chaque capture à l'échelle native, puis **seconde lecture indépendante**
> des zones porteuses de chiffres et des en-têtes, par recadrage + agrandissement ×3 à ×4
> (Pillow/LANCZOS). Toute valeur sur laquelle les deux lectures n'ont pas concordé est marquée `?`.
>
> **Aucun `.pine` n'a été modifié.**

---

## 0. Preuve de complétude (à lire en premier)

Les numéros relevés dans la dernière version vont de **1 à 82, sans aucun trou** :

```
1 2 3 4 | 5 6 | 7 … 22 | 23 … 27 | 28 29 | 30 … 35 | 36 37 | 38 … 58
59 60 61 62 | 63 64 65 | 66 … 71 | 72 | 73 | 74 … 78 | 79 | 80 81 | 82
```

Les 82 numéros sont présents exactement une fois. **La capture de la dernière version est donc
complète** : aucun « Réglage NN » ne manque. Les seules lacunes sont des lignes **non numérotées**
(un en-tête de sous-section, cf. §6).

Deuxième preuve, croisée : l'ancienne version reconstitue **exactement les 67 valeurs** de la
ligne 1 de la légende TradingView décodée dans `tools/NOTES_LEGENDE_PARAMS.md`
(« Ephore Market Ultimate v30 »), dans l'ordre, sans décalage. **L'ancien panneau EST la v30.**
Et la dernière version reconstitue la ligne 4 de cette même légende (preset « Intraday (15m-1h) »),
y compris son en-tête `Middle Left Large 8 60 📅? Normal 🔵 Bleu à gauche` — voir §5.

Lecture structurelle du numérotage : **1 → 58** couvrent les inputs non-booléens dans l'ordre de
déclaration (première passe d'anonymisation) ; **59 → 82** couvrent les cases à cocher et les
paramètres ajoutés après (seconde passe). C'est pour cela que la numérotation « saute » à l'écran.

---

## 1. TABLE DE CORRESPONDANCE COMPLÈTE

Légende de la confiance :
**A** = alignement positionnel strict dans la même section, même type, même valeur (certitude).
**B** = alignement positionnel, valeur différente (le paramètre a été re-réglé entre les versions).
**C** = pas d'équivalent dans l'ancienne version → **paramètre nouveau**, nom réel inconnu.

### 1.1 `=== EPHORE DETECTOR V6 ===`

| Réglage | Nom réel (ancienne version) | Type | Valeur (nouvelle) | Valeur (ancienne) | Conf. |
|---|---|---|---|---|---|
| **1** | `Volume Pivot Length` | nombre | 5 | 5 | **A** |
| **2** | `Bullish Detector` | nombre + 3 couleurs | 3 | 3 | **A** |
| **3** | `Bearish Detector` | nombre + 3 couleurs | 3 | 3 | **A** |
| — | `Average Line Style` (non anonymisé) | liste | ——— | ——— | A |
| — | `Average Line Width` (non anonymisé) | nombre | 1 | 1 | A |
| **4** | `Mitigation Methods` | liste | Mèche | Mèche | **A** |
| **72** | *(aucun)* — interrupteur du bloc d'atténuation | case cochée | ☑ | absent | **C** |
| **59** | *(aucun)* | liste | Griser | absent | **C** |
| **60** | *(aucun)* | nombre | 1.5 | absent | **C** |
| **80** | *(aucun)* | liste | % fixe | absent | **C** |
| **81** | *(aucun)* | nombre | 0.1 | absent | **C** |
| **61** | *(aucun)* | case cochée (ⓘ) | ☑ | absent | **C** |
| — | `Couleur atténuée` (non anonymisé) | couleur | damier/transparent | absent | C |
| **62** | *(aucun)* | case décochée | ☐ | absent | **C** |

> Le sous-bloc 72/59/60/80/81/61/`Couleur atténuée`/62 est **nouveau** et il est **dans le
> Detector**, pas ailleurs : c'est l'atténuation (« Griser ») d'un order block à **1.5 % fixe**
> avec une tolérance **0.1**. Cela tranche la question P4 de `NOTES_LEGENDE_PARAMS.md`, qui
> hésitait entre le Detector et un effet cosmétique sur les bougies. Et la légende lisait
> « 1,5 % fixe » comme **une** valeur : ce sont en réalité **deux** inputs (`1.5` puis `% fixe`).

### 1.2 `=== EPHORE HEISHINATOR V4 ===`

Section **entièrement non anonymisée**, identique dans les deux versions :
`🎨 Personnaliser Couleurs` (☐), `Couleur Bougie Haussière` (bleu), `Couleur Bougie Baissière`
(rouge). Aucun paramètre numérique — cohérent avec le fait que la formule Heishinator est codée
en dur (cf. MEMOIRE §5 : `EMA(ohlc4,4) > EMA(ohlc4,32)`).

### 1.3 `=== EPHORE SIGNATOR V6 ===`

| Réglage | Nom réel | Type | Valeur (nouvelle) | Valeur (ancienne) | Conf. |
|---|---|---|---|---|---|
| — | `⚪ Afficher Tableau Signator` | case | **supprimé** | ☑ | — |
| — | `Position Tableau` | liste | **supprimé** | Top Right | — |
| — | `🎨 Personnaliser Couleurs Flèches` | case | ☑ | ☑ | A |
| **63** | `Afficher flèches FORT` | case | ☑ | ☑ | **A** |
| — | `Couleur flèche Long (FORT)` | couleur | blanc | blanc | A |
| — | `Couleur flèche Short (FORT)` | couleur | noir | noir | A |
| **64** | `Afficher flèches MOYEN` | case | ☑ | ☑ | **A** |
| — | `Couleur flèche Long (MOYEN)` | couleur | **blanc** | **orange** | B |
| — | `Couleur flèche Short (MOYEN)` | couleur | **noir** | **violet** | B |
| — | `Style des signaux` (nouveau, nommé) | liste | Flèches… | absent | C |
| — | `Taille des labels de signaux` (nouveau) | liste | Normale | absent | C |
| — | `Historique des labels de signaux` (nouveau) | nombre | 250 | absent | C |
| **65** | `Activer Filtre` | case | **☑ coché** | **☐ décoché** | **A** |
| **5** | `Seuil de Force (Min)` | nombre | 18 | 18 | **A** |
| **6** | `Mode de Lag` | liste | Normal | Normal | **A** |

> Deux faits importants :
> 1. **`Réglage 5` = « Seuil de Force (Min) » = 18.** C'est notre `sg_force`. Confirmation
>    directe, par le panneau, de la valeur calée sur données (MEMOIRE §5 : optimum net à 18).
> 2. Le tableau Signator et sa position **ont disparu** de la dernière version : ils ont été
>    absorbés par la nouvelle **TABLE UNIFIÉE** (§3.1). Cela explique pourquoi le tableau
>    Signator « ancienne version » que Jeremy voulait dans `TABLEAU.pine` n'existe plus chez lui.
> 3. `Réglage 65` (**Activer Filtre**) est **coché** dans la version actuelle. C'est la
>    confirmation panneau du constat de MEMOIRE §5 (exports `Filtres/`, filtre ON).

### 1.4 `=== CANDLE QUALITY FILTER V1 ===`

| Réglage | Nom réel | Type | Valeur | Conf. |
|---|---|---|---|---|
| — | `⚪ Activer le Filtre Qualité Bougie` | case | ☑ | A |
| **66** | `① Activer Filtre Structure` | case | ☑ | **A** |
| **7** | `↳ Ratio Corps/Range Min` | nombre | 0.5 | **A** |
| **8** | `↳ Position Close (tiers)` | nombre | 0.33 | **A** |
| **9** | `↳ Mèche Adverse Max` | nombre | 0.35 | **A** |
| **67** | `② Activer Filtre Momentum ATR` | case | ☑ | **A** |
| **10** | `↳ Période ATR` | nombre | 14 | **A** |
| **11** | `↳ Range Min (x ATR)` | nombre | 0.5 | **A** |
| **68** | `③ Activer Filtre Volume` | case | ☑ | **A** |
| **12** | `↳ Période SMA Volume` | nombre | 20 | **A** |
| **13** | `↳ Ratio Volume Min` | nombre | 1 | **A** |
| **69** | `④ Activer Filtre Engulfing` | case | ☑ | **A** |
| **14** | `↳ Exiger Engulfing Complet` | case | ☑ | **A** |
| **70** | `⑤ Activer Filtre Gap Conviction` | case | ☑ | **A** |
| **15** | `↳ Type de Mesure` | liste | ATR | **A** |
| **16** | `↳ Gap Min (x ATR)` | nombre | 0.3 | **A** |
| **17** | `↳ Gap Min (%)` | nombre | 0.5 | **A** |
| **71** | `⑥ Utiliser Mode Scoring` | case | ☑ | **A** |
| **18** | `↳ Score Minimum (0-100)` | nombre | 50 | **A** |
| **19** | `↳ Poids Structure` | nombre | 25 | **A** |
| **20** | `↳ Poids Momentum` | nombre | 25 | **A** |
| **21** | `↳ Poids Volume` | nombre | 25 | **A** |
| **22** | `↳ Poids Gap` | nombre | 25 | **A** |

> **C'est le bloc le plus précieux du document.** Les cinq filtres sont **numérotés ① à ⑤** dans
> l'interface, et le **mode scoring est le ⑥**, séparé. Et surtout : il y a **quatre poids**
> (Structure, Momentum, Volume, Gap) pour **cinq filtres**. **L'Engulfing n'a pas de poids** :
> ce n'est pas une composante notée, c'est un **filtre dur** avec sa propre case
> (`④ Activer Filtre Engulfing` + `Exiger Engulfing Complet`).
> Conséquence et tension à trancher — voir §4.2.

### 1.5 `=== EPHORE TRENDLINES V1 ===`

| Réglage | Nom réel | Type | Valeur | Conf. |
|---|---|---|---|---|
| — | `⚪ Activer Trendlines` | case | ☑ | A |
| — | `🎨 Personnaliser Couleurs` | case | ☑ | A |
| **23** | `Pivot High Bars Required for Anchor` | nombre | 10 | **A** |
| **24** | `Price Buffer %` | nombre | 0.1 | **A** |
| **25** | `Minimum Number of Touches` | nombre | 3 | **A** |
| — | `Trendline Color` + `Width` | couleur + nombre | noir, 2 | A |
| — | `Extend Trendlines` | case | ☑ | A |
| **26** | `Look for New Pivot High after X Bars` | nombre | 100 | **A** |
| — | `Show Trendline Breakouts` + `Breakout Color` | case + couleur | ☑, vert | A |
| **27** | `Number of Trendlines to show` | nombre | 1 | **A** |
| — | `⚪ Activer Trendlines baissières (cassures short)` | case | ☑ | **C** |
| — | `Couleur support ascendant` | couleur | noir | **C** |
| — | `Couleur cassure baissière` | couleur | rouge | **C** |

> Les **libellés anglais d'origine sont conservés** : ils viennent mot pour mot du script public
> « Trendlines » d'Amphibiantrading (MPL 2.0), déjà identifié en MEMOIRE §5. Les valeurs
> 10 / 0.1 / 3 / 100 / 1 sont exactement celles validées par Jeremy. **Rien à corriger chez nous.**
> Le bloc « trendlines baissières » est une **addition récente** et porte des noms en clair.

### 1.6 `=== EPHORE RONDATOR V1 ===` (ancien nom : `=== EPHORE ROUND LEVELS V1 ===`)

| Réglage | Nom réel | Type | Valeur (nouvelle) | Valeur (ancienne) | Conf. |
|---|---|---|---|---|---|
| — | `⚪ Activer Niveaux Ronds` | case | **☑** | **☐** | B |
| — | `🎨 Personnaliser Couleurs` | case | ☑ | ☑ | A |
| **28** | `Intervalle entre les niveaux` | nombre | 100 | 100 | **A** |
| **29** | `Nombre de niveaux au-dessus/en dessous` | nombre | 10 | 10 | **A** |
| — | `Couleur des lignes` | couleur | damier | damier | A |
| — | `Épaisseur des lignes` | nombre | 1 | 1 | A |
| — | `Style des lignes` | liste | Solide | Solide | A |
| — | `Afficher les labels de prix` | case | **☐** | **☑** | B |
| — | `Position des labels` | liste | Gauche | Gauche | A |
| — | `Décalage des labels (barres)` | nombre | 150 | 150 | A |
| — | `Taille des labels` | liste | **small** | **normal** | B |

> **La section a été renommée « RONDATOR » entre les deux versions** (double lecture au zoom ×4 :
> `=== EPHORE RONDATOR V1 ===` d'un côté, `=== EPHORE ROUND LEVELS V1 ===` de l'autre).
> Cela **tranche P6 de `NOTES_LEGENDE_PARAMS.md`** : la suite `Solide / Gauche / 150 / <taille>`
> de la légende n'était ni le Rangeator ni un module PDH/PDL/ORB, c'est le **module de niveaux
> ronds**. Hypothèse (b) de P6 réfutée, hypothèse (a) partiellement vraie (c'est bien un module de
> niveaux horizontaux, mais des niveaux ronds, pas des niveaux de séance).

### 1.7 `--- TABLEAU VOLUME : TIMEFRAMES ---` et `=== EPHORE DASHATOR V6 ===`

| Nom réel | Type | Valeur (nouvelle) | Valeur (ancienne) | Conf. |
|---|---|---|---|---|
| `Position` (table volume) | liste | **supprimé** | Bottom … | — |
| `Taille` (table volume) | liste | **supprimé** | Normal | — |
| `TF[01]` | case + TF | ☑ 1 minute | ☑ 1 minute | A |
| `TF[02]` | case + TF | ☑ 5 minut… | ☑ 5 minut… | A |
| `TF[03]` | case + TF | ☑ 15 min… | ☑ 15 min… | A |
| `TF[04]` | case + TF | ☑ 1 heure | ☑ 1 heure | A |
| `TF[05]` | case + TF | ☑ 4 heures | ☑ 4 heures | A |
| `TF[06]` | case + TF | ☑ 1 jour | ☑ 1 jour | A |
| `TF[07]` | case + TF | **☐** 1 semai… | **☐** 1 semai… | A |
| `Position` (Dashator) | liste | **supprimé** | Middle … | — |
| `Taille` (Dashator) | liste | **supprimé** | Large | — |
| `🎨 Adapter couleurs au Skin` | case | ☑ | ☑ | A |

> **Aucun « Réglage NN » dans ce bloc** : le Dashator n'a pas été anonymisé du tout.
> **P7 de `NOTES_LEGENDE_PARAMS.md` est confirmé** : il y a bien **7** champs de TF, le 7ᵉ (1
> semaine) étant **décoché** — d'où les 6 colonnes visibles et les 6 voix « Tendances
> multi-unités » du Feu de Confluence. **À prévoir : 7 champs chez nous, pas 6.**
> Nouveauté : les TF sont désormais sous le sous-titre **`TABLEAU VOLUME : TIMEFRAMES`**, ce qui
> indique qu'ils alimentent le **tableau Volume**, pas le Dashator.

### 1.8 `=== EPHORE PIVATOR DUAL V2 ===`

| Réglage | Nom réel | Type | Valeur (nouvelle) | Valeur (ancienne) | Conf. |
|---|---|---|---|---|---|
| **30** | `Type` | liste | Traditio… | Traditio… | **A** |
| **31** | `Nombre de pivots en arrière` | nombre | 1 | 1 | **A** |
| **32** | `Utiliser des valeurs à base journalière` | case | ☑ | ☑ | **A** |
| — | `Afficher les étiquettes` | case | **☐** | **☑** | B |
| — | `Afficher les prix` | case | **☐** | **☑** | B |
| — | `Position des Etiquettes` | liste | Vrai | Vrai | A |
| — | `Largeur de la ligne` | nombre | **1** | **2** | B |
| — | *sous-titre* `--- ALERTES PIVOTS ---` | — | nouveau | absent | C |
| — | `Activer Alertes Set 1` | case | **☑** | **☐** | B |
| — | `Activer Alertes Set 2` | case | **☑** | **☐** | B |
| — | `Activer Alertes Set 3` | case | **☑** | **absent** | C |
| — | `🎨 Personnaliser Couleurs Set 1` | case | ☐ | ☐ | A |
| **33** | `Set 1 Timeframe` | liste | Annuel | Annuel | **A** |
| — | `P` + `S1..S5` / `R1..R5` (couleurs + cases) | — | toutes ☑ | toutes ☑ | A |
| — | `Enable Set 2` | case | ☑ | ☑ | A |
| — | `🎨 Personnaliser Couleurs Set 2` | case | ☐ | ☐ | A |
| **34** | `Set 2 Timeframe` | liste | Mensuel | Mensuel | **A** |
| — | `P` + `S/R` Set 2 | — | toutes ☑ | toutes ☑ | A |
| **35** | `Set 3 Timeframe` | liste | **Hebdo…** | **absent** | **C** |
| — | `P` + `S/R` Set 3 | — | toutes ☑ | absent | C |

> `Position des Etiquettes = Vrai` : relu deux fois au zoom ×4 dans les **deux** versions. C'est
> bien « Vrai » (une liste déroulante qui affiche une valeur booléenne — vraisemblablement un
> `input.string` dont les options ont été mal renseignées par l'auteur). La légende TradingView
> affichait `Right` à cette position dans la v30 : **désaccord non résolu**, probablement une
> différence de build entre la v30 de la légende et le panneau capturé. Sans impact.
> Le **Set 3 hebdomadaire est bien une addition récente**, comme chez nous (V5 → V8).

### 1.9 `=== EPHORE MOYENATOR V5 ===`

| Réglage | Nom réel | Type | Valeur (nouvelle) | Valeur (ancienne) | Conf. |
|---|---|---|---|---|---|
| — | `🎨 Personnaliser Couleurs` | case | ☐ | ☐ | A |
| — | `Afficher Moyenator 1` | case | ☑ | ☑ | A |
| **36** | `Source Moyenator 1` | source | Clôture | Clôture | **A** |
| — | `Couleur ligne Moyenator 1` | couleur | noir | noir | A |
| — | `Épaisseur Moyenator 1` | nombre | **1** | **2** | B |
| — | `Afficher Moyenator 2` | case | ☑ | ☑ | A |
| **37** | `Source Moyenator 2` | source | Clôture | Clôture | **A** |
| — | `Couleur ligne Moyenator 2` | couleur | noir | noir | A |
| — | `Épaisseur Moyenator 2` | nombre | 1 | 1 | A |
| — | `Afficher le remplissage` | case | ☑ | ☑ | A |
| — | `Couleur haussière (Moyenator 1 > Moyenator 2)` | couleur | bleu clair | bleu clair | A |
| — | `Couleur baissière (Moyenator 1 < Moyenator 2)` | couleur | rouge | rouge | A |
| — | `Opacité du remplissage (0=opaque, 100=transparent)` | nombre | 0 | 0 | A |
| **79** | `Pas de couleur si Moyenator 1 = Moyenator 2` | case | ☑ | ☑ | **A** |

> **Point capital : il n'existe AUCUN input de période pour le Moyenator.** Ni 50, ni 60, nulle
> part, dans aucune des deux versions. Les périodes EMA50/EMA60 sont **codées en dur** dans
> l'original. Notre implémentation est donc structurellement correcte, et il est inutile de
> chercher ces valeurs dans la légende.

### 1.10 `📊 NOUVEAUX DASHBOARDS` (ancienne version uniquement)

| Nom réel | Type | Valeur | Devenu quoi |
|---|---|---|---|
| `⚪ Afficher Table INDICATOR\|SIGNAL` | case | ☑ | → `Colonne SIGNAL` de la TABLE UNIFIÉE |
| `⚪ Afficher Table TIMEFRAME\|TREND` | case | ☑ | → `Colonnes TREND et STRENGTH` |
| `Position Table Indicators` | liste | Bottom … | → `Position` de la TABLE UNIFIÉE |
| `Position Table Timeframes` | liste | Bottom … | → idem |
| `Taille Texte` | liste | Normal | → `Taille` |
| `Afficher Emojis` | case | ☑ | → `Puces devant les états` (?) |

> **C'est la clé du chantier « tableaux » de MEMOIRE §6.3 :** les deux tableaux
> `INDICATOR | SIGNAL` et `TIMEFRAME | TREND | STRENGTH` étaient, dans l'ancienne version,
> **deux tableaux séparés** avec leur position propre. Dans la dernière version ils ont **fusionné**
> en une seule TABLE UNIFIÉE à colonnes activables. Les captures d'écran de tableaux prises avant
> et après la bascule ne décrivent donc pas le même objet — à prendre en compte en calibration.

---

## 2. SECTIONS ENTIÈREMENT NOUVELLES (absentes de l'ancienne version)

Quatre modules, transcrits exhaustivement. **Trois des quatre ne sont pas anonymisés du tout** :
Blackout et Monday High Low portent leurs vrais noms, la Table Unifiée n'a qu'un seul numéro.
Seul le **Rangeator** est massivement anonymisé (21 numéros) : c'est manifestement le module que
l'auteur protège le plus.

### 2.1 `📁 TABLE UNIFIÉE` — tout en haut du panneau

| Libellé | Type | Valeur | État |
|---|---|---|---|
| `Position` | liste | Bottom … *(tronqué par l'UI)* | — |
| `Taille` | liste | Normal | — |
| `📐 Taille fine en points` | case | — | ☐ |
| `Points` | nombre | 8 | — |
| `⚪ Colonne SIGNAL` | case | — | ☑ |
| `⚪ Colonnes TREND et STRENGTH` | case | — | ☑ |
| `⚪ Puces devant les états` | case | — | ☐ |
| `🚦 Feu de Confluence (agrégat de la table)` | case | — | ☑ |
| **`Réglage 82`** | nombre | **60** | — |
| `🧲 Disposition des cellules` | liste | 🚦 Feu … *(tronqué)* ⓘ | — |
| `Côté des camps` | liste | 🔵 Bleu… *(tronqué)* | — |

> **`Réglage 82` = 60 = le seuil du Feu de Confluence.** Recoupement direct avec MEMOIRE §9 :
> l'API publique du terminal expose « Feu de Confluence : 29 votes, **seuil 60 %** ». C'est le
> même nombre, au même endroit, dans le module qui porte le même nom. **Confiance haute.**
> `Points = 8` est la taille de police en points (activable par `Taille fine en points`).

### 2.2 `⛔ BLACKOUT NO-TRADE` — **le module d'annonces, enfin en clair**

Aucun paramètre anonymisé. Transcription intégrale :

**Bloc principal**

| Libellé | Type | Valeur | État |
|---|---|---|---|
| `Activer Blackout` | case | — | ☑ |
| `Minutes avant` | nombre | 3 | — |
| `Minutes après` | nombre | 3 | — |
| `Bloquer les signaux pendant le blackout` ⓘ | case | — | ☑ |
| `Bloquer aussi les BREAK Rangeator` ⓘ | case | — | ☐ |
| `Couleur de la zone` | couleur | rouge | — |
| `Transparence zone` | nombre | 90 | — |
| `Projeter les fenêtres à venir` ⓘ | case | — | ☑ |
| `Horizon de projection (heures)` ⓘ | nombre | 24 | — |

**`⛔ BLACKOUT · FUSEAUX`**

| Libellé | Type | Valeur |
|---|---|---|
| `Fuseau news/open US (ET)` ⓘ | liste | Americ… *(= America/New_York)* |
| `Fuseau open Europe` | liste | Europe/… *(= Europe/Paris)* |

**`⛔ BLACKOUT · OUVERTURES DE MARCHÉ`**

| Libellé | Type | H | M | État |
|---|---|---|---|---|
| `Open Europe` | case + H + M | 9 | 0 | ☑ |
| `Open US (ET)` | case + H + M | 9 | 30 | ☑ |

**`⛔ BLACKOUT · NEWS RÉCURRENTES (HEURE ET)`**

| Libellé | État |
|---|---|
| `NFP (1er vendredi 08:30 ET)` | ☑ |
| `Jobless Claims (chaque jeudi 08:30 ET)` | ☑ |
| `Données US 08:30 ET (CPI/PPI/Retail/GDP/PCE, tous jours)` | ☑ |
| `Données 10:00 ET (ISM/JOLTS/UMich, tous jours)` | ☑ |
| `FOMC (mercredi 14:00 ET)` ⓘ | ☐ |

**`⛔ BLACKOUT · CRÉNEAUX PERSONNALISÉS (HEURE ET)`**

| Libellé | Jour | H | M | 1ère occurrence du mois | État |
|---|---|---|---|---|---|
| `Créneau 1` | Tous | 14 | 30 | ☐ | ☐ |
| `Créneau 2` | Tous | 20 | 0 | ☐ | ☐ |

> **C'est la pièce la plus utile du lot pour nos chiffres.** Traduction en heure de Paris
> (ET + 6 h en été) :
> - `Données US 08:30 ET` → **14:30 Paris** ✔ ;
> - `Données 10:00 ET` → **16:00 Paris** ✔ ;
> - `Open US 09:30 ET` → **15:30 Paris** ;
> - `Open Europe 09:00` (heure de Paris, fuseau Europe) → **09:00 Paris**.
>
> Soit **exactement les quatre bandes rouges** mesurées sur le terminal web (MEMOIRE §9), et
> **exactement les deux horaires** que notre V8 bloque (14:30 / 16:00). Notre règle codée en dur
> n'est donc pas une approximation : c'est **le sous-ensemble « news » du module**, les deux
> autres bandes venant des **ouvertures de marché**, cochées sur le terminal web et pas sur
> TradingView.
>
> **Correction à `NOTES_LEGENDE_PARAMS.md` (P2).** Le découpage proposé était faux sur deux
> points : il n'y a **pas de « plage horaire de séance 09:00–20:00 »**. Le `9 0` est
> *Open Europe*, le `9 30` est *Open US*, le `14 30 Tous` est le *Créneau personnalisé 1* et le
> `20 0 Tous` le *Créneau personnalisé 2* — ces deux derniers étant **décochés**. Cela confirme
> par le panneau ce que MEMOIRE §5 avait déjà établi par la mesure (« piste morte : plage de
> séance… le `9 0 … 20 0` de la légende ne concerne PAS les flèches »). Les deux `Tous` sont des
> **sélecteurs de jour** des créneaux personnalisés, pas des sélecteurs de jour des news.
> En revanche la **marge ±3 minutes** (`Minutes avant` / `Minutes après`) est confirmée, et elle
> reste la seule piste non testée pour les 3 faux positifs résiduels.

### 2.3 `📦 RANGEATOR` — le module le plus protégé (21 numéros)

**Bloc principal**

| Réglage | Type | Valeur | État |
|---|---|---|---|
| — `Afficher le Rangeator` | case | — | ☑ |
| **38** | case | — | ☑ |
| **39** | case | — | ☑ |
| **73** | nombre | 100 | — |
| **40** | liste | Scalpin… *(= « Scalping Nasdaq (1-5m) »)* | — |

**`📦 RANGEATOR · DÉTECTION (MODE PERSONNALISÉ)`**

| Réglage | Type | Valeur |
|---|---|---|
| **41** | nombre | 22 |
| **42** | nombre | 0.34 |
| **43** | nombre | 3 |
| **44** | nombre | 8 |
| **45** | nombre | 1 |
| **46** | nombre | 1 |
| **47** | nombre | 0.45 |
| **48** | nombre | 0.12 |
| **49** | nombre | 20 |
| **50** | nombre | 61.8 |
| **51** | nombre | 0.3 |

**`📦 RANGEATOR · FILTRES OPTIONNELS`**

| Réglage | Type | Valeur | État |
|---|---|---|---|
| **74** | case | — | ☑ |
| **75** | case | — | ☑ |
| **52** | nombre | 20 | — |
| **76** | case | — | ☐ |
| **53** | nombre | 14 | — |
| **77** | case | — | ☐ |
| **54** | nombre | 14 | — |
| **55** | nombre | 14 | — |

**`📦 RANGEATOR · FIN DE RANGE`**

| Réglage | Type | Valeur | État |
|---|---|---|---|
| **56** | liste | ATR | — |
| **57** | nombre | 10 | — |
| **58** | nombre | 0 | — |
| **78** | case | — | ☑ |

**`📦 RANGEATOR · STYLE`**

| Libellé (non anonymisé) | Type | Valeur | État |
|---|---|---|---|
| `🎨 Personnaliser Couleurs` | case | — | ☑ |
| `Couleur range / contre-tendance` | couleur | gris | — |
| `Couleur cassure haussiere` | couleur | bleu | — |
| `Couleur cassure baissiere` | couleur | rouge | — |
| `Transparence remplissage` | nombre | 88 | — |
| `Epaisseur bordure` | nombre | 1 | — |
| `Afficher mediane (equilibre)` | case | — | ☑ |
| `Afficher infos (hauteur, duree)` | case | — | ☐ |
| `Afficher fleches de cassure` | case | — | ☐ |
| `Conserver les ranges passes` | case | — | ☑ |

**`📦 RANGEATOR · ALERTES`**

| Libellé | Type | État |
|---|---|---|
| `Activer alertes Rangeator` | case | ☑ |

> Les libellés du bloc STYLE sont **sans accents** (« mediane », « duree », « cassure
> haussiere »), contrairement au reste du panneau : signe d'un bloc écrit plus tard, à la hâte.

### 2.4 `📅 MONDAY HIGH LOW`

| Libellé | Type | Valeur | État |
|---|---|---|---|
| `Afficher Monday High Low` ⓘ | case | — | ☑ |
| `Couleur des lignes` | couleur | bleu | — |
| `Épaisseur` | nombre | 1 | — |
| `Historique (semaines)` ⓘ | nombre | 26 | — |

> Module minuscule et entièrement nommé : il trace le plus haut et le plus bas du **lundi**, sur
> 26 semaines d'historique. Jamais vu nulle part ailleurs dans le projet.

---

## 3. LE VERDICT DEMANDÉ : `22 0,34 3 8 1 1 0,45 0,12 20 61,8 0,3`

**C'est le RANGEATOR. Confiance : certitude.**

`tools/NOTES_LEGENDE_PARAMS.md` attribuait cette suite au Signator (fiche P1 pour
`22 0,34 3 8 1`, fiche P9 pour `1 0,45 0,12 20 61,8 0,3`), en supposant que `22` était un
Seuil de Force et `0,34` un seuil de conviction `dBand`. **C'est faux.**

La capture `29.png` donne la correspondance terme à terme, dans l'ordre, sous l'en-tête
`📦 RANGEATOR · DÉTECTION (MODE PERSONNALISÉ)` :

| légende L3, pos. 74→84 | 22 | 0,34 | 3 | 8 | 1 | 1 | 0,45 | 0,12 | 20 | 61,8 | 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **panneau actuel** | R41 | R42 | R43 | R44 | R45 | R46 | R47 | R48 | R49 | R50 | R51 |

Et les deux valeurs qui précèdent collent aussi :
- légende L3 pos. 72 = `100` → **`Réglage 73` = 100** (dans le bloc principal Rangeator) ;
- légende L3 pos. 73 = `Scalping Nasdaq (1-5m)` → **`Réglage 40`** = `Scalpin…`.

**Donc le « preset » nommé par style de trading n'est pas un preset global de l'indicateur : c'est
le preset de détection du Rangeator** (correction de la fiche P10). Le mode affiché dans le
panneau capturé est `MODE PERSONNALISÉ`, ce qui explique que les 11 valeurs soient éditables.

Pour la ligne 4 de la légende (preset « Intraday (15m-1h) »), les valeurs `86→90 = 22 0,34 3 8 1`
sont les **cinq premiers** réglages du même bloc : la ligne était simplement **tronquée** à
90 valeurs par la largeur de l'écran.

**Ce que cela règle définitivement :**
1. Les tests de MEMOIRE/`test_hypotheses_legende.py` qui « réfutaient » P1 (ADX 22 → 55 flèches
   perdues ; dBand 0,34 → légèrement pire) ne réfutaient rien du tout : ils testaient des valeurs
   d'un **autre module** sur le Signator. **Le Seuil de Force à 18 n'est pas contredit** — il est
   au contraire **confirmé par le panneau** (`Réglage 5 = 18`).
2. Le `61,8` n'a rien à voir avec un module d'entrée sur repli ni avec `fib_75` : c'est un
   paramètre de détection de range (très probablement un niveau de retracement interne au range).
3. Les signaux `v7a:ALLUMAGE` / `v7c:CONTINUATION` de l'API **n'ont toujours aucun réglage
   identifié**. L'hypothèse de repli formulée en fin de `NOTES_LEGENDE_PARAMS.md`
   (« `22 0,34 3 8 1` = réglages ALLUMAGE/CONTINUATION ») est **également fausse**. Il reste
   possible qu'ALLUMAGE/CONTINUATION soient **produits par le Rangeator** (cassure de range), ce
   qui serait cohérent avec `Bloquer aussi les BREAK Rangeator` du module Blackout : l'original
   appelle ses cassures de range des « **BREAK** ».

---

## 4. CE QUE CE DOCUMENT CONFIRME OU CORRIGE DANS `NOTES_LEGENDE_PARAMS.md`

### 4.1 Confirmé (et désormais prouvé, plus seulement supposé)

| fiche | contenu | verdict |
|---|---|---|
| §0 | la légende n'affiche ni les booléens ni les couleurs | **confirmé** : le panneau contient des dizaines de cases/couleurs absentes de la légende |
| Ancrage A | Detector `5 3 3 ——— 1 Wick` | **confirmé nom par nom** |
| Ancrage B | Trendlines `10 0,1 3 2 100 1` | **confirmé nom par nom**, libellés anglais d'Amphibiantrading intacts |
| bloc Signator 13 valeurs | les 13 noms proposés | **confirmés**, sauf détail : `Mode de Lag` existe bel et bien |
| P3 | `25 25 25 25` = pondérations du score | **confirmé** : `Poids Structure / Momentum / Volume / Gap` |
| P5 | `Flèches (défaut) / Normale / 250` | **confirmé** : `Style des signaux` / `Taille des labels de signaux` / `Historique des labels de signaux` |
| P7 | 7 champs TF dont un masqué | **confirmé** : `TF[07] = 1 semaine`, **décoché** |
| P2 (partie « c'est bien le filtre d'annonces ») | — | **confirmé** : module `BLACKOUT NO-TRADE` |
| Moyenator / Pivator | nos inputs | **confirmés**, y compris l'absence de période EMA paramétrable |

### 4.2 Corrigé

| fiche | ce qui était écrit | ce qu'il faut lire |
|---|---|---|
| **P1 / P9** | `22 0,34 3 8 1` et `1 0,45 0,12 20 61,8 0,3` = Signator (puis ALLUMAGE/CONTINUATION) | **Rangeator**, `Réglage 41…51`, sous `DÉTECTION (MODE PERSONNALISÉ)` |
| **P10** | preset global de l'indicateur, et `100` inconnu | **preset du Rangeator** (`Réglage 40`) ; le `100` est `Réglage 73`, du même module |
| **P2** | `9 0` / `20 0` = plage de séance 09:00–20:00 | `9 0` = **Open Europe**, `9 30` = **Open US (ET)**, `14 30 Tous` et `20 0 Tous` = **créneaux personnalisés décochés** |
| **P4** | `Griser 1,5 % fixe 0,1` = 3 inputs, module incertain | **4 inputs** (`Griser`, `1.5`, `% fixe`, `0.1`) + 3 autres, **dans le Detector**, avec `Couleur atténuée` |
| **P6** | `Solide Gauche 150 <taille>` = niveaux de séance ou Rangeator | **`EPHORE RONDATOR V1`** (ex-`ROUND LEVELS`), niveaux ronds |
| **P12** | en-tête L4 `Middle Left Large 8 60 📅 Normal 🔵 Bleu à gauche` = EMA 8/60 ? | **`TABLE UNIFIÉE`** : Position, Taille, `Points = 8`, **`Réglage 82 = 60` = seuil du Feu de Confluence**, `Disposition des cellules`, `Côté des camps` |
| **P8** | « au moins 5 emplacements de tableaux » | exact pour l'**ancienne** version (Signator + volume + Dashator + Indicators + Timeframes). Dans la **nouvelle**, tout est fusionné dans la TABLE UNIFIÉE : **un seul emplacement** |
| **P11** | thème = 5 inputs | exact pour la v30 (`Thème Global`, `Design Table Volume`, `Design Table SuperTrader`, `Style Bordures`, `Intensité (%)`). Dans la nouvelle version il ne reste que **`Thème Global`** |
| **§4 du document** | « 0,33 vs notre 0,67 » | le libellé réel est **`Position Close (tiers)` = 0.33**. « tiers » plaide pour un seuil exprimé en tiers de bougie, donc notre lecture `1 − 0,33 = 0,67` reste défendable ; la simulation les dit équivalentes (13 erreurs chacune). **Question laissée ouverte, impact nul.** |

### 4.3 La tension à ne pas enterrer : les 4 poids contre nos 5 composantes

Le panneau est formel : **4 poids à 25 %** (Structure, Momentum, Volume, Gap) et **pas de poids
pour l'Engulfing**, qui a sa propre case `④ Activer Filtre Engulfing` + `↳ Exiger Engulfing
Complet` (toutes deux **cochées**).

Or `test_hypotheses_legende.py` a mesuré que passer à 4 composantes à 25 % **dégrade** nos
résultats (9 faux positifs au lieu de 3). Les deux faits sont vrais en même temps. Trois lectures
possibles, par ordre de plausibilité :

1. **L'Engulfing est un filtre dur, pas une composante notée** — et comme il est **impossible à
   satisfaire en Heiken Ashi** (MEMOIRE §5 : « toujours 0 en HA »), le filtre ④ coché devrait
   tuer **tous** les signaux. Il ne le fait pas → donc en pratique l'original **ne l'applique
   pas** comme un veto, ou son test d'englobement est différent du nôtre en HA. **À creuser :
   c'est le seul endroit du CQF où notre modèle et le panneau se contredisent franchement.**
2. Notre division par 5 (avec un terme toujours nul) **imite par accident** un plafonnement que
   l'original obtient autrement, et le seuil `Score Minimum = 50` n'a donc pas la même échelle
   chez lui et chez nous.
3. Le `Mode Scoring` (⑥) remplace les filtres ①-⑤ au lieu de s'y ajouter : quand il est coché,
   seuls les poids comptent et les cases ①-⑤ ne servent qu'à **inclure ou non** une composante
   dans le score. C'est la lecture la plus économique, et elle est **testable** : désactiver un
   filtre devrait redistribuer son poids.

**Recommandation : ne pas toucher au score tant que ce point n'est pas tranché sur données.**
La V9 des flèches est à 100 % de précision et ne dépend pas du score ; c'est seulement la
frontière Fort/Moyen qui en dépend (MEMOIRE §5).

---

## 5. Ce que notre code n'implémente PAS

Classé par valeur opérationnelle.

### 🔴 Modules entiers absents

| module | réglages | pourquoi ça compte |
|---|---|---|
| **RANGEATOR** (détection, filtres, fin de range, style, alertes) | `Réglage 38-58, 73-78` + 10 inputs de style | Jamais traité (MEMOIRE §6.4). Probable source des `BREAK` / `ALLUMAGE` / `CONTINUATION` de l'API. 21 paramètres, dont 11 de détection déjà connus par la légende. |
| **BLACKOUT NO-TRADE** (module complet) | ~25 inputs, tous nommés | Nous codons « 14:30 et 16:00 Paris » **en dur**. L'original a : marge ±3 min, 2 fuseaux, 2 ouvertures de marché, 5 news récurrentes nommées, 2 créneaux personnalisés avec jour et « 1ère occurrence du mois », projection 24 h. |
| **TABLE UNIFIÉE** + **Feu de Confluence** | `Réglage 82` + 10 inputs | Le seuil 60 % est connu, les 29 votes aussi (MEMOIRE §6.3). Rien n'est codé. |
| **MONDAY HIGH LOW** | 4 inputs | Trivial à écrire (plus haut/bas du lundi, 26 semaines), jamais vu avant aujourd'hui. |
| **RONDATOR** (niveaux ronds) | `Réglage 28-29` + 9 inputs | Intervalle 100, 10 niveaux de part et d'autre, labels à gauche décalés de 150 barres, taille `small`. Purement graphique mais trivial. |

### 🟠 Sous-blocs absents dans des modules que nous avons

| où | quoi | valeur |
|---|---|---|
| Detector | atténuation des order blocks : `Réglage 72` (on/off), `59` = `Griser`, `60` = `1.5`, `80` = `% fixe`, `81` = `0.1`, `61`, `Couleur atténuée`, `62` | **à vérifier** : si « Griser » touche la *validité* d'un order block et pas seulement son rendu, cela change le Detector |
| Trendlines | `Activer Trendlines baissières (cassures short)` + `Couleur support ascendant` + `Couleur cassure baissière` | nous avons le miroir, mais pas l'interrupteur ni les couleurs dédiées |
| Signator | `Style des signaux`, `Taille des labels de signaux`, `Historique des labels de signaux` = 250 | cosmétique ; le `250` explique pourquoi les vieilles flèches disparaissent du graphique |
| Dashator | `TF[07] = 1 semaine` (présent mais décoché) | **prévoir 7 champs, pas 6** |
| Pivator | sous-titre `ALERTES PIVOTS` + `Activer Alertes Set 1/2/3` **toutes cochées** | nous n'émettons aucune alerte de pivot |
| Skin | `Design Table Volume`, `Design Table SuperTrader`, `Style Bordures`, `Accentuation Couleurs`, `Intensité (%)` (v30 ; supprimés depuis) | cosmétique, à ignorer |

### 🟢 Confirmé conforme chez nous

Detector (6 valeurs), Trendlines (6 valeurs), Fibonator, Pivator (type/lookback/largeur/3 sets),
Moyenator (sources, épaisseurs, remplissage, opacité), bloc Signator (`Seuil de Force = 18`,
`Mode de Lag = Normal`), les 5 filtres du CQF et leurs 9 constantes
(0.5 / 0.33 / 0.35 / 14 / 0.5 / 20 / 1 / ATR / 0.3), `Score Minimum = 50`.

---

## 6. Lacunes de la capture et incertitudes honnêtes

1. **Entre `25.png` et `26.png`** : l'en-tête du Set 3 du Pivator (vraisemblablement
   `SET 3 (…)`, `Enable Set 3`, `🎨 Personnaliser Couleurs Set 3`) n'apparaît sur aucune image.
   Ces lignes ne portent pas de numéro, la table de correspondance n'en souffre pas.
2. **Entre `29.png` et `30.png`** : un champ est coupé en haut de `30.png`. Comme les numéros
   51→58 sont tous présents, il s'agit au pire d'un libellé non numéroté.
3. **Entre `23.png` et `24.png`** : l'en-tête de section au-dessus de
   `--- TABLEAU VOLUME : TIMEFRAMES ---` n'est pas visible. Même remarque.
4. **Valeurs tronquées par l'interface TradingView elle-même** (aucun zoom ne les révélera, le
   texte est coupé dans le widget) : `Bottom …`, `Middle …`, `Traditio…`, `Americ…`, `Europe/…`,
   `Scalpin…`, `Flèches…`, `🚦 Feu …`, `🔵 Bleu…`, `Hebdo…`, `Clas…`, `Classiq…`, `5 minut…`,
   `15 min…`, `1 semai…`. Les valeurs complètes sont déductibles de la légende TradingView
   (`NOTES_LEGENDE_PARAMS.md`) : `Bottom Left/Right/Center`, `Middle Right`, `Traditional`,
   `America/New_York`, `Europe/Paris`, `Scalping Nasdaq (1-5m)`, `Flèches (défaut)`,
   `🔵 Bleu à gauche`, `Hebdomadaire`, `🏆 Classique Ultime`, `Classique (Original)`.
   **Je les marque comme déduites, pas comme lues.**
5. **`Position des Etiquettes = Vrai`** : lu deux fois, dans les deux versions. La légende v30
   donnait `Right` à cette position. Désaccord non résolu, sans impact.
6. **Couleurs** : relevées à l'œil sur des pastilles de 20 px. Les teintes (bleu / rouge / vert /
   orange / violet / noir / blanc / gris) sont fiables ; les codes hexadécimaux ne le seraient
   pas et ne sont donc pas donnés.

---

## 7. Ce qu'il faudrait demander à Jeremy ensuite

Par ordre de rentabilité, et formulé pour être exécuté sans réfléchir :

1. **Ouvrir la liste `Réglage 40` du Rangeator** (section `📦 RANGEATOR`, la liste qui affiche
   `Scalpin…`) et **capturer le menu déroulant ouvert**. On saurait combien de presets existent et
   comment ils s'appellent — donc sur quelles unités de temps le Rangeator est censé tourner.
2. **Passer la souris sur chaque ⓘ** du module `BLACKOUT NO-TRADE` et du `RANGEATOR`
   (`Réglage 61`, `Réglage 76/77`, `Feu de Confluence`, `FOMC`, `Monday High Low`,
   `Historique (semaines)`, `Disposition des cellules`, `Horizon de projection`) et capturer les
   **infobulles**. Ce sont des descriptions écrites par l'auteur : elles survivent souvent à
   l'anonymisation des libellés.
3. **Élargir la fenêtre de réglages** (la tirer vers la droite) et refaire une passe : les valeurs
   des listes déroulantes cesseraient d'être tronquées.
4. **Ouvrir les listes `Disposition des cellules` et `Côté des camps`** de la TABLE UNIFIÉE, menu
   déployé : cela nous dirait comment le Feu de Confluence est disposé, donc comment lire les
   captures de tableaux qu'on calibre.
5. **Capturer le Rangeator à l'écran** (un range visible, avec sa médiane et une cassure) +
   **exporter le CSV au même instant**, en 15 m sur MNQ1! ou MES1!. C'est la seule façon de caler
   les 11 valeurs de détection `22 / 0,34 / 3 / 8 / 1 / 1 / 0,45 / 0,12 / 20 / 61,8 / 0,3`.

---

*Document produit le 2026-10-12. Sources : captures 11–17 (ancienne version, noms réels) et
18–31 (dernière version, numéros). Recadrages de vérification :
`…/scratchpad/zoom/`. Aucun `.pine` modifié.*
