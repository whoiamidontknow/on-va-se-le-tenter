# Mémoire du projet — réplique d'Ephore Market Ultimate

> **À lire en premier à chaque nouvelle session.** Ce fichier résume ce qui a été fait, ce qui est
> validé, comment on travaille et ce qu'il reste à faire. Dernière mise à jour : 2026-10-02
> (sections 9 et 10 ajoutées ce jour-là).
>
> **Nouvelle session sur un nouveau compte ?** Lis ce fichier, puis **`PASSATION.md`** : il
> contient l'état de l'ENVIRONNEMENT (un vérificateur de syntaxe Pine installé mais non branché,
> aucun plugin actif, 8 agents maison qui dorment), ce qui survit au changement de compte, le
> travail de scratchpad définitivement perdu, et 5 nouveaux agents proposés dans
> `agents-proposes/`.

## 1. L'objectif
Reproduire en Pine Script, « à notre sauce mais identique à l'œil et en chiffres », l'indicateur
TradingView **fermé** *Ephore Market Ultimate* (formation d'Elio). On n'a pas son code : on retrouve
chaque module par **rétro-ingénierie** (scripts publics d'origine, exports CSV, screens).

**Tout est calculé sur graphique en Heiken Ashi** (confirmé par Jeremy) : les exports CSV
contiennent des valeurs HA, et les règles retrouvées ne valent que sur graphique HA.

## 2. Les fichiers qui comptent (dossier `on-va-se-le-tenter/`, branche `claude/install-superpowers-plugin-1EQcd`)

| Fichier | Rôle | État |
|---|---|---|
| `PORSCHEONARRIVE.pine` | Indicateur principal de Jeremy (V8). Version + journal en en-tête | **Ne pas modifier sans accord** |
| `TABLEAU.pine` | Indicateur séparé « Ephore Tableaux » (V8) : tableaux + flèches Signator | Chantier en cours |
| `TL_LAB.pine` + `TL_LAB_COMBOS.md` | Outil de diagnostic des trendlines | Terminé |
| `tools/` | Sources publiques d'origine + simulateurs Python | Référence |
| `EPHORE_METHODE.md` | Logique officielle tirée de la formation | Référence |

Anciens essais (ne plus utiliser) : `TL_FIGEE.pine`, `TL_PAIRES.pine`, `TRENDLINES.pine`, `SIGNATOR.pine`,
`REPLIQUE.pine`, `ZORADIK.pine`.

## 3. Règles de travail (demandées par Jeremy)
- **Commit + push après chaque modification**, sans redemander. Jamais `.DS_Store`.
- **PorscheOnArrive** : fichier unique `PORSCHEONARRIVE.pine`. Version et journal dans l'en-tête, à
  incrémenter à chaque MAJ majeure. **Ne jamais y intégrer un nouveau chantier sans son accord** :
  les tableaux ont été annulés de Porsche pour aller dans `TABLEAU.pine`.
- **TABLEAU.pine** : même principe (version + journal). On y ajoute les tableaux un par un.
- Jeremy préfère des **.pine** (pas de code dans des .md).
- Répondre en français, simplement. Il veut qu'on **utilise des agents en parallèle** pour les grosses
  recherches et qu'on **vérifie sur données** avant de lui envoyer du code.
- On ne peut pas compiler le Pine ici : toujours le dire, et lui demander le message rouge en cas d'erreur.

## 4. La méthode qui marche (à réutiliser pour chaque module)
1. **Chercher d'abord le script PUBLIC d'origine** grâce aux libellés exacts des réglages.
   L'auteur d'Ephore copie des scripts publics :
   - recherche web, puis l'API de titres `https://fr.tradingview.com/pubscripts-suggest-json/?search=…` ;
   - code récupéré avec `curl -s "https://pine-facade.tradingview.com/pine-facade/get/PUB;<id>/last"` ;
   - `www.tradingview.com` est injoignable en WebFetch, mais `fr.tradingview.com` marche.
2. Sinon, **caler sur données** :
   - Jeremy exporte des CSV (menu du graphique → « Exporter les données du graphique ») avec l'original,
     notre indicateur et l'indicateur **Volume** affichés (sinon pas de colonne volume) ;
   - les colonnes de l'original sont dans l'export (flèches, Moyenator…) ;
   - on simule en Python, on compare ligne à ligne, on teste des hypothèses.
3. Les **tableaux** ne s'exportent pas : seule la dernière bougie est visible, donc il faut des
   screens horodatés + le CSV exporté au même instant.
4. Toujours **couper le CSV à l'heure du screen**. Méfiance avec le début des fichiers (chauffe des
   EMA) : les colonnes « Moyenator 1/2 » de l'original donnent les EMA50/60 exactes.

## 5. Ce qui est VALIDÉ

### Heishinator (couleur des bougies, dans PorscheOnArrive)
SHA = a·ohlc4 + (1−a)·SHA[1] (a = 0.42 si TF < 30 min, sinon 0.44) ; haussier si SHA > EMA(close, 33).
Validé à l'œil par Jeremy.
**Pour les flèches Signator**, la formule exacte est **EMA(ohlc4, 4) > EMA(ohlc4, 32)** : elle retrouve
138 des 139 changements imposés par les flèches. Elle n'est utilisée que dans `TABLEAU.pine`.

### Moyenator
EMA50 et EMA60 du close (+ remplissage).

### Trendlines (PorscheOnArrive V2 → V8, `TL_LAB.pine`) — **validées par Jeremy sur toutes les TF**
- Source : script public **« Trendlines » d'Amphibiantrading** (MPL 2.0), modifié par Ephore :
  - 2e point = **pivot confirmé** ;
  - droite revérifiée **à chaque bougie** ;
  - support ascendant en miroir.
- Réglages : pivots 10/10, tampon 0.1 %, 3 touches minimum, nouvelle ancre après 100 barres, 1 ligne par côté.
- Ancre = pivot si aucune ancre, si le pivot est plus extrême, ou si l'ancre a plus de 100 barres.
  La droite ancre → dernier pivot est validée si aucune mèche ne dépasse la droite (+ tampon) depuis
  l'ancre et qu'elle a au moins 3 touches. Elle reste affichée, même cassée, jusqu'à la suivante.
- **Points de cassure** : la **mèche** dépasse la droite de plus que le tampon (vérifié : point rouge
  MES 15m à 07:00). Un seul point haussier + un seul point baissier à la fois. Forme, taille et
  couleur sont réglables.
- 38/38 en simulation (MES + NQ, 1m à 4h).

### Pivots (PorscheOnArrive V5 → V8)
- 3 sets : Annuel (rouge), Mensuel (noir), Weekly (bleu).
- Tracés en `xloc.bar_time`, fuseau Europe/Paris :
  - weekly : lundi 00:00 → lundi suivant 00:00 ;
  - mensuel : → 1er du mois suivant 11:00 ;
  - annuel : du 2 janvier → au 4 janvier de l'année suivante, étiquettes en fin de ligne.
- Validé par Jeremy.

### Tableau principal (`TABLEAU.pine`) — **validé par Jeremy (« tout coïncide »)**
- Source : script public **« SuperTrader Trend Analysis and Trade Study Dashboard » de Midgar-**
  (copie dans `tools/midgar_supertrader_dashboard_source.pine`).
- Formules :
  - Trend = VIDYA ± ATR200 ;
  - Bull/Bear Score non complémentaires (EMA50/200, RSI 30/70, Bollinger) ;
  - YoYo = distance au SMA10 ;
  - Gap Prob pondéré ;
  - MACD 10m 20/40/5 (SUPERBULL / Basing / Bullish / Bearish) ;
  - TF PA en 1/5/15 min ;
  - volumes Melt / Low Vol / Normal / Elevated / Unusual ;
  - VIX.
- Vérifié au centième sur la bougie HA **en cours** : RSI 60.67, CCI 134.23, YoYo 0.08 %.

### Signator — flèches + tableau (`TABLEAU.pine` V8), ~96 % d'accord
- **Flèche** : 2e bougie du nouvel état Heishinator (EMA(ohlc4,4) vs EMA(ohlc4,32)), avec en plus :
  - **ADX(14,14) ≥ 18** (« Seuil de Force ») ;
  - **clôture du bon côté de l'EMA50** ;
  - **conviction** : clôture ≥ 0.3 ATR au-delà de la bande EMA50/EMA60 **ou** volume ≥ SMA20.
- **Score** = moyenne des **5 filtres continus** du Candle Quality Filter × 100 :
  - structure = (min(corps/range / 0.5, 1) + (1 − min(mèche depuis le close / 0.35, 1)) + min(position du close / 0.67, 1)) / 3 ;
  - momentum = min(range / (0.5·ATR14), 1) ;
  - volume = min(vol / SMA20, 1) ;
  - gap = min(|open − close[1]| / (0.3·ATR14), 1) ;
  - engulfing complet = 0 ou 1 (toujours 0 en HA, donc score max 80).
- Classement : **Fort ≥ 50** (Score Minimum), **Moyen ≥ 18** (Seuil de Force), Faible en dessous.
  Classe Fort/Moyen de l'original retrouvée sur 192/193 flèches.
- **« Activer Filtre »** = le module **BLACKOUT NO-TRADE**. ⚠️ La description qui figurait ici
  (« les bougies qui *contiennent* 14:30 ou 16:00 ») était **fausse** et détruisait 21 bonnes
  flèches : l'original teste l'heure d'**ouverture** de la bougie. **Voir §12**, qui fait foi.
- Résultats :
  - Singal (sans filtre) : 112/113, 5 en trop ;
  - Filtres (avec filtre) : 65/65, 5 en trop ;
  - 9348b : 16/16, 0 en trop.
- Tableau Signator (ancienne version voulue par Jeremy) : Heishinator / TBT / Tendance / Score / TF.
  - Tendance = clôture vs EMA50.
  - TF = « Actuel ».

### Flèches Signator — où on en est vraiment (mesuré le 10/10)

| source de vérité | exactes | en trop | manquées | rappel | précision |
|---|---:|---:|---:|---:|---:|
| CSV Singal (filtre OFF) | 118 | 5 | 1 | 99.2 % | 95.9 % |
| CSV Filtres (filtre ON) | 70 | 5 | 0 | 100 % | 93.3 % |
| API 15m (bandes d'annonces appliquées) | 23 | 2 | 0 | 100 % | **92.0 %** |
| API 2m | 19 | 0 | 1 | 95.0 % | **100 %** |

### FLÈCHES — PRÉCISION 100 % le 12/10 (Signator V9)

**Ce qui manquait : la bougie du signal doit SATURER un terme du Candle Quality Filter.**
La V8 notait le momentum et la position de clôture dans le score, sans jamais exiger qu'ils
soient atteints. L'original exige que l'un des deux le soit.

```
V9 = V8  ET  ( range >= 0.5 × ATR14   OU   cpos >= 0.67 )
```

**Aucune constante nouvelle** : 0.5·ATR est déjà celle de `sg_sMom`, et 0.67 celle de
`sg_sStr`. C'est une relecture du filtre existant, qui passe de « noté » à « doit être
franchi ». Ce n'est donc pas un seuil ajusté aux données.

| corpus | V8 | V9 |
|---|---|---|
| Ajustements groupe 4 (155 flèches, MES+NQ, 7 TF, ~9000 barres) | 153/6/2 — précision 96.2 % | **153/0/2 — précision 100 %** |
| `~/Ephore/Singal` | 118/5/1 | 118/**3**/1 |
| `~/Ephore/Filtres` | 70/5/0 | 70/**3**/0 |
| API terminal 15m | 23/6/0 | 23/**5**/0 |

Aucune perte de rappel nulle part. Les 3 « en trop » restants sur Singal et Filtres sont les
flèches du **groupe 2** (28/09 16:15, 25/09 09:00, 29/09 18:00) : différences de version, pas
des erreurs.

**Solidité.** Deux recherches indépendantes ont convergé dessus le même jour : l'une sur les
variables de contexte, l'autre sur la forme de la conviction (~186 500 combinaisons). Les
6 faux positifs de la V8 occupaient **6 des 7 plus petits `range/ATR`** sur 161 événements —
p = 3.2e-10. Validation croisée MES↔NQ et par groupes d'unités de temps : le seuil 0.50
ressort indépendamment à chaque découpage.

**Effet au niveau Fort, mesuré après coup** (l'agent ne l'avait pas fait) : V8 140/3/10
(précision 97.9 %) → V9 **140/2/10** (précision 98.6 %). Aucune régression, un faux positif de
moins. La V9 est donc sûre aux deux niveaux. Le chantier du Score reste entier : les
10 manquées sont des cas de frontière Fort/Moyen, et le groupe 4 ne contient que 6 flèches
Moyen sur 176 — trop peu pour caler ce seuil.

**Les 2 manquées restantes** sont des échecs de conviction de peu, sans rapport avec la V9 :
MES 5m 08/10 07:05 (dBand 0.28 contre 0.30, volume 0.89 contre 1.00) et NQ 240 31/07 08:00
(dBand 0.20, volume 0.69).

**Pistes mortes, ne pas refaire** : plage de séance dans les deux fuseaux (600 fenêtres —
46 % des vraies flèches sont hors 09:00-20:00 Paris, donc le `9 0 … 20 0` de la légende ne
concerne PAS les flèches) ; jour de la semaine ; volume rapporté au même créneau horaire
(fait passer les faux de 6 à 17) ; distance au plus haut/bas ; délai minimum entre flèches ;
régime ATR ; plancher de volume sur la clause dBand (supprime les faux mais tue 25 vraies).

Implémenté dans `EPHORE_COMPLET.pine` V2, réversible par input. Scripts :
`tools/ephore_api/sim_signator_conviction_v9.py` et `sim_signator_range_atr.py`.

**LE DÉCLENCHEMENT DES FLÈCHES EST RÉSOLU (10/10).** Mesuré sur le groupe 4 des 14 exports
« Ajustements », **sans distinguer Fort et Moyen** : **153 exactes, 6 en trop, 2 manquées** sur
155 flèches — rappel 98.7 %, précision 96.2 %. Vérifié deux fois.

Et les paramètres de la V8 sont **l'optimum exact** d'une grille de 111 combinaisons :

| seuil ADX | en trop | manquées |
|---:|---:|---:|
| 16 | 35 | 2 |
| 17 | 20 | 2 |
| **18** | **6** | **2** |
| 19 | 4 | 9 |
| 20 | 3 | 29 |

La conviction (`dBand >= 0.3` OU `volume >= SMA20`) supprime **37 faux positifs pour 2 manquées**.
La « 2e bougie du nouvel état » est la seule valeur possible : la 1re et la 3e donnent 0 exacte.

**Ce qui reste n'est PAS le déclenchement, c'est la frontière Fort/Moyen**, donc le score CQF :
au niveau Fort on tombe à 142/5/8. Et le problème est concentré sur **NQ 1D, où la colonne
Volume est vide** — le score y est donc faussé par construction. Hors 1D, le niveau Fort donne
**134 exactes / 2 en trop / 6 manquées** (précision 98.5 %).
Seuils de score comparés : 42 → 11 erreurs, 46 → 12, 50 → 13. L'écart porte sur 11 cas : trop
peu pour trancher sans surajuster. Le groupe 4 ne contient que **6 flèches Moyen sur 176**.

Autre fait mesuré : **le groupe 4 n'applique PAS le filtre annonces.** L'appliquer dégrade le
résultat (138/6/17 contre 153/6/2) car 15 de ses flèches tombent sur 14:30 ou 16:00. C'est le
groupe 2 qui filtre.

**RENVERSEMENT DU 10/10 (lot « Base 10:10/Ajustements ») — à lire avant tout le reste de
cette section.** Jeremy a **4 versions d'Ephore sur son graphique**, donc chaque export contient
**4 jeux** de colonnes `Signal Long/Short Fort|Moyen`. Les groupes 1 et 3 sont vides ; le
**groupe 2** et le **groupe 4** portent les flèches. Mesuré sur 14 fichiers (MES + NQ, 7 unités,
données jusqu'au 09/10) :

- le **groupe 4 émet 176 flèches**, le **groupe 2 en émet 161**, et le groupe 2 est un
  **sous-ensemble strict** du groupe 4 (aucune flèche en propre, 161/176 = 91.5 % d'accord) ;
- **11 des 15 flèches que le groupe 2 retire (73 %) tombent sur une heure d'annonce**, contre
  26 % des 161 conservées — enrichissement d'un facteur 3. C'est donc une différence de
  **réglage du filtre**, pas de code ;
- notre règle V8 confrontée à chaque version séparément :

| version | exactes | en trop | manquées | rappel | précision |
|---|---:|---:|---:|---:|---:|
| groupe 2 | 130 | 18 | 7 | 94.9 % | 87.8 % |
| **groupe 4** | **144** | **4** | **7** | **95.4 %** | **97.3 %** |

→ **Notre V8 reproduit la version du groupe 4**, avec 4 faux positifs au lieu de 18.
Les « faux positifs » traqués jusqu'ici (25/09 09:00 MES60, 29/09 18:00 NQ15, 23/09 16:00 MES60)
figurent **parmi les 15 flèches que le groupe 2 retire** : ce ne sont pas des erreurs de notre
règle, c'était une comparaison à la mauvaise version. **Toujours préciser à quel groupe de
colonnes on se compare.**

**Correction précédente du 10/10 (lot « Base 10:10/base »), désormais dépassée :** les 3 flèches présentées jusqu'ici comme
« retirées par la nouvelle version, donc différence de version » sont en réalité **de vrais faux
positifs de notre règle**. Preuve directe : le réexport MES 60m du 10/10, qui couvre le
2026-09-25 09:00, contient bien la barre et l'original n'y met **aucune flèche**
(`Signal Long Fort = 0`, `Signal Short Fort = 0`). Comme on se compare à la version actuelle,
l'argument « différence de version » n'excuse rien.

**Aucun correctif par seuil n'existe** (analysé sur 203 détections, 188 vraies / 15 fausses) :
les faux positifs n'ont pas de signature commune — `dBand` de −0.01 à 2.59, volume de 0.18 à
8.28. Dans la zone où ils se concentrent (`dBand` 0.3–0.5 porté sans volume) on compte
**19 vraies pour 7 fausses** : relever le seuil détruirait presque 3 fois plus de bonnes flèches
qu'il n'en supprimerait de mauvaises. L'ingrédient manquant n'est pas un réglage des variables
actuelles, c'est une variable absente.

**Les erreurs résiduelles sont expliquées, pas mystérieuses :**
- Côté CSV, **3 des 5 « en trop » sont les flèches que la nouvelle version d'Ephore a retirées**
  (MES15 09-28 16:15, MES60 09-25 09:00, NQ15 09-29 18:00, cf. §10). Ce sont des différences de
  version, pas des défauts de règle.
- Côté API, **4 des 6 « en trop » tombent exactement dans les bandes d'annonces** du terminal web
  (09-24 16:00, 09-25 15:30, 09-28 14:30, 09-29 09:00). En appliquant les `bande_verticale` de
  l'API, la précision 15m passe de **79.3 % à 92.0 %** sans perdre un seul rappel.
  → Confirme §9 par la mesure : le terminal web bloque **4 horaires** (09:00, 14:30, 15:30,
  16:00) alors que TradingView n'en bloque que **2** (14:30, 16:00). Notre V8 implémente la
  version TradingView, ce qui est correct pour les flèches de Jeremy.
- **Hypothèse testée et ÉCARTÉE** : les faux positifs ne sont pas des marqueurs d'un autre type.
  L'API émet aussi `v7a:ALLUMAGE` (21 en 15m) et `v7c:CONTINUATION` (3), mais **un seul** de nos
  faux tombe sur un ALLUMAGE ; les autres ne correspondent à rien.

**Il ne reste donc que 2 vrais faux en 15m** (09-25 18:45 score 46.2 ; 09-29 18:00 score 55.1)
**et 1 manquée en 2m**. Le module est à ~96 %. Pour aller plus loin il faut des **données
neuves** (exports de la nouvelle version sur des périodes déjà couvertes), pas plus de recherche :
~25 variantes ont déjà échoué (§10).

### Simulateur Signator — RECONSTRUIT le 10/10 : `tools/signator_sim.py`
Les scripts d'origine (`signator_final/*.py`, `signator_v9/NOTES.md`) vivaient dans un
scratchpad `/tmp` et sont **perdus**. Le simulateur a été réécrit depuis `TABLEAU.pine` V8 et
committé — **ne plus jamais laisser ce code hors du dépôt**.
```bash
python3 tools/signator_sim.py          ~/Ephore/Singal    # filtre OFF
python3 tools/signator_sim.py --filtre ~/Ephore/Filtres   # filtre ON
```
Résultats du 10/10, qui reproduisent la V8 :
- Singal (filtre OFF) : **118/119 = 99.2 % de rappel**, 5 en trop, 1 manquée, 1 écart de classe.
- Filtres (filtre ON) : **70/70 = 100 % de rappel**, 5 en trop.
- **Preuve nouvelle** : sur les mêmes fichiers *sans* le filtre, les faux positifs passent de
  **5 à 10**. Le filtre « pas de flèche sur une bougie contenant 14:30 ou 16:00 (Paris) » n'est
  donc plus une hypothèse, il est mesuré.
- Les écarts résiduels sont **exactement** ceux de §10 : les 3 flèches retirées par la nouvelle
  version d'Ephore (MES15 09-28 16:15, MES60 09-25 09:00, NQ15 09-29 18:00) et la manquée
  NQ240 07-31 08:00. Inutile de les rechercher : ce sont des différences de version, pas des
  défauts de règle.
- Détail qui fait gagner du temps : les colonnes `Moyenator 1/2` de l'original sont utilisées
  comme EMA50/60 exactes (§4.4), ce qui supprime toute chauffe d'EMA et permet de descendre le
  warmup de 300 à 120 barres — soit ~40 flèches évaluables en plus sur des fichiers de 557 barres.

## 6. Ce qui RESTE à faire / incertain
1. **TBT** — piste web MORTE (10/10) : **0 occurrence** de « TBT » dans les 2,4 Mo de sources
   du terminal, 0 dans l'API, **0 post sur le forum public** ; « Seuil de Force » introuvable
   aussi. Le terme n'existe que dans nos propres fichiers : libellé interne jamais commenté, ou
   mal lu à l'origine. Ne plus chercher côté web. Règle actuelle = ADX ≥ 18 (✔ OK / ⛔ Faible),
   calée sur 2 cas seulement (30/09 10:30 :
   MES OK, NQ Faible). « TBT » = probablement « Tick By Tick », mais le sens exact est inconnu.
   → Il faut 3 ou 4 screens du tableau de l'original au moment où TBT change, + le CSV au même instant.
2. **Signator** : il reste ~5 flèches en trop par jeu de données. Il n'y a jamais eu de screen de la ligne
   « Score » de l'original pour confirmer Moyen/Faible.
3. **Tableaux — PERCÉE DU 10/10**, voir `tools/ephore_api/NOTES_TABLEAUX.md`. Le Feu de
   Confluence les décompose exactement : `GROUPES_FEU` du terminal web donne « Colonne temps
   6 voix + Bloc SuperTrader 10 + Colonne SIGNAL 7 + Tendances multi-unités 6 » = **29**, soit
   les 29 votes de l'API. Donc `feux.votes` est une **cible numérique** pour valider nos
   répliques. Le contenu des 3 tableaux est lu sur captures (valeurs, vocabulaire d'états,
   échelle de couleurs, paliers de 25 % du STRENGTH). Attention : `INDICATOR | SIGNAL` dépend
   de **l'unité de temps du graphique** (Lin Regress = Bull en 15m et Bear en 2m sur la même
   capture) — à caler par TF. Et **la source de données qui manquait existe** : la catégorie
   publique `le-mur-des-victoires` du forum (~490 sujets) contient des centaines de captures
   horodatées, téléchargeables sans compte, dont beaucoup citent le Feu en clair (« feu à 82 %
   long »). Détail des tableaux :
   - INDICATOR | SIGNAL (SuperTrend, Moving Avg, VWAP, Lin Regress, CPR, ORB 15min, PDH/PDL) ;
   - TIMEFRAME | TREND | STRENGTH (STRENGTH = « pression acheteuse » 0-100 % par paliers de 25 %,
     selon la formation) ;
   - colonne **Dashator** (1m…1D bleu/rouge, logique différente du tableau TIMEFRAME).
   Il faut des exports multi-TF + screens au même instant.
4. Autres modules : **Climator / Climax PREMIÈREMENT CALÉ le 10/10** (91 % rappel / 90 %
   précision en 15m, 98 % / 92 % en 2m ; règle, pistes épuisées et prochaine étape dans
   `tools/ephore_api/NOTES_CLIMAX.md`). Piste n°1 pour progresser : **5 des 14 faux positifs
   sont de simples erreurs de calage temporel** (un climax de l'original est à ±3 barres), donc
   une règle de déduplication sur la fenêtre de 3 barres en supprimerait ~35 % sans nouvelle
   donnée. Restent jamais traités : Detector (order blocks), Rangeator, Breakator.
5. Jeremy utilise la **dernière version d'Ephore** depuis le 30/09 au soir : certaines valeurs ont pu bouger.

## 7. Où sont les données (dossier `~/Ephore/`)
- `Singal/` (sic) : 14 exports HA avec volume, MES + NQ, de 1 à 240 min, filtre Signator **décoché**.
- `Filtres/` : 7 exports HA avec volume, filtre **coché** (dernière version d'Ephore).
- `Trendlinehelper/` : 15 exports HA (trendlines), MES + NQ, de 1 à 240 min.
- Racine : nombreux exports `CME_MINI_*.csv`. `15_9348b` = MES 15m avec volume, 1053 bougies.
  Les 4 gros MES1! 15m de juillet n'ont pas de volume.
- `formation_txt/` : textes de la formation. `formation_txt/videos/` : transcriptions (02/10, whisper,
  horodatées) des 3 vidéos de `Formation/` : installation de l'indicateur, réglage du Climator, capture.
  Elles n'expliquent aucun calcul (ni TBT, ni score). Elles confirment seulement : graphique **Heiken Ashi**,
  15m + 2m (scalping Nasdaq, MNQ1!), et les 5 alertes de l'original : Signal Long Fort, Short Fort,
  Long Moyen, Short Moyen, Trendline Breakout.
  Outil : `~/whisper-env/bin/python` (mlx_whisper + ffmpeg inclus).
- `facecode_transcripts/`, `Hugo tournier facecode/` : SANS RAPPORT avec Ephore (formation sur l'apparence).
- Colonnes utiles des exports : `Signal Long/Short Fort|Moyen` (flèches de l'original : prendre la
  **dernière** paire non vide), `Moyenator 1/2` (EMA50/60 exactes), `Climax BUY/SELL`,
  `Signator Long/Short` (nos flèches), `Volume`.

## 8. Pièges connus
- Pine v6 :
  - pas de `na()` sur un booléen ;
  - pas de déclaration de fonction dans un bloc local ;
  - les listes `options=[...]` doivent être littérales (pas de variable) ;
  - une comparaison avec `na` vaut false, donc tester `na(x)` d'abord ;
  - `max_bars_back` est nécessaire pour les boucles sur l'historique.
- Lignes très loin dans le futur : `xloc.bar_index` est limité à 500 barres, `xloc.bar_time` marche.
- Heures : les CSV sont en heure de Paris ; le tableau TL_LAB affiche l'heure de la bourse (Chicago, −7 h).
- Les agents en arrière-plan peuvent se bloquer (watchdog 600 s) : vérifier qu'ils ont produit
  quelque chose, sinon reprendre à la main.

## 9. Source de vérité indépendante : l'API publique du terminal web d'Ephore (trouvée le 02/10)
- `https://app.ephore-market.com/api/vitrine/instantane` : page de démonstration publique, sans connexion.
  Elle renvoie, pour XYZ100 (Nasdaq) en 15m et 2m, 1500 bougies. Chaque bougie contient :
  - o/h/l/c en **Heiken Ashi** ;
  - cr/hr/lr, les valeurs réelles ;
  - le volume.

  Elle renvoie aussi les objets des indicateurs :
  - état du Heishinator par bougie ;
  - flèches Signator `sig_lf` / `sig_sf` avec leur niveau (FORT…), signaux v7a « ALLUMAGE » et
    v7c « CONTINUATION » (nouvelle version) ;
  - trendlines `trl_res` / `trl_sup` (pente par barre, cassée oui/non) ;
  - climax (HIGH / PREMIUM), Moyenator, Detector, Rangeator, Pivator, fib_75 ;
  - **bandes rouges d'annonces** ;
  - « Feu de Confluence » : 29 votes, seuil 60 %.
- Une copie (02/10) est dans `tools/ephore_api/api_vitrine_instantane.json`, avec le script de test `sig_api.py`.
  **Ne pas interroger l'API en boucle** : une copie de temps en temps suffit.
- Ce qu'elle a confirmé :
  - **Heishinator = EMA(ohlc4,4) > EMA(ohlc4,32) : 2600/2600 bougies (100 %)**, en 15m et 2m ;
    l'ancienne formule 0.42/0.44 vs EMA33 fait 99.5 % ;
  - Moyenator 1 = EMA50 du close HA (écart 0.005) ;
  - Signator V8 : 15m 22/22 flèches, 7 en trop ; 2m 19/20, 0 en trop ;
  - aucune vraie flèche dans les bandes d'annonces.
- **Annonces** : sur le terminal web, les bandes rouges couvrent 09:00, 14:30, 15:30 et 16:00 (Paris),
  à ±2 min en 2m. Sur TradingView (exports Filtres), l'original garde ses flèches de 09:00 et de 15:30 :
  le filtre TradingView ne bloque que **14:30 et 16:00** (c'est ce que fait la V8).

## 10. Versions de l'original (constat du 02/10)
- **Ephore a changé de version le 30/09 entre 11:04 et 11:37.** Les exports d'avant ont les mêmes OHLC
  que ceux d'après, mais les flèches diffèrent. Exports **ancienne version** : racine (dont 9348b, 3eac1),
  Trendlinehelper. Exports **nouvelle version** : Singal (11:37), Filtres (23:31).
- La nouvelle version retire 3 flèches (MES15 09-28 16:15 S, MES60 09-25 09:00 L, NQ15 09-29 18:00 S).
  Elle ajoute 2 flèches Moyen (NQ240 07-16 08:00, NQ60 09-17 00:00). L'ancienne n'affichait aucune
  Moyen (761 Fort, 0 Moyen).
- Reste chez nous (V8) : ces 3 flèches + 4 autres en trop et 1 manquée (NQ240 07-31 08:00, où la conviction
  échoue de peu). Aucune règle robuste ne les supprime : ~25 variantes testées (détail dans le
  scratchpad signator_v9/NOTES.md de la session du 02/10).
- Pour aller plus loin : des exports de la **nouvelle** version sur des périodes déjà couvertes par
  d'anciens exports (pour avoir plus de flèches retirées), ou le journal des changements d'Ephore.

---

## 11. LA PIERRE DE ROSETTE DES RÉGLAGES (12/10) — à lire avant toute hypothèse sur un paramètre

Jeremy a fourni les panneaux de réglages de **deux** versions d'Ephore : une ancienne
où les paramètres portent leurs **vrais noms**, et la dernière où le créateur les a
anonymisés en « Réglage 1 » à « Réglage 82 » pour empêcher la copie. Les deux listent
**les mêmes champs dans le même ordre de déclaration**. Tout est donc décodable, et la
table complète est dans **`tools/NOTES_REGLAGES_ROSETTE.md`**.

Deux preuves que la table est complète : les numéros vont de 1 à 82 **sans aucun trou**,
et l'ancien panneau reconstitue **exactement les 67 valeurs** de la légende TradingView,
dans l'ordre et sans décalage.

### Ce que ça CORRIGE dans ce document

1. **`22 0,34 3 8 1 1 0,45 0,12 20 61,8 0,3` est le RANGEATOR, pas le Signator.**
   Certitude : ce sont les Réglages 41 à 51, sous l'en-tête `RANGEATOR · DÉTECTION`.
   Conséquence sur §5 : les tests qui « réfutaient » ces valeurs ne réfutaient rien,
   ils appliquaient au Signator les réglages d'un autre module. **Erreur de catégorie,
   pas falsification.** Le `61,8` n'est pas un niveau de Fibonacci d'entrée sur repli.

2. **Le Seuil de Force à 18 est CONFIRMÉ par le panneau** (`Réglage 5 = 18`). Ce n'était
   jusqu'ici qu'un optimum trouvé sur grille ; c'est désormais une valeur lue.

3. **Il n'y a pas de plage de séance 09:00–20:00.** Ce que la légende montrait ainsi,
   c'étaient les ouvertures de marché et les créneaux personnalisés du Blackout, tous
   **décochés**. Confirme par le panneau la piste morte déjà mesurée.

4. **`Réglage 82 = 60` est le seuil du Feu de Confluence** — le même 60 % que l'API.
   Et l'en-tête `… Large 8 60 …` n'était pas des EMA 8/60, c'était ce bloc.

5. **Il n'existe aucun input de période pour le Moyenator**, dans aucune version :
   les EMA 50 et 60 sont codées en dur dans l'original. Inutile de les chercher.

6. **Le tableau Signator a été supprimé** de la dernière version, et `INDICATOR|SIGNAL`
   et `TIMEFRAME|TREND` ont **fusionné** en une TABLE UNIFIÉE. Les captures prises avant
   et après la bascule du 30/09 ne décrivent donc pas le même objet.

### Les modules entiers qu'on ignorait

- **`BLACKOUT NO-TRADE`** — entièrement en clair, aucun paramètre anonymisé. Résolu et
  implémenté, voir §12.
- **`RANGEATOR`** — 21 réglages plus 10 inputs de style. Jamais calibré : ses colonnes
  sont vides dans tous les exports.
- **`MONDAY HIGH LOW`** — 4 inputs, historique 26 semaines. Jamais vu auparavant.
- **`TABLE UNIFIÉE`** — avec `Points = 8`, `Disposition des cellules` et `Côté des camps`.

### La tension non résolue, à ne pas enterrer

Le panneau donne **4 poids à 25 %** et **aucun poids pour l'Engulfing**, qui est un filtre
dur coché. Or notre simulation mesure qu'une pondération 4×25 % dégrade le résultat. Et
surtout : si l'Engulfing était un vrai veto, il tuerait **tous** les signaux en Heiken Ashi,
où l'englobement vaut toujours 0 — ce n'est pas le cas. Lecture la plus économique : le
`Mode Scoring` **remplace** les filtres au lieu de s'y ajouter. **Ne pas toucher au score
tant que ce n'est pas tranché sur données** ; la V9 des flèches est à 100 % de précision
et n'en dépend pas.

---

## 12. BLACKOUT NO-TRADE — résolu et implémenté (12/10)

**Un bug réel corrigé.** Notre filtre testait si la bougie **contient** 14:30 ou 16:00.
L'original teste si la bougie **ouvre** à cette heure. Mesuré sur les 176 flèches :
« contient » en bloque **30**, « ouvre à » en bloque **9**. On détruisait 21 bonnes flèches
dès que la case était cochée — Jeremy l'a toujours laissée décochée, le bug n'a jamais mordu.
Preuve la plus nette : l'original conserve 14 des 15 flèches journalières, alors qu'un jour
contient forcément 14:30.

**Règle validée**, mêmes paramètres sur deux jeux de données indépendants :

```
fuseau America/New_York ; on teste l'heure d'OUVERTURE de la bougie
  08:30 ET  (données US : CPI, PPI, Retail, GDP, PCE, NFP, Jobless) — tous les jours
  10:00 ET  (données : ISM, JOLTS, UMich)                           — tous les jours
  marge ±3 min
DÉCOCHÉS chez Ephore : ouverture Europe 09:00, ouverture US 09:30 ET, FOMC, créneaux persos
```

Accord : **13 retraits corrects, 0 à tort, 6 non expliqués → précision 100 %.**

Les ouvertures de marché sont décochées **par mesure, pas par supposition** : 3 flèches sont
conservées à 15:30 Paris et 2 à 09:00. **C'est là que le graphique de Jeremy diffère du
terminal web**, qui lui affiche bien 4 bandes rouges (§9). Le panneau dit ce que le créateur
a *écrit* ; chaque copie exécute ses propres réglages.

Le code exprime les heures en fuseau New York, donc **le changement d'heure se règle tout
seul** : du 25 au 31 octobre 2026, 08:30 ET tombe à 13:30 Paris. C'est précisément la semaine
que nos données ne couvrent pas — elle est gérée sans qu'on ait eu à la mesurer.

**Les 6 retraits restants ne sont pas un sujet d'horaire** : leurs heures sont toutes
différentes et non récurrentes. Ils ont une signature de volume (4 sur 5 mesurables ont
vol/SMA20 < 0,50 ; p = 0,0012), mais le plancher de volume reste **non viable** — il tue plus
de bonnes flèches qu'il n'en retire. Piste morte confirmée pour la troisième fois.

### Ce que le panneau ne permet PAS de conclure

La marge de ±3 min **n'est pas contrainte par les données** : toute valeur de 0 à 9 donne le
même résultat, la flèche conservée la plus proche d'un créneau étant à 10 minutes. La valeur 3
vient du panneau, pas d'une mesure. De même, NFP, Jobless, FOMC et les créneaux personnalisés
sont réglés **par absence de contre-exemple**, pas par des cas positifs.

### Leçon de méthode, valable au-delà de ce module

**Quand un panneau de réglages et une mesure se contredisent, on garde la mesure.** Le cas du
grisage du Detector l'illustre : le panneau indique « 1,5 % fixe », mais ce seuil griserait
16 des 19 boîtes observées alors qu'une seule l'est. Soit le terminal web est réglé autrement,
soit « 1,5 % » mesure autre chose. Le code garde donc la règle vérifiée par défaut et expose
la structure du vrai réglage pour pouvoir élargir.
