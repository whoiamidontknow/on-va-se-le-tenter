# Mémoire du projet — réplique d'Ephore Market Ultimate

> **À lire en premier à chaque nouvelle session.** (MAJ 02/10 : voir aussi section 9) Ce fichier résume ce qui a été fait, ce qui est
> validé, comment on travaille et ce qu'il reste à faire. Dernière mise à jour : 2026-10-01.

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
- **« Activer Filtre »** = **aucun signal sur les bougies qui contiennent 14:30 ou 16:00 (Paris)**,
  c'est-à-dire les annonces US.
- Résultats :
  - Singal (sans filtre) : 112/113, 5 en trop ;
  - Filtres (avec filtre) : 65/65, 5 en trop ;
  - 9348b : 16/16, 0 en trop.
- Tableau Signator (ancienne version voulue par Jeremy) : Heishinator / TBT / Tendance / Score / TF.
  - Tendance = clôture vs EMA50.
  - TF = « Actuel ».

## 6. Ce qui RESTE à faire / incertain
1. **TBT** : règle actuelle = ADX ≥ 18 (✔ OK / ⛔ Faible). Elle n'est calée que sur 2 cas (30/09 10:30 :
   MES OK, NQ Faible). « TBT » = probablement « Tick By Tick », mais le sens exact est inconnu.
   → Il faut 3 ou 4 screens du tableau de l'original au moment où TBT change, + le CSV au même instant.
2. **Signator** : il reste ~5 flèches en trop par jeu de données. Il n'y a jamais eu de screen de la ligne
   « Score » de l'original pour confirmer Moyen/Faible.
3. **Tableaux non faits** (pas de source publique trouvée sur ~1 600 scripts) :
   - INDICATOR | SIGNAL (SuperTrend, Moving Avg, VWAP, Lin Regress, CPR, ORB 15min, PDH/PDL) ;
   - TIMEFRAME | TREND | STRENGTH (STRENGTH = « pression acheteuse » 0-100 % par paliers de 25 %,
     selon la formation) ;
   - colonne **Dashator** (1m…1D bleu/rouge, logique différente du tableau TIMEFRAME).
   Il faut des exports multi-TF + screens au même instant.
4. Autres modules jamais traités ici : Climator / Climax, Detector (order blocks), Rangeator, Breakator.
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
